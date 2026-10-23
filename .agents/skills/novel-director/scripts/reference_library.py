"""Offline, scoped reference metadata. Acquisition is not literary close reading."""
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,urlunsplit
import json
import re
import unicodedata
from evidence_audit import read_utf8,no_symlink_components

LIBRARY=Path(__file__).resolve().parents[1]/'assets/reference-library'


def _sha(v):return isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) is not None


def check_author_policy(value,works):
    """Optional selection policy, independent of per-work evidence hashes."""
    names=value.get('excluded_authors',[])
    if not isinstance(names,list) or len(names)>200 or any(not isinstance(n,str) or not n.strip() or len(n)>100 for n in names):raise ValueError('排除作者政策须为有限非空姓名列表')
    def normalized(name):return re.sub(r'\s+','',unicodedata.normalize('NFKC',name)).casefold()
    banned={normalized(n) for n in names}
    if len(banned)!=len(names):raise ValueError('排除作者政策含重复姓名')
    if banned:
        for work in works:
            if not isinstance(work,dict) or not isinstance(work.get('author'),str) or not work['author'].strip():raise ValueError('排除政策下参考须明确作者')
            identity=work.get('source_identity',{})
            authors=[work['author']]
            if isinstance(identity,dict) and identity.get('author') is not None:authors.append(identity['author'])
            if any(not isinstance(a,str) or not a.strip() or normalized(a) in banned for a in authors):raise ValueError('当前参考包含已排除作者')
    return names


def sample_policy(value):
    if not isinstance(value,dict):raise ValueError('参考库须为对象')
    if value.get('schema_version')=='1' and type(value.get('minimum_per_work')) is int and value['minimum_per_work']==50:
        return 50,50  # Existing frozen receipts have 50 chapters; imports cannot evade the current upper bound.
    if value.get('schema_version')=='2' and type(value.get('minimum_per_work')) is int and type(value.get('maximum_per_work')) is int and value['minimum_per_work']==20 and value['maximum_per_work']==50:
        return 20,50
    raise ValueError('当前schema2采集范围须逐部20–50章；历史schema1保留原50章门槛')


