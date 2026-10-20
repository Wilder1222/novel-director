"""V0.2: deterministic historical-version, character-presence and artifact audits.

The ledger is explicit; this is a consistency checker, not a time-travel simulator.
No canon is mutated. All timestamps are fictional-city local naive ISO values.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
import json


def _time(text):
    if not isinstance(text, str) or 'T' not in text:
        return None
    try:
        val = datetime.fromisoformat(text)
        return val if val.tzinfo is None else None
    except (TypeError, ValueError):
        return None


def _items(project: Path, filename: str, key: str, issues: list, required: bool):
    source = project / filename
    if not source.exists():
        if required:
            issues.append(('ERROR', 'LEDGER_MISSING', filename, '新版本缺少规定的台账'))
        return []
    try:
        obj = json.loads(source.read_text(encoding='utf-8'))
        val = obj.get(key)
        if not isinstance(val, list):
            raise ValueError(f'{key} must be a list')
        return val
    except (ValueError, UnicodeError, OSError, AttributeError) as exc:
        issues.append(('ERROR', 'LEDGER_INVALID', filename, str(exc)))
        return []


def _unique(records, label, issues):
    index = {}
    for idx, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get('id'), str) or not record['id']:
            issues.append(('ERROR', 'LEDGER_ID_INVALID', f'{label}[{idx}]', 'id 必须是非空字符串'))
            continue
        if record['id'] in index:
            issues.append(('ERROR', 'LEDGER_ID_DUPLICATE', label, record['id']))
        else:
            index[record['id']] = record
    return index


def _ancestors(vid, versions):
    visited = set()
    while vid in versions and vid not in visited:
        visited.add(vid)
        vid = versions[vid].get('parent')
    return visited


def audit_timeline(project: Path, data: dict):
    """Returns issues without writing. Works with original v0.1 (no new ledgers)."""
    issues = []
    newer = data.get('project', {}).get('schema_version') != '0.1'
    characters = {x['id']:x for x in data.get('characters', {}).get('characters', []) if isinstance(x, dict) and x.get('id')}
    versions = {x['id']:x for x in data.get('versions', {}).get('versions', []) if isinstance(x, dict) and x.get('id')}
    trips = {x['id']:x for x in data.get('trips', {}).get('trips', []) if isinstance(x, dict) and x.get('id')}
    events = {x['id']:x for x in data.get('events', {}).get('events', []) if isinstance(x, dict) and x.get('id')}
    presences = _unique(_items(project,'presences.json','presences',issues,newer), 'presences', issues)
    objects = _unique(_items(project,'artifacts.json','artifacts',issues,newer), 'artifacts', issues)
    rewrites = _unique(_items(project,'rewrites.json','rewrites',issues,newer), 'rewrites', issues)
    edges = _unique(_items(project,'causal_edges.json','edges',issues,newer), 'causal_edges', issues)

    for tid, trip in trips.items():
        sh = trip.get('source_history_id', trip.get('history_id'))
        dh = trip.get('destination_history_id', trip.get('history_id'))
        if sh not in versions or dh not in versions:
            issues.append(('ERROR', 'TRIP_HISTORY_BOUNDARY', tid, '出发/目的历史版本未知'))
        # A traveler may cross histories only if they are actually version-related.
        if sh in versions and dh in versions and sh!=dh and not (
                sh in _ancestors(dh,versions) or dh in _ancestors(sh,versions)):
            issues.append(('ERROR','TRIP_HISTORY_UNRELATED',tid,'跨版本旅行未能找到祖先关系'))
    native_ranges = defaultdict(list)
    for pid, pres in presences.items():
        char, hid, role = pres.get('character_id'), pres.get('history_id'), pres.get('mode')
        start,end = _time(pres.get('from_at')),_time(pres.get('to_at'))
        if char not in characters:
            issues.append(('ERROR','PRESENCE_CHARACTER_UNKNOWN',pid,str(char)))
        if hid not in versions:
            issues.append(('ERROR','PRESENCE_HISTORY_UNKNOWN',pid,str(hid)))
        if not start or not end or start > end:
            issues.append(('ERROR','PRESENCE_INTERVAL_INVALID',pid,'在场时间必须有效且起点不晚于终点'))
            continue
        if role not in ('native','traveler'):
            issues.append(('ERROR','PRESENCE_MODE_INVALID',pid,str(role)))
            continue
        if role=='native':
            native_ranges[(char,hid)].append((start,end,pid))
            try:
                birth = date.fromisoformat(pres.get('birth_date',characters[char]['birth_date']))
                if start.date() < birth:
                    issues.append(('ERROR','NATIVE_BEFORE_BIRTH',pid,'本历史原生实例不能早于其出生'))
                if isinstance(pres.get('age_at_start'),int):
                    age=start.year-birth.year-((start.month,start.day)<(birth.month,birth.day))
                    if age!=pres['age_at_start']:
                        issues.append(('ERROR','INSTANCE_AGE_INVALID',pid,f'原生年龄应为 {age}'))
            except (ValueError, KeyError, TypeError):
                issues.append(('ERROR','PRESENCE_BIRTH_INVALID',pid,'无法核对出生日期'))
        else:
            trip=trips.get(pres.get('trip_id'))
            if not trip or trip.get('traveler_id')!=char:
                issues.append(('ERROR','TRAVELER_WITHOUT_TRIP',pid,'穿越者实例必须引用同一个人的有效旅行'))
                continue
            if hid!=trip.get('destination_history_id',trip.get('history_id')):
                issues.append(('ERROR','TRAVELER_HISTORY_MISMATCH',pid,'在场版本与旅行目的版本不同'))
            arrival,exit_at=_time(trip.get('arrive_at')),_time(trip.get('destination_exit_at'))
            if not arrival or not exit_at or (start,end)!=(arrival,exit_at):
                issues.append(('ERROR','TRAVELER_INTERVAL_MISMATCH',pid,'旅行在场区间必须对应到达和离开时钟'))
            departure=_time(trip.get('depart_at'))
            if departure and isinstance(pres.get('age_at_start'),int):
                try:
                    birth=date.fromisoformat(characters[char]['birth_date'])
                    age=departure.year-birth.year-((departure.month,departure.day)<(birth.month,birth.day))
                    if age != pres['age_at_start']:
                        issues.append(('ERROR','TRAVELER_AGE_INVALID',pid,f'穿越者应保留出发时年龄 {age}'))
                except (KeyError,ValueError,TypeError):
                    pass
    for pair,ranges in native_ranges.items():
        ranges.sort()
        for older,young in zip(ranges,ranges[1:]):
            if young[0] <= older[1]:
                issues.append(('ERROR','NATIVE_OVERLAP',f'{older[2]} / {young[2]}','同一个历史分支的同一人物不能同时存在两个原生实例'))

    for rid,r in rewrites.items():
        frm,to=r.get('from_history_id'),r.get('to_history_id')
        if frm not in versions or to not in versions:
            issues.append(('ERROR','REWRITE_HISTORY_UNKNOWN',rid,f'{frm} -> {to}'))
        elif versions[to].get('parent')!=frm:
            issues.append(('ERROR','REWRITE_NOT_CHILD',rid,'新历史必须直接从指定父历史分歧'))
        if r.get('cause_event_id') not in events:
            issues.append(('ERROR','REWRITE_CAUSE_UNKNOWN',rid,str(r.get('cause_event_id'))))
        elif events[r['cause_event_id']].get('history_id')!=frm:
            issues.append(('ERROR','REWRITE_CAUSE_HISTORY',rid,'重写触发事件应标识其原始历史版本'))
        if not _time(r.get('at')):
            issues.append(('ERROR','REWRITE_TIME_INVALID',rid,str(r.get('at'))))
        for oid in r.get('preserved_artifact_ids', []):
            obj=objects.get(oid)
            if not obj:
                issues.append(('ERROR','REWRITE_ARTIFACT_UNKNOWN',rid,str(oid)))
            elif obj.get('protection_mode')!='archival':
                issues.append(('ERROR','UNPROTECTED_ARTIFACT',rid,f'{oid} 未指定 archival 保存机制'))

    for oid,obj in objects.items():
        origin=obj.get('origin_history_id')
        if origin not in versions:
            issues.append(('ERROR','ARTIFACT_ORIGIN_HISTORY',oid,str(origin)))
        if not _time(obj.get('created_at')):
            issues.append(('ERROR','ARTIFACT_CREATED_INVALID',oid,'创建时间无效'))
        if obj.get('protection_mode','none') not in ('none','archival'):
            issues.append(('ERROR','ARTIFACT_PROTECTION_INVALID',oid,str(obj.get('protection_mode'))))
        transfers=obj.get('transfers',[])
        for i,trans in enumerate(transfers):
            label=f'{oid}.transfer[{i}]'
            src,dst=trans.get('from_history_id'),trans.get('to_history_id')
            if src not in versions or dst not in versions:
                issues.append(('ERROR','ARTIFACT_TRANSFER_HISTORY',label,f'{src}->{dst}'))
            method=trans.get('mechanism')
            if method not in ('ordinary','archival','traveler_carry'):
                issues.append(('ERROR','ARTIFACT_TRANSFER_MODE',label,str(method)))
            a,b=_time(trans.get('from_at')),_time(trans.get('to_at'))
            if not a or not b:
                issues.append(('ERROR','ARTIFACT_TRANSFER_TIME',label,'转移两端时间必须有效'))
            if method=='ordinary' and ((a and b and b<a) or src!=dst):
                issues.append(('ERROR','ARTIFACT_CAUSAL_LEAP',label,'普通物品传递不能倒流时间或越过历史分支'))
            if method=='archival' and obj.get('protection_mode')!='archival':
                issues.append(('ERROR','ARTIFACT_PROTECTION_MISSING',label,'跨历史归档记录必须先声明保护机制'))
            if method=='traveler_carry':
                trip=trips.get(trans.get('via_trip'))
                if not trip or (trip.get('source_history_id',trip.get('history_id'))!=src) or (trip.get('destination_history_id',trip.get('history_id'))!=dst):
                    issues.append(('ERROR','ARTIFACT_TRIP_INVALID',label,'物件穿越需有版本匹配的有效旅行'))
                elif _time(trip.get('depart_at')) != a or _time(trip.get('arrive_at')) != b:
                    issues.append(('ERROR','ARTIFACT_TRIP_CLOCK',label,'物件传递须与携带者的穿越时钟对应'))
        for i,app in enumerate(obj.get('appearances', [])):
            hid=app.get('history_id')
            if hid not in versions:
                issues.append(('ERROR','ARTIFACT_APPEARANCE_HISTORY',f'{oid}[{i}]',str(hid)))
            if not _time(app.get('at')):
                issues.append(('ERROR','ARTIFACT_APPEARANCE_TIME',f'{oid}[{i}]','出现时间无效'))
            if hid!=origin:
                # Must have explicit cross-history transport or archival preservation.
                received=any(t.get('to_history_id')==hid and t.get('mechanism') in ('archival','traveler_carry') for t in transfers)
                protected=any(r.get('to_history_id')==hid and oid in r.get('preserved_artifact_ids',[]) for r in rewrites.values())
                if not (received or protected):
                    issues.append(('ERROR','ARTIFACT_UNEXPLAINED_BRANCH',f'{oid}[{i}]','物件跨历史版本出现，但缺少受保护或旅行携带的来源路径'))

    causal_graph=defaultdict(list)
    for edgeid,edge in edges.items():
        fr,to=edge.get('from_event_id'),edge.get('to_event_id')
        mode=edge.get('mechanism','ordinary')
        if fr not in events or to not in events:
            issues.append(('ERROR','CAUSAL_EVENT_UNKNOWN',edgeid,f'{fr} -> {to}'))
            continue
        if mode not in ('ordinary','time_travel','bootstrap'):
            issues.append(('ERROR','CAUSAL_EDGE_MODE',edgeid,str(mode)))
        source,target=events[fr],events[to]
        a,b=_time(source.get('at')),_time(target.get('at'))
        if mode=='ordinary':
            if source.get('history_id') != target.get('history_id') or (a and b and a>b):
                issues.append(('ERROR','CAUSAL_EDGE_ORDER',edgeid,'普通因果不可逆时或跨历史版本'))
        else:
            trip=trips.get(edge.get('via_trip'))
            if not trip:
                issues.append(('ERROR','CAUSAL_EDGE_TRIP',edgeid,'时间因果必须标注有效 via_trip'))
            else:
                d,arr=_time(trip.get('depart_at')),_time(trip.get('arrive_at'))
                if (a and d and a>d) or (b and arr and b<arr):
                    issues.append(('ERROR','CAUSAL_EDGE_TRIP_TIME',edgeid,'原因不能晚于穿越出发、结果不能早于抵达'))
                if source.get('history_id')!=trip.get('source_history_id',trip.get('history_id')) or target.get('history_id')!=trip.get('destination_history_id',trip.get('history_id')):
                    issues.append(('ERROR','CAUSAL_EDGE_TRIP_HISTORY',edgeid,'事件历史与旅程出发/抵达历史不匹配'))
            if mode=='bootstrap' and not edge.get('loop_id'):
                issues.append(('ERROR','BOOTSTRAP_NOT_DECLARED',edgeid,'自举因果环必须具名，便于作者明确承担逻辑'))
        causal_graph[fr].append((to,edgeid,mode))
    # A feedback loop is not silently approved. All cycle edges must be declared bootstrap.
    seen,stack=set(),[]
    logged=set()
    def dfs(node):
        seen.add(node)
        stack.append(node)
        for nextnode,eid,mode in causal_graph.get(node,[]):
            if nextnode in stack:
                at=stack.index(nextnode)
                cycle_nodes=stack[at:]+[nextnode]
                cycle_edges=[]
                for x,y in zip(cycle_nodes,cycle_nodes[1:]):
                    cycle_edges.append(next((e for n,e,_ in causal_graph[x] if n==y),None))
                label=' -> '.join(cycle_nodes)
                if label not in logged:
                    logged.add(label)
                    if all(edges.get(e,{}).get('mechanism')=='bootstrap' and edges.get(e,{}).get('loop_id') for e in cycle_edges):
                        issues.append(('WARN','BOOTSTRAP_LOOP',label,'显式声明的自举环，需人工验证稳定性与来源'))
                    else:
                        issues.append(('ERROR','CAUSAL_CYCLE',label,'因果链构成未经说明的循环'))
            elif nextnode not in seen:
                dfs(nextnode)
        stack.pop()
    for node in list(causal_graph):
        if node not in seen:
            dfs(node)

    for entry in data.get('knowledge',{}).get('knowledge',[]):
        if not isinstance(entry,dict):
            continue
        if entry.get('retained_across_histories') is True:
            justification=entry.get('retention_basis')
            if justification not in ('protected_archive','traveler_memory'):
                issues.append(('ERROR','RETENTION_BASIS_MISSING',entry.get('id','?'),'跨版本记忆需要明确保存依据'))
            if justification=='traveler_memory' and entry.get('via_trip') not in trips:
                issues.append(('ERROR','RETENTION_TRIP_MISSING',entry.get('id','?'),'旅者记忆需要旅行标识'))
    return issues
