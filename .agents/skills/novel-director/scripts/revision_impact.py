"""Read-only, typed story dependency impact analysis; not a causal simulator."""
from __future__ import annotations
from collections import defaultdict, deque
from pathlib import Path
import json
from evidence_audit import read_utf8, digest

COLLECTIONS = {
    'canon': 'facts', 'characters': 'characters', 'versions': 'versions',
    'events': 'events', 'chapters': 'chapters', 'clues': 'clues',
    'trips': 'trips', 'presences': 'presences', 'artifacts': 'artifacts',
    'rewrites': 'rewrites', 'knowledge': 'knowledge', 'memory_docs': 'memories',
    'world_rules': 'rules', 'story_units': 'units', 'relationships': 'moments',
    'scenes': 'scenes',
}
# These are reference dependencies, not assertions that A physically causes B.
REF_FIELDS = {
    'character_id': 'characters', 'traveler_id': 'characters', 'pov': 'characters',
    'actor_ids': 'characters', 'pair_ids': 'characters', 'character_ids': 'characters',
    'chapter_id': 'chapters', 'learned_chapter': 'chapters', 'reveal_chapter': 'chapters',
    'setup_chapter': 'chapters', 'payoff_chapter': 'chapters',
    'first_chapter': 'chapters', 'last_chapter': 'chapters',
    'fact_id': 'canon', 'fact_ids': 'canon', 'rule_ids': 'world_rules',
    'event_id': 'events', 'event_ids': 'events', 'cause_event_id': 'events',
    'caused_by': 'events', 'trip_id': 'trips', 'via_trip': 'trips',
    'artifact_id': 'artifacts', 'preserved_artifact_ids': 'artifacts',
    'clue_ids': 'clues',
    'history_id': 'versions', 'origin_history_id': 'versions',
    'source_history_id': 'versions', 'destination_history_id': 'versions',
    'from_history_id': 'versions', 'to_history_id': 'versions',
}
STATUSES = {'confirmed', 'planned', 'hypothesis', 'draft', 'published', 'approved', 'unknown'}


def _load(project: Path, name: str, default: dict) -> dict:
    p = project / name
    if not p.exists() and not p.is_symlink():
        return default
    text, _ = read_utf8(p)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f'{name} 根节点必须是对象')
    return data


