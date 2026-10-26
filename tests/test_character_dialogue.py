"""Actual packet and evidence invariants, not automatic dialogue quality scoring."""
import copy,tempfile,unittest
from pathlib import Path
from tests.support import project,put,profile,scene_data,response
from tests.test_writing_spec import configured,mapped
import ensemble_runtime as e
import writing_spec as writing
import writing_profile as wp
import creative_workflow as flow


class CharacterDialogue(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.p=project(Path(t.name))

    def test_actor_gets_expression_rules_and_own_context_without_narrator_profile(self):
        value=profile();value['rules']=['NARRATOR_PROFILE_ONLY'];put(self.p/'writing_profile.json',value)
        config,scene=scene_data();aid=scene['turn_order'][0];character=next(a['character_id'] for a in config['instances'] if a['id']==aid)
        config['profiles'][character]['voice']='PRIVATE_ACTOR_OWN_VOICE'
        sid=e.start(self.p,config,scene)['ensemble_id'];packet=e.packet(self.p,sid)
        self.assertEqual(packet['input']['profile']['voice'],'PRIVATE_ACTOR_OWN_VOICE')
        self.assertIn('relationship_view',packet['input']);self.assertIn('observations',packet['input'])
        self.assertIn('已设绰号',packet['system']);self.assertIn('relationship_view',packet['system'])
        self.assertNotIn('writing_profile',packet['input']);self.assertNotIn('NARRATOR_PROFILE_ONLY',str(packet))
        self.assertNotIn('DIRECTOR_SECRET',str(packet))

    def test_compose_cannot_polish_accepted_speech_even_for_naming(self):
        config,scene=scene_data();sid=e.start(self.p,config,scene)['ensemble_id']
        while e.status(self.p,sid)['stage']!='compose':e.respond(self.p,sid,response(e.packet(self.p,sid)),'synthetic_test')
        packet=e.packet(self.p,sid);reply=response(packet);speech=next(x['speech'] for x in packet['input']['events'] if x['speech'])
        wrong=copy.deepcopy(reply);wrong['text']=wrong['text'].replace(speech,'润色后的另一句台词')
        with self.assertRaisesRegex(ValueError,'对白'):e.respond(self.p,sid,wrong,'synthetic_test')
        e.respond(self.p,sid,reply,'synthetic_test');self.assertEqual(e.status(self.p,sid)['stage'],'complete')

    def test_naming_and_dialogue_reviews_cannot_be_omitted(self):
        configured(self.p);text='甲乙丙丁戊己';targets=writing.targets(self.p,'V01-C01')
        result={'spec_sha256':writing.load(self.p)['sha256'],'candidate_sha256':flow.digest(text.encode()),'checks':[{'id':r['id'],'verdict':'satisfied','rationale':'合成协议检验，不证明语义','citations':[{'quote':'丁戊己' if r['scope']=='P2' else '甲乙丙'}]} for r in targets]}
        writing.verify_review(self.p,'V01-C01',text,mapped(self.p),result)
        for identifier in ('character_naming','dialogue_context','dialogue_embodiment'):
            self.assertIn(identifier,{r['id'] for r in targets});bad=copy.deepcopy(result);bad['checks']=[r for r in bad['checks'] if r['id']!=identifier]
            with self.subTest(identifier=identifier),self.assertRaises(ValueError):writing.verify_review(self.p,'V01-C01',text,mapped(self.p),bad)

    def test_scene_compose_preserves_speech_order_and_each_repeated_occurrence(self):
        for repeated in (False,True):
            with self.subTest(repeated=repeated):
                config,scene=scene_data(label='repeat' if repeated else 'ordered');sid=e.start(self.p,config,scene)['ensemble_id']
                while e.status(self.p,sid)['stage']!='compose':
                    packet=e.packet(self.p,sid);reply=response(packet)
                    if repeated and packet['role']=='actor':reply['speech']='请先核对登记。'
                    e.respond(self.p,sid,reply,'synthetic_test')
                packet=e.packet(self.p,sid);words=[x['speech'] for x in packet['input']['events'] if x.get('speech')]
                wrong={'request_id':packet['request_id'],'text':'雨水沿屋檐落下，他们把登记簿放到柜台上，慢慢对照名字。'+(''.join(reversed(words)) if not repeated else words[0])}
                with self.assertRaisesRegex(ValueError,'对白'):e.respond(self.p,sid,wrong,'synthetic_test')
                e.respond(self.p,sid,response(packet),'synthetic_test');self.assertEqual(e.status(self.p,sid)['stage'],'complete')

    def test_legacy_narration_does_not_gain_invented_author_confirmation(self):
        value=profile();put(self.p/'writing_profile.json',value);self.assertEqual(wp.projection(self.p)['narration_origin'],'legacy_unspecified')
        value['narration_origin']='tool_default';put(self.p/'writing_profile.json',value);self.assertEqual(wp.projection(self.p)['narration_origin'],'tool_default')
        value['narration_origin']='made_up';put(self.p/'writing_profile.json',value)
        with self.assertRaises(ValueError):wp.projection(self.p)
