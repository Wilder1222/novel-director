"""Contextual prose editing, not AI authorship detection. Offline, no rewrites."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import re
import creative_workflow as flow
from evidence_audit import read_utf8,locate,no_symlink_components,author_destination

ASSET=Path(__file__).resolve().parents[1]/'assets/prose-risk-corpus.json'
CATEGORIES={
 'empty_situation':'抽象概念是否遮蔽人物的具体处境、世界限制和代价。',
 'emotion_restatement':'情绪命名是否重复，还是增加感受、判断、选择与余波。',
 'redundant_explanation':'行为之后的解释/总结是否增加信息、节奏或视角作用。',
 'imprecise_modifier':'修饰与意象是否准确贴合对象；不以短句/少形容词为唯一标准。',
 'stock_gesture':'动作/对白标签是否机械复现，是否符合人物当下身体与关系。',
 'decorative_detail':'环境/物件/背景是否有处境、氛围、节奏或质感功能。',
 'forced_elevation':'结尾升华、预告与感悟是否有当前叙事依据，而非统一套式。',
 'flattened_voice':'称呼是否有依据；对白是否随人设、场景、情绪与关系变化，避免统一腔调、轮流说明与舞台标签；保护有作用的口头禅和合理正式语体。'}
PARAMETERS={'max_codepoints':200000,'max_findings':256,'repeat_min_codepoints':12,'repeat_occurrences':2}


def exact(v,required,optional=()):
    if not isinstance(v,dict) or not set(required)<=v.keys() or v.keys()-set(required)-set(optional):
        raise ValueError('编辑语料/报告字段不完整或含未知字段')


def short(v):
    if not isinstance(v,str) or not v.strip() or len(v)>4000 or v.strip().lower() in ('todo','tbd','待补充','...'):
        raise ValueError('编辑案例与理由须为具体非空文本，不超过4000码点')


def _hash(v): return flow.digest(flow._pretty(v).encode('utf-8'))


def _entry(row):
    exact(row,('id','category','context','bad','revision','why','preserves','exceptions','valid_example','cues','source'))
    if not isinstance(row['id'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',row['id']): raise ValueError('编辑案例ID无效')
    if row['category'] not in CATEGORIES or row['source']!='original_editorial_example': raise ValueError('语料仅接受明确原创编辑案例与已知类别')
    for key in ('context','bad','revision','why','preserves','exceptions','valid_example'): short(row[key])
    if not isinstance(row['cues'],list) or not 1<=len(row['cues'])<=8 or len(set(row['cues']))!=len(row['cues']): raise ValueError('仅允许1–8条唯一字面线索，不执行正则')
    if any(not isinstance(c,str) or not 2<=len(c)<=80 or c not in row['bad'] for c in row['cues']): raise ValueError('线索须为问题示例中的2–80码点原文')


def corpus(project):
    raw,pubsha=read_utf8(ASSET); value=json.loads(raw)
    exact(value,('schema_version','version','categories','entries','notice'))
    if value['schema_version']!='1' or value['categories']!=CATEGORIES: raise ValueError('未知公共语料版本/分类')
    short(value['version']);short(value['notice'])
    private_path=project/'prose_risks.json';no_symlink_components(private_path)
    private_sha=None;private={'schema_version':'1','entries':[],'protections':[]}
    if private_path.exists():
        raw,private_sha=read_utf8(private_path);private=json.loads(raw)
        exact(private,('schema_version','entries','protections'))
        if private['schema_version']!='1': raise ValueError('未知书内编辑语料版本')
    if not isinstance(value['entries'],list) or not isinstance(private['entries'],list) or len(value['entries'])+len(private['entries'])>512:
        raise ValueError('公共/书内编辑案例合计最多512条')
    entries=deepcopy(value['entries']+private['entries']); ids=set()
    for row in entries:
        _entry(row)
        if row['id'] in ids or row['id'] in ('repeat_paragraph','repeat_sentence'): raise ValueError('编辑案例ID重复/保留')
        ids.add(row['id'])
    protections=private['protections']
    if not isinstance(protections,list) or len(protections)>256: raise ValueError('片段保护最多256条')
    seen=set()
    for row in protections:
        exact(row,('id','chapter_id','rule_id','candidate_sha256','quote','start','end','reason','author_quote'))
        for k in ('id','chapter_id','rule_id','reason','author_quote','quote'):short(row[k])
        if row['id'] in seen or row['rule_id'] not in ids|{'repeat_paragraph','repeat_sentence'}: raise ValueError('保护ID重复或规则未登记')
        seen.add(row['id'])
        if not isinstance(row['candidate_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',row['candidate_sha256']): raise ValueError('保护须绑定当前正文SHA')
        if type(row['start']) is not int or type(row['end']) is not int or not 0<=row['start']<row['end']<=PARAMETERS['max_codepoints']: raise ValueError('保护偏移不合法')
    return {'entries':entries,'protections':deepcopy(protections),'public_sha256':pubsha,'private_sha256':private_sha,
            'version':value['version']}


def metadata(project):
    c=corpus(project)
    return {'public_sha256':c['public_sha256'],'private_sha256':c['private_sha256'],'version':c['version'],
            'checker_sha256':read_utf8(Path(__file__))[1],'parameters':deepcopy(PARAMETERS)}


def scan(project,cid,text):
    if not isinstance(text,str) or not text.strip() or len(text)>PARAMETERS['max_codepoints']: raise ValueError('风格检查需1–200000码点实际正文，不静默截断')
    c=corpus(project); meta=metadata(project); body_sha=flow.digest(text.encode('utf-8'));findings=[]
    def add(rule,category,start,end):
        quote=text[start:end]
        finding={'rule_id':rule,'category':category,'start':start,'end':end,'quote':quote,'protected_by':[]}
        finding['id']='F'+_hash({'candidate':body_sha,'rule':rule,'start':start,'end':end})[:20]
        for keep in c['protections']:
            if keep['chapter_id']==cid and keep['rule_id']==rule and keep['candidate_sha256']==body_sha:
                if keep['start']<=start<end<=keep['end'] and text[keep['start']:keep['end']]==keep['quote']:
                    finding['protected_by'].append(keep['id'])
        findings.append(finding)
        if len(findings)>PARAMETERS['max_findings']: raise ValueError('编辑线索超过256条；显式缩小检查范围/调整策略，不截断后假称完成')
    for row in c['entries']:
        spans=set()
        for cue in row['cues']:
            start=0
            while (start:=text.find(cue,start))>=0:
                span=(start,start+len(cue))
                if span not in spans: add(row['id'],row['category'],*span);spans.add(span)
                start+=len(cue)
    for rule,pattern in [('repeat_paragraph',r'[^\r\n]+'),('repeat_sentence',r'[^\r\n。！？!?]+[。！？!?]')]:
        seen={}
        for match in re.finditer(pattern,text):
            raw=match.group();quote=raw.strip()
            if len(quote)<PARAMETERS['repeat_min_codepoints']:continue
            if not any('\u3400'<=x<='\u9fff' or x.isalnum() for x in quote):continue
            start=match.start()+len(raw)-len(raw.lstrip());end=start+len(quote)
            if quote in seen:add(rule,'redundant_explanation',start,end)
            seen[quote]=start
    findings.sort(key=lambda f:(f['start'],f['end'],f['rule_id']))
    result={'schema_version':'1','chapter_id':cid,'candidate_sha256':body_sha,'corpus':meta,'findings':findings,
            'category_requirements':deepcopy(CATEGORIES),'requires_context_review':True,'literary_quality_proven':False,
            'notice':'字面命中与重复仅为编辑线索；零命中不代表文风合格；不判断作者身份，不自动改稿。'}
    result['scan_id']=_hash(result)
    return result


def verify_report(project,cid,text,report,require_resolved=True):
    current=scan(project,cid,text)
    exact(report,('scan_id','categories','findings'))
    if report['scan_id']!=current['scan_id']: raise ValueError('正文/语料/保护/参数/检查器版本变化，须重扫重审')
    normalized=deepcopy(report)
    def rows(key,expected,verdict,choices):
        values=normalized[key]
        if not isinstance(values,list) or len(values)!=len(expected) or {r.get('id') for r in values if isinstance(r,dict)}!=set(expected): raise ValueError('编辑复审漏项/重复，包括零命中时的全类别阅读')
        for row in values:
            exact(row,('id',verdict,'rationale','citations'));short(row['rationale'])
            if row[verdict] not in choices: raise ValueError('未知编辑复审结论')
            if not isinstance(row['citations'],list) or not 1<=len(row['citations'])<=16: raise ValueError('编辑复审须有当前正文确切引文')
            cites=[locate(text,cite,current['candidate_sha256']) for cite in row['citations']]
            if key=='findings':
                f=expected[row['id']]
                if not any(x['start']<=f['start']<f['end']<=x['end'] for x in cites): raise ValueError('线索复审引文未覆盖被检查片段')
            row['citations']=cites
            if require_resolved and row[verdict] in ('needs_revision','uncertain'): raise ValueError('风格问题尚需改/不确定，登记处置不等于闭合')
    rows('categories',CATEGORIES,'verdict',{'clear','needs_revision','uncertain'})
    rows('findings',{f['id']:f for f in current['findings']},'disposition',{'intentional','false_positive','needs_revision','uncertain'})
    return normalized


def assert_issue_coverage(report,issues):
    needed={'category:'+r['id'] for r in report['categories'] if r['verdict']=='needs_revision'}
    needed|={'finding:'+r['id'] for r in report['findings'] if r['disposition']=='needs_revision'}
    covered=set()
    for issue in issues:
        values=issue.get('prose_targets',[])
        if not isinstance(values,list) or any(not isinstance(v,str) for v in values): raise ValueError('prose_targets必须是编辑目标ID列表')
        covered.update(values)
    if needed-covered: raise ValueError('需改的风格项须进入Run issues.prose_targets，再定向修改和重审')


def review_packet(project,cid,text):
    from writing_profile import projection
    current=scan(project,cid,text);ids={x['rule_id'] for x in current['findings']}
    public=json.loads(read_utf8(ASSET)[0])
    cards=[deepcopy(x) for x in public['entries'] if x['id'] in ids]
    return {'work':text,'scan':current,'writing_profile':projection(project),'matched_public_rule_cards':cards,
            'private_cards_notice':'书内原始案例/作者确认原话不自动投影；主会话只提供已审安全的当前语境说明。',
            'instructions':'逐项读八类及所有线索，核对上下文、POV、人物声音与作用。字面命中不定罪。保留合理重复/诗性/口头禅；改写不添事实。需改或不确定仍阻断；同模型不是外部读者。',
            'report_contract':{'required':['scan_id','categories','findings'],'category_verdicts':['clear','needs_revision','uncertain'],
                'finding_dispositions':['intentional','false_positive','needs_revision','uncertain'],
                'row_fields':['id','verdict或disposition','rationale','citations'],
                'needs_revision_issue_binding':'Run issue.prose_targets: category:ID 或 finding:ID'}}


def template(project):
    author_destination(project)
    path=project/'prose_risks.json'
    flow.atomic_write(path,flow._pretty({'schema_version':'1','entries':[],'protections':[]}))
    return {'path':str(path),'notice':'书内资料由主会话整理；不自动学习/上传，已有文件不覆盖。'}
