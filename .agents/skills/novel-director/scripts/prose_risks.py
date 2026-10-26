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
 'stock_gesture':'语气/停顿、表情/目光、动作与对白是否同一次有依据的反应，先后及身体/空间条件是否成立；避免逐句配表演或标签代替现场表达，保护沉默、无动作短答和有意反差。',
 'decorative_detail':'环境/物件/背景是否有处境、氛围、节奏或质感功能。',
 'forced_elevation':'结尾升华、预告与感悟是否有当前叙事依据，而非统一套式。',
 'flattened_voice':'结合本人当前任务/goal、单向关系看法、性格/价值与声线、常态语气及当场回应，核称呼、语体、分寸、句式与口头禅是否实际适合；口癖按使用/回避条件判断，未出现口头禅不判错，不把性格绝对化。语气词、省略号/骤断、结巴、重复和改口须与情绪身体和实际反应相连；审情境需要却语句过平、人人同样断续及无功能标点堆叠。零命中也读语境，不设配额、不凭符号读心；保护有作用的重复/口头禅、稳定口吃、克制和正式/紧急短答。'}
CATEGORIES['flattened_voice']+=' 按交流段/场景/整章核对白密度及直接对白/概述取舍，判断重复事务是否拖沓、重要变化是否有承接、人物时空/身体是否仍可辨；保留有作用的快速对答，不设对白比例或句数硬阈值，不要求每句推动情节。'
CATEGORIES['stock_gesture']+=' 对白过密不能靠逐句微动作、无关景物或情绪标签稀释；只在变化处使用已有依据的叙述，不为平衡数量补事实。'
PARAMETERS={'max_codepoints':200000,'max_findings':256,'repeat_min_codepoints':12,'repeat_occurrences':2}
DENSITY_REVIEW_INSTRUCTION='按交流段、场景与整章核对白密度：直接对白/概述取舍、重要变化的反应与后果、人物位置/时限/身体锚点和整体节奏。快速对答、闲聊或长独白有作用可保留，不要求每句推进情节；不设对白比例或连续句数硬阈值。问题须引具体交流范围，说明缺失的作用、影响和有权限的修订路径，不只数引号；不靠逐句动作/心理/景物稀释。已采纳speech不因密度删改或概述，须退回场景/人物或显式修订；缺当前对照仍须保留不确定，不凭空补反应。'
GROWTH_REVIEW_INSTRUCTION='相关章节零命中也核自述、功法练习与晋升铺垫：当前视角的感知/回想/自我判断是否有许可，尝试、反馈、方法调整和局部结果是否具体；晋升的前证/门槛、过程选择、前后能力差异、稳定程度及代价是否依本书规则，是否把体感当客观成功。铺垫强化/回收须有真实前证与实际作用，不倒填前章或泄露未来答案。未要求的章节不硬塞修炼，不按篇幅/术语数量打分，不强制失败受伤；保护有作用的自述、平静练习和重复过程概述。将过程空泛、情绪复述或无功能解释归相应现有八类，引用实际范围、说明缺口及权限内修订路径；缺对照保留不确定，不能靠补内心/机制/新能力改稿。'
# Delivery clues, not errors or diagnoses. Preserve original codepoint offsets.
DIALOGUE_QUOTES=re.compile(r'“(?P<curly>[^“”]*)”|「(?P<corner>[^「」]*)」|『(?P<double_corner>[^『』]*)』|"(?P<straight>(?:[^"\\]|\\.)*)"')
DIALOGUE_RULES={
 'dialogue_pause':(re.compile(r'…+|\.{3,}|—+'),
                   '核省略号/破折号的迟延、话尾未尽或骤断是否有当场作用；不是心理诊断，不自动删改。'),
 'dialogue_restart':(re.compile(r'(?P<word>[\u3400-\u9fff]{1,8})[，,、…—\-。！？!?.]{1,8}(?P=word)|(?P<char>[\u3400-\u9fff])(?P=char){2,}'),
                     '核短词/短句重复、结巴或改口是否符合声线和当前交流；保护强调、复沓和稳定口吃，不一概当冗余。'),
 'dialogue_punctuation_stack':(re.compile(r'[！？!?]{2,}'),
                              '核问叹符号堆叠是否有语境作用或书风依据，不把强情绪等同叠标点。')}
BUILTIN_RULE_IDS=frozenset(DIALOGUE_RULES)|{'repeat_paragraph','repeat_sentence'}


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
        if row['id'] in ids or row['id'] in BUILTIN_RULE_IDS: raise ValueError('编辑案例ID重复/保留')
        ids.add(row['id'])
    protections=private['protections']
    if not isinstance(protections,list) or len(protections)>256: raise ValueError('片段保护最多256条')
    seen=set()
    for row in protections:
        exact(row,('id','chapter_id','rule_id','candidate_sha256','quote','start','end','reason','author_quote'))
        for k in ('id','chapter_id','rule_id','reason','author_quote','quote'):short(row[k])
        if row['id'] in seen or row['rule_id'] not in ids|BUILTIN_RULE_IDS: raise ValueError('保护ID重复或规则未登记')
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
    for quoted in DIALOGUE_QUOTES.finditer(text):
        group=quoted.lastgroup
        utterance=quoted.group(group);offset=quoted.start(group)
        for rule,(pattern,_) in DIALOGUE_RULES.items():
            match=pattern.search(utterance)
            if match is not None:
                add(rule,'flattened_voice',offset+match.start(),offset+match.end())
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
            'dialogue_rhythm_rules':{key:DIALOGUE_RULES[key][1] for key in DIALOGUE_RULES if key in ids},
            'private_cards_notice':'书内原始案例/作者确认原话不自动投影；主会话只提供已审安全的当前语境说明。',
            'instructions':DENSITY_REVIEW_INSTRUCTION+GROWTH_REVIEW_INSTRUCTION+'逐项读八类及所有线索，核对上下文、POV、人物声音与作用。以主会话提供的当场安全对照核任务、对象和单向关系、性格/价值、常态语气与当场情绪、口头禅使用/回避条件是否共同影响称呼、分寸、句式和策略；不因换对象变语气就判人格改变，未出现口头禅不判错。缺对照保留未知，不索取或转发私密总账。零命中也逐位发言者核对白是否过平、机械结巴/重复或标点堆叠；省略号、骤断、改口及重复可承载语气，不能按有无或数量判好坏。引号内书名/引文等可能误报；单引号、无引号或复杂嵌套未被完整识别时仍读全文，不把漏扫当合格。字面命中不定罪。保留合理重复/诗性/口头禅、稳定口吃、克制及正式短答；改写不添事实，不擅改已采纳speech。需改或不确定仍阻断；同模型不是外部读者。',
            'report_contract':{'required':['scan_id','categories','findings'],'category_verdicts':['clear','needs_revision','uncertain'],
                'finding_dispositions':['intentional','false_positive','needs_revision','uncertain'],
                'row_fields':['id','verdict或disposition','rationale','citations'],
                'needs_revision_issue_binding':'Run issue.prose_targets: category:ID 或 finding:ID'}}


def template(project):
    author_destination(project)
    path=project/'prose_risks.json'
    flow.atomic_write(path,flow._pretty({'schema_version':'1','entries':[],'protections':[]}))
    return {'path':str(path),'notice':'书内资料由主会话整理；不自动学习/上传，已有文件不覆盖。'}
