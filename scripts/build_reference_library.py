"""Build portable, metadata-only per-work indexes from reviewed research sources."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.agents/skills/novel-director/scripts'))
import reference_library as refs


def build():
    current=ROOT/'research/samples/2026-10-22-reference-study-samples.json'
    source=current if current.exists() else ROOT/'research/samples/2026-10-22-reference-samples.json'
    refs.validate_file(source)
    data=json.loads(source.read_text(encoding='utf-8'));out=refs.LIBRARY;out.mkdir(exist_ok=True)
    catalog={'schema_version':'1','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'works':[],
             'sample_policy':{k:data[k] for k in ('schema_version','minimum_per_work','maximum_per_work') if k in data},
             'notice':'当前按书逐部20–50章；历史50章采集档案保留当时证据范围。实际细读须有逐章分析和审查，reading_focus只表示方向。'}
    if 'study_contract' in data:catalog['study_contract']=data['study_contract']
    for key in ('excluded_authors','author_policy'):
        if key in data:catalog[key]=data[key]
    for work in data['works']:
        value={k:v for k,v in work.items() if k not in ('source_record','source_record_sha256','study_record','study_record_sha256')}
        value['source_record_receipt']={'file':work['source_record'],'sha256':work['source_record_sha256'],
                                       'location':'full workspace/plugin: research/samples; portable skill carries metadata only'}
        if work.get('study_record'):
            raw_study=(source.parent/work['study_record']).read_bytes()
            target=out/'studies'/(work['id']+'.json');target.parent.mkdir(exist_ok=True)
            target.write_bytes(raw_study)
            value.update(study_file='studies/'+target.name,study_sha256=hashlib.sha256(raw_study).hexdigest(),
                         model_read_chapters=len(json.loads(raw_study)['read_numbers']))
        path=out/(value['id']+'.json');raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8');path.write_bytes(raw)
        summary={k:v for k,v in value.items() if k not in ('chapters',)}
        catalog['works'].append({**summary,'file':path.name,'sha256':hashlib.sha256(raw).hexdigest(),
            'collected_chapters':len(value['chapters']),'semantic_scope':value['claim_scope'],
            'usable_as_collection_reference':value['status']=='collected'})
    (out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'works':len(data['works']),'ready_ids':refs.validate_samples(data)['ready_ids'],'source':str(source)}


if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