def graph(project: Path) -> tuple[dict, list, list]:
    nodes, edges, diagnostics = {}, [], []
    for kind, field in COLLECTIONS.items():
        records = _load(project, kind + '.json', {field: []}).get(field, [])
        if not isinstance(records, list):
            raise ValueError(f'{kind}.{field} 必须是数组')
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get('id'), str) or not record['id']:
                raise ValueError(f'{kind} 对象缺少字符串 ID')
            key = f'{kind}:{record["id"]}'
            if key in nodes:
                raise ValueError(f'重复节点：{key}')
            nodes[key] = {
                'id': key, 'kind': kind, 'record_id': record['id'],
                'file': kind + '.json', 'status': record.get('status', 'unknown'),
                'history_id': record.get('history_id', record.get('origin_history_id')),
                'record': record,
            }
    def add(source: str, target: str, relation: str, status: str, evidence: str):
        if source not in nodes or target not in nodes:
            diagnostics.append({'code': 'UNRESOLVED_REFERENCE', 'from': source, 'to': target, 'evidence': evidence})
            return
        edge = {'from': source, 'to': target, 'relation': relation,
                'status': status, 'evidence': evidence}
        if edge not in edges:
            edges.append(edge)
    for key, node in nodes.items():
        record = node['record']
        for field, kind in REF_FIELDS.items():
            value = record.get(field)
            if value is None or (kind == 'versions' and value == 'global'):
                continue
            values = value if isinstance(value, list) else [value]
            for ref in values:
                if not isinstance(ref, str):
                    raise ValueError(f'{key}.{field} 必须引用字符串 ID')
                add(f'{kind}:{ref}', key, 'reference_dependency', node['status'], f'{node["file"]}#{node["record_id"]}.{field}')
        deps = record.get('depends_on', [])
        if not isinstance(deps, list):
            raise ValueError(f'{key}.depends_on 必须是数组')
        for ref in deps:
            if not isinstance(ref, str):
                raise ValueError('depends_on 必须使用带类型的字符串 ID')
            add(ref, key, 'declared_dependency', node['status'], f'{node["file"]}#{node["record_id"]}.depends_on')
    causal = _load(project, 'causal_edges.json', {'edges': []}).get('edges', [])
    if not isinstance(causal, list):
        raise ValueError('causal_edges.edges 必须是数组')
    for edge in causal:
        if not isinstance(edge, dict):
            raise ValueError('因果边必须是对象')
        add('events:' + str(edge.get('from_event_id')), 'events:' + str(edge.get('to_event_id')),
            'declared_causal', edge.get('status', 'unknown'), f'causal_edges.json#{edge.get("id")}')
    links = _load(project, 'dependency_links.json', {'links': []}).get('links', [])
    if not isinstance(links, list):
        raise ValueError('dependency_links.links 必须是数组')
    seen = set()
    for link in links:
        if not isinstance(link, dict) or not isinstance(link.get('id'), str) or not link['id']:
            raise ValueError('显式依赖边缺少 ID')
        if link['id'] in seen:
            raise ValueError('重复依赖边 ID')
        seen.add(link['id'])
        if not isinstance(link.get('reason'), str) or not link['reason'].strip():
            raise ValueError('显式依赖边必须说明 reason')
        if link.get('status') not in STATUSES:
            raise ValueError('依赖边缺少合法 status，不能默认视为已确认')
        if not isinstance(link.get('from'), str) or not isinstance(link.get('to'), str):
            raise ValueError('依赖边 from/to 必须是带类型的节点 ID')
        add(link['from'], link['to'], 'declared_dependency', link['status'],
            f'dependency_links.json#{link["id"]}: {link["reason"]}')
    return nodes, sorted(edges, key=lambda e: (e['from'], e['to'], e['relation'], e['evidence'])), diagnostics


def analyze(project: Path, changed: list[str]) -> dict:
    nodes, edges, diagnostics = graph(project)
    if not changed:
        raise ValueError('至少指定一个改动节点')
    for key in changed:
        if key not in nodes:
            raise ValueError(f'未知改动节点：{key}')
    adjacency = defaultdict(list)
    for edge in edges:
        adjacency[edge['from']].append(edge)
    seeds = sorted(set(changed))
    paths = {key: [] for key in seeds}
    queue = deque(seeds)
    while queue:
        current = queue.popleft()
        for edge in adjacency[current]:
            target = edge['to']
            if target in paths:
                continue
            paths[target] = paths[current] + [edge]
            queue.append(target)
    affected = []
    for key in sorted(set(paths) - set(seeds), key=lambda k: (len(paths[k]), k)):
        node = nodes[key]
        affected.append({
            'id': key, 'kind': node['kind'], 'status': node['status'],
            'history_id': node['history_id'], 'file': node['file'],
            'path': paths[key], 'review_required': True,
            'reason': '沿已登记的引用/依赖路径可达，不代表现实或正文必然改变',
        })
    reached = set(paths)
    scope_edges = [e for e in edges if e['from'] in reached and e['to'] in reached]
    snapshot = json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False, sort_keys=True).encode('utf-8')
    return {
        'schema_version': '0.5', 'changed': seeds, 'affected': affected,
        'affected_count': len(affected), 'reachable_edges': scope_edges,
        'graph_sha256': digest(snapshot), 'diagnostics': diagnostics,
        'scope': 'author_editor_only; may contain later-chapter spoilers',
        'canon_modified': False,
        'coverage': '仅已登记的顶层类型化引用、causal_edges 与 dependency_links；不做自然语言或物理因果推断。',
        'warning': '路径为最短示例，不是唯一原因。循环可遍历但不表示时间悖论已解决。未登记依赖仍需人工审查。',
    }
