"""Novel pacing guidance must coexist with accepted-speech and review gates."""
import copy,tempfile,unittest
from pathlib import Path
from tests.support import project,scene_data,response,complete
from tests.test_prose_risks import clear_report
import ensemble_runtime as ensemble
import chapter_tools as chapters
import prose_risks as prose


class DialogueDensity(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.p=project(Path(temp.name))

    def test_actual_phase_and_chapter_packets_carry_novel_pacing_guidance(self):
        config,scene=scene_data();sid=ensemble.start(self.p,config,scene)['ensemble_id']
        actor=ensemble.packet(self.p,sid);self.assertIn('不凑轮次',actor['system'])
        ensemble.respond(self.p,sid,response(actor),'synthetic_test')
        resolver=ensemble.packet(self.p,sid);self.assertIn('关键未决',resolver['system'])
        while ensemble.status(self.p,sid)['stage']!='compose':
            packet=ensemble.packet(self.p,sid);ensemble.respond(self.p,sid,response(packet),'synthetic_test')
        composer=ensemble.packet(self.p,sid)
        self.assertIn(ensemble.NOVEL_DIALOGUE_PACING,composer['system'])
        self.assertIn('不设对白比例',composer['system'])
        ensemble.respond(self.p,sid,response(composer),'synthetic_test')
        other=complete(self.p,'two',11)
        aid=chapters.assembly_plan(self.p,'V01-C01',{'scene_ids':[sid,other]})['assembly_id']
        packet=chapters.assembly_packet(self.p,aid)
        self.assertIn(ensemble.NOVEL_DIALOGUE_PACING,packet['system'])
        self.assertNotIn('DIRECTOR_SECRET',str(packet))

    def test_density_advice_cannot_erase_summarize_or_split_accepted_speech(self):
        config,scene=scene_data();scene['turn_order']=['a_now','b_now','a_now','b_now']
        sid=ensemble.start(self.p,config,scene)['ensemble_id']
        words=['几点？地点呢？','九点。东门。','已经约好了吗？','已经约好了。'];index=0
        while ensemble.status(self.p,sid)['stage']!='compose':
            packet=ensemble.packet(self.p,sid);reply=response(packet)
            if packet['role']=='actor':reply['speech']=words[index];index+=1
            ensemble.respond(self.p,sid,reply,'synthetic_test')
        packet=ensemble.packet(self.p,sid);good=response(packet)
        alternatives=[good['text'].replace(words[0],''),
                      '他们已经约好九点于东门交接，约定的时间没有改变，地点也仍是刚才确认的东门。',
                      good['text'].replace(words[0],'几点？”他停了一下。“地点呢？')]
        for text in alternatives:
            with self.subTest(text=text),self.assertRaisesRegex(ValueError,'对白'):
                ensemble.respond(self.p,sid,{**good,'text':text},'synthetic_test')
        ensemble.respond(self.p,sid,good,'synthetic_test')
        other=complete(self.p,'two',11)
        aid=chapters.assembly_plan(self.p,'V01-C01',{'scene_ids':[sid,other]})['assembly_id']
        packet=chapters.assembly_packet(self.p,aid)
        valid={'request_id':packet['request_id'],
               'sections':[{'ensemble_id':s['ensemble_id'],'text':s['text']} for s in packet['input']['scenes']],
               'transitions':['随后雨停了。']}
        for text in alternatives:
            bad=copy.deepcopy(valid);bad['sections'][0]['text']=text
            with self.assertRaisesRegex(ValueError,'对白'):chapters.assembly_submit(self.p,aid,bad,'synthetic_test')
        chapters.assembly_submit(self.p,aid,valid,'synthetic_test')

    def test_zero_hit_context_review_includes_density_and_can_block(self):
        body='“东门？”“封了。”“西门？”“有火。”“北巷？”“还能走。”'
        packet=prose.review_packet(self.p,'V01-C01',body)
        self.assertEqual(packet['scan']['findings'],[])
        instructions=packet['instructions']+packet['scan']['category_requirements']['flattened_voice']
        for term in ('交流段','场景','整章','对白密度','概述','快速对答','不设对白比例'):
            self.assertIn(term,instructions)
        report=clear_report(self.p,body);prose.verify_report(self.p,'V01-C01',body,report)
        row=next(r for r in report['categories'] if r['id']=='flattened_voice')
        row['verdict']='uncertain';row['rationale']='合成协议夹具：当前缺少场景对照，不据对白数量下结论。'
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',body,report)
