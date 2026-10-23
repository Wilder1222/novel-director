"""Hard prose budgets and evidence-bound craft requirements. Stdlib, no models.

Project counting is NOT a platform settlement algorithm. Semantic reports are
claims by reviewers, not proof of literary quality or authenticated identities.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import re
import unicodedata
from collections import deque
from evidence_audit import read_utf8, locate, project_source, author_destination
import creative_workflow as flow

COUNTER = 'letters_numbers_v1'
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')
CRAFT = {
    'character_naming': '人物默认用当前获准全名或已设绰号昵称；单姓称人有明确特殊语境，别称对应清楚，不补未知真名或临时造昵称；代词/职业关系称谓及完整复姓名不机械误判。',
    'dialogue_context': '对白措辞、语体、句长、接话和隐含意图符合人设、当时目标、场景、情绪身体状态与关系；自然口语，不统一腔调/说明轮流念/舞台标签。合理正式表达或无对白，须据当前原文说明，不强加口头禅或对白。',
    'character_agency': '重要人物的当时目标、所知、阻碍、选择依据与代价有实际行为/对白；反常选择有触发。',
    'character_specificity': '有服务处境与个性的辨识细节，不重复履历，不给每人机械填外貌/动作/心理配额。',
    'pov_knowledge': '观察与推断符合当前视角和可知范围，不直接读取他人私密心理。',
    'sensory_function': '具体观察服务环境压力、注意力、判断或关系，不堆五感形容；说明删去会损失什么。',
    'emotion_consequence': '重要情感变化有触发、理解、回应和余波，事件结束不自动重置关系；不默认爱情。',
    'exposition': '解释、背景和重复有当下叙事作用，不以总结、百科或重复信息填足最低字数。',
    'setup_strategy': '核对已计划的因果准备/情感积累/信息线索，无新增伏笔的说明成立；不强迫每章新埋或全回收。',
}


def exact(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError('创作规格字段不完整或含未知字段：' + ','.join(required))


def short(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000 or value.strip().lower() in ('todo','tbd','待填写','待补充','...'):
        raise ValueError(label + '必须是具体非空短文本')


def bounds(value):
    exact(value, ('min','max'))
    if type(value['min']) is not int or type(value['max']) is not int or not 1 <= value['min'] <= value['max'] <= 200000:
        raise ValueError('篇幅必须是1–200000的闭区间整数，min≤max')
    return value['min'], value['max']


def count(text):
    return sum(unicodedata.category(c)[0] in ('L','N') for c in text)


def template_value():
    return {'schema_version':'1', 'counter':COUNTER, 'origin':'tool_default',
            'defaults': {'chapter_range':{'min':3000,'max':6000}, 'plot_range':{'min':500,'max':2500}}, 'chapters':[]}


def _parts(chapter):
    return sorted([{**part, 'plot_id': unit['id']} for unit in chapter['plot_units'] for part in unit['parts']], key=lambda p:p['order'])


def _budget_feasible(chapter):
    """Exact integral lower-bound circulation for plot/scene shared capacity."""
    graph={}; demand={}
    def edge(u,v,capacity):
        graph.setdefault(u,[]); graph.setdefault(v,[])
        graph[u].append([v,capacity,len(graph[v])]); graph[v].append([u,0,len(graph[u])-1])
    def bounded(u,v,low,high):
        edge(u,v,high-low); demand[u]=demand.get(u,0)-low; demand[v]=demand.get(v,0)+low
    source,sink=('source',),('sink',)
    scenes=set()
    for unit in chapter['plot_units']:
        node=('plot',unit['id']); bounded(source,node,unit['range']['min'],unit['range']['max'])
        grouped={}
        for part in unit['parts']:
            scene=part['scene_id']; scenes.add(scene); low,high=grouped.get(scene,(0,0))
            grouped[scene]=(low+part['range']['min'],high+part['range']['max'])
        for scene,(low,high) in grouped.items(): bounded(node,('scene',scene),low,high)
    for scene in scenes: bounded(('scene',scene),sink,0,20000)
    bounded(sink,source,chapter['range']['min'],chapter['range']['max'])
    ss,tt=('super_source',),('super_sink',); needed=0
    for node,value in list(demand.items()):
        if value>0: edge(ss,node,value); needed+=value
        elif value<0: edge(node,tt,-value)
    total=0
    while total<needed:
        queue=deque([ss]); prev={ss:None}
        while queue and tt not in prev:
            node=queue.popleft()
            for index,(dest,capacity,_) in enumerate(graph.get(node,[])):
                if capacity>0 and dest not in prev: prev[dest]=(node,index); queue.append(dest)
        if tt not in prev: return False
        amount=needed-total; node=tt
        while node!=ss:
            parent,index=prev[node]; amount=min(amount,graph[parent][index][1]); node=parent
        node=tt
        while node!=ss:
            parent,index=prev[node]; current=graph[parent][index]
            current[1]-=amount; graph[node][current[2]][1]+=amount; node=parent
        total+=amount
    return True


def validate(project, value):
    exact(value, ('schema_version','counter','origin','defaults','chapters'))
    if value['schema_version'] != '1' or value['counter'] != COUNTER or value['origin'] not in ('tool_default','author_request','synthetic_test'):
        raise ValueError('未知创作规格/计数器/来源；默认值不是作者确认')
    exact(value['defaults'], ('chapter_range','plot_range'))
    for item in value['defaults'].values(): bounds(item)
    if not isinstance(value['chapters'], list) or len(value['chapters']) > 5000: raise ValueError('chapters必须为有限数组')
    chapters = flow._chapters(project); seen_chapters = set()
    for chapter in value['chapters']:
        exact(chapter, ('chapter_id','range','plot_units','detail_requirements','setups','setup_strategy'))
        cid = chapter['chapter_id']
        if cid not in chapters or cid in seen_chapters: raise ValueError('创作规格章节未登记或重复')
        seen_chapters.add(cid); low, high = bounds(chapter['range']); short(chapter['setup_strategy'], '铺垫承接策略')
        units = chapter['plot_units']
        if not isinstance(units, list) or not 1 <= len(units) <= 24: raise ValueError('章内必须有1–24个明确剧情单元')
        ids, part_ids, orders = set(), set(), set()
        effective = []
        for unit in units:
            exact(unit, ('id','purpose','range','parts'))
            uid = unit['id']
            if not isinstance(uid,str) or not NAME.fullmatch(uid) or uid in ids: raise ValueError('剧情ID无效/重复')
            ids.add(uid); short(unit['purpose'],'剧情任务'); umin, umax = bounds(unit['range'])
            if not isinstance(unit['parts'],list) or not 1 <= len(unit['parts']) <= 32: raise ValueError('剧情需明确分配场景/节拍部件')
            mins, maxs = [], []
            for part in unit['parts']:
                exact(part, ('id','scene_id','order','range','purpose'))
                if not isinstance(part['id'],str) or not NAME.fullmatch(part['id']) or part['id'] in part_ids: raise ValueError('部件ID无效/重复')
                part_ids.add(part['id']); short(part['scene_id'],'scene_id'); short(part['purpose'],'部件任务')
                if type(part['order']) is not int or part['order'] < 1 or part['order'] in orders: raise ValueError('部件顺序无效/重复')
                orders.add(part['order']); pmin,pmax = bounds(part['range']); mins.append(pmin); maxs.append(pmax)
            actual_min,actual_max = max(umin,sum(mins)),min(umax,sum(maxs))
            if actual_min > actual_max: raise ValueError('剧情与子部件预算无可行交集')
            effective.append((actual_min,actual_max))
        if max(low,sum(x[0] for x in effective)) > min(high,sum(x[1] for x in effective)):
            raise ValueError('章与剧情预算无可行交集')
        scene_sequence = []
        for part in _parts(chapter):
            if not scene_sequence or scene_sequence[-1] != part['scene_id']: scene_sequence.append(part['scene_id'])
        if len(scene_sequence) != len(set(scene_sequence)): raise ValueError('同一场景部件须连续，跨场回返另建场景实例')
        # The existing compose transport accepts at most 20000 codepoints.
        # LN cannot exceed raw codepoints; catch impossible lower bounds now.
        scene_capacity=0
        for scene_id in scene_sequence:
            scene_parts=[p for p in _parts(chapter) if p['scene_id']==scene_id]
            mandatory=max(sum(p['range']['min'] for p in scene_parts),
                          sum(u['range']['min'] for u in units if all(p['scene_id']==scene_id for p in u['parts'])))
            if mandatory>20000: raise ValueError('场景最低篇幅超过compose的20000原文码点上限，先拆分场景')
            scene_capacity+=min(20000,sum(p['range']['max'] for p in scene_parts))
        if max(low,sum(x[0] for x in effective))>scene_capacity: raise ValueError('章节最低预算超过全部场景执行容量')
        if not _budget_feasible(chapter): raise ValueError('章/剧情/共享场景容量无共同可行分配，先修改预算')
        registered_path = project / 'scenes.json'
        if registered_path.exists():
            registered = [s['id'] for s in sorted(flow.getjson(registered_path).get('scenes',[]), key=lambda s:s.get('order',0)) if s.get('chapter_id') == cid]
            if registered and registered != scene_sequence: raise ValueError('创作预算与已登记场景清单/顺序不符')
        rule_ids = set(CRAFT)
        for field in ('detail_requirements','setups'):
            if not isinstance(chapter[field],list) or len(chapter[field]) > 64: raise ValueError('细节/铺垫要求必须为有限数组')
            for rule in chapter[field]:
                required = ('id','scope','criterion') if field == 'detail_requirements' else ('id','scope','criterion','operation','prior')
                exact(rule,required,('completion',) if field=='setups' else ())
                if not isinstance(rule['id'],str) or not NAME.fullmatch(rule['id']) or rule['id'] in rule_ids: raise ValueError('细节/铺垫ID无效/重复')
                rule_ids.add(rule['id'])
                if rule['scope'] not in ids | {'chapter'}: raise ValueError('细节/铺垫scope不在当前章剧情内')
                short(rule['criterion'],'当前章可见要求')
                if field == 'setups':
                    if rule['operation'] not in ('plant','reinforce','payoff'): raise ValueError('未知铺垫操作')
                    if rule.get('completion','partial') not in ('partial','full'): raise ValueError('回收须区分局部解释或完整回收')
                    if not isinstance(rule['prior'],list) or len(rule['prior']) > 16 or (rule['operation'] in ('reinforce','payoff') and not rule['prior']):
                        raise ValueError('强化/回收须有此前实际证据；不能只在计划里登记')
                    for cite in rule['prior']:
                        exact(cite,('source','quote'),('start','end','sha256'))
                        short(cite['quote'],'前置证据')
                        if cite['source'] != 'candidate':
                            match = re.fullmatch(r'manuscript/(V\d{2,3}-C\d{2,4})\.md',cite['source'])
                            order=lambda c:(chapters[c].get('volume',0),chapters[c].get('number',0))
                            if not match or match[1] not in chapters or order(match[1])>=order(cid): raise ValueError('铺垫前证据须来自此前正式章或当前候选此前位置')
                            prior_text,digest = read_utf8(project_source(project,cite['source'])); locate(prior_text,cite,digest)
    return value


def load(project):
    path = project / 'writing_spec.json'
    from evidence_audit import no_symlink_components
    no_symlink_components(path)
    if not path.exists(): return None
    raw,digest = read_utf8(path); value=json.loads(raw); validate(project,value)
    return {'value':value,'sha256':digest,'counter':COUNTER,'unicode_version':unicodedata.unidata_version}


def chapter_spec(project,cid):
    spec=load(project)
    if spec is None: return None
    result=next((x for x in spec['value']['chapters'] if x['chapter_id']==cid),None)
    if result is None: raise ValueError('当前章尚无具体剧情/细节预算；主会话先按章卡完善writing_spec')
    return result


def metadata(project,cid):
    chapter=chapter_spec(project,cid)
    if chapter is None: return None
    source=load(project)
    return {'spec_sha256':source['sha256'],'counter':COUNTER,'unicode_version':source['unicode_version']}


def projection(project,cid,scene_id=None):
    chapter=chapter_spec(project,cid)
    if chapter is None: return None
    parts=_parts(chapter)
    if scene_id is not None:
        parts=[x for x in parts if x['scene_id']==scene_id]
        if not parts: raise ValueError('当前场景没有已计划的剧情预算')
    units={p['plot_id'] for p in parts}
    # Only current, explicitly safe requirements; never author-only world truth.
    fully_local={u['id'] for u in chapter['plot_units'] if all(p['scene_id']==scene_id for p in u['parts'])} if scene_id is not None else units
    rules=targets(project,cid)
    if scene_id is not None:
        rules=[r for r in rules if r['id'] in CRAFT or r['scope'] in fully_local]
    return {**metadata(project,cid),'chapter_id':cid,'chapter_range':chapter['range'],'parts':parts,
            'plot_units':[{**{k:v for k,v in x.items() if k not in ('parts','purpose')},
                           'purpose':x['purpose'] if x['id'] in fully_local else '跨场剧情；只执行当前parts的任务，不预写后场'} for x in chapter['plot_units'] if x['id'] in units],
            'requirements':rules, 'setup_strategy':chapter['setup_strategy'] if scene_id is None else '只呈现当前场景可见信息，不沿用后场计划或私密真相。',
            'count_notice':'项目正文LN计数，非平台结算；标题/PS/日志不属于正文。'}


def make_map(project,cid,text,segments):
    return {'schema_version':'1', **metadata(project,cid), 'chapter_id':cid,
            'candidate_sha256':flow.digest(text.encode('utf-8')),'segments':deepcopy(segments)}


def compile_parts(project,cid,parts,scene_id=None):
    """Join exact supplied prose; never ask a tool-free writer to invent hashes."""
    chapter=chapter_spec(project,cid)
    if chapter is None: raise ValueError('原始parts需要已登记规格')
    selected=[p for p in _parts(chapter) if scene_id is None or p['scene_id']==scene_id]
    if not isinstance(parts,list) or len(parts)!=len(selected): raise ValueError('原始parts须恰好覆盖当前范围的有序部件')
    chunks=[]; segments=[]; cursor=0
    for row,planned in zip(parts,selected):
        exact(row,('part_id','text'))
        if row['part_id']!=planned['id'] or not isinstance(row['text'],str) or not row['text'].strip():
            raise ValueError('原始parts身份/顺序/正文不符')
        end=cursor+len(row['text'])
        if end>200000: raise ValueError('原始parts正文超过200000码点，不截断')
        segments.append({'part_id':row['part_id'],'start':cursor,'end':end}); chunks.append(row['text']); cursor=end
    text=''.join(chunks); content_map=make_map(project,cid,text,segments)
    check(project,cid,text,content_map,scene_id=scene_id)
    return text,content_map


def check(project,cid,text,content_map=None,scene_id=None):
    chapter=chapter_spec(project,cid)
    if chapter is None:
        if content_map is not None: raise ValueError('没有规格不能伪称已核验内容映射')
        return {'status':'spec_not_configured','literary_quality_proven':False}
    if not isinstance(text,str) or not text.strip(): raise ValueError('创作规格需要实际正文')
    if re.search(r'(?m)^\s{0,3}#{1,6}\s+',text) or re.search(r'(?mi)^(?:PS\s*[:：]|作者(?:的话|有话说)\s*[:：])',text):
        raise ValueError('提交纯正文；标题/作者附言另存，不能用于凑字。隐含元信息仍须语义审查')
    parts=_parts(chapter); selected=[p for p in parts if scene_id is None or p['scene_id']==scene_id]
    if not selected: raise ValueError('当前场景没有预算')
    if isinstance(content_map,dict) and 'parts' in content_map:
        exact(content_map,('parts',))
        joined,content_map=compile_parts(project,cid,content_map['parts'],scene_id=scene_id)
        if joined!=text: raise ValueError('原始parts拼接须逐字等于实际正文，不能换文验收')
    if content_map is None:
        if len(selected)!=1: raise ValueError('多部件正文必须提供明确content_map，不推断剧情边界')
        content_map=make_map(project,cid,text,[{'part_id':selected[0]['id'],'start':0,'end':len(text)}])
    exact(content_map,('schema_version','spec_sha256','counter','unicode_version','chapter_id','candidate_sha256','segments'))
    if content_map['schema_version']!='1' or content_map['chapter_id']!=cid or content_map['candidate_sha256']!=flow.digest(text.encode('utf-8')):
        raise ValueError('正文映射版本/章节/SHA不匹配')
    for key,value in metadata(project,cid).items():
        if content_map[key]!=value: raise ValueError('规格/计数器/Unicode版本已变化，重建映射并重审')
    segments=content_map['segments']
    if not isinstance(segments,list) or not 1<=len(segments)<=1000: raise ValueError('segments须为有限非空数组')
    allowed={p['id']:p for p in selected}; totals={key:0 for key in allowed}; sequence=[]; cursor=0
    for segment in segments:
        exact(segment,('part_id','start','end'))
        key=segment['part_id']; start,end=segment['start'],segment['end']
        if key not in allowed or type(start) is not int or type(end) is not int or start!=cursor or not start<end<=len(text):
            raise ValueError('正文映射有遗漏、重叠、越界或未登记部件')
        totals[key]+=count(text[start:end]); cursor=end
        if not sequence or sequence[-1]!=key: sequence.append(key)
    if cursor!=len(text) or sequence!=[p['id'] for p in selected]: raise ValueError('正文尾部/部件清单/顺序未完整覆盖')
    plots={u['id']:0 for u in chapter['plot_units']}
    for key,n in totals.items():
        part=allowed[key]; low,high=bounds(part['range'])
        if not low<=n<=high: raise ValueError(f'部件{key}实际{n}不在硬范围{low}–{high}')
        plots[part['plot_id']]+=n
    for unit in chapter['plot_units']:
        if all(p['id'] in allowed for p in unit['parts']):
            low,high=bounds(unit['range']); actual=plots[unit['id']]
            if not low<=actual<=high: raise ValueError(f'剧情{unit["id"]}实际{actual}不在硬范围{low}–{high}')
    actual=count(text)
    if scene_id is None:
        low,high=bounds(chapter['range'])
        if not low<=actual<=high: raise ValueError(f'章节实际{actual}不在硬范围{low}–{high}')
    return {'status':'deterministic_pass','scope':'chapter' if scene_id is None else 'scene:'+scene_id,
            **metadata(project,cid),'candidate_sha256':content_map['candidate_sha256'], 'chapter_count':actual,
            'raw_codepoints':len(text),'part_counts':totals,'plot_counts':{k:v for k,v in plots.items() if v},
            'content_map':deepcopy(content_map),'literary_quality_proven':False}


def targets(project,cid):
    chapter=chapter_spec(project,cid)
    if chapter is None: return []
    result=[{'id':key,'scope':'chapter','criterion':value} for key,value in CRAFT.items()]
    for unit in chapter['plot_units']:
        for key,criterion in [('causality','剧情有实际触发、行动、阻碍/调整、结果与承接；短结算不为凑最低字数扩写。'),
                              ('functional_detail','关键过程/位置/物件可复原，具体观察服务选择或后果，不以总结替代展开。')]:
            result.append({'id':unit['id']+':'+key,'scope':unit['id'],'criterion':criterion})
    result.extend(deepcopy(chapter['detail_requirements']))
    result.extend({'id':'setup:'+x['id'],'scope':x['scope'],'criterion':x['criterion'],'operation':x['operation'],
                   'completion':x.get('completion','partial')} for x in chapter['setups'])
    return result


def scope_spans(project,cid,content_map,scope):
    if scope=='chapter': return [(0,max(x['end'] for x in content_map['segments']))]
    parts={p['id'] for p in _parts(chapter_spec(project,cid)) if p['plot_id']==scope}
    return [(x['start'],x['end']) for x in content_map['segments'] if x['part_id'] in parts]


def verify_review(project,cid,text,content_map,report,require_satisfied=True):
    checked=check(project,cid,text,content_map); content_map=checked['content_map']
    exact(report,('spec_sha256','candidate_sha256','checks'))
    if report['spec_sha256']!=metadata(project,cid)['spec_sha256'] or report['candidate_sha256']!=checked['candidate_sha256']:
        raise ValueError('细节/铺垫审查没有绑定当前规格和正文')
    rules={x['id']:x for x in targets(project,cid)}; rows=report['checks']
    if not isinstance(rows,list) or len(rows)!=len(rules) or {x.get('id') for x in rows if isinstance(x,dict)}!=set(rules):
        raise ValueError('人物/事件/细节/铺垫审查漏项或重复')
    result=deepcopy(report)
    for row in result['checks']:
        exact(row,('id','verdict','rationale','citations'))
        if row['verdict'] not in ('satisfied','partial','missing','contradicted','uncertain'): raise ValueError('未知创作规格语义结论')
        short(row['rationale'],'语义理由')
        if not isinstance(row['citations'],list) or not row['citations']: raise ValueError('每个细节要求须有当前正文证据')
        spans=scope_spans(project,cid,content_map,rules[row['id']]['scope'])
        cites=[locate(text,cite,checked['candidate_sha256']) for cite in row['citations']]
        if not all(any(a<=c['start']<c['end']<=b for a,b in spans) for c in cites): raise ValueError('细节证据不在指定剧情正文范围')
        row['citations']=cites
    for setup in chapter_spec(project,cid)['setups']:
        effect=next(row for row in result['checks'] if row['id']=='setup:'+setup['id'])
        for prior in setup['prior']:
            if prior['source']=='candidate':
                cite=locate(text,prior,checked['candidate_sha256'])
                if setup['operation']!='plant' and not any(cite['end']<=c['start'] for c in effect['citations']):
                    raise ValueError('回收/强化的前置证据没有早于当前作用证据')
            else:
                prior_text,digest=read_utf8(project_source(project,prior['source'])); locate(prior_text,prior,digest)
    if require_satisfied and any(x['verdict']!='satisfied' for x in rows): raise ValueError('细节/铺垫存在未解决或不确定判断，不能通过')
    return result


def assert_run(project,run_id,require_review=False,final_operation=False):
    root,m=flow._manifest(project,run_id)
    contract=flow.getjson(root/'contract.json')
    assert_contract(project,m['chapter_id'],contract)
    if load(project) is None: return {'status':'spec_not_configured','literary_quality_proven':False}
    flow._check_contract(root,m)
    if flow.signature(project)!=m['source_signature']: raise ValueError('Run故事/正文/规格来源已变化，不能沿用旧审查')
    if final_operation and load(project)['value']['origin']=='synthetic_test': raise ValueError('合成创作规格不能用于正式批准/发布')
    if m.get('writing_baseline'):
        if require_review: raise ValueError('诊断原稿不能冒充新规格合格稿批准')
        return {'status':'diagnostic_baseline_only','literary_quality_proven':False}
    if not m.get('current_candidate') or not m.get('content_map'): raise ValueError('Run缺少实际正文/映射')
    if m['content_map']!=Path(m['current_candidate']).stem+'.map.json': raise ValueError('Run映射路径不匹配正文版本')
    path=root/m['content_map']; raw,digest=read_utf8(path)
    if digest!=m.get('content_map_sha256'): raise ValueError('Run内容映射已改变')
    text,body_sha=read_utf8(root/m['current_candidate'])
    if body_sha!=m['candidate_sha']: raise ValueError('候选正文已改变')
    checked=check(project,m['chapter_id'],text,json.loads(raw))
    if require_review:
        if not m.get('latest_review'): raise ValueError('缺少当前细节审查')
        data=flow.getjson(root/m['latest_review'])
        verify_review(project,m['chapter_id'],text,checked['content_map'],data.get('writing_spec_review'))
        import prose_risks
        prose_risks.verify_report(project,m['chapter_id'],text,data.get('prose_risks_review'))
    return checked


def assert_contract(project,cid,contract):
    if contract.get('writing_spec')!=metadata(project,cid): raise ValueError('Run创作规格或计数版本已过期')
    if contract.get('writing_spec') is not None:
        import prose_risks
        if contract.get('prose_risks')!=prose_risks.metadata(project): raise ValueError('Run编辑语料/保护或检查器已升级，请新建Run')


def remap(project,cid,before,after,content_map,edits):
    old=check(project,cid,before,content_map)['content_map']; spans=old['segments']
    for edit in edits:
        if not any(s['start']<=edit['start']<edit['end']<=s['end'] for s in spans): raise ValueError('跨部件补丁必须提供新的显式content_map')
    def shifted(pos): return pos+sum(len(e['new'])-(e['end']-e['start']) for e in edits if e['end']<=pos)
    segments=[{'part_id':s['part_id'],'start':shifted(s['start']),'end':shifted(s['end'])} for s in spans]
    result=make_map(project,cid,after,segments); check(project,cid,after,result)
    return result


def template(project):
    author_destination(project)
    path=project/'writing_spec.json'
    flow.atomic_write(path,flow._pretty(template_value()))
    return {'path':str(path),'status':'tool_default_requires_chapter_plan','defaults':template_value()['defaults'],
            'notice':'默认不是作者确认，不等于平台计费；先补具体剧情与部件再写章。'}


def render_budget(project,cid):
    chapter=chapter_spec(project,cid)
    if chapter is None: return 'spec_not_configured：未核验篇幅/细节。'
    lines=[f'章节{cid}：{chapter["range"]["min"]}–{chapter["range"]["max"]} LN（含端点）',
           f'计数器{COUNTER}；Unicode {unicodedata.unidata_version}；不是平台结算字数。']
    for unit in chapter['plot_units']:
        lines.append(f'剧情{unit["id"]}：{unit["range"]["min"]}–{unit["range"]["max"]} LN；{unit["purpose"]}')
        for part in unit['parts']:
            lines.append(f'  部件{part["id"]} / 场景{part["scene_id"]} / 顺序{part["order"]}：{part["range"]["min"]}–{part["range"]["max"]} LN；{part["purpose"]}')
    lines.extend(f'核验{rule["id"]} [{rule["scope"]}]：{rule["criterion"]}' for rule in targets(project,cid))
    lines.append('铺垫策略：'+chapter['setup_strategy'])
    return '\n'.join(lines)+'\n'