def validate_samples(value,required_ids=()):
    minimum,maximum=sample_policy(value)
    works=value.get('works')
    if not isinstance(works,list) or not 1<=len(works)<=200:raise ValueError('参考作品清单须为1–200部')
    check_author_policy(value,works)
    seen=set();ready=[];summaries=[]
    for work in works:
        if not isinstance(work,dict):raise ValueError('参考作品须为对象')
        for key in ('id','title','genre','status','expected_numbers','chapters','claim_scope'):
            if key not in work:raise ValueError('参考作品缺字段：'+key)
        wid=work['id']
        if not isinstance(wid,str) or not re.fullmatch('[a-z0-9][a-z0-9-]{0,79}',wid) or wid in seen:raise ValueError('作品/版次ID无效或重复')
        seen.add(wid)
        if work['status'] not in ('collected','incomplete','blocked','probe_only'):raise ValueError('未知采集状态')
        for key in ('title','genre'):
            if not isinstance(work[key],str) or not work[key].strip():raise ValueError('作品名称/类型缺失')
        expected=work['expected_numbers'];rows=work['chapters']
        if not isinstance(expected,list) or not minimum<=len(expected)<=maximum or any(type(n) is not int or n<1 for n in expected) or sorted(set(expected))!=expected:raise ValueError(f'每部先冻结{minimum}–{maximum}个不同有序章号')
        if not isinstance(rows,list) or len(rows)>maximum:raise ValueError('实际采集章节超过当前逐部上限')
        numbers=[];urls=set();hashes=set()
        for row in rows:
            if not isinstance(row,dict):raise ValueError('章节采集记录须为对象')
            n=row.get('number')
            if type(n) is not int or n not in expected or n in numbers:raise ValueError('重复/未计划的采集章号')
            numbers.append(n)
            if row.get('access')!='public_free_plaintext' or row.get('complete_collection_claim') is not True:raise ValueError('目录/付费/截断/乱码不能当完整公开正文')
            if not row.get('title') or not row.get('free_evidence') or not row.get('collected_at'):raise ValueError('采集需标题、时间和可读依据')
            url=row.get('url');parts=urlsplit(url) if isinstance(url,str) else None
            if not parts or parts.scheme!='https' or not parts.hostname or parts.username or parts.password:raise ValueError('参考来源须为正常公开HTTPS URL')
            canonical=urlunsplit((parts.scheme,parts.netloc.lower(),parts.path.rstrip('/'),parts.query,''))
            body=row.get('body_sha256')
            if canonical in urls or body in hashes or not _sha(body) or not _sha(row.get('original_sha256')):raise ValueError('重复URL/正文摘要或无效SHA；换标题不能凑章')
            urls.add(canonical);hashes.add(body)
            upper=row.get('nonspace') if row.get('nonspace') is not None else row.get('raw_codepoints')
            if type(row.get('LN')) is not int or type(upper) is not int or not 0<row['LN']<=upper:raise ValueError('章长计数无效，不能用目录数替正文')
            if row.get('paragraphs') is not None and (type(row['paragraphs']) is not int or row['paragraphs']<1):raise ValueError('段落计数不合法；未记录须null，不能捏造')
            if row.get('semantic_status') not in ('not_semantically_reviewed','selected_paragraphs_only','fully_semantically_reviewed'):raise ValueError('语义阅读状态须明确')
        if numbers!=sorted(numbers):raise ValueError('采集章序不一致')
        scope=work['claim_scope']
        if not isinstance(scope,dict) or not isinstance(scope.get('semantic_numbers'),list) or not scope.get('limits'):raise ValueError('采集与语义结论范围必须分开')
        full={r['number'] for r in rows if r['semantic_status']=='fully_semantically_reviewed'}
        if set(scope['semantic_numbers'])!=full or len(scope['semantic_numbers'])!=len(full):raise ValueError('语义覆盖超出实际全章审读记录或重复')
        for n in scope.get('selected_paragraph_observations',[]):
            if n not in {r['number'] for r in rows if r['semantic_status'] in ('selected_paragraphs_only','fully_semantically_reviewed')}:raise ValueError('选段观察无对应采集记录')
        if work['status']=='collected':
            if work.get('counter')!='unicode_letters_numbers_codepoints' or not isinstance(work.get('unicode_version'),str):raise ValueError('已采参考必须明确实际LN口径和Unicode版本')
            if len(rows)<minimum or numbers!=expected:raise ValueError(f'每部独立{minimum}章下限及计划章序未满足')
            ready.append(wid)
        elif len(rows)>=minimum and numbers==expected:raise ValueError('候选状态与已完成计划不一致，应明确核验后更新')
        summaries.append({'id':wid,'status':work['status'],'collected_chapters':len(rows),'missing_numbers':sorted(set(expected)-set(numbers)),
                          'full_semantic_chapters':len(full)})
    if not isinstance(required_ids,(list,tuple)) or len(set(required_ids))!=len(required_ids) or set(required_ids)-set(ready):raise ValueError(f'声明采用的作品须逐部独立满足{minimum}章下限与原计划，不能用其他书代替')
    identities=[tuple(re.sub(r'\s+','',str(w.get(k,''))).casefold() for k in ('title','author')) for w in works if w['id'] in required_ids]
    if len(identities)!=len(set(identities)):raise ValueError('同书不同平台/版次不能充多部采用作品')
    study=value.get('study_contract')
    if study is not None:
        if not isinstance(study,dict):raise ValueError('专题契约须为对象')
        ids=study.get('work_ids')
        count=study.get('minimum_works');read_min=study.get('minimum_read_per_work')
        if not isinstance(ids,list) or not ids or len(set(ids))!=len(ids) or type(count) is not int or not 1<=count<=200 or len(ids)<count or read_min!=20 or type(read_min) is not int:raise ValueError('专题须有不同作品及逐部至少20章细读的明确契约')
        chosen=[w for w in works if w['id'] in ids]
        if len(chosen)!=len(ids) or set(ids)-set(ready) or any(len(w['claim_scope']['semantic_numbers'])<read_min for w in chosen):raise ValueError('专题采集达标但逐部20章细读未完成')
        keys=[tuple(re.sub(r'\s+','',str(w.get(k,''))).casefold() for k in ('title','author')) for w in chosen]
        if len(set(keys))!=len(keys):raise ValueError('专题不能用同书多个平台/版次凑作品数')
        primary=study.get('primary_genres',[]);minimum_primary=study.get('minimum_primary',0)
        if not isinstance(primary,list) or type(minimum_primary) is not int or minimum_primary<0 or sum(w['genre'] in primary for w in chosen)<minimum_primary:raise ValueError('专题主要题材范围未满足')
    return {'ready_ids':ready,'works':summaries,'semantic_full_read_verified':False,
            'notice':'只验证记录一致性；SHA不证明采集真实性、完整性、合法性或文学判断。'}


