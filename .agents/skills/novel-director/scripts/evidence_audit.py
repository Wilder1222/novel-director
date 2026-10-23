"""Exact, source-bound editorial citations. No semantic or literary judgment.

Offsets count Unicode code points in the UTF-8 decoded source, NOT bytes or
UTF-16 code units. No whitespace or punctuation normalization is performed.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re

MAX_SOURCE_BYTES = 4 * 1024 * 1024
PROJECT_SOURCES = frozenset({
    'project.json', 'canon.json', 'characters.json', 'chapters.json', 'clues.json',
    'events.json', 'knowledge.json', 'versions.json', 'trips.json', 'presences.json',
    'artifacts.json', 'rewrites.json', 'causal_edges.json', 'world_rules.json',
    'story_units.json', 'relationships.json', 'scenes.json', 'memory_docs.json',
    'dependency_links.json', 'bible.md', 'style.md',
})


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def no_symlink_components(path: Path) -> None:
    """Reject symlinks anywhere on a supplied local path before reading/writing."""
    absolute = path.expanduser().absolute()
    for item in (absolute, *absolute.parents):
        if item.is_symlink() or (item.exists() and getattr(item.stat(follow_symlinks=False), 'st_file_attributes', 0) & 0x400):
            raise ValueError(f'不接受符号链接路径：{item}')


def author_destination(path: Path) -> None:
    """A plugin installation is code, never an author data destination."""
    no_symlink_components(path)
    target = path.expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent/'plugin.json').is_file() and (parent/'.codex-plugin/plugin.json').is_file():
            if target.is_relative_to(parent):
                raise ValueError('不能向插件安装目录写作品；请指定外部作者目录')
            break


def read_utf8(path: Path) -> tuple[str, str]:
    no_symlink_components(path)
    if not path.is_file():
        raise ValueError(f'不是普通文本文件：{path}')
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError('单个文本文件超过4 MiB')
    raw = path.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError('单个文本文件超过4 MiB')
    try:
        return raw.decode('utf-8'), digest(raw)
    except UnicodeError as exc:
        raise ValueError('引证来源必须是 UTF-8') from exc


def project_source(project: Path, name: str) -> Path:
    if not isinstance(name, str) or '\\' in name:
        raise ValueError('来源路径必须是项目内 POSIX 相对路径')
    p = PurePosixPath(name)
    if p.is_absolute() or not p.parts or any(x in ('.', '..') or x.startswith('.') for x in p.parts):
        raise ValueError('不允许绝对路径、隐藏目录或目录穿越')
    allowed = name in PROJECT_SOURCES or name in ('writing_profile.json', 'writing_spec.json','prose_risks.json') or (
        len(p.parts) == 2 and p.parts[0] == 'manuscript' and
        re.fullmatch(r'V\d{2,3}-C\d{2,4}\.md', p.name) is not None
    )
    if not allowed:
        raise ValueError(f'来源不在故事资料白名单：{name}')
    path = project / name
    no_symlink_components(path)
    if not path.resolve().is_relative_to(project.resolve()):
        raise ValueError('来源超出项目边界')
    return path


def locate(text: str, citation: dict, source_sha: str | None = None) -> dict:
    """Verify an exact quote, disambiguate repetitions, return stable offsets."""
    if not isinstance(citation, dict):
        raise ValueError('citation 必须是对象')
    quote = citation.get('quote')
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError('引文 quote 必须为非空原文，不接受概括代替')
    actual_sha = source_sha or digest(text.encode('utf-8'))
    claimed_sha = citation.get('sha256')
    if claimed_sha is not None and claimed_sha != actual_sha:
        raise ValueError('引证来源 SHA-256 已过期或错误')
    has_start, has_end = 'start' in citation, 'end' in citation
    if has_start != has_end:
        raise ValueError('start/end 必须同时提供')
    if has_start:
        start, end = citation['start'], citation['end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError('引文字符范围不合法')
        if text[start:end] != quote:
            raise ValueError('引文不匹配指定原文范围')
    else:
        start = text.find(quote)
        if start < 0:
            raise ValueError('引文不存在于指定来源')
        if text.find(quote, start + 1) >= 0:
            raise ValueError('引文出现多次，必须提供明确 start/end')
        end = start + len(quote)
    return {
        'source': citation.get('source', 'candidate'), 'quote': quote,
        'start': start, 'end': end, 'sha256': actual_sha,
        'line_start': text.count('\n', 0, start) + 1,
        'line_end': text.count('\n', 0, end - 1) + 1,
    }


def verify_review(project: Path, candidate: Path, report: dict) -> tuple[dict, dict]:
    """Resolve and freeze citations; repeated calls recheck sources, never trust flags."""
    if not isinstance(report, dict):
        raise ValueError('审稿报告必须为对象')
    result = deepcopy(report)
    texts = {'candidate': read_utf8(candidate)}
    groups = []
    issues, scores = result.get('issues', []), result.get('scores', {})
    if not isinstance(issues, list) or not isinstance(scores, dict):
        raise ValueError('issues/scores 类型错误')
    for index, item in enumerate(issues):
        if not isinstance(item, dict):
            raise ValueError('issue 必须是对象')
        groups.append((f'issues[{index}]', item))
    for dim, item in scores.items():
        if not isinstance(item, dict):
            raise ValueError('score 必须是对象')
        groups.append((f'scores.{dim}', item))
    if 'summary_citations' in result:
        summary = {'citations': result['summary_citations']}
        groups.append(('summary', summary))
    else:
        summary = None
    if not groups:
        raise ValueError('空审稿也须提供 summary_citations，说明实际阅读范围')
    total = 0
    candidate_seen = False
    for where, obj in groups:
        cites = obj.get('citations')
        if not isinstance(cites, list) or not cites:
            raise ValueError(f'{where} 缺少结构化 citations；旧版自由文本证据不可审批')
        normalized = []
        for cite in cites:
            if not isinstance(cite, dict):
                raise ValueError('citation 必须为对象')
            name = cite.get('source', 'candidate')
            if not isinstance(name, str):
                raise ValueError('source 必须为字符串')
            if name not in texts:
                texts[name] = read_utf8(project_source(project, name))
            text, sha = texts[name]
            item = locate(text, {**cite, 'source': name}, sha)
            normalized.append(item)
            candidate_seen |= name == 'candidate'
            total += 1
        obj['citations'] = normalized
    if not candidate_seen:
        raise ValueError('审稿必须至少引用一处当前候选正文，不能只引用大纲')
    if summary is not None:
        result['summary_citations'] = summary['citations']
    result['review_schema_version'] = '0.5'
    audit = {
        'verified': True, 'citation_count': total,
        'sources': {k: v[1] for k, v in sorted(texts.items())},
        'offset_unit': 'Unicode code points; exact UTF-8 decoded source',
        'semantic_support': 'not_evaluated',
        'warning': '只确认引文和来源版本真实，不证明审稿推理、缺席判断或文学评分正确。',
    }
    result['evidence_audit'] = audit
    return result, audit
