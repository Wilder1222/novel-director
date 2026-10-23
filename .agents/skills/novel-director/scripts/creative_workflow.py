"""V0.5 evidence-verified filesystem-first novel collaboration with explicit approval and immutable candidates.

No LLM is called. Agents or authors supply drafts and JSON reviews. The runtime
holds them until the author explicitly approves and publishes the exact bytes.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import json
import os
import re
import tempfile
from evidence_audit import verify_review, no_symlink_components, read_utf8, PROJECT_SOURCES, author_destination

RUNS='.novel_runs'
CHAPTER_ID=re.compile(r'^V\d{2,3}-C\d{2,4}$')
SCORE_DIMENSIONS=('plot','characters','emotion','mystery','continuity','prose')
SOURCE_FILES=('project.json','canon.json','characters.json','chapters.json','clues.json','events.json','knowledge.json','versions.json','trips.json','presences.json','artifacts.json','rewrites.json','causal_edges.json')


def timestamp():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def digest(content: bytes):return sha256(content).hexdigest()
def getjson(path:Path):return json.loads(path.read_text(encoding='utf8'))
def _pretty(x):return json.dumps(x,ensure_ascii=False,indent=2)+'\n'
def _absent_symlink(path:Path):
    no_symlink_components(path)


def atomic_write(path:Path, text:str, replace:bool=False):
    """Write a new file atomically. For existing files require explicit replace."""
    author_destination(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    _absent_symlink(path.parent)
    if path.exists() and not replace: raise FileExistsError(f'拒绝覆盖：{path}')
    fd,tmp=tempfile.mkstemp(prefix='.novel-tmp-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf8',newline='') as f:
            f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def signature(project:Path):
    # Runtime V0.5 includes craft constraints and all current manuscript chapters.
    paths = set(PROJECT_SOURCES)
    # Optional v0.8 sources do not change the signature of projects that lack them.
    for name in ('writing_profile.json','writing_spec.json','prose_risks.json'):
        _absent_symlink(project/name)
        if (project/name).exists():
            paths.add(name)
    manuscript = project/'manuscript'
    _absent_symlink(manuscript)
    if manuscript.exists():
        for item in manuscript.glob('*.md'):
            _absent_symlink(item)
            paths.add(str(item.relative_to(project)))
    state = {}
    for name in sorted(paths):
        path = project/name
        _absent_symlink(path)
        state[name] = digest(path.read_bytes()) if path.exists() else '-'
    return digest(json.dumps(state,sort_keys=True).encode('utf8'))


def _run_dir(project:Path,run_id:str):
    if not re.fullmatch(r'run-[0-9a-f]{12}',run_id):raise ValueError('run_id 格式错误')
    base=project/RUNS
    _absent_symlink(base)
    folder=base/run_id
    _absent_symlink(folder)
    if not folder.is_dir(): raise FileNotFoundError(f'不存在的创作 Run：{run_id}')
    return folder


def _manifest(project:Path,run_id:str):
    folder=_run_dir(project,run_id)
    _absent_symlink(folder/'manifest.json')
    manifest=getjson(folder/'manifest.json')
    if manifest.get('run_id')!=run_id:raise ValueError('Run 文件标识不一致')
    for key,pattern in (('current_candidate',r'candidate-v[1-9]\d*\.md'),('latest_review',r'review-v[1-9]\d*\.json')):
        filename=manifest.get(key)
        if filename is not None:
            if not isinstance(filename,str) or not re.fullmatch(pattern,filename):
                raise ValueError(f'Run 内部路径字段不安全：{key}')
            _absent_symlink(folder/filename)
    return folder,manifest


def _update(folder:Path,m:dict, action:str, **details):
    m['updated_at']=timestamp()
    m.setdefault('journal',[]).append({'at':m['updated_at'],'action':action,'details':details})
    atomic_write(folder/'manifest.json',_pretty(m),replace=True)


def _chapters(project:Path):
    return {c['id']:c for c in getjson(project/'chapters.json')['chapters']}


def start(project:Path,chapter_id:str, *, run_id:str|None=None):
    author_destination(project)
    project=project.resolve()
    from stage_gates import assert_operation
    assert_operation(project, chapter_id, 'start')
    if not CHAPTER_ID.fullmatch(chapter_id):raise ValueError('章节 ID 格式错误')
    chapters=_chapters(project)
    if chapter_id not in chapters:raise ValueError('未登记的章节，先建立章卡')
    chapter=chapters[chapter_id]
    run_id=run_id or 'run-'+uuid4().hex[:12]
    if not re.fullmatch(r'run-[0-9a-f]{12}', run_id):raise ValueError('run_id格式错误')
    final_dir=project/RUNS/run_id
    _absent_symlink(final_dir)
    if final_dir.exists():raise FileExistsError('Run已存在，拒绝覆盖')
    # Publish the complete initial directory only after both contract and manifest exist.
    run_dir=project/RUNS/('.initializing-'+run_id+'-'+uuid4().hex[:12])
    _absent_symlink(run_dir)
    run_dir.mkdir(parents=True,exist_ok=False)
    _absent_symlink(run_dir)
    manuscript=project/'manuscript'/f'{chapter_id}.md'
    _absent_symlink(manuscript)
    original_sha=digest(manuscript.read_bytes()) if manuscript.exists() else None
    plan={'chapter_id':chapter_id,'title':chapter.get('title'), 'pov':chapter.get('pov'),
          'history_id':chapter.get('history_id'),'in_world_at':chapter.get('in_world_at'),
          'goal':chapter.get('goal'),'conflict':chapter.get('conflict'),
          'choice':chapter.get('choice'),'change':chapter.get('change'),
          'allowed_current_chapter_clue_ids':[],
          'constraints':{'do_not_auto_update_canon':True,'do_not_assume_future_chapter':True,'use_matching_history':True},
          'writing_tasks':[
              {'role':'story-architect','deliverable':'检查本章因果与前后承接'},
              {'role':'character-director','deliverable':'核对角色目标与关系铺垫'},
              {'role':'chapter-writer','deliverable':'本章候选小说正文'},
              {'role':'continuity-auditor','deliverable':'提供确定性审校证据'},
              {'role':'development-editor','deliverable':'按六维标准提交 JSON 审稿'}]}
    for clue in getjson(project/'clues.json').get('clues',[]):
        if chapter_id in (clue.get('setup_chapter'),clue.get('payoff_chapter')):
            plan['allowed_current_chapter_clue_ids'].append(clue['id'])
    import writing_spec
    spec = writing_spec.metadata(project, chapter_id)
    if spec is not None:
        plan['writing_spec'] = spec
        import prose_risks
        plan['prose_risks'] = prose_risks.metadata(project)
    atomic_write(run_dir/'contract.json',_pretty(plan))
    manifest={'runtime_version':'0.5.0','contract_sha256':digest((run_dir/'contract.json').read_bytes()),'run_id':run_id,'chapter_id':chapter_id,'status':'planned',
              'created_at':timestamp(),'updated_at':timestamp(),'source_signature':signature(project),
              'existing_manuscript_sha':original_sha,'current_candidate':None,
              'candidate_sha':None,'latest_review':None,'approval':None,
              'journal':[{'at':timestamp(),'action':'start'}]}
    atomic_write(run_dir/'manifest.json',_pretty(manifest))
    os.rename(run_dir,final_dir)
    return {'run_id':run_id,'state':manifest['status'],'directory':str(final_dir),'contract':str(final_dir/'contract.json')}


def _read_draft(path:Path):
    path=path.expanduser()
    _absent_symlink(path)
    path=path.resolve()
    if not path.is_file() or path.suffix.lower() not in ('.md','.txt'):
        raise ValueError('候选稿必须是可读取的 .md/.txt 普通文本文件')
    _absent_symlink(path)
    raw=path.read_bytes()
    if len(raw)>4*1024*1024:raise ValueError('候选稿超过4 MiB，拒绝一次性提交')
    try:text=raw.decode('utf8')
    except UnicodeDecodeError:raise ValueError('候选稿必须是 UTF-8') from None
    if len(text.strip()) < 30:raise ValueError('正文过短，无法作为章节候选稿')
    return text


def submit(project:Path,run_id:str,draft_file:Path, *, _revision_apply:bool=False, content_map:dict|None=None):
    project=project.resolve();folder,m=_manifest(project,run_id)
    from stage_gates import assert_operation
    assert_operation(project, m['chapter_id'], 'submit', run_id)
    if m['status'] not in ('planned','drafted','reviewed'):
        raise ValueError('当前状态不能更换候选稿')
    if m.get('current_revision') and not _revision_apply:
        raise ValueError('当前稿件绑定定向修订；请用新的 revision-plan/apply 或另建 Run，不可绕过验收')
    text=_read_draft(draft_file)
    from stage_gates import assert_submission
    assert_submission(project, m['chapter_id'], text, _revision_apply)
    import writing_spec
    writing_spec.assert_contract(project, m['chapter_id'], getjson(folder/'contract.json'))
    from stage_gates import is_revision_baseline
    baseline = not _revision_apply and is_revision_baseline(project, m['chapter_id'], text)
    checked = None
    if writing_spec.load(project) is not None:
        if baseline:
            try: checked = writing_spec.check(project, m['chapter_id'], text, content_map)
            except ValueError: checked = None  # Original remains diagnostic evidence, never a compliant new draft.
        else: checked = writing_spec.check(project, m['chapter_id'], text, content_map)
    elif content_map is not None: raise ValueError('没有writing_spec不能提交内容映射')
    n=1
    while (folder/f'candidate-v{n}.md').exists():n+=1
    dest=folder/f'candidate-v{n}.md'
    atomic_write(dest,text)
    if writing_spec.load(project) is not None:
        m['writing_baseline'] = baseline
        m['content_map'] = None
        m['content_map_sha256'] = None
        if checked:
            map_path = dest.with_suffix('.map.json')
            atomic_write(map_path, _pretty(checked['content_map']))
            m.update(content_map=map_path.name, content_map_sha256=digest(map_path.read_bytes()))
    m.update(status='drafted',current_candidate=dest.name,candidate_sha=digest(dest.read_bytes()),
             latest_review=None,approval=None)
    m.pop('current_revision',None)
    _update(folder,m,'submit',candidate=dest.name,sha=m['candidate_sha'])
    return {'run_id':run_id,'state':m['status'],'candidate':dest.name,'sha256':m['candidate_sha']}


def _validate_review(report):
    if not isinstance(report,dict) or report.get('reviewer_type') not in ('agent','human'):
        raise ValueError('审稿报告 reviewer_type 应为 agent 或 human')
    issues=report.get('issues')
    if not isinstance(issues,list):raise ValueError('审稿报告必须提供 issues 数组')
    for item in issues:
        if not isinstance(item,dict) or item.get('severity') not in ('BLOCKING','MAJOR','MINOR'):
            raise ValueError('issue severity 应为 BLOCKING/MAJOR/MINOR')
        if not isinstance(item.get('evidence'),str) or not item['evidence'].strip() or not isinstance(item.get('code'),str) or not item['code'].strip():
            raise ValueError('每条审稿问题必须提供证据 evidence 和 code')
    if not isinstance(report.get('scores',{}),dict):raise ValueError('scores 必须是对象')
    for dim,score in report.get('scores',{}).items():
        if dim not in SCORE_DIMENSIONS:raise ValueError(f'未知评分维度 {dim}')
        if not isinstance(score,dict) or not isinstance(score.get('score'),(int,float)) or isinstance(score.get('score'),bool) or not 0<=score['score']<=5 or not isinstance(score.get('evidence'),str) or not score['evidence'].strip():
            raise ValueError(f'{dim} 评分需 0~5 并提供引文/定位证据')


def review(project:Path,run_id:str,review_file:Path):
    project=project.resolve();folder,m=_manifest(project,run_id)
    from stage_gates import assert_operation
    assert_operation(project, m['chapter_id'], 'review', run_id)
    import writing_spec
    writing_spec.assert_run(project, run_id)
    if m['status'] not in ('drafted','reviewed'):raise ValueError('只有待审稿或待重审正文可以进入审稿')
    draft=folder/m['current_candidate']
    if digest(draft.read_bytes())!=m['candidate_sha']:raise ValueError('候选正文在提交后发生变化')
    _absent_symlink(review_file)
    data=json.loads(read_utf8(review_file)[0])
    _validate_review(data)
    data, evidence_result = verify_review(project, draft, data)
    if writing_spec.load(project) is not None and not m.get('writing_baseline'):
        content_map = getjson(folder/m['content_map'])
        data['writing_spec_review'] = writing_spec.verify_review(project, m['chapter_id'], read_utf8(draft)[0], content_map,
            data.get('writing_spec_review'), require_satisfied=False)
        import prose_risks
        data['prose_risks_review'] = prose_risks.verify_report(project,m['chapter_id'],read_utf8(draft)[0],data.get('prose_risks_review'),require_resolved=False)
        prose_risks.assert_issue_coverage(data['prose_risks_review'],data['issues'])
    data.update(reviewed_candidate_sha256=m['candidate_sha'],reviewed_at=timestamp())
    n=1
    while (folder/f'review-v{n}.json').exists():n+=1
    dest=folder/f'review-v{n}.json'
    atomic_write(dest,_pretty(data))
    m.update(status='reviewed',latest_review=dest.name,review_sha256=digest(dest.read_bytes()),approval=None)
    _update(folder,m,'review',review=dest.name)
    blocking=sum(x['severity']=='BLOCKING' for x in data['issues'])
    return {'run_id':run_id,'state':m['status'],'blocking':blocking,'review':dest.name,'evidence_audit':evidence_result}


def _check_contract(folder:Path,m:dict):
    contract=folder/'contract.json'
    _absent_symlink(contract)
    if m.get('runtime_version')!='0.5.0' or digest(contract.read_bytes())!=m.get('contract_sha256'):
        raise ValueError('旧版 Run 或创作契约已变更，请创建新 Run 并重新审稿')


def approve(project:Path,run_id:str,by:str):
    project=project.resolve();folder,m=_manifest(project,run_id)
    from stage_gates import assert_operation
    assert_operation(project, m['chapter_id'], 'approve', run_id)
    import writing_spec
    writing_spec.assert_run(project, run_id, require_review=True, final_operation=True)
    if m['status']!='reviewed':raise ValueError('只有已审稿正文可以审批')
    if not isinstance(by,str) or not by.strip():raise ValueError('必须显式提供执行审批者标识')
    draft=folder/m['current_candidate'];reviewp=folder/m['latest_review']
    if digest(draft.read_bytes())!=m['candidate_sha']:raise ValueError('正文内容变化，必须重新提交')
    _check_contract(folder,m)
    reviewdata=getjson(reviewp)
    _validate_review(reviewdata)
    verify_review(project,draft,reviewdata)
    if digest(reviewp.read_bytes())!=m.get('review_sha256'):
        raise ValueError('审稿文件已改变或属于未绑定的旧版报告，请重新审稿')
    if reviewdata.get('reviewed_candidate_sha256')!=m['candidate_sha']:
        raise ValueError('审稿记录没有与候选版本绑定')
    if any(x['severity']=='BLOCKING' for x in reviewdata['issues']):
        raise ValueError('审稿存在 BLOCKING 问题，必须修订候选稿后重新审稿')
    if signature(project)!=m['source_signature']:
        raise ValueError('故事设定或章节大纲已变更；必须重新创建本章 Run 进行审稿')
    if m.get('current_revision'):
        from directed_revision import assert_ready
        assert_ready(project,run_id)
    # This is an explicit local CLI approval action, not identity authentication.
    m['approval']={'by':by.strip(),'approved_at':timestamp(),
                   'candidate_sha256':m['candidate_sha'],'review_sha256':digest(reviewp.read_bytes()),
                   'source_signature':m['source_signature'],'approval_mode':'explicit_cli_action'}
    m['status']='approved'
    _update(folder,m,'approve',by=by.strip())
    return {'run_id':run_id,'state':'approved','by':by.strip()}


def publish(project:Path,run_id:str,replace=False):
    project=project.resolve();folder,m=_manifest(project,run_id)
    from stage_gates import assert_operation
    assert_operation(project, m['chapter_id'], 'publish', run_id)
    import writing_spec
    writing_spec.assert_run(project, run_id, require_review=True, final_operation=True)
    if m['status']!='approved' or not m.get('approval'):
        raise ValueError('稿件未获得显式批准，不能发布')
    _check_contract(folder,m)
    candidate=folder/m['current_candidate'];reviewp=folder/m['latest_review']
    report=getjson(reviewp)
    _validate_review(report)
    verify_review(project,candidate,report)
    approval=m['approval']
    if digest(candidate.read_bytes())!=approval['candidate_sha256'] or digest(reviewp.read_bytes())!=approval['review_sha256']:
        raise ValueError('稿件或审稿在批准后遭到修改，拒绝发布')
    if signature(project)!=approval['source_signature']:
        raise ValueError('项目设定变化，发布需要新一轮审稿与批准')
    if m.get('current_revision'):
        from directed_revision import assert_ready
        assert_ready(project,run_id)
    target=project/'manuscript'/f'{m["chapter_id"]}.md'
    _absent_symlink(target);_absent_symlink(target.parent)
    if target.exists():
        if not replace:raise FileExistsError('已有正式章节，只有显式 --replace 才可替换')
        old_sha=digest(target.read_bytes())
        if old_sha!=m['existing_manuscript_sha']:raise ValueError('正式稿已变更，拒绝盲目覆盖')
        backup=project/'manuscript'/'.history'/f'{m["chapter_id"]}.{old_sha[:16]}.md'
        atomic_write(backup,read_utf8(target)[0])
    elif m['existing_manuscript_sha'] is not None:
        raise ValueError('原稿在此期间被删除；不接受旧审批直接创建')
    atomic_write(target,read_utf8(candidate)[0],replace=replace)
    m.update(status='published',published_file=str(target.relative_to(project)),
             published_sha256=digest(target.read_bytes()))
    _update(folder,m,'publish',path=str(target.relative_to(project)))
    return {'run_id':run_id,'state':m['status'],'published':str(target),'sha256':m['published_sha256']}


def status(project:Path,run_id:str):
    folder,m=_manifest(project.resolve(),run_id)
    return {'run_id':run_id,'chapter_id':m['chapter_id'],'state':m['status'],
            'current_candidate':m.get('current_candidate'),'latest_review':m.get('latest_review'),
            'approval':m.get('approval'),'history':m.get('journal',[])}


def quality_report(project:Path,run_id:str):
    folder,m=_manifest(project.resolve(),run_id)
    reports=[]
    if m['status']=='planned': reports.append(('INFO','PLAN_ONLY','尚未提交候选正文'))
    if m.get('current_candidate'):
        text=(folder/m['current_candidate']).read_text(encoding='utf8')
        if len(text)<250: reports.append(('WARN','SHORT_DRAFT','中文章节不到250字符，可能只是片段'))
        if text.count('“')!=text.count('”'): reports.append(('WARN','QUOTES_UNBALANCED','中文引号可能不匹配'))
    score=None;by_dimension={};evidence_result={'verified':False,'reason':'尚未审稿'}
    if m.get('latest_review'):
        rev=getjson(folder/m['latest_review'])
        try:
            _,evidence_result=verify_review(project,folder/m['current_candidate'],rev)
        except (ValueError,OSError) as exc:
            evidence_result={'verified':False,'reason':str(exc)}
        for dim,v in rev.get('scores',{}).items():by_dimension[dim]=v['score']
        if by_dimension:score=round(sum(by_dimension.values())/len(by_dimension),2)
        for issue in rev['issues']:
            reports.append((issue['severity'],issue['code'],issue['evidence']))
    return {'run_id':run_id,'state':m['status'],'reviewed_dimensions':by_dimension,
            'indicative_editor_score':score,'issues':reports,'evidence_audit':evidence_result,
            'warning':'评分是输入的审稿判断，不是模型自动理解文学质量的客观指标'}
