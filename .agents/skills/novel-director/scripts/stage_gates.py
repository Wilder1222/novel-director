"""Versioned, evidence-bound stage gates. No model calls or literary truth claims.

Receipts are local host reports, not authenticated identities or isolation proof.
Old projects remain usable; chapters registered here cannot bypass the gates.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from uuid import uuid4
import hashlib
import json
import os
import re
from evidence_audit import author_destination, no_symlink_components, read_utf8, locate, project_source

BASE = '.novel_stages'
CATALOG = Path(__file__).resolve().parents[1] / 'assets/stage-contracts.json'
ID = re.compile(r'stages-[a-f0-9]{16}')
ITEM = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')


def pretty(value): return json.dumps(value, ensure_ascii=False, indent=2) + '\n'
def sha(value): return hashlib.sha256(value).hexdigest()
def hashed(value): return sha(pretty(value).encode('utf-8'))
def obj(path): return json.loads(read_utf8(path)[0])
def catalog(): return obj(CATALOG)


def new(path, text):
    author_destination(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as out:
        out.write(text)


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 200000:
        raise ValueError(label + ' 必须为非空文本且不超过200000字符')
    if value.strip().casefold() in ('todo', 'tbd', '待填写', '待补充', '占位', '...', '…'):
        raise ValueError(label + ' 不接受占位符')
    return value


def exact(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError('字段不完整或包含未知字段：' + ','.join(required))


def folder(project, pid):
    if not isinstance(pid, str) or not ID.fullmatch(pid): raise ValueError('无效 pipeline_id')
    path = project / BASE / pid
    no_symlink_components(path)
    return path


def registry(project):
    path = project / BASE / 'registry.json'
    no_symlink_components(path)
    return obj(path) if path.exists() else {}


def _register(project, scope, pid, supersedes):
    import creative_workflow as flow
    entries = registry(project)
    for chapter in scope:
        old = entries.get(chapter)
        if old and old != supersedes: raise ValueError('章节已绑定阶段流程；替代必须显式指定 supersedes')
        if supersedes and old != supersedes: raise ValueError('supersedes 不匹配当前章节绑定')
    entries.update({chapter: pid for chapter in scope})
    flow.atomic_write(project / BASE / 'registry.json', pretty(entries), replace=True)


def start(project, spec):
    author_destination(project)
    exact(spec, ('profile', 'mode', 'author_input', 'requirements', 'scope', 'context_files'), ('supersedes','reference_books'))
    book = obj(project / 'project.json')
    cat = catalog()
    if spec['profile'] not in cat['profiles'] or spec['mode'] not in ('host_supplied', 'synthetic_test'):
        raise ValueError('未知阶段路径或执行来源')
    raw = text(spec['author_input'], '作者原话')
    books=spec.get('reference_books',[])
    if not isinstance(books,list) or len(books)>24 or any(not isinstance(x,str) or not re.fullmatch('[a-z0-9][a-z0-9-]{0,79}',x) for x in books) or len(set(books))!=len(books):raise ValueError('reference_books须为不重复的具名作品/版次ID')
    if books and spec['profile']!='develop':raise ValueError('新作品采集契约绑定开发研究；日常写作按需读取已有参考索引')
    reqs = spec['requirements']
    if not isinstance(reqs, list) or not 1 <= len(reqs) <= 64: raise ValueError('要求必须为1–64项')
    ids = set()
    for item in reqs:
        exact(item, ('id', 'text', 'quote'))
        if not isinstance(item['id'], str) or not ITEM.fullmatch(item['id']) or item['id'] in ids: raise ValueError('要求ID无效或重复')
        ids.add(item['id']); text(item['text'], '要求')
        locate(raw, {'quote': item['quote'], 'start': raw.find(item['quote']), 'end': raw.find(item['quote']) + len(item['quote'])})
    scope = spec['scope']
    if not isinstance(scope, list) or len(scope) > 24 or any(not isinstance(x, str) for x in scope) or len(set(scope)) != len(scope):
        raise ValueError('scope必须为不重复章节ID列表，最多24项')
    known = {x['id'] for x in obj(project / 'chapters.json')['chapters']}
    if set(scope) - known or (spec['profile'] in ('draft', 'revise') and len(scope) != 1): raise ValueError('创作/修订必须绑定一个已登记章节；多章拆成独立流程')
    if spec['profile'] not in ('draft', 'revise') and scope: raise ValueError('只有正文/修订路径可以管理章节写入')
    entries = registry(project)
    for chapter in scope:
        if entries.get(chapter) and entries[chapter] != spec.get('supersedes'): raise ValueError('章节已绑定阶段流程')
    import writing_spec
    production = None
    if spec['profile'] in ('draft','revise'):
        production = writing_spec.projection(project,scope[0])
        if production is None: raise ValueError('新正文/修订任务必须先有章/剧情硬范围与具体writing_spec；主会话准备，不让作者填JSON')
        if spec['mode']=='host_supplied' and writing_spec.load(project)['value']['origin']=='synthetic_test': raise ValueError('真实创作流程不能采用已标记合成的创作规格')
    names = spec['context_files']
    if not isinstance(names, list) or len(names) > 64 or any(not isinstance(x, str) for x in names) or len(set(names)) != len(names):
        raise ValueError('context_files必须为不重复路径列表')
    # Every canonical constraint is frozen, including absent optional sources.
    from evidence_audit import PROJECT_SOURCES
    names = sorted(set(names) | set(PROJECT_SOURCES) | {'writing_profile.json','writing_spec.json','prose_risks.json'})
    contexts = []
    for name in names:
        path = project_source(project, name)
        contexts.append({'path': name, 'sha256': read_utf8(path)[1] if path.exists() else None})
    pid = 'stages-' + uuid4().hex[:16]
    import creative_workflow as flow
    contract = {**spec, 'schema_version': '1', 'pipeline_id': pid, 'context': contexts,
                'stages': cat['profiles'][spec['profile']], 'catalog': cat, 'catalog_sha256': read_utf8(CATALOG)[1],
                'project_identity': str(project.resolve()), 'author_input_sha256': sha(raw.encode('utf-8')),
                'project_signature': flow.signature(project),
                'budget': {'versions_per_stage': 3, 'reviews_per_version': 3}, 'canon_effect': 'none'}
    contract['validator_sha256'] = read_utf8(Path(__file__))[1]
    contract['writing_validator_sha256'] = read_utf8(Path(writing_spec.__file__))[1]
    if books:
        import reference_library
        contract['reference_validator_sha256']=read_utf8(Path(reference_library.__file__))[1]
        import reference_study
        contract['reference_study_validator_sha256']=read_utf8(Path(reference_study.__file__))[1]
    if production is not None:
        contract['writing_spec'] = production
        import prose_risks
        contract['prose_risks'] = prose_risks.metadata(project)
    dest = folder(project, pid)
    new(dest / 'contract.json', pretty(contract))
    new(dest / 'contract.sha256', read_utf8(dest / 'contract.json')[1])
    if scope: _register(project, scope, pid, spec.get('supersedes'))
    return {'pipeline_id': pid, 'profile': spec['profile'], 'stages': contract['stages'], 'author_approved': False}


def load(project, pid):
    dest = folder(project, pid)
    raw, digest = read_utf8(dest / 'contract.json')
    if read_utf8(dest / 'contract.sha256')[0] != digest: raise ValueError('阶段契约已改变')
    contract = json.loads(raw)
    if contract['pipeline_id'] != pid or contract['project_identity'] != str(project.resolve()): raise ValueError('阶段流程不属于本项目')
    return dest, contract


def _current(project, contract):
    if contract.get('reference_validator_sha256'):
        import reference_library
        if contract['reference_validator_sha256']!=read_utf8(Path(reference_library.__file__))[1]:raise ValueError('参考库核验规则已更新，请新建流程')
    if contract.get('reference_study_validator_sha256'):
        import reference_study
        if contract['reference_study_validator_sha256']!=read_utf8(Path(reference_study.__file__))[1]:raise ValueError('细读/技巧核验规则已更新，请新建流程')
    if 'prose_risks' in contract:
        import prose_risks
        if contract['prose_risks']!=prose_risks.metadata(project): raise ValueError('阶段编辑语料/保护/检查器已更新，须新建流程')
    if read_utf8(CATALOG)[1] != contract['catalog_sha256']: raise ValueError('阶段规则已升级，需新建流程')
    if contract.get('validator_sha256') and read_utf8(Path(__file__))[1] != contract['validator_sha256']: raise ValueError('阶段核验实现已升级，需新建流程')
    if contract.get('writing_validator_sha256'):
        import writing_spec
        if read_utf8(Path(writing_spec.__file__))[1] != contract['writing_validator_sha256']: raise ValueError('创作规格核验实现已升级，需新建流程')
    import creative_workflow as flow
    if flow.signature(project) != contract['project_signature']: raise ValueError('故事资料/正式正文基线已变化；新建流程并重新核验')
    for ref in contract['context']:
        path = project_source(project, ref['path'])
        actual = read_utf8(path)[1] if path.exists() else None
        if actual != ref['sha256']: raise ValueError('上游设定/约束已变化：' + ref['path'])
    if any(registry(project).get(ch) != contract['pipeline_id'] for ch in contract['scope']): raise ValueError('流程已被显式替代')


def _latest(dest, stage):
    base = dest / stage
    no_symlink_components(base)
    versions = [p for p in base.glob('v*') if re.fullmatch(r'v[1-9][0-9]*', p.name)]
    return max(versions, key=lambda p: int(p.name[1:])) if versions else None


def _sources(project, contract, refs, stage):
    if not isinstance(refs, list) or len(refs) > 64: raise ValueError('sources必须为列表，最多64项')
    bound = []
    for ref in refs:
        if not isinstance(ref, dict): raise ValueError('来源必须为对象')
        kind = ref.get('kind')
        if kind == 'baseline' and 'path' in ref:
            exact(ref, ('kind', 'path'))
            if ref['path'] not in {f'manuscript/{ch}.md' for ch in contract['scope']}: raise ValueError('修订基线必须是当前章节实际正式稿')
            bound.append({**ref, 'sha256': read_utf8(project_source(project, ref['path']))[1]})
        elif kind in ('candidate', 'run_review', 'baseline'):
            exact(ref, ('kind', 'run_id'))
            revision_binding = {}
            import creative_workflow as flow
            root, m = flow._manifest(project, ref['run_id']); flow._check_contract(root, m)
            if m['chapter_id'] not in contract['scope']: raise ValueError('Run不在当前章节范围')
            if flow.signature(project) != m['source_signature']: raise ValueError('Run已过期')
            key = 'latest_review' if kind == 'run_review' else 'current_candidate'
            if not m.get(key): raise ValueError('Run缺少实际正文/审稿')
            path = root / m[key]
            raw, digest = read_utf8(path)
            expected = m.get('review_sha256') if kind == 'run_review' else m['candidate_sha']
            if digest != expected: raise ValueError('Run产物已改变')
            if kind in ('candidate','run_review'):
                import writing_spec
                writing_spec.assert_run(project,ref['run_id'],require_review=kind=='run_review')
            if kind == 'run_review':
                report = json.loads(raw)
                from evidence_audit import verify_review
                verify_review(project, root / m['current_candidate'], report)
                if report.get('reviewed_candidate_sha256') != m['candidate_sha'] or any(x['severity'] in ('BLOCKING', 'MAJOR') for x in report['issues']):
                    raise ValueError('审稿未闭合阻塞/重要问题，不能作为阶段出口')
                if set(report.get('scores', {})) != set(flow.SCORE_DIMENSIONS):
                    raise ValueError('阶段审稿必须覆盖全部六维；不适用维度也须说明范围与证据')
            if stage == 'revision' and kind == 'candidate':
                import directed_revision
                checked = directed_revision.assert_ready(project, ref['run_id'])
                dest = folder(project, contract['pipeline_id'])
                diagnosis = obj(_latest(dest, 'diagnosis') / 'index.json')
                if checked['before_sha256'] not in {x['sha256'] for x in diagnosis['sources'] if x['kind'] == 'baseline'}:
                    raise ValueError('定向修订不是从已诊断原稿派生')
                revision_binding = {'revision_gate_sha256': hashed(checked)}
            bound.append({**ref, 'path': path.relative_to(project).as_posix(), 'sha256': digest, 'candidate_sha256': m['candidate_sha'], **revision_binding})
        elif kind == 'ensemble':
            exact(ref, ('kind', 'ensemble_id'))
            import ensemble_runtime as ensemble
            root, state = ensemble._load(project, ref['ensemble_id'])
            if state['scene']['chapter_id'] not in contract['scope'] or state['stage'] != 'complete': raise ValueError('排练未完成或不属于当前章节')
            raw = read_utf8(root / 'state.json')
            if contract['mode'] != 'synthetic_test' and any(x['source'] != 'host_supplied' for x in state['calls']): raise ValueError('真实阶段排练须全部host_supplied；字符串声明不是宿主隔离证明')
            bound.append({**ref, 'path': (root / 'state.json').relative_to(project).as_posix(),
                          'sha256': _ensemble_subject(state), 'hash_scope':'completed_execution_excluding_handoff'})
        elif kind in ('file','reference_samples'):
            exact(ref, ('kind', 'path'))
            name = ref['path']
            if not isinstance(name, str) or '\\' in name or ':' in name or '\x00' in name: raise ValueError('文件来源路径无效')
            parts = PurePosixPath(name).parts
            if not parts or PurePosixPath(name).is_absolute() or any(p.startswith('.') for p in parts): raise ValueError('文件来源必须是项目内普通相对路径')
            path = project / name
            entry={**ref, 'sha256': read_utf8(path)[1]}
            if kind=='reference_samples':
                import reference_library
                entry['work_ids']=contract.get('reference_books',[])
                entry['collection_gate']=reference_library.validate_file(path,entry['work_ids'])
            bound.append(entry)
        else: raise ValueError('未知产物来源')
    required = {'rehearsal': 'ensemble', 'draft': 'candidate', 'revision': 'candidate', 'editorial': 'run_review'}
    if contract['profile'] == 'revise': required['diagnosis'] = 'baseline'
    if stage in required and not any(x['kind'] == required[stage] for x in bound): raise ValueError('缺少该阶段真实引擎产物：' + required[stage])
    if stage in required and required[stage] in ('candidate','run_review') and sum(x['kind']==required[stage] for x in bound)!=1:
        raise ValueError('一个正文/审稿阶段必须绑定唯一Run候选/审稿')
    for chapter in contract['scope']:
        if stage in required:
            # All managed chapters need an actual endpoint, not one chapter standing in for several.
            relevant = [x for x in bound if x['kind'] == required[stage]]
            if stage == 'rehearsal':
                import ensemble_runtime as ensemble
                covered = {ensemble._load(project, x['ensemble_id'])[1]['scene']['chapter_id'] for x in relevant}
            elif stage == 'diagnosis':
                covered = set(contract['scope'])  # baseline paths/Run membership validated above
            else:
                import creative_workflow as flow
                covered = {flow._manifest(project, x['run_id'])[1]['chapter_id'] for x in relevant}
            if chapter not in covered: raise ValueError('引擎产物未覆盖全部章节')
    if stage == 'rehearsal':
        import ensemble_runtime as ensemble
        scenes = [ensemble._load(project, x['ensemble_id'])[1]['scene'] for x in bound if x['kind'] == 'ensemble']
        if len({(x['chapter_id'], x['id']) for x in scenes}) != len(scenes): raise ValueError('同一场景重复计入排练产物')
        registered = obj(project / 'scenes.json').get('scenes', []) if (project / 'scenes.json').exists() else []
        for chapter in contract['scope']:
            expected = [x['id'] for x in sorted(registered, key=lambda x: x.get('order', 0)) if x.get('chapter_id') == chapter]
            actual = [x['id'] for x in scenes if x['chapter_id'] == chapter]
            if expected and expected != actual: raise ValueError('排练遗漏或倒排登记场景')
    if stage in ('implementation', 'validation') and not any(x['kind'] == 'file' for x in bound):
        raise ValueError('实现/验证必须绑定实际源码差异或执行记录文件')
    if stage=='research' and contract.get('reference_books') and not any(x['kind']=='reference_samples' for x in bound):raise ValueError('研究出口缺逐书20–50章实际采集记录及所声明的细读档案')
    return bound


def _verify_refs(project, refs):
    for ref in refs:
        if ref['kind']=='ensemble':
            import ensemble_runtime as ensemble
            _,state=ensemble._load(project,ref['ensemble_id'])
            if state['stage']!='complete' or _ensemble_subject(state)!=ref['sha256']: raise ValueError('排练的实际成稿/调用已变化')
            continue
        if read_utf8(project / ref['path'])[1] != ref['sha256']: raise ValueError('产物来源已变化：' + ref['path'])
        if ref['kind']=='reference_samples':
            import reference_library
            if reference_library.validate_file(project/ref['path'],ref['work_ids'])!=ref['collection_gate']:raise ValueError('参考库采集/语义范围已变化')
        if ref['kind'] in ('candidate', 'run_review'):
            import creative_workflow as flow
            root, m = flow._manifest(project, ref['run_id'])
            import writing_spec
            writing_spec.assert_run(project,ref['run_id'],require_review=ref['kind']=='run_review')
            key = 'current_candidate' if ref['kind'] == 'candidate' else 'latest_review'
            if not m.get(key) or (root / m[key]).relative_to(project).as_posix() != ref['path'] or m['candidate_sha'] != ref['candidate_sha256']:
                raise ValueError('当前Run正文/审稿版本已推进，旧阶段结论过期')
            if 'revision_gate_sha256' in ref:
                import directed_revision
                if hashed(directed_revision.assert_ready(project, ref['run_id'])) != ref['revision_gate_sha256']:
                    raise ValueError('定向修订验收已变化，阶段核验过期')


def _ensemble_subject(state):
    return hashed({k:v for k,v in state.items() if k not in ('handoff',)})


def _artifact(version):
    index = obj(version / 'index.json')
    seals = obj(version / 'seal.json')
    for name in ('work.md', 'index.json'):
        if read_utf8(version / name)[1] != seals[name]: raise ValueError('已归档阶段产物被修改')
    return index, read_utf8(version / 'work.md')[0], seals


def _targets(contract, stage, index):
    targets = ['criterion:' + k for k in contract['catalog']['stages'][stage]['checks']]
    targets += ['item:' + x['id'] for x in index['items']]
    if stage in ('brief', 'delivery'): targets += ['requirement:' + x['id'] for x in contract['requirements']]
    if stage in ('draft','revision') and contract.get('writing_spec'):
        targets += ['writing:' + x['id'] for x in contract['writing_spec']['requirements']]
        targets += ['prose:category:'+key for key in index['prose_scan']['category_requirements']]
        targets += ['prose:finding:'+f['id'] for f in index['prose_scan']['findings']]
    if stage=='research' and contract.get('reference_books'):targets+=['reference:collection','reference:claim_scope']
    return targets


def _packet(dest, contract, stage, version):
    index, work, seals = _artifact(version)
    packet = {'pipeline_id': contract['pipeline_id'], 'stage': stage, 'version': int(version.name[1:]),
              'profile': contract['profile'], 'mode': contract['mode'], 'author_input': contract['author_input'],
              'requirements': contract['requirements'], 'contract': contract['catalog']['stages'][stage],
              'items': index['items'], 'work': work, 'work_sha256': seals['work.md'],
              'review_targets': _targets(contract, stage, index), 'upstream': index['upstream'],
              'context_notice': 'editor_only; not a character packet; receipt is host-reported, not attested'}
    # Only stage works are loaded. Never include engine state/character private ledgers.
    prior = contract['stages'][:contract['stages'].index(stage)]
    packet['previous_work'] = {s: read_utf8(_latest(dest, s) / 'work.md')[0] for s in prior}
    if stage=='research' and contract.get('reference_books'):
        packet['reference_books']=contract['reference_books']
        packet['reference_collection_gates']=[x['collection_gate'] for x in index['sources'] if x['kind']=='reference_samples']
    if contract.get('writing_spec'):
        packet['writing_spec'] = contract['writing_spec']
    if stage in ('draft','revision') and contract.get('writing_spec'):
        import writing_spec
        import creative_workflow as flow
        ref=next(x for x in index['sources'] if x['kind']=='candidate')
        root,m=flow._manifest(dest.parents[1],ref['run_id'])
        body=read_utf8(root/m['current_candidate'])[0]; cm=obj(root/m['content_map']); offset=work.index(body)
        packet['writing_scope_spans']={
            'writing:'+rule['id']:[[a+offset,b+offset] for a,b in writing_spec.scope_spans(dest.parents[1],m['chapter_id'],cm,rule['scope'])]
            for rule in contract['writing_spec']['requirements']}
        packet['prose_scan']=index['prose_scan']
        import prose_risks
        packet['prose_rule_cards']=prose_risks.review_packet(dest.parents[1],m['chapter_id'],body)['matched_public_rule_cards']
        packet['prose_scope_spans']={'prose:category:'+key:[[offset,offset+len(body)]] for key in index['prose_scan']['category_requirements']}
        packet['prose_scope_spans'].update({'prose:finding:'+f['id']:[[offset+f['start'],offset+f['end']]] for f in index['prose_scan']['findings']})
    if len(pretty(packet)) > 200000: raise ValueError('审查包超过200000字符，不截断；拆小任务')
    packet['packet_sha256'] = hashed(packet)
    return packet


def _validate_report(packet, report, receipt, producer):
    exact(report, ('packet_sha256', 'checks', 'unresolved', 'limitations', 'read_sha256'))
    exact(receipt, ('source', 'worker_id', 'invocation_id', 'host_thread_id', 'context_claim'))
    if receipt['source'] != packet['mode']: raise ValueError('合成与真实审查来源不能混用')
    for key in ('worker_id', 'invocation_id', 'context_claim'): text(receipt[key], key)
    if receipt['worker_id'] == producer['worker_id'] or receipt['invocation_id'] == producer['invocation_id']:
        raise ValueError('生产者自评不能作为独立阶段出口')
    if receipt['host_thread_id'] is not None: text(receipt['host_thread_id'], 'host_thread_id')
    if report['packet_sha256'] != packet['packet_sha256'] or report['read_sha256'] != packet['work_sha256']:
        raise ValueError('审查包/实际阅读作品版本不匹配，禁止重放')
    text(report['limitations'], '审查局限')
    if not isinstance(report['unresolved'], list) or any(not isinstance(x, str) or not x.strip() for x in report['unresolved']): raise ValueError('unresolved必须为文本数组')
    checks = report['checks']
    if not isinstance(checks, list) or any(not isinstance(x, dict) for x in checks): raise ValueError('checks必须为对象数组')
    if len(checks) != len(packet['review_targets']) or {x.get('target') for x in checks} != set(packet['review_targets']): raise ValueError('审查未逐项完整覆盖或有重复项')
    item_map = {'item:' + x['id']: x for x in packet['items']}
    for check in checks:
        exact(check, ('target', 'verdict', 'reason', 'citations'))
        if check['verdict'] not in ('pass', 'revise', 'unknown'): raise ValueError('未知审查结论')
        text(check['reason'], '判断理由')
        if not isinstance(check['citations'], list) or not check['citations']: raise ValueError('每项必须提供实际作品引文')
        spans = [locate(packet['work'], cite, packet['work_sha256']) for cite in check['citations']]
        if check['target'] in item_map:
            item = item_map[check['target']]
            if not any(s['start'] >= item['start'] and s['end'] <= item['end'] for s in spans): raise ValueError('条目审查引文未落在该条目作品范围')
        if check['target'].startswith('writing:'):
            ranges=packet.get('writing_scope_spans',{}).get(check['target'],[])
            if not all(any(a<=s['start']<s['end']<=b for a,b in ranges) for s in spans): raise ValueError('创作细节证据不在对应剧情正文范围')
        if check['target'].startswith('prose:'):
            ranges=packet.get('prose_scope_spans',{}).get(check['target'],[])
            if check['target'].startswith('prose:finding:'):
                if not any(s['start']<=a<b<=s['end'] for a,b in ranges for s in spans): raise ValueError('风格线索复审须完整引用该命中，不可只引用其中单字')
                body_ranges=packet['prose_scope_spans'][next(k for k in packet['prose_scope_spans'] if k.startswith('prose:category:'))]
                if not all(any(a<=s['start']<s['end']<=b for a,b in body_ranges) for s in spans): raise ValueError('风格引文须在实际正文内')
            elif not all(any(a<=s['start']<s['end']<=b for a,b in ranges) for s in spans): raise ValueError('风格复审须引用该项实际正文片段')
    return not report['unresolved'] and all(x['verdict'] == 'pass' for x in checks)


def status(project, pid):
    dest, contract = load(project, pid)
    reason = None
    try: _current(project, contract)
    except (ValueError, OSError) as exc: reason = str(exc)
    result, tokens = [], {}
    for stage in contract['stages']:
        version = _latest(dest, stage)
        row = {'stage': stage, 'state': 'missing', 'ready': False, 'version': None}
        if version:
            row['version'] = int(version.name[1:])
            try:
                index, work, seals = _artifact(version)
                if reason: raise ValueError(reason)
                if index['upstream'] != tokens: raise ValueError('上游版本/核验已变化或尚未通过')
                _verify_refs(project, index['sources'])
                reviews = sorted(version.glob('gate-*.json'), key=lambda p: int(p.stem.split('-')[1]))
                row['state'] = 'needs_review'
                if reviews:
                    gate = obj(reviews[-1]); number = gate['number']
                    report = obj(version / f'review-{number}.json'); receipt = obj(version / f'receipt-{number}.json')
                    if hashed(report) != gate['review_sha256'] or hashed(receipt) != gate['receipt_sha256']: raise ValueError('审查或回执被修改')
                    passed = _validate_report(_packet(dest, contract, stage, version), report, receipt, index['producer'])
                    row.update(state='ready' if passed else 'requires_revision', ready=passed,
                               deterministic_pass=True, evidence_coverage_complete=True, semantic_review_satisfied=passed)
                    if passed:
                        token = hashed({'version': row['version'], 'seals': seals, 'gate': gate})
                        row['gate_sha256'] = token
            except (OSError, ValueError, KeyError, TypeError) as exc:
                row.update(state='stale', reason=str(exc), ready=False)
        result.append(row)
        if row['ready']: tokens[stage] = row['gate_sha256']
        else: tokens[stage] = None
    complete = all(x['ready'] for x in result)
    return {'pipeline_id': pid, 'profile': contract['profile'], 'mode': contract['mode'], 'stages': result,
            'complete': complete, 'next_stage': next((x['stage'] for x in result if not x['ready']), None),
            'assurance': 'synthetic_test_only' if contract['mode'] == 'synthetic_test' else 'host_reported_semantic_review',
            'author_approved': False, 'canon_effect': 'none', 'literary_truth_verified': False}


def _upstream(project, pid, stage):
    dest, contract = load(project, pid)
    _current(project, contract)
    if stage not in contract['stages']: raise ValueError('该阶段不属于当前任务路径')
    state = status(project, pid)
    prior = state['stages'][:contract['stages'].index(stage)]
    if any(not x['ready'] for x in prior): raise ValueError('上游阶段未核验通过，禁止跳阶段')
    return dest, contract, {x['stage']: x['gate_sha256'] for x in prior}


def submit(project, pid, stage, spec):
    author_destination(project)
    dest, contract, upstream = _upstream(project, pid, stage)
    exact(spec, ('work', 'items', 'producer'), ('sources',))
    work = text(spec['work'], '阶段实际作品')
    if stage=='scene_plan' and contract.get('writing_spec'):
        import writing_spec
        work += '\n\n## 引擎核对的硬篇幅预算\n\n' + writing_spec.render_budget(project,contract['scope'][0])
    exact(spec['producer'], ('worker_id', 'invocation_id'))
    for key in spec['producer']: text(spec['producer'][key], key)
    items = spec['items']
    if not isinstance(items, list) or not 1 <= len(items) <= 256: raise ValueError('作品索引必须为1–256项')
    sections = contract['catalog']['stages'][stage]['sections']
    seen, normalized = set(), []
    for item in items:
        exact(item, ('id', 'section', 'quote', 'meaning'), ('start', 'end'))
        if not isinstance(item['id'], str) or not ITEM.fullmatch(item['id']) or item['id'] in seen: raise ValueError('产物条目ID无效/重复')
        seen.add(item['id'])
        if item['section'] not in sections: raise ValueError('未知产物维度')
        text(item['meaning'], '条目作用')
        if isinstance(item['quote'], str) and re.fullmatch(r'#{1,6}\s+[^\n]+', item['quote'].strip()):
            raise ValueError('作品索引须锚定实际内容，不能只引标题')
        cite = locate(work, item)
        normalized.append({**item, 'start': cite['start'], 'end': cite['end']})
    if {x['section'] for x in items} != set(sections): raise ValueError('阶段作品缺少必需维度')
    refs = _sources(project, contract, spec.get('sources', []), stage)
    if stage in ('draft', 'revision'):
        # The entire engine candidate must be present, not just its title or checksum.
        for ref in refs:
            if ref['kind'] == 'candidate' and read_utf8(project / ref['path'])[0] not in work:
                raise ValueError('正文阶段必须包含实际Run完整候选全文')
    if stage == 'rehearsal':
        import ensemble_runtime as ensemble
        for ref in refs:
            if ref['kind'] == 'ensemble' and ensemble._load(project, ref['ensemble_id'])[1]['candidate'] not in work:
                raise ValueError('排练作品必须包含实际完成的可读候选；私密账本不交给审查者')
    if stage == 'editorial':
        for ref in refs:
            if ref['kind'] == 'run_review' and read_utf8(project / ref['path'])[0] not in work:
                raise ValueError('审稿产物必须包含实际Run审稿报告，不能以通过标签代替')
    if stage == 'diagnosis' and contract['profile'] == 'revise':
        for ref in refs:
            if ref['kind'] == 'baseline' and read_utf8(project / ref['path'])[0] not in work:
                raise ValueError('修订诊断必须包含确切原稿全文与问题/保护范围')
    prior = _latest(dest, stage)
    number = int(prior.name[1:]) + 1 if prior else 1
    if number > contract['budget']['versions_per_stage']: raise ValueError('阶段修订预算耗尽，保存阻塞与新方案后显式新建流程')
    base = dest / stage
    temp = base / ('.initializing-' + uuid4().hex)
    index = {'items': normalized, 'producer': spec['producer'], 'sources': refs, 'upstream': upstream}
    if stage in ('draft','revision') and 'prose_risks' in contract:
        import prose_risks
        body=read_utf8(project/next(x['path'] for x in refs if x['kind']=='candidate'))[0]
        index['prose_scan']=prose_risks.scan(project,contract['scope'][0],body)
    new(temp / 'work.md', work); new(temp / 'index.json', pretty(index))
    new(temp / 'seal.json', pretty({name: read_utf8(temp / name)[1] for name in ('work.md', 'index.json')}))
    final = base / f'v{number}'
    no_symlink_components(final)
    os.rename(temp, final)
    return {'stage': stage, 'version': number, 'state': 'needs_review', 'work': str(final / 'work.md')}


def packet(project, pid, stage):
    dest, contract, upstream = _upstream(project, pid, stage)
    version = _latest(dest, stage)
    if not version: raise ValueError('先提交该阶段的实际作品')
    index, _, _ = _artifact(version)
    if index['upstream'] != upstream: raise ValueError('阶段作品依赖已过期，先修订作品')
    _verify_refs(project, index['sources'])
    return _packet(dest, contract, stage, version)


def review(project, pid, stage, report, receipt):
    author_destination(project)
    current = packet(project, pid, stage)
    dest, contract = load(project, pid)
    version = _latest(dest, stage)
    index, _, _ = _artifact(version)
    passed = _validate_report(current, report, receipt, index['producer'])
    numbers = [int(p.stem.split('-')[1]) for p in version.glob('review-*.json')]
    number = max(numbers, default=0) + 1
    if number > contract['budget']['reviews_per_version']: raise ValueError('该版本审查预算耗尽')
    new(version / f'review-{number}.json', pretty(report))
    new(version / f'receipt-{number}.json', pretty(receipt))
    new(version / f'gate-{number}.json', pretty({'number': number, 'review_sha256': hashed(report), 'receipt_sha256': hashed(receipt)}))
    return {'stage': stage, 'state': 'ready' if passed else 'requires_revision',
            'deterministic_pass': True, 'evidence_coverage_complete': True, 'semantic_review_satisfied': passed,
            'provenance': 'host_reported_not_attested', 'author_approved': False}


def assert_operation(project, chapter, operation, run_id=None):
    pid = registry(project).get(chapter)
    if not pid: return {'assurance': 'legacy_unverified'}
    state = status(project, pid)
    dest, contract = load(project, pid)
    table = {'draft': {'start': 'scene_plan', 'submit': 'rehearsal', 'review': 'draft', 'approve': 'delivery', 'publish': 'delivery'},
             'revise': {'start': 'diagnosis', 'submit': 'diagnosis', 'review': 'revision', 'approve': 'delivery', 'publish': 'delivery'}}
    needed = table[contract['profile']][operation]
    if contract['profile'] == 'revise' and operation == 'review':
        # Initial baseline review must precede directed_revision.plan. The new
        # candidate still requires the separate revision gate before re-review.
        import creative_workflow as flow
        _, manifest = flow._manifest(project, run_id)
        baseline_version = _latest(dest, 'diagnosis')
        if baseline_version and not manifest.get('current_revision'):
            diagnosis, _, _ = _artifact(baseline_version)
            if manifest['candidate_sha'] in {x['sha256'] for x in diagnosis['sources'] if x['kind'] == 'baseline'}:
                needed = 'diagnosis'
    if not next(x for x in state['stages'] if x['stage'] == needed)['ready']: raise ValueError('阶段门槛未通过：' + needed)
    if operation in ('approve', 'publish'):
        if contract['mode'] == 'synthetic_test': raise ValueError('合成测试流程不能批准/发布')
        import creative_workflow as flow
        _, m = flow._manifest(project, run_id)
        source_stage = 'draft' if contract['profile'] == 'draft' else 'revision'
        index, _, _ = _artifact(_latest(dest, source_stage))
        expected = [x for x in index['sources'] if x['kind'] == 'candidate' and x['run_id'] == run_id and x['sha256'] == m['candidate_sha']]
        editorial, _, _ = _artifact(_latest(dest, 'editorial'))
        matching = [x for x in editorial['sources'] if x['kind'] == 'run_review' and x['run_id'] == run_id and x['sha256'] == m.get('review_sha256') and x['candidate_sha256'] == m['candidate_sha']]
        if not expected or not matching: raise ValueError('交付核验未绑定当前Run正文/审稿版本')
    return state


def assert_submission(project, chapter, content, revision_apply=False):
    pid = registry(project).get(chapter)
    if not pid: return
    dest, contract = load(project, pid)
    if contract['profile'] != 'revise' or revision_apply: return
    diagnosis, _, _ = _artifact(_latest(dest, 'diagnosis'))
    if sha(content.encode('utf-8')) not in {x['sha256'] for x in diagnosis['sources'] if x['kind'] == 'baseline'}:
        raise ValueError('修订流程只可直接提交诊断原稿；新稿必须由revision-plan/apply派生')


def assert_response_source(project, chapter, source):
    pid = registry(project).get(chapter)
    if not pid: return
    _, contract = load(project, pid)
    if contract['mode'] == 'host_supplied' and source != 'host_supplied':
        raise ValueError('托管真实排练/组章不能接收manual或synthetic_test响应；来源字符串仍不是宿主隔离证明')


def is_revision_baseline(project, chapter, content):
    pid=registry(project).get(chapter)
    if not pid: return False
    dest,contract=load(project,pid)
    if contract['profile']!='revise': return False
    version=_latest(dest,'diagnosis')
    if not version: return False
    index,_,_=_artifact(version)
    return sha(content.encode('utf-8')) in {x['sha256'] for x in index['sources'] if x['kind']=='baseline'}
