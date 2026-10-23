"""Validate and retrieve evidence-bound model close-reading reports, never authorship proof."""
from pathlib import Path
import hashlib
import json
import re
from evidence_audit import read_utf8

FIELDS=('event','character','emotion','detail','setup','bridge')
DIMENSIONS=('world','plot','character','emotion','detail','setup')


def source_context_sha(work):
    """Bind the actual identity, source rows and anchors without study-file cycles."""
    keys=('id','title','author','genre','source_identity','counter','unicode_version','expected_numbers','chapters','claim_scope')
    context={key:work.get(key) for key in keys}
    return hashlib.sha256(json.dumps(context,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()


def chapter_map(work):
    rows=work.get('chapters')
    if not isinstance(rows,list) or any(not isinstance(c,dict) or type(c.get('number')) is not int or c['number']<1 for c in rows):raise ValueError('细读来源章节无效')
    numbers=[c['number'] for c in rows]
    if numbers!=sorted(set(numbers)):raise ValueError('细读来源章号重复或无序')
    return {c['number']:c for c in rows}


def payload_sha(report):
    payload={k:v for k,v in report.items() if k!='peer_review'}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()


def nonempty(value,label):
    if not isinstance(value,str) or not value.strip() or len(value)>20000 or value.strip() in ('TODO','TBD','待补','待分析','未完成','略'):raise ValueError(label+'须为实际非空分析文本')


def validate(work,report,require_host=True):
    if not isinstance(report,dict) or report.get('schema_version')!='1' or report.get('work_id')!=work['id']:raise ValueError('细读档案身份不符')
    producer=report.get('producer',{})
    if not isinstance(producer,dict):raise ValueError('细读执行者须为对象')
    if not producer.get('worker_id') or not producer.get('invocation_id'):raise ValueError('细读须有实际执行者和调用标识')
    if producer.get('source') not in ('host_supplied','synthetic_test') or (require_host and producer['source']!='host_supplied'):raise ValueError('正式参考不能采用合成细读报告')
    numbers=report.get('read_numbers');notes=report.get('chapter_notes')
    if not isinstance(numbers,list) or not 20<=len(numbers)<=50 or any(type(n) is not int for n in numbers) or numbers!=sorted(set(numbers)):raise ValueError('每部实际细读须为20–50个不同有序章号')
    if not isinstance(notes,list) or any(not isinstance(n,dict) for n in notes) or [n.get('number') for n in notes]!=numbers:raise ValueError('细读声明与逐章分析不一致')
    if len({tuple(str(n.get(f,'')) for f in ('event','character','bridge')) for n in notes})!=len(notes):raise ValueError('不能复制同一事件/人物/承接摘要充作逐章细读')
    chapters=chapter_map(work)
    if report.get('source_context_sha256')!=source_context_sha(work):raise ValueError('细读审查所绑定作品/来源/短证据已改版')
    if set(numbers)-chapters.keys():raise ValueError('细读章号没有实际采集正文')
    if set(work['claim_scope']['semantic_numbers'])!=set(numbers):raise ValueError('作品语义范围与实际细读档案不一致')
    valid_anchors={};known_nonstory={};seen_anchor_ids=set()
    nonstory=report.get('nonstory_paragraphs',[])
    if not isinstance(nonstory,list):raise ValueError('非故事段注释须为列表')
    for item in nonstory:
        if not isinstance(item,dict):raise ValueError('非故事段注释须为对象')
        n=item.get('chapter');indices=item.get('paragraphs')
        if n not in chapters or not isinstance(indices,list) or any(type(p) is not int or not 1<=p<=chapters[n]['paragraphs'] for p in indices):raise ValueError('非故事段注释位置无效')
        if item.get('exclude_from_story_evidence') is True or item.get('kind') in ('author_note','web_noise','separator'):
            known_nonstory.setdefault(n,set()).update(indices)
    for note in notes:
        n=note['number'];chapter=chapters[n]
        if note.get('body_sha256')!=chapter['body_sha256']:raise ValueError('细读引用了其他版本正文')
        for field in FIELDS:nonempty(note.get(field),'逐章'+field)
        anchors=chapter.get('reading_evidence',[])
        if not isinstance(anchors,list) or any(not isinstance(e,dict) for e in anchors):raise ValueError('短证据须为对象列表')
        by_id={e.get('id'):e for e in anchors}
        if len(by_id)!=len(anchors) or any(not isinstance(i,str) or not i for i in by_id):raise ValueError('短证据ID重复或无效')
        paras=chapter.get('paragraph_records',[])
        if not isinstance(paras,list) or any(not isinstance(p,dict) for p in paras) or len(paras)!=chapter['paragraphs'] or [p.get('number') for p in paras]!=list(range(1,len(paras)+1)):raise ValueError('逐段元数据不完整')
        for p in paras:valid_anchors[f'paragraph:{n}:{p["number"]}']=(n,p['number'])
        for e in anchors:
            aid=e.get('id')
            if not isinstance(aid,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}',aid) or aid in seen_anchor_ids:raise ValueError('短证据ID须全书唯一且不能冒充段落定位')
            seen_anchor_ids.add(aid)
            p=e.get('paragraph');quote=e.get('quote');start=e.get('start');end=e.get('end')
            if type(p) is not int or not 1<=p<=len(paras) or not isinstance(quote,str) or not 8<=len(quote)<=12 or type(start) is not int or type(end) is not int or end-start!=len(quote) or not 0<=start<end<=paras[p-1]['codepoints']:raise ValueError('短锚位置/长度不合法')
            if e.get('paragraph_sha256')!=paras[p-1]['sha256'] or e.get('body_sha256')!=chapter['body_sha256']:raise ValueError('短锚正文/段落版本不符')
            valid_anchors[e['id']]=(n,p)
        evidence=note.get('evidence')
        if not isinstance(evidence,list) or len(evidence)<2 or len(set(evidence))!=len(evidence) or any(e not in by_id for e in evidence):raise ValueError('每章分析需两个不同的实际短证据')
        if len({by_id[e]['paragraph'] for e in evidence})<2:raise ValueError('每章分析证据须来自不同段落')
        if any(by_id[e]['paragraph'] in known_nonstory.get(n,set()) for e in evidence):raise ValueError('作者作话不能冒充故事证据')
    cards=report.get('techniques');seen=set();dimensions=set()
    if not isinstance(cards,list) or not cards:raise ValueError('不能以阅读方向标签冒充技巧索引')
    for card in cards:
        if not isinstance(card,dict):raise ValueError('技巧卡须为对象')
        cid=card.get('id')
        if not isinstance(cid,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}',cid) or cid in seen:raise ValueError('技巧ID重复或无效')
        seen.add(cid);dimension=card.get('dimension')
        if dimension not in DIMENSIONS:raise ValueError('未知技巧维度')
        dimensions.add(dimension)
        for field in ('method','preconditions','limits','original_exercise'):nonempty(card.get(field),'技巧'+field)
        evidence=card.get('evidence')
        if not isinstance(evidence,list) or not evidence or len(set(evidence))!=len(evidence) or any(e not in valid_anchors for e in evidence):raise ValueError('技巧无有效章段出处')
        if any(valid_anchors[e][1] in known_nonstory.get(valid_anchors[e][0],set()) for e in evidence):raise ValueError('技巧不能以作者作话为情节证据')
    if dimensions!=set(DIMENSIONS):raise ValueError('技巧未覆盖世界/情节/人物/情感/细节/铺垫六维')
    if not isinstance(report.get('cross_chapter'),list) or len(report['cross_chapter'])<3:raise ValueError('缺跨章变化链分析')
    for text in report['cross_chapter']:nonempty(text,'跨章变化链')
    nonempty(report.get('limitations'),'细读范围与局限')
    review=report.get('peer_review',{})
    if not isinstance(review,dict):raise ValueError('细读审查须为对象')
    if review.get('reviewed_payload_sha256')!=payload_sha(report):raise ValueError('细读审查过期或正文/技巧已改版')
    allowed=('host_supplied',) if require_host else ('host_supplied','synthetic_test')
    if not review.get('reviewer_id') or review['reviewer_id']==producer['worker_id'] or review.get('source') not in allowed:raise ValueError('细读须由不同实际执行者审查，不是身份认证')
    targets={f'chapter:{n}' for n in numbers}|{f'technique:{i}' for i in seen}|{'scope'}
    checks=review.get('checks',[])
    if not isinstance(checks,list) or any(not isinstance(c,dict) for c in checks) or len(checks)!=len(targets) or {c.get('target') for c in checks}!=targets or review.get('unresolved')!=[]:raise ValueError('细读独立审查未覆盖全部章/技巧或存在未决')
    for check in checks:
        if check.get('verdict')!='pass':raise ValueError('细读审查尚有未通过项')
        nonempty(check.get('reason'),'细读审查理由')
    nonempty(review.get('limitations'),'审查局限')
    return {'work_id':work['id'],'model_read_chapters':len(numbers),'chapter_notes':len(notes),'techniques':len(cards),'evidence_consistency':True,'assurance':'host_reported_model_reading_and_peer_review_not_attested','external_reader_acceptance':False}


def load(work,library):
    name=work.get('study_file')
    if not isinstance(name,str) or not re.fullmatch(r'studies/[a-z0-9-]+\.json',name):raise ValueError('未知或不安全的细读档案路径')
    text,sha=read_utf8(Path(library)/name)
    if sha!=work.get('study_sha256'):raise ValueError('细读投影已改版')
    report=json.loads(text);validate(work,report);return report


def evidence(work,identifier):
    chapters=chapter_map(work)
    if identifier.startswith('paragraph:'):
        _,number,paragraph=identifier.split(':');number=int(number);paragraph=int(paragraph)
        row=chapters[number];digest=row['paragraph_records'][paragraph-1]['sha256']
        return {'chapter':number,'title':row['title'],'url':row['url'],'body_sha256':row['body_sha256'],'paragraph':paragraph,'paragraph_sha256':digest,'kind':'paragraph_digest','notice':'段号对应本次采集分段，非平台固定行号'}
    for row in work['chapters']:
        for anchor in row.get('reading_evidence',[]):
            if anchor['id']==identifier:return {'chapter':row['number'],'title':row['title'],'url':row['url'],**anchor}
    raise ValueError('未知细读证据ID')


def _works(library,book=None):
    catalog=json.loads(read_utf8(Path(library)/'catalog.json')[0])
    if catalog.get('schema_version')!='1':raise ValueError('未知参考目录')
    import reference_library as refs
    refs.check_author_policy(catalog,catalog['works'])
    if book is not None and book not in {w['id'] for w in catalog['works']}:raise ValueError('未知参考作品ID')
    for summary in catalog['works']:
        if book is not None and summary['id']!=book:continue
        name=summary.get('file')
        if not isinstance(name,str) or not re.fullmatch(r'[a-z0-9-]+\.json',name):raise ValueError('参考作品路径无效')
        text,sha=read_utf8(Path(library)/name)
        if sha!=summary.get('sha256'):raise ValueError('参考作品投影已改版')
        work=json.loads(text)
        if work.get('id')!=summary['id']:raise ValueError('参考作品ID不一致')
        import reference_library as refs
        policy=catalog.get('sample_policy',{'schema_version':'1','minimum_per_work':50})
        refs.validate_samples({**policy,'excluded_authors':catalog.get('excluded_authors',[]),'works':[work]})
        if not work.get('study_file'):
            if policy.get('schema_version')=='2' and work['claim_scope']['semantic_numbers']:raise ValueError('当前全章细读声明缺实际分析档案')
            continue
        yield work,load(work,library)


def search(library,book=None,dimension=None,query=None):
    if dimension is not None and dimension not in DIMENSIONS:raise ValueError('未知技巧维度')
    result=[]
    for work,report in _works(library,book):
        for card in report['techniques']:
            if dimension and card['dimension']!=dimension:continue
            if query and query.casefold() not in json.dumps(card,ensure_ascii=False).casefold():continue
            result.append({'work_id':work['id'],'title':work['title'],'author':work.get('author'),**card,'sources':[evidence(work,e) for e in card['evidence']],'read_numbers':report['read_numbers'],'notice':'来自所列章节的模型分析；方法须按新作品前提迁移，不代表全书规律或外部验收。'})
    return result


def read(library,book,chapter=None):
    rows=list(_works(library,book))
    if not rows:raise ValueError('该作品尚无完整细读档案')
    work,report=rows[0]
    if chapter is None:return report
    note=next((n for n in report['chapter_notes'] if n['number']==chapter),None)
    if note is None:raise ValueError('该章未纳入本次实际细读范围')
    return {'work_id':book,'title':work['title'],**note,'sources':[evidence(work,e) for e in note['evidence']],'limitations':report['limitations']}
