"""Dialogue/action flow and review coverage; no literary quality scoring."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.support import project,scene_data,response,complete
from tests.test_writing_spec import configured
import ensemble_runtime as e
import chapter_tools as ct
import prose_risks as pr


class DialogueEmbodiment(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.p=project(Path(t.name))

    def _scene(self,label='one',hour=10):
        config,scene=scene_data(label=label,hour=hour)
        scene['turn_order']=['a_now','b_now','a_now']
        sid=e.start(self.p,config,scene)['ensemble_id'];turn=0
        while e.status(self.p,sid)['stage']!='complete':
            packet=e.packet(self.p,sid);reply=response(packet,label)
            if packet['role']=='actor':
                reply['action_intent']='RAW_UNRESOLVED_INTENT';reply['private_intent']='PRIVATE_MOTIVE'
            elif packet['role']=='resolve':
                reply.update(result=['PUBLIC_APPROVED','OTHER_OBSERVER_ONLY','HIDDEN_RESULT'][turn],
                             observers=['b_now'] if turn==1 else ['a_now','b_now'],reader_visible=turn!=2)
                turn+=1
            else:
                reply['text']+=''.join(x['result'] for x in packet['input']['events'])
            e.respond(self.p,sid,reply,'synthetic_test')
        return sid

    def test_joint_expression_reaches_actual_phase_packets(self):
        config,scene=scene_data();sid=e.start(self.p,config,scene)['ensemble_id']
        packet=e.packet(self.p,sid)
        self.assertIn('同一次',packet['system']);self.assertIn('action_intent',packet['system'])
        self.assertIn('语气词',packet['system']);self.assertIn('relationship_view',packet['input'])
        e.respond(self.p,sid,response(packet),'synthetic_test');packet=e.packet(self.p,sid)
        self.assertIn('result',packet['system']);self.assertIn('先后',packet['system'])
        self.assertNotIn('private_intent',packet['input']['proposal'])
        while e.status(self.p,sid)['stage']!='compose':e.respond(self.p,sid,response(e.packet(self.p,sid)),'synthetic_test')
        packet=e.packet(self.p,sid)
        self.assertIn('同一次',packet['system']);self.assertIn('连续',packet['system'])

    def test_scene_and_chapter_share_visible_results_without_raw_intents(self):
        a=self._scene();b=self._scene('two',11)
        aid=ct.assembly_plan(self.p,'V01-C01',{'scene_ids':[a,b]})['assembly_id']
        packet=ct.assembly_packet(self.p,aid)
        for item in packet['input']['scenes']:
            self.assertEqual(len(item['accepted_events']),1)
            event=item['accepted_events'][0]
            self.assertEqual(set(event),{'id','actor_id','speech','result'})
            self.assertEqual(event['result'],'PUBLIC_APPROVED')
            original=e._load(self.p,item['ensemble_id'])[1]
            self.assertEqual(item['accepted_events'],e.visible_events(original))
            self.assertEqual(item['accepted_speech'],[event['speech']])
        for secret in ('RAW_UNRESOLVED_INTENT','PRIVATE_MOTIVE','OTHER_OBSERVER_ONLY','HIDDEN_RESULT','pov_interior'):
            self.assertNotIn(secret,str(packet))

    def test_legacy_pending_assembly_requires_explicit_replan(self):
        a=complete(self.p);b=complete(self.p,'two',11)
        aid=ct.assembly_plan(self.p,'V01-C01',{'scene_ids':[a,b]})['assembly_id']
        folder,state=ct._load(self.p,aid)
        for item in state['scenes']:item.pop('accepted_events',None)
        ct._save(folder,state,replace=True);before=(folder/'state.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'重建'):ct.assembly_packet(self.p,aid)
        self.assertEqual((folder/'state.json').read_bytes(),before)
        fresh=ct.assembly_plan(self.p,'V01-C01',{'scene_ids':[a,b]})['assembly_id']
        self.assertTrue(ct.assembly_packet(self.p,fresh)['input']['scenes'][0]['accepted_events'])

    def test_expired_production_scene_cannot_be_restored_by_assembly_only(self):
        configured(self.p,single=True);a=complete(self.p);b=complete(self.p,'one',11)
        folder,_=e._load(self.p,a);before=(folder/'state.json').read_bytes()
        corpus=json.loads(pr.ASSET.read_text(encoding='utf-8'));corpus['version']+='-synthetic-upgrade'
        changed=self.p.parent/'upgraded-corpus.json';changed.write_text(json.dumps(corpus,ensure_ascii=False),encoding='utf-8')
        with patch.object(pr,'ASSET',changed):
            with self.assertRaisesRegex(ValueError,'重建排练'):ct.assembly_plan(self.p,'V01-C01',{'scene_ids':[a,b]})
        self.assertEqual((folder/'state.json').read_bytes(),before)

    def test_rejected_expression_does_not_become_an_event(self):
        config,scene=scene_data();sid=e.start(self.p,config,scene)['ensemble_id']
        e.respond(self.p,sid,response(e.packet(self.p,sid)),'synthetic_test')
        packet=e.packet(self.p,sid);reply=response(packet);reply.update(accept=False,reason='空间不允许',result='',observers=[],reader_visible=False,end_scene=True)
        bad=copy.deepcopy(reply);bad['result']='虚构已经拉住对方'
        with self.assertRaisesRegex(ValueError,'拒绝'):e.respond(self.p,sid,bad,'synthetic_test')
        e.respond(self.p,sid,reply,'synthetic_test')
        self.assertEqual(e.packet(self.p,sid)['input']['events'],[])

    def test_action_cannot_split_a_locked_utterance(self):
        config,scene=scene_data();sid=e.start(self.p,config,scene)['ensemble_id']
        while e.status(self.p,sid)['stage']!='compose':
            packet=e.packet(self.p,sid);reply=response(packet)
            if packet['role']=='actor':reply['speech']='先别走。把登记给我。'
            e.respond(self.p,sid,reply,'synthetic_test')
        packet=e.packet(self.p,sid);reply=response(packet)
        reply['text']=reply['text'].replace('先别走。把登记给我。','先别走。”他伸出手。“把登记给我。')
        with self.assertRaisesRegex(ValueError,'对白'):e.respond(self.p,sid,reply,'synthetic_test')
