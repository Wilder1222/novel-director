"""Independent-review repros. All values are temporary protocol fixtures."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.support import project, put
from tests.test_writing_spec import configured, mapped
from tests.test_stages import report, receipt
from tests.test_stage_revision import fixture
import creative_workflow as flow
import writing_spec as writing
import stage_gates as gates
import directed_revision as revision


class WritingReviewRegressions(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.p=project(Path(temp.name))

    def craft_report(self,text):
        return {'spec_sha256':writing.load(self.p)['sha256'],'candidate_sha256':flow.digest(text.encode('utf-8')),
            'checks':[{'id':r['id'],'verdict':'satisfied','rationale':'协议测试，不代表文学验收。',
                       'citations':[{'quote':'丁戊己' if r['scope']=='P2' or r['id']=='setup:F1' else '甲乙丙'}]}
                      for r in writing.targets(self.p,'V01-C01')]}

    def test_scene_projection_excludes_future_requirements(self):
        value=configured(self.p)
        value['chapters'][0]['detail_requirements']=[{'id':'future_detail','scope':'P2','criterion':'FUTURE_DETAIL'}]
        value['chapters'][0]['setup_strategy']='FUTURE_STRATEGY'; put(self.p/'writing_spec.json',value)
        packet=writing.projection(self.p,'V01-C01','one')
        self.assertEqual([p['id'] for p in packet['parts']],['A'])
        self.assertNotIn('FUTURE_DETAIL',str(packet)); self.assertNotIn('FUTURE_STRATEGY',str(packet))

    def test_prior_chapter_uses_volume_number(self):
        value=configured(self.p); chapters=flow.getjson(self.p/'chapters.json')
        chapters['chapters'][0],chapters['chapters'][1]=chapters['chapters'][1],chapters['chapters'][0]
        put(self.p/'chapters.json',chapters); (self.p/'manuscript').mkdir(exist_ok=True)
        (self.p/'manuscript/V01-C02.md').write_text('第二章未来证据',encoding='utf-8')
        value['chapters'][0]['setups']=[{'id':'F1','scope':'P2','criterion':'回收前文','operation':'payoff',
            'prior':[{'source':'manuscript/V01-C02.md','quote':'第二章未来证据'}]}]
        with self.assertRaises(ValueError): writing.validate(self.p,value)

    def test_chapter_payoff_uses_actual_effect_position(self):
        value=configured(self.p)
        value['chapters'][0]['setups']=[{'id':'F1','scope':'chapter','criterion':'后半章回收前半章','operation':'payoff',
            'prior':[{'source':'candidate','quote':'甲乙丙'}]}]
        put(self.p/'writing_spec.json',value); text='甲乙丙丁戊己'; cm=mapped(self.p); result=self.craft_report(text)
        writing.verify_review(self.p,'V01-C01',text,cm,result)
        next(r for r in result['checks'] if r['id']=='setup:F1')['citations']=[{'quote':'甲乙丙'}]
        with self.assertRaises(ValueError): writing.verify_review(self.p,'V01-C01',text,cm,result)

    def test_scope_external_citation_cannot_fake_later_effect(self):
        value=configured(self.p)
        value['chapters'][0]['setups']=[{'id':'F1','scope':'P1','criterion':'第一剧情回收','operation':'payoff',
            'prior':[{'source':'candidate','quote':'丁戊己'}]}]
        put(self.p/'writing_spec.json',value); text='甲乙丙丁戊己庚辛壬'; result=self.craft_report(text)
        next(r for r in result['checks'] if r['id']=='setup:F1')['citations']=[{'quote':'甲乙丙'},{'quote':'庚辛壬'}]
        with self.assertRaises(ValueError): writing.verify_review(self.p,'V01-C01',text,mapped(self.p,text),result)

    def test_scene_capacity_rejected_before_compose(self):
        value=configured(self.p,single=True); chapter=value['chapters'][0]
        for target in (chapter,chapter['plot_units'][0],chapter['plot_units'][0]['parts'][0]):
            target['range']={'min':25000,'max':30000}
        with self.assertRaises(ValueError): writing.validate(self.p,value)

    def test_unrelated_scene_cannot_hide_plot_capacity_failure(self):
        def part(key,scene,order,low,high):
            return {'id':key,'scene_id':scene,'order':order,'purpose':'测试部件','range':{'min':low,'max':high}}
        value=configured(self.p); chapter=value['chapters'][0]; chapter['range']={'min':25001,'max':55000}
        chapter['plot_units']=[{'id':'P1','purpose':'跨场剧情','range':{'min':25000,'max':25000},
            'parts':[part('A','one',1,1,30000),part('B','two',2,1,1)]},
            {'id':'P2','purpose':'无关剧情','range':{'min':1,'max':30000},'parts':[part('C','three',3,1,30000)]}]
        with self.assertRaises(ValueError): writing.validate(self.p,value)
        chapter['plot_units'][0]['range']={'min':20001,'max':20001}; writing.validate(self.p,value)

    def test_revision_preflight_leaves_no_partial_patch(self):
        class BeforeApply(Exception): pass
        captured={}
        def pause(*args): captured['args']=args; raise BeforeApply
        with patch.object(revision,'apply',side_effect=pause):
            with self.assertRaises(BeforeApply): fixture(self.p)
        _,run,rid,patch_path=captured['args']; pid=gates.registry(self.p)['V01-C01']
        packet=gates.packet(self.p,pid,'brief'); gates.review(self.p,pid,'brief',report(packet),receipt('host_supplied'))
        with self.assertRaises(ValueError): revision.apply(self.p,run,rid,patch_path)
        root=flow._manifest(self.p,run)[0]/'revisions'/rid
        for name in ('patch.json','proposal.md','record.json'): self.assertFalse((root/name).exists(),name)
        self.assertEqual(flow.status(self.p,run)['state'],'reviewed')
