"""Coverage/projection invariants; synthetic prose is not literary acceptance."""
import copy,json,tempfile,unittest
from pathlib import Path
from tests.support import project,put,scene_data,response,profile
from tests.test_stages import specification,artifact,report,receipt,pass_stage
from tests.test_writing_spec import configured,mapped
import stage_gates as gates
import ensemble_runtime as ensemble
import writing_spec as writing
import creative_workflow as flow


class OpeningVolume(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.p=project(Path(temp.name))

    def test_design_and_outline_require_structure_and_actual_review_coverage(self):
        pid=gates.start(self.p,specification(profile='plan'))['pipeline_id'];pass_stage(self.p,pid,'brief')
        for stage,sections,criterion in [('design',['opening_promise','volume_goals'],'volume_goal'),('outline',['opening_sequence','volume_progression','peaks_payoffs'],'payoff_curve')]:
            for section in sections:
                bad=artifact(stage);bad['items']=[i for i in bad['items'] if i['section']!=section]
                with self.subTest(stage=stage,section=section),self.assertRaises(ValueError):gates.submit(self.p,pid,stage,bad)
            gates.submit(self.p,pid,stage,artifact(stage));packet=gates.packet(self.p,pid,stage)
            target='criterion:'+criterion;self.assertIn(target,packet['review_targets'])
            missing=report(packet);missing['checks']=[c for c in missing['checks'] if c['target']!=target]
            with self.assertRaises(ValueError):gates.review(self.p,pid,stage,missing,receipt())
            unknown=report(packet);next(c for c in unknown['checks'] if c['target']==target)['verdict']='unknown'
            gates.review(self.p,pid,stage,unknown,receipt());self.assertFalse(next(s for s in gates.status(self.p,pid)['stages'] if s['stage']==stage)['ready'])
            gates.review(self.p,pid,stage,report(packet),receipt())

    def test_local_character_plan_can_explain_out_of_scope_without_inventing_volumes(self):
        raw=(self.p/'canon.json').read_bytes();spec=specification(profile='plan');spec['author_input']='只讨论人物当场措辞，不规划开场或分卷。';spec['requirements']=[{'id':'R1','text':'只讨论人物当场措辞','quote':'不规划开场或分卷'}]
        pid=gates.start(self.p,spec)['pipeline_id'];pass_stage(self.p,pid,'brief')
        for stage in ('design','outline'):
            data=artifact(stage)
            for item in data['items']:
                if item['section'] in ('opening_promise','volume_goals','opening_sequence','volume_progression','peaks_payoffs'):
                    old=item['quote'];item['quote']='【'+item['section']+'】本任务只讨论当场措辞；尚无卷卡，开场/分卷未获授权，不适用并不补编。';data['work']=data['work'].replace(old,item['quote'])
            gates.submit(self.p,pid,stage,data);packet=gates.packet(self.p,pid,stage);gates.review(self.p,pid,stage,report(packet),receipt())
        pass_stage(self.p,pid,'delivery');self.assertTrue(gates.status(self.p,pid)['complete']);self.assertEqual((self.p/'canon.json').read_bytes(),raw)

    def test_opening_obligation_reaches_real_compose_without_future_plan(self):
        value=configured(self.p);value['chapters'][0]['detail_requirements']=[
            {'id':'opening_conflict','scope':'P1','criterion':'眼前目标、阻力、选择及可见后果'},
            {'id':'later_payoff','scope':'P2','criterion':'FUTURE_PAYOFF_SECRET'},
            {'id':'whole_chapter','scope':'chapter','criterion':'WHOLE_CHAPTER_OBLIGATION'}]
        put(self.p/'writing_spec.json',value);safe=profile();safe['rules']=['从关键冲突进入，随当前行动补足因果。'];safe['narration_origin']='tool_default';put(self.p/'writing_profile.json',safe)
        config,scene=scene_data();sid=ensemble.start(self.p,config,scene)['ensemble_id']
        while ensemble.status(self.p,sid)['stage']!='compose':
            packet=ensemble.packet(self.p,sid);self.assertNotIn('writing_profile',packet['input']);ensemble.respond(self.p,sid,response(packet),'synthetic_test')
        data=ensemble.packet(self.p,sid)['input'];rendered=json.dumps(data,ensure_ascii=False)
        self.assertIn('opening_conflict',rendered);self.assertEqual(data['writing_profile']['rules'],safe['rules'])
        self.assertEqual(data['writing_profile']['narration_origin'],'tool_default')
        for secret in ('FUTURE_PAYOFF_SECRET','WHOLE_CHAPTER_OBLIGATION','DIRECTOR_SECRET'):self.assertNotIn(secret,rendered)
        self.assertIn('WHOLE_CHAPTER_OBLIGATION',str(writing.projection(self.p,'V01-C01')))

    def test_opening_review_cannot_omit_or_cite_another_plot(self):
        value=configured(self.p);value['chapters'][0]['detail_requirements']=[{'id':'opening_conflict','scope':'P1','criterion':'当前冲突的可观察选择后果'}];put(self.p/'writing_spec.json',value)
        text='甲乙丙丁戊己';result={'spec_sha256':writing.load(self.p)['sha256'],'candidate_sha256':flow.digest(text.encode('utf-8')),'checks':[{'id':r['id'],'verdict':'satisfied','rationale':'合成协议覆盖，不证明文学质量','citations':[{'quote':'丁戊己' if r['scope']=='P2' else '甲乙丙'}]} for r in writing.targets(self.p,'V01-C01')]}
        writing.verify_review(self.p,'V01-C01',text,mapped(self.p),result)
        bad=copy.deepcopy(result);bad['checks']=[r for r in bad['checks'] if r['id']!='opening_conflict']
        with self.assertRaises(ValueError):writing.verify_review(self.p,'V01-C01',text,mapped(self.p),bad)
        next(r for r in result['checks'] if r['id']=='opening_conflict')['citations']=[{'quote':'丁戊己'}]
        with self.assertRaises(ValueError):writing.verify_review(self.p,'V01-C01',text,mapped(self.p),result)
