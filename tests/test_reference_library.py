import copy
import tempfile
import shutil
import unittest
from pathlib import Path
from tests.support import project,put
import reference_library as refs


class ReferenceLibrary(unittest.TestCase):
    def test_current_collections_respect_per_work_policy_and_candidate_separate(self):
        data=refs.load()
        result=refs.validate_samples(data)
        self.assertGreaterEqual(len(result['ready_ids']),4)
        for wid in result['ready_ids']:
            work=next(w for w in data['works'] if w['id']==wid)
            minimum,maximum=refs.sample_policy(data)
            self.assertGreaterEqual(len(work['chapters']),minimum)
            self.assertLessEqual(len(work['chapters']),maximum)
        self.assertFalse(result['semantic_full_read_verified'])

    def test_reject_49_plus_51_and_same_body_different_names(self):
        import json
        source=Path(__file__).resolve().parents[1]/'research/samples/2026-10-22-reference-samples.json'
        data=json.loads(source.read_text(encoding='utf-8'));works=[w for w in data['works'] if w['status']=='collected'][:2]
        value={'schema_version':'1','minimum_per_work':50,'works':copy.deepcopy(works)}
        value['works'][0]['chapters'].pop()
        with self.assertRaises(ValueError):refs.validate_samples(value)
        value={'schema_version':'1','minimum_per_work':50,'works':copy.deepcopy(works)}
        value['works'][0]['chapters'][1]['body_sha256']=value['works'][0]['chapters'][0]['body_sha256']
        with self.assertRaises(ValueError):refs.validate_samples(value)

    def test_directory_or_changed_semantic_claim_cannot_pass(self):
        import json
        source=Path(__file__).resolve().parents[1]/'research/samples/2026-10-22-reference-samples.json'
        data=json.loads(source.read_text(encoding='utf-8'))
        work=copy.deepcopy(next(w for w in data['works'] if w['status']=='collected'))
        work['chapters'][0]['complete_collection_claim']=False
        with self.assertRaises(ValueError):refs.validate_samples({'schema_version':'1','minimum_per_work':50,'works':[work]})
        work=copy.deepcopy(next(w for w in data['works'] if w['status']=='collected'))
        work['claim_scope']['semantic_numbers']=list(range(1,51))
        with self.assertRaises(ValueError):refs.validate_samples({'schema_version':'1','minimum_per_work':50,'works':[work]})

    def test_query_reports_scope_not_invented_techniques(self):
        rows=refs.search(genre='mystery')
        self.assertTrue(rows)
        self.assertTrue(all('collected_chapters' in r and 'semantic_scope' in r for r in rows))
        self.assertTrue(all('reading_focus' in r for r in refs.search(topic='伏笔')))
        self.assertNotIn('full_text',str(refs.search()))

    def test_current_study_keeps_ten_work_minimum_and_matches_declared_sources(self):
        source=Path(__file__).resolve().parents[1]/'research/samples/2026-10-22-reference-study-samples.json'
        result=refs.validate_file(source)
        reports=result['close_reading_reports']
        import json
        declared=json.loads(source.read_text(encoding='utf-8'))
        ids=declared['study_contract']['work_ids']
        self.assertGreaterEqual(len(ids),10)
        self.assertEqual({r['work_id'] for r in reports},set(ids))
        for r in reports:
            work=next(w for w in declared['works'] if w['id']==r['work_id'])
            self.assertEqual(r['model_read_chapters'],len(work['expected_numbers']))
            self.assertGreaterEqual(r['model_read_chapters'],20)
            self.assertLessEqual(r['model_read_chapters'],50)
            self.assertEqual(r['techniques'],6)
        self.assertTrue(all(not r['external_reader_acceptance'] for r in reports))
        import reference_study
        cards=reference_study.search(refs.LIBRARY,book='tianxia-changning',dimension='world')
        self.assertEqual(len(cards),1)
        self.assertTrue(all(s['chapter'] in (17,20) for s in cards[0]['sources']))
        note=reference_study.read(refs.LIBRARY,'weiwei',20)
        self.assertEqual(note['number'],20)
        with self.assertRaises(ValueError):reference_study.read(refs.LIBRARY,'weiwei',4)

    def test_declared_work_must_be_ready_individually(self):
        data=refs.load();ready=refs.validate_samples(data)['ready_ids']
        refs.validate_samples(data,required_ids=ready[:1])
        with self.assertRaises(ValueError):refs.validate_samples(data,required_ids=['not_collected'])

    def test_raw_source_binding_rejects_edited_count_and_platform_mix(self):
        source=Path(__file__).resolve().parents[1]/'research/samples/2026-10-22-reference-samples.json'
        import json
        data=json.loads(source.read_text(encoding='utf-8'));by={w['id']:w for w in data['works']}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for wid in ('jianlai','tianxia-changning','lushao-zongheng','lushao-iqiyi'):
                shutil.copyfile(source.parent/by[wid]['source_record'],root/by[wid]['source_record'])
            sample=root/'samples.json'
            good={'schema_version':'1','minimum_per_work':50,'works':[copy.deepcopy(by['jianlai'])]}
            put(sample,good);refs.validate_file(sample,['jianlai'])
            bad=copy.deepcopy(good);bad['works'][0]['chapters'][0]['LN']+=1;put(sample,bad)
            with self.assertRaises(ValueError):refs.validate_file(sample)
            bad=copy.deepcopy(good)
            for key in ('source_record','source_record_sha256','source_identity'):bad['works'][0][key]=by['tianxia-changning'][key]
            put(sample,bad)
            with self.assertRaises(ValueError):refs.validate_file(sample)
            mixed=copy.deepcopy(by['lushao-zongheng']);mixed['status']='collected'
            for num,row in zip((48,49,50),[by['lushao-iqiyi']['chapters'][n-1] for n in (2,3,6)]):
                mixed['chapters'].append({**row,'number':num})
            put(sample,{'schema_version':'1','minimum_per_work':50,'works':[mixed]})
            with self.assertRaises(ValueError):refs.validate_file(sample,['lushao-zongheng'])
            wrong=copy.deepcopy(by['lushao-zongheng']);wrong['edition']='爱奇艺小说官方站'
            put(sample,{'schema_version':'1','minimum_per_work':50,'works':[wrong]})
            with self.assertRaises(ValueError):refs.validate_file(sample)
            claim=copy.deepcopy(good)
            for row in claim['works'][0]['chapters']:row['semantic_status']='fully_semantically_reviewed'
            claim['works'][0]['claim_scope']['semantic_numbers']=list(range(1,51));put(sample,claim)
            with self.assertRaises(ValueError):refs.validate_file(sample)

    def test_develop_research_requires_bound_fifty_and_stales_on_change(self):
        from tests.test_stages import specification,artifact,pass_stage,report,receipt
        import json
        import stage_gates as gates
        source=Path(__file__).resolve().parents[1]/'research/samples/2026-10-22-reference-samples.json'
        data=json.loads(source.read_text(encoding='utf-8'));work=next(w for w in data['works'] if w['id']=='jianlai')
        with tempfile.TemporaryDirectory() as temp:
            p=project(Path(temp));spec=specification('develop');spec['reference_books']=['jianlai']
            pid=gates.start(p,spec)['pipeline_id'];pass_stage(p,pid,'brief')
            with self.assertRaises(ValueError):gates.submit(p,pid,'research',artifact('research'))
            evidence=p/'evidence';evidence.mkdir()
            shutil.copyfile(source.parent/work['source_record'],evidence/work['source_record'])
            samples=evidence/'samples.json';put(samples,{'schema_version':'1','minimum_per_work':50,'works':[work]})
            gates.submit(p,pid,'research',artifact('research',sources=[{'kind':'reference_samples','path':'evidence/samples.json'}]))
            packet=gates.packet(p,pid,'research')
            self.assertIn('reference:claim_scope',packet['review_targets'])
            gates.review(p,pid,'research',report(packet),receipt())
            self.assertTrue(gates.status(p,pid)['stages'][1]['ready'])
            value=json.loads(samples.read_text(encoding='utf-8'));value['works'][0]['chapters'][0]['LN']+=1;put(samples,value)
            self.assertEqual(gates.status(p,pid)['stages'][1]['state'],'stale')
