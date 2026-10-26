"""Growth guidance must reach real packets without widening POV disclosure."""
import tempfile,unittest
from pathlib import Path
from tests.support import project,scene_data,response,complete
from tests.test_prose_risks import clear_report
import ensemble_runtime as ensemble
import chapter_tools as chapters
import prose_risks as prose


class InteriorityProgression(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.p=project(Path(temp.name))

    def test_real_actor_resolver_scene_and_chapter_packets_carry_growth_rules(self):
        config,scene=scene_data();sid=ensemble.start(self.p,config,scene)['ensemble_id']
        actor=ensemble.packet(self.p,sid)
        self.assertIn('自行宣布晋升',actor['system'])
        self.assertIn('自我判断',actor['system'])
        ensemble.respond(self.p,sid,response(actor),'synthetic_test')
        resolver=ensemble.packet(self.p,sid)
        self.assertIn('体感',resolver['system'])
        self.assertIn('门槛',resolver['system'])
        while ensemble.status(self.p,sid)['stage']!='compose':
            packet=ensemble.packet(self.p,sid)
            ensemble.respond(self.p,sid,response(packet),'synthetic_test')
        packet=ensemble.packet(self.p,sid)
        self.assertIn(ensemble.INTERIORITY_PROGRESSION,packet['system'])
        ensemble.respond(self.p,sid,response(packet),'synthetic_test')
        second=complete(self.p,'next',11)
        aid=chapters.assembly_plan(self.p,'V01-C01',{'scene_ids':[sid,second]})['assembly_id']
        packet=chapters.assembly_packet(self.p,aid)
        self.assertIn(ensemble.INTERIORITY_PROGRESSION,packet['system'])
        self.assertNotIn('DIRECTOR_SECRET',str(packet))

    def test_authorized_interior_reaches_scene_and_finished_text_without_reopening_hidden_channels(self):
        for i,mode in enumerate(('allowed','off','default','unobserved','hidden')):
            with self.subTest(mode=mode):
                config,scene=scene_data(label='pov'+str(i))
                if mode!='default':scene['allow_pov_interior']=mode!='off'
                sid=ensemble.start(self.p,config,scene)['ensemble_id']
                while ensemble.status(self.p,sid)['stage']!='compose':
                    packet=ensemble.packet(self.p,sid);reply=response(packet)
                    if packet['role']=='actor':
                        reply['private_intent']='PRIVATE_MOTIVE'
                        reply['pov_interior']='SELF_REFLECTION' if reply['actor_id']=='a_now' else 'OTHER_INTERIOR'
                    else:
                        self.assertNotIn('PRIVATE_MOTIVE',str(packet))
                        self.assertNotIn('SELF_REFLECTION',str(packet))
                        if mode=='unobserved':reply['observers']=['b_now']
                        if mode=='hidden':reply['reader_visible']=False
                    ensemble.respond(self.p,sid,reply,'synthetic_test')
                packet=ensemble.packet(self.p,sid)
                self.assertEqual('SELF_REFLECTION' in str(packet),mode=='allowed')
                for marker in ('OTHER_INTERIOR','PRIVATE_MOTIVE','DIRECTOR_SECRET'):
                    self.assertNotIn(marker,str(packet))
                reply=response(packet)
                # A synthetic composer uses only the projected input; this is not a prose leak detector.
                reply['text']+=''.join(event.get('pov_interior','') for event in packet['input']['events'])
                ensemble.respond(self.p,sid,reply,'synthetic_test')
                second=complete(self.p,'follow'+str(i),11)
                aid=chapters.assembly_plan(self.p,'V01-C01',{'scene_ids':[sid,second]})['assembly_id']
                chapter=chapters.assembly_packet(self.p,aid)
                self.assertEqual('SELF_REFLECTION' in chapter['input']['scenes'][0]['text'],mode=='allowed')
                for item in chapter['input']['scenes']:
                    self.assertTrue(all('pov_interior' not in event for event in item['accepted_events']))
                for marker in ('OTHER_INTERIOR','PRIVATE_MOTIVE','DIRECTOR_SECRET'):
                    self.assertNotIn(marker,str(chapter))

    def test_private_knowledge_cannot_become_prose_ready_self_reflection(self):
        config,scene=scene_data();scene['allow_pov_interior']=True
        sid=ensemble.start(self.p,config,scene)['ensemble_id'];packet=ensemble.packet(self.p,sid)
        reply=response(packet);reply.update(used_fact_ids=['a_secret'],pov_interior='私密机制解释晋升。')
        with self.assertRaisesRegex(ValueError,'不可公开知识'):
            ensemble.respond(self.p,sid,reply,'synthetic_test')
        self.assertEqual(ensemble.status(self.p,sid)['stage'],'actor')
        reply=response(packet);reply.update(used_fact_ids=['a_public'],pov_interior='他重新衡量已知处境。')
        ensemble.respond(self.p,sid,reply,'synthetic_test')

    def test_zero_hit_editor_reviews_process_and_setups_and_uncertainty_blocks(self):
        body='他把手收了回来。'
        packet=prose.review_packet(self.p,'V01-C01',body)
        self.assertEqual(packet['scan']['findings'],[])
        for term in ('自述','功法练习','晋升','铺垫','前证','局部','内心'):
            self.assertIn(term,packet['instructions'])
        report=clear_report(self.p,body);prose.verify_report(self.p,'V01-C01',body,report)
        row=next(r for r in report['categories'] if r['id']=='empty_situation')
        row.update(verdict='uncertain',rationale='合成协议夹具：章卡要求练习细节，但缺少当前法门与前证，暂不能判断。')
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',body,report)