def validate_file(path,required_ids=()):
    raw,_=read_utf8(path);value=json.loads(raw);result=validate_samples(value,required_ids)
    studies=[]
    # Production research must bind normalized rows back to actual raw records.
    # Portable metadata-only load() is a different, explicitly weaker check.
    for work in value['works']:
        if 'source_record' not in work:raise ValueError('实际研究清单必须携带原始采集来源；portable索引不能冒充源验证')
        name=PurePosixPath(work['source_record'])
        if name.is_absolute() or len(name.parts)!=1 or name.name.startswith('.'):raise ValueError('原始采集记录须为同目录普通文件')
        raw,sha=read_utf8(path.parent/name.name)
        if sha!=work.get('source_record_sha256'):raise ValueError('原始采集记录已改版')
        identity,originals=source_projection(json.loads(raw))
        if work.get('source_identity')!=identity:raise ValueError('作品/平台/版次身份未绑定原始来源')
        if 'edition' in work and work['edition']!=identity['edition']:raise ValueError('顶层版次标签与来源身份不符')
        if identity['title'] is not None and work['title']!=identity['title']:raise ValueError('作品名与原始来源不符，不可换源背书')
        if identity['author'] is not None and work.get('author')!=identity['author']:raise ValueError('作者与原始来源不符')
        if originals and work.get('unicode_version')!=identity['unicode_version']:raise ValueError('统一清单Unicode版本不符原始计数')
        if len(work['chapters'])!=len(originals):raise ValueError('采集章节数不符来源，不可跨平台补齐')
        for row,original in zip(work['chapters'],originals):
            if any(row.get(key)!=value for key,value in original.items()):raise ValueError('章号/标题/URL/正文摘要/计数与实际来源不符，不可改号或拼接')
        if work.get('study_record'):
            study_name=PurePosixPath(work['study_record'])
            if study_name.is_absolute() or len(study_name.parts)!=1 or not re.fullmatch(r'[a-z0-9-]+\.json',study_name.name):raise ValueError('细读原始档案须为同目录普通JSON')
            study_raw,study_sha=read_utf8(path.parent/study_name.name)
            if study_sha!=work.get('study_record_sha256'):raise ValueError('细读档案已改版')
            import reference_study
            studies.append(reference_study.validate(work,json.loads(study_raw)))
        elif value.get('schema_version')=='2' and work['claim_scope']['semantic_numbers']:
            raise ValueError('当前全章细读声明缺实际分析档案')
    if studies:result['close_reading_reports']=studies
    return result


