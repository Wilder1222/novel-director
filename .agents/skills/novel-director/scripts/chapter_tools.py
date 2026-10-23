"""Frozen chapter assembly and evidence-bound arc reviews; never approvals."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import json
import re
import creative_workflow as flow
import ensemble_runtime as ensemble
from evidence_audit import read_utf8, no_symlink_components, locate, author_destination
from writing_profile import projection, GENRES

ASM = re.compile(r'asm-[a-f0-9]{12}')
MAX_CHARS = 200000


def _object(obj, required, optional=()):
    if not isinstance(obj, dict) or not set(required) <= obj.keys() or obj.keys() - set(required) - set(optional):
        raise ValueError('字段不完整或含未知字段')


def _folder(project, aid):
    if not isinstance(aid, str) or not ASM.fullmatch(aid):
        raise ValueError('assembly ID 不合法')
    path = project / '.novel_assemblies' / aid
    no_symlink_components(path)
    return path


def _save(folder, state, replace=False):
    flow.atomic_write(folder / 'state.json', flow._pretty(ensemble._seal(state)), replace=replace)


def _load(project, aid):
    folder = _folder(project, aid)
    state = json.loads(read_utf8(folder / 'state.json')[0])
    integrity = state.pop('integrity_sha256', None)
    if integrity != ensemble._hash(state) or state['assembly_id'] != aid:
        raise ValueError('组装记录已改变')
    if flow.signature(project) != state['source_signature']:
        raise ValueError('组装依赖的项目版本已改变')
    if 'prose_risks' in state:
        import prose_risks
        if state['prose_risks']!=prose_risks.metadata(project): raise ValueError('组章编辑语料/检查器已更新')
    for item in state['scenes']:
        _, original = ensemble._load(project, item['ensemble_id'])
        if original['stage'] != 'complete' or flow.digest(original['candidate'].encode('utf-8')) != item['candidate_sha256']:
            raise ValueError('场景候选版本已改变')
    return folder, state


def assembly_plan(project, chapter_id, spec):
    author_destination(project)
    from stage_gates import assert_operation
    assert_operation(project, chapter_id, 'submit')
    no_symlink_components(project)
    project = project.resolve()
    _object(spec, {'scene_ids'}, {'expected_scene_ids'})
    ids = spec['scene_ids']
    if not isinstance(ids, list) or not 2 <= len(ids) <= 24 or len(set(ids)) != len(ids):
        raise ValueError('整章组装需要2–24个不重复的完成场景')
    chapter = flow._chapters(project).get(chapter_id)
    if not chapter:
        raise ValueError('未登记章卡')
    scenes = []
    for sid in ids:
        _, state = ensemble._load(project, sid)
        sc = state['scene']
        if state['stage'] != 'complete' or sc['chapter_id'] != chapter_id or sc['history_id'] != chapter['history_id']:
            raise ValueError('场景未完成或不属于当前章/历史')
        pov = ensemble._instances(state['config'])[sc['pov_instance']]['character_id']
        if pov != chapter['pov']:
            raise ValueError('场景视角与章卡不符')
        if scenes and ensemble._time(sc['at']) < ensemble._time(scenes[-1]['at']):
            raise ValueError('场景时点逆序；闪回须另行明确设计，不能静默倒排')
        speech = [event['speech'] for event in state['events'] if event['reader_visible'] and sc['pov_instance'] in event['observers'] and event.get('speech')]
        scenes.append({'ensemble_id': sid, 'scene_id': sc['id'], 'at': sc['at'], 'location': sc['location'],
                       'pov_instance': sc['pov_instance'], 'text': state['candidate'], 'accepted_speech': speech,
                       'candidate_sha256': flow.digest(state['candidate'].encode('utf-8'))})
        if 'content_map' in state: scenes[-1]['content_map'] = deepcopy(state['content_map'])
    names = [item['scene_id'] for item in scenes]
    if len(set(names)) != len(names):
        raise ValueError('同一场景的不同排练不能重复算作不同场次')
    registered = []
    if (project / 'scenes.json').exists():
        registered = [s['id'] for s in sorted(flow.getjson(project / 'scenes.json').get('scenes', []), key=lambda s: s.get('order', 0)) if s.get('chapter_id') == chapter_id]
    expected = spec.get('expected_scene_ids', [])
    if (registered and names != registered) or (expected and names != expected):
        raise ValueError('选定场景遗漏或顺序不符合本章场景清单')
    aid = 'asm-' + uuid4().hex[:12]
    state = {'schema_version': '1', 'assembly_id': aid, 'stage': 'awaiting_narrator', 'chapter_id': chapter_id,
             'history_id': chapter['history_id'], 'pov': chapter['pov'], 'source_signature': flow.signature(project),
             'scenes': scenes, 'writing_profile': projection(project), 'handoff': None,
             'completeness_basis': 'registered_scene_list' if registered else 'explicit_scene_selection_requires_editorial_check'}
    import writing_spec
    if writing_spec.load(project) is not None:
        import prose_risks
        state['prose_risks']=prose_risks.metadata(project)
    folder = _folder(project, aid)
    folder.mkdir(parents=True, exist_ok=False)
    _save(folder, state)
    return {'assembly_id': aid, 'stage': state['stage'], 'canonical_write': False, 'completeness_basis': state['completeness_basis']}


def assembly_packet(project, aid):
    _, state = _load(project, aid)
    if state['stage'] != 'awaiting_narrator':
        raise ValueError('组装已交接，不重放')
    packet = {'role': 'chapter_compose', 'worker_id': 'narrator', 'session_key': aid + ':narrator:chapter_compose',
              'allowed_tools': [], 'context_policy': 'replace_with_scoped_packet',
              'system': '你是唯一narrator的独立整章汇编实例。只据当前包组织有序场景和转场，不读取其他phase。保留每场已采纳对白；不引入关键新事实、不替角色作出新选择。返回sections和场间transitions。结果仅为候选，完整性与语义仍需整章审稿。',
              'input': {'chapter_id': state['chapter_id'], 'history_id': state['history_id'], 'pov': state['pov'],
                        'scenes': deepcopy(state['scenes']), 'writing_profile': deepcopy(state['writing_profile'])},
              'response_contract': {'required': ['request_id', 'sections', 'transitions'],
                                    'section_fields': ['ensemble_id', 'text'], 'transitions_count': len(state['scenes']) - 1}}
    packet['request_id'] = ensemble._hash({'state': state, 'packet': packet})
    import writing_spec
    spec = writing_spec.projection(project, state['chapter_id'])
    if spec is not None:
        packet['input']['writing_spec'] = spec
        packet['response_contract']['optional'] = ['content_map','parts']
        packet['system'] += '\n遵守章节/每剧情硬LN范围；原文原序拼接可平移原map，重写sections可给按序parts:[{part_id,text}]，拼接须与含转场的整章逐字一致，由工具算SHA/偏移；也可给新的全文content_map。转场默认归前场最后部件并计数。'
        packet['request_id'] = ensemble._hash({'state': state, 'packet': {k:v for k,v in packet.items() if k!='request_id'}})
    if len(json.dumps(packet, ensure_ascii=False)) > MAX_CHARS:
        raise ValueError('整章包超过字符预算；缩小章节，不静默裁掉场景')
    return packet


def assembly_submit(project, aid, response, source='manual'):
    if source not in ensemble.SOURCES:
        raise ValueError('未知响应来源')
    folder = _folder(project, aid)
    with ensemble._lock(folder):
        _, state = _load(project, aid)
        from stage_gates import assert_operation
        assert_operation(project, state['chapter_id'], 'submit')
        from stage_gates import assert_response_source
        assert_response_source(project, state['chapter_id'], source)
        packet = assembly_packet(project, aid)
        import writing_spec
        production = writing_spec.load(project) is not None
        _object(response, {'request_id', 'sections', 'transitions'}, {'content_map','parts'} if production else ())
        if response['request_id'] != packet['request_id']:
            raise ValueError('组装请求已过期')
        sections, transitions = response['sections'], response['transitions']
        if not isinstance(sections, list) or len(sections) != len(state['scenes']):
            raise ValueError('成稿漏场或增加未登记场景')
        if not isinstance(transitions, list) or len(transitions) != len(sections) - 1 or any(not isinstance(x, str) or len(x) > 8000 for x in transitions):
            raise ValueError('转场数量或长度不符合契约')
        parts = []
        for index, (item, original) in enumerate(zip(sections, state['scenes'])):
            _object(item, {'ensemble_id', 'text'})
            if item['ensemble_id'] != original['ensemble_id'] or not isinstance(item['text'], str) or len(item['text'].strip()) < 30:
                raise ValueError('场景身份/顺序或正文长度不符')
            cursor = 0
            for speech in original['accepted_speech']:
                found = item['text'].find(speech, cursor)
                if found < 0:
                    raise ValueError('汇编遗漏、改变或倒排已采纳的对白')
                cursor = found + len(speech)
            if index:
                parts.extend(('\n\n***\n\n', transitions[index - 1], '\n\n'))
            parts.append(item['text'])
        text = ''.join(parts)
        if len(text) > MAX_CHARS:
            raise ValueError('整章候选超过字符预算')
        content_map = None
        if production:
            content_map = response.get('content_map')
            if 'parts' in response:
                if content_map is not None: raise ValueError('parts和content_map二选一')
                compiled,content_map=writing_spec.compile_parts(project,state['chapter_id'],response['parts'])
                if compiled!=text: raise ValueError('组章parts必须与sections及转场拼接逐字相同')
            cursor = 0; segments = []; section_spans = []
            for index, (item, original) in enumerate(zip(sections,state['scenes'])):
                if index:
                    bridge = '\n\n***\n\n' + transitions[index-1] + '\n\n'
                    if not content_map:
                        previous = state['scenes'][index-1]['content_map']['segments'][-1]['part_id']
                        segments.append({'part_id':previous,'start':cursor,'end':cursor+len(bridge)})
                    cursor += len(bridge)
                section_spans.append((cursor,cursor+len(item['text']),original['scene_id']))
                if not content_map:
                    if item['text'] != original['text'] or 'content_map' not in original:
                        raise ValueError('组章重写必须提供新的显式全文content_map')
                    segments.extend({**s,'start':s['start']+cursor,'end':s['end']+cursor} for s in original['content_map']['segments'])
                cursor += len(item['text'])
            if content_map is None: content_map = writing_spec.make_map(project,state['chapter_id'],text,segments)
            checked = writing_spec.check(project,state['chapter_id'],text,content_map)
            content_map = checked['content_map']
            part_scenes = {p['id']:p['scene_id'] for p in writing_spec._parts(writing_spec.chapter_spec(project,state['chapter_id']))}
            for begin,end,scene_id in section_spans:
                if any(max(begin,s['start']) < min(end,s['end']) and part_scenes[s['part_id']] != scene_id for s in content_map['segments']):
                    raise ValueError('组章映射把场景正文计入另一个场景的剧情预算')
        attempt = folder / ('attempt-' + uuid4().hex[:12])
        flow.atomic_write(attempt / 'response.json', flow._pretty(response))
        flow.atomic_write(attempt / 'candidate.md', text)
        # A stable handoff identity lets retry recover after the final state save fails.
        run_id = 'run-' + ensemble._hash({'assembly_id': aid})[:12]
        run_folder = project / flow.RUNS / run_id
        if not run_folder.exists():
            flow.start(project, state['chapter_id'], run_id=run_id)
        _, manifest = flow._manifest(project, run_id)
        flow._check_contract(run_folder, manifest)
        if manifest['chapter_id'] != state['chapter_id'] or manifest['source_signature'] != state['source_signature']:
            raise ValueError('固定交接Run身份或来源不符；先核对中断记录')
        if manifest['status'] == 'planned':
            result = flow.submit(project, run_id, attempt / 'candidate.md', content_map=content_map)
        elif manifest['status'] == 'drafted' and manifest['candidate_sha'] == flow.digest(text.encode('utf-8')) and read_utf8(run_folder / manifest['current_candidate'])[0] == text:
            recovered=writing_spec.assert_run(project,run_id)
            if production and recovered['content_map']!=content_map: raise ValueError('恢复Run的内容映射与本次原始parts不符，不可冒充相同交接')
            result = {'run_id': run_id, 'state': 'drafted', 'candidate': manifest['current_candidate'], 'sha256': manifest['candidate_sha']}
        else:
            raise ValueError('交接Run已改变或推进；不重复提交')
        state.update(stage='handed_off', handoff=result, response_source=source, response_digest=ensemble._hash(response))
        _save(folder, state, replace=True)
    return {**result, 'assembly_id': aid, 'semantic_review': 'required', 'canonical_write': False}


def arc_packet(project, chapters, budget=100000):
    no_symlink_components(project)
    if type(budget) is not int or not 1 <= budget <= MAX_CHARS:
        raise ValueError('跨章预算须为1–200000字符')
    known = flow._chapters(project)
    ordered = sorted(known, key=lambda cid: (known[cid]['volume'], known[cid]['number']))
    if not isinstance(chapters, list) or not 3 <= len(chapters) <= 5 or len(set(chapters)) != len(chapters) or any(cid not in known for cid in chapters):
        raise ValueError('跨章审查需要3–5个已登记、不重复的章节')
    positions = [ordered.index(cid) for cid in chapters]
    if positions != list(range(positions[0], positions[0] + len(chapters))):
        raise ValueError('跨章审查必须是有序的连续章节')
    sources, repeated = [], []
    paragraphs = {}
    for cid in chapters:
        if not flow.CHAPTER_ID.fullmatch(cid):
            raise ValueError('章节ID无效')
        text, sha = read_utf8(project / 'manuscript' / (cid + '.md'))
        sources.append({'chapter_id': cid, 'text': text, 'sha256': sha})
        for paragraph in text.splitlines():
            if len(paragraph.strip()) >= 40:
                paragraphs.setdefault(paragraph, []).append(cid)
    for text, occurrences in paragraphs.items():
        if len(occurrences) > 1:
            repeated.append({'quote': text, 'chapters': occurrences, 'classification': 'risk', 'notice': '可能是有意复沓；不得自动删除'})
    style = projection(project)
    packet = {'schema_version': '1', 'mode': 'arc_editor_only', 'scope': chapters, 'budget': budget,
              'source_signature': flow.signature(project), 'chapters': sources, 'writing_profile': style,
              'mechanical_hints': repeated,
              'questions': ['规则使用是否前后一致，代价是否消失？', '行动之间的因果与未兑现承诺是否清楚？',
                            '人物目标、知识和声音是否延续？', '关系触发、误读、回应和情绪余波是否有证据？',
                            '是否重复调查、解释或心理总结？有意复沓是否仍有作用？', '伏笔是否公平，当前阅读范围缺什么证据？'] + (style['genre_focus'] if style else []),
              'notice': '只包含选定正式稿，不证明这些文件有远程作者认证。审稿标self_review/cross_review/human，不自动更新任何Run或Canon。'}
    packet['request_id'] = ensemble._hash(packet)
    if type(budget) is not int or budget < 1 or len(json.dumps(packet, ensure_ascii=False)) > budget:
        raise ValueError('跨章材料超过预算，不静默丢章或裁去证据')
    return packet


def arc_accept(project, packet, report):
    _object(report, {'request_id', 'reviewer_type', 'issues', 'summary_citations'})
    if report['reviewer_type'] not in ('self_review', 'cross_review', 'human'):
        raise ValueError('审查来源须如实声明；同宿主审查不是外部读者验收')
    # Rebuild scope and hashes; neither supplied packet text nor its flags are trusted.
    current = arc_packet(project, packet['scope'], budget=packet['budget'])
    if current != packet or report['request_id'] != current['request_id']:
        raise ValueError('跨章包或其来源已改变')
    if not isinstance(report['issues'], list) or len(report['issues']) > 128:
        raise ValueError('issues须为数组，至多128项')
    normalized = deepcopy(report)
    groups = [normalized['summary_citations']]
    for issue in normalized['issues']:
        _object(issue, {'classification', 'explanation', 'citations'})
        if issue['classification'] not in ('error', 'risk', 'taste') or not isinstance(issue['explanation'], str) or not issue['explanation'].strip():
            raise ValueError('问题须区分确定错误、风险推论和审美建议，并解释')
        groups.append(issue['citations'])
    sources = {item['chapter_id']: item for item in current['chapters']}
    summary_seen = set()
    for index, citations in enumerate(groups):
        if not isinstance(citations, list) or not citations:
            raise ValueError('每个问题和阅读摘要须有真实引文')
        for ci, cite in enumerate(citations):
            if not isinstance(cite, dict) or cite.get('chapter_id') not in sources or cite.keys() - {'chapter_id', 'quote', 'start', 'end', 'sha256'}:
                raise ValueError('引用超出选定阅读范围或字段不符')
            cid = cite['chapter_id']; src = sources[cid]
            citations[ci] = {'chapter_id': cid, **locate(src['text'], {k: v for k, v in cite.items() if k != 'chapter_id'}, src['sha256'])}
            if index == 0:
                summary_seen.add(cid)
    if summary_seen != set(sources):
        raise ValueError('阅读摘要必须分别举证每个选定章节')
    rid = 'arc-' + uuid4().hex[:12]
    folder = project / '.novel_arc' / rid
    no_symlink_components(folder)
    flow.atomic_write(folder / 'packet.json', flow._pretty(current))
    flow.atomic_write(folder / 'review.json', flow._pretty(normalized))
    return {'arc_review_id': rid, 'citations_verified': True, 'semantic_support': 'not_evaluated',
            'reviewer_type': report['reviewer_type'], 'canonical_write': False, 'run_states_changed': False}
