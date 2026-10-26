"""Instance-scoped speech habits and context delivery; no generated-quality claim."""
import copy
import tempfile
import unittest
from pathlib import Path
from tests.support import project, put, scene_data, response, complete
import ensemble_runtime as ensemble
import chapter_tools as chapters
import prose_risks as prose
import creative_workflow as flow


def style(marker='OWN_HABIT'):
    return {'personality':'谨慎但能拒绝，不等于胆怯', 'baseline_tone':'平常简洁温和',
            'verbal_habits':'先问当前问题，不念性格标签',
            'catchphrases':[{'phrase':marker, 'when':'熟悉搭档急于行动时劝其放慢',
                            'avoid_when':'正式交接或对陌生人，不显得轻慢'}]}


class DialogueIdentity(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.p=project(Path(temp.name))

    def test_old_config_and_partial_styles_do_not_gain_invented_habits(self):
        for value in (None, {}, {'baseline_tone':'简洁'}, {'catchphrases':[]}):
            with self.subTest(style=value):
                config,scene=scene_data()
                if value is not None:config['instances'][0]['speech_style']=value
                sid=ensemble.start(self.p,config,scene)['ensemble_id']
                packet=ensemble.packet(self.p,sid)
                if value is None:self.assertNotIn('speech_style',packet['input'])
                else:self.assertEqual(packet['input']['speech_style'],value)

    def test_style_contract_rejects_bad_types_conditions_and_duplicate_phrases(self):
        bad=[None, [], '温和', {'personality':''}, {'baseline_tone':False},
             {'verbal_habits':[]}, {'hidden_relation':'私密'}, {'catchphrases':'哦'},
             {'catchphrases':[{'phrase':'哦','when':'说话时'}]},
             {'catchphrases':[{'phrase':'哦','when':'说话时','avoid_when':''}]},
             {'catchphrases':[{'phrase':'哦','when':'说话时','avoid_when':'正式','extra':'未知'}]}]
        repeated=style();repeated['catchphrases']*=2;bad.append(repeated)
        spaced=style();spaced['catchphrases'].append({**spaced['catchphrases'][0],'phrase':' OWN_HABIT '});bad.append(spaced)
        crowded=style();crowded['catchphrases']=[{**crowded['catchphrases'][0],'phrase':str(i)} for i in range(9)];bad.append(crowded)
        for value in bad:
            with self.subTest(value=value):
                config,scene=scene_data();config['instances'][0]['speech_style']=value
                with self.assertRaises(ValueError):ensemble.start(self.p,config,scene)
        config,scene=scene_data();config['profiles']['a']['speech_style']=style()
        with self.assertRaises(ValueError):ensemble.start(self.p,config,scene)

    def test_core_and_npc_receive_only_their_style_with_context_and_deepcopy(self):
        config,scene=scene_data();config['core_ids']=['a']
        for actor,marker in zip(config['instances'],('A_PRIVATE_HABIT','B_PRIVATE_HABIT')):
            actor['speech_style']=style(marker)
        sid=ensemble.start(self.p,config,scene)['ensemble_id']
        packet=ensemble.packet(self.p,sid)
        self.assertEqual(packet['input']['speech_style'],config['instances'][0]['speech_style'])
        self.assertEqual(packet['input']['goal'],config['instances'][0]['goal'])
        self.assertEqual(packet['input']['relationship_view'],config['instances'][0]['relationship_view'])
        for marker in ('B_PRIVATE_HABIT','DIRECTOR_SECRET','a_FUTURE','b_SECRET'):
            self.assertNotIn(marker,str(packet))
        packet['input']['speech_style']['catchphrases'][0]['phrase']='CHANGED_COPY'
        self.assertEqual(ensemble.packet(self.p,sid)['input']['speech_style']['catchphrases'][0]['phrase'],'A_PRIVATE_HABIT')
        self.assertEqual(config['instances'][0]['speech_style']['catchphrases'][0]['phrase'],'A_PRIVATE_HABIT')
        for _ in range(2):
            packet=ensemble.packet(self.p,sid);ensemble.respond(self.p,sid,response(packet),'synthetic_test')
        packet=ensemble.packet(self.p,sid)
        self.assertEqual(packet['worker_id'],'npc-pool')
        self.assertEqual(packet['input']['speech_style'],config['instances'][1]['speech_style'])
        self.assertNotIn('A_PRIVATE_HABIT',str(packet))
        self.assertTrue(packet['input']['observations'])

    def test_same_character_in_another_history_cannot_supply_missing_style(self):
        config,scene=scene_data()
        versions=flow.getjson(self.p/'versions.json');versions['versions'].append({'id':'H1','name':'合成另一历史'})
        put(self.p/'versions.json',versions)
        other=copy.deepcopy(config['instances'][0]);other.update(id='a_other',history_id='H1',age=46,speech_style=style('FUTURE_PRIVATE_HABIT'))
        config['instances'].append(other)
        for own_style in (None,style('CURRENT_HABIT')):
            if own_style is not None:config['instances'][0]['speech_style']=own_style
            sid=ensemble.start(self.p,config,scene)['ensemble_id'];packet=ensemble.packet(self.p,sid)
            self.assertNotIn('FUTURE_PRIVATE_HABIT',str(packet))
            if own_style is None:self.assertNotIn('speech_style',packet['input'])
            else:self.assertEqual(packet['input']['speech_style'],own_style)

    def test_goal_relationship_and_new_reply_remain_alongside_stable_voice(self):
        config,scene=scene_data();scene['turn_order']=['a_now','b_now','a_now']
        config['instances'][0]['speech_style']=style()
        sid=ensemble.start(self.p,config,scene)['ensemble_id'];before=ensemble.packet(self.p,sid)
        _,state=ensemble._load(self.p,sid);changed=copy.deepcopy(state)
        changed['config']['instances'][0].update(goal='请求多等十分钟',relationship_view='只认识对方，不预设亲近')
        after=ensemble._build_packet(changed)
        self.assertEqual(after['input']['profile'],before['input']['profile'])
        self.assertEqual(after['input']['speech_style'],before['input']['speech_style'])
        self.assertEqual(after['input']['goal'],'请求多等十分钟')
        self.assertEqual(after['input']['relationship_view'],'只认识对方，不预设亲近')
        self.assertNotEqual(after['request_id'],before['request_id'])
        for _ in range(4):
            packet=ensemble.packet(self.p,sid);reply=response(packet)
            if packet['role']=='actor' and packet['input']['instance_id']=='b_now':reply['speech']='可以等十分钟，但不保证延期获准。'
            ensemble.respond(self.p,sid,reply,'synthetic_test')

        again=ensemble.packet(self.p,sid)
        self.assertIn('可以等十分钟，但不保证延期获准。',str(again['input']['observations']))
        self.assertEqual(again['input']['speech_style'],before['input']['speech_style'])

    def test_private_style_is_not_sent_to_resolver_or_composer(self):
        config,scene=scene_data();config['instances'][0]['speech_style']=style('UNSPOKEN_PRIVATE_HABIT')
        config['instances'][0]['relationship_view']='PRIVATE_ONE_WAY_RELATION'
        sid=ensemble.start(self.p,config,scene)['ensemble_id']
        while ensemble.status(self.p,sid)['stage']!='complete':
            packet=ensemble.packet(self.p,sid)
            if packet['role']!='actor':
                self.assertNotIn('speech_style',packet['input'])
                self.assertNotIn('UNSPOKEN_PRIVATE_HABIT',str(packet))
                self.assertNotIn('PRIVATE_ONE_WAY_RELATION',str(packet))
            reply=response(packet)
            if packet['role']=='actor' and packet['input']['instance_id']=='a_now':reply['speech']='先等等，先核对登记。'
            if packet['role']=='compose':
                good=copy.deepcopy(reply);bad=copy.deepcopy(reply)
                bad['text']=bad['text'].replace('先等等，先核对登记。','先核对登记。')
                with self.assertRaisesRegex(ValueError,'对白'):ensemble.respond(self.p,sid,bad,'synthetic_test')
                reply=good
            ensemble.respond(self.p,sid,reply,'synthetic_test')

        other=complete(self.p,'two',11)
        aid=chapters.assembly_plan(self.p,'V01-C01',{'scene_ids':[sid,other]})['assembly_id']
        assembly=chapters.assembly_packet(self.p,aid)
        self.assertNotIn('UNSPOKEN_PRIVATE_HABIT',str(assembly))
        self.assertNotIn('PRIVATE_ONE_WAY_RELATION',str(assembly))
        self.assertNotIn('speech_style',str(assembly['input']))

    def test_actor_instruction_joins_relationship_task_personality_tone_and_habits(self):
        config,scene=scene_data();sid=ensemble.start(self.p,config,scene)['ensemble_id']
        instruction=ensemble.packet(self.p,sid)['system']
        for term in ('speech_style','单向','goal','常态语气','口头禅','when','avoid_when','不考勤'):
            self.assertIn(term,instruction)

    def test_zero_hit_editor_still_reviews_context_and_does_not_require_a_catchphrase(self):
        packet=prose.review_packet(self.p,'V01-C01','“收到。”')
        self.assertEqual(packet['scan']['findings'],[])
        instructions=packet['instructions']+packet['scan']['category_requirements']['flattened_voice']
        for term in ('任务','性格','常态语气','口头禅','关系','未出现口头禅不判错'):
            self.assertIn(term,instructions)