def source_projection(value):
    """Known metadata adapters, no arbitrary extractor execution or regex input."""
    if not isinstance(value,dict):raise ValueError('原始采集档案须为对象')
    if value.get('acquisition_schema')=='novel-reference-v2':
        if not isinstance(value.get('work'),dict) or not isinstance(value.get('count_policy'),dict) or not isinstance(value.get('chapters'),list):raise ValueError('本轮采集身份/计数/章节结构无效')
        book=value.get('work',{});identity={'title':book.get('title'),'author':book.get('author'),'book_id':book.get('book_id'),'edition':value.get('source_platform'),'unicode_version':value.get('count_policy',{}).get('unicode_version')}
        if not all(isinstance(identity[k],str) and identity[k] for k in identity):raise ValueError('本轮采集作品/平台/版本身份不完整')
        result=[]
        for c in value.get('chapters',[]):
            if not isinstance(c,dict):raise ValueError('采集章节须为对象')
            if c.get('technical_complete') is not True or c.get('transport') not in ('web_tool_rendered','http_public_html'):raise ValueError('本轮采集未取得完整正常公开正文')
            if c['transport']=='web_tool_rendered' and (type(c.get('complete_rendered_lines')) is not int or c['complete_rendered_lines']<2):raise ValueError('web完整视图记录缺失')
            if c['transport']=='http_public_html' and c.get('http_status')!=200:raise ValueError('HTTP采集未取得正常正文')
            paras=c.get('paragraph_records',[])
            if not isinstance(paras,list) or not paras or any(not isinstance(p,dict) for p in paras) or len(paras)!=c.get('body_paragraph_count') or [p.get('number') for p in paras]!=list(range(1,len(paras)+1)):raise ValueError('采集逐段记录不完整')
            for p in paras:
                if not _sha(p.get('sha256')) or any(type(p.get(k)) is not int for k in ('LN','nonspace','codepoints')) or not 0<=p['LN']<=p['nonspace']<=p['codepoints'] or p['codepoints']<1:raise ValueError('段落摘要/计数无效')
            if sum(p['LN'] for p in paras)!=c.get('body_LN') or sum(p['nonspace'] for p in paras)!=c.get('raw_nonspace') or sum(p['codepoints'] for p in paras)+2*(len(paras)-1)!=c.get('clean_raw_codepoints'):raise ValueError('段落与正文计数未闭合')
            result.append({'number':c['chapter_number'],'title':c['title'],'url':c['url'],'body_sha256':c['body_sha256'],'original_sha256':c['original_extracted_sha256'],'LN':c['body_LN'],'nonspace':c['raw_nonspace'],'raw_codepoints':c['clean_raw_codepoints'],'paragraphs':c['body_paragraph_count'],'paragraph_records':paras,'reading_evidence':c.get('reading_evidence',[]),'semantic_status':c.get('semantic_status','not_semantically_reviewed')})
        return identity,result
    classic='records' in value and value['records'] and isinstance(value['records'][0],dict) and 'metadata' in value['records'][0]
    if classic:
        items=[r['metadata'] for r in value['records']]
        editions={r['edition_key'] for r in items}
        if editions!={'wikisource_chengjia_nlc1791_transcription'}:raise ValueError('古典采集混底本')
        versions={r['unicode_version'] for r in items}
        if len(versions)!=1:raise ValueError('同一版次混用Unicode计数版本')
        identity={'title':'红楼梦（程甲本）','author':None,'book_id':None,'edition':next(iter(editions)),'unicode_version':next(iter(versions))}
    else:
        work=value.get('work');book=work if isinstance(work,dict) else {}
        identity={'title':book.get('title') if book else work if isinstance(work,str) else None,
                  'author':book.get('author') if book else value.get('author'),
                  'book_id':book.get('book_id') if book else value.get('book_id'),
                  'edition':value.get('source_platform'),
                  'unicode_version':value.get('count_policy',{}).get('unicode_version') or value.get('algorithm',{}).get('unicode_data_version')}
        items=value.get('chapters',[])
    result=[]
    for c in items:
        if not (classic or c.get('body_sha256') or c.get('clean_sha256')):continue
        evidence=c.get('collection_completeness',c.get('structural_completeness',{}))
        for key in ('content_div_closed','content_main_closed','full_response_read','full_body_tree_traversed','nonempty_prose','chapter_sequence_matches','catalog_sequence_matches'):
            if key in evidence and evidence[key] is not True:raise ValueError('原始记录技术完整性存在缺口，不能计为完整章')
        if not classic and c.get('http_status')!=200:raise ValueError('原始采集没有正常正文响应')
        semantic=c.get('semantic_status','not_semantically_reviewed')
        if not isinstance(semantic,str):raise ValueError('原始语义阅读状态须为文本')
        semantic='selected_paragraphs_only' if semantic.startswith('partially_semantically_reviewed') else semantic
        if classic:
            result.append({'number':c['chapter_number'],'title':c['chapter_heading'],'url':c['canonical_url'],
                'body_sha256':c['clean_body_sha256'],'original_sha256':c['rendered_html_sha256'],
                'LN':c['ln_count'],'nonspace':None,'raw_codepoints':c['clean_raw_codepoints'],'paragraphs':None})
        elif c.get('body_sha256'):
            result.append({'number':c['chapter_number'],'title':c['title'],'url':c['url'],'body_sha256':c['body_sha256'],
                'original_sha256':c['original_extracted_sha256'],'LN':c['body_LN'],'nonspace':c['raw_nonspace'],'paragraphs':c['body_paragraph_count']})
        elif c.get('clean_sha256'):
            result.append({'number':c['chapter_number'],'title':c['title'],'url':c['url'],'body_sha256':c['clean_sha256'],
                'original_sha256':c['raw_sha256'],'LN':c['clean_counts']['LN'],'nonspace':c['clean_counts']['nonspace'],
                'raw_codepoints':c['clean_counts']['codepoints'],'paragraphs':c['clean_paragraph_count']})
        if result:result[-1]['semantic_status']='not_semantically_reviewed' if classic else semantic
    return identity,result


def load():
    catalog=json.loads(read_utf8(LIBRARY/'catalog.json')[0]);works=[]
    if catalog.get('schema_version')!='1':raise ValueError('未知参考库索引版本')
    for row in catalog.get('works',[]):
        name=row.get('file')
        if not isinstance(name,str) or not re.fullmatch(r'[a-z0-9-]+\.json',name):raise ValueError('参考索引文件名不安全')
        text,sha=read_utf8(LIBRARY/name)
        if sha!=row.get('sha256'):raise ValueError('参考索引投影过期，请从研究源重新生成')
        value=json.loads(text)
        if value.get('id')!=row.get('id'):raise ValueError('参考作品ID与索引不一致')
        works.append(value)
    value={**catalog.get('sample_policy',{'schema_version':'1','minimum_per_work':50}),'excluded_authors':catalog.get('excluded_authors',[]),'works':works}
    if 'study_contract' in catalog:value['study_contract']=catalog['study_contract']
    validate_samples(value)
    import reference_study
    for work in works:
        if work.get('study_file'):reference_study.load(work,LIBRARY)
        elif value.get('schema_version')=='2' and work['claim_scope']['semantic_numbers']:raise ValueError('当前全章细读声明缺实际分析档案')
    return value


def search(genre=None,status=None,topic=None,query=None):
    results=[]
    catalog=json.loads(read_utf8(LIBRARY/'catalog.json')[0])
    if catalog.get('schema_version')!='1':raise ValueError('未知参考索引版本')
    check_author_policy(catalog,catalog['works'])
    for work in catalog['works']:
        if genre and genre!=work['genre']:continue
        if status and status!=work['status']:continue
        if topic and not any(topic in x for x in work.get('reading_focus',[])):continue
        if query and query.casefold() not in json.dumps({k:work.get(k) for k in ('id','title','author','reading_focus')},ensure_ascii=False).casefold():continue
        if catalog.get('excluded_authors'):
            # Summaries are an index, not authority for author selection.
            actual=show(work['id'])
            if any(actual.get(k)!=work.get(k) for k in ('author','source_identity')):raise ValueError('排除政策下目录作者与实际来源不一致')
        results.append({'id':work['id'],'title':work['title'],'author':work.get('author'),'genre':work['genre'],'status':work['status'],
                        'collected_chapters':work['collected_chapters'],'usable_as_collection_reference':work['status']=='collected',
                        'semantic_scope':work['claim_scope'],'reading_focus':work.get('reading_focus',[]),
                        'selection_evidence':work.get('selection_evidence',[]),'notice':'reading_focus是后续阅读方向，非已从全书提炼的方法。'})
    return results


def show(wid):
    catalog=json.loads(read_utf8(LIBRARY/'catalog.json')[0])
    check_author_policy(catalog,catalog['works'])
    row=next((w for w in catalog['works'] if w['id']==wid),None)
    if row is None:raise ValueError('未知参考作品ID')
    name=row.get('file')
    if not isinstance(name,str) or not re.fullmatch(r'[a-z0-9-]+\.json',name):raise ValueError('参考索引文件名不安全')
    raw,sha=read_utf8(LIBRARY/name)
    if sha!=row.get('sha256'):raise ValueError('参考索引投影已变版')
    work=json.loads(raw)
    if work['id']!=wid:raise ValueError('参考索引作品ID不一致')
    validate_samples({**catalog.get('sample_policy',{'schema_version':'1','minimum_per_work':50}),'excluded_authors':catalog.get('excluded_authors',[]),'works':[work]})
    if work.get('study_file'):
        import reference_study
        reference_study.load(work,LIBRARY)
    elif catalog.get('sample_policy',{}).get('schema_version')=='2' and work['claim_scope']['semantic_numbers']:raise ValueError('当前全章细读声明缺实际分析档案')
    return work
