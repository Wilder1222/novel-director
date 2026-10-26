"""Dialogue rhythm clues and accepted-speech integrity, never AI identity scoring."""
import copy
import tempfile
import unittest
from pathlib import Path
from tests.support import project, put, scene_data, response
from tests.test_prose_risks import clear_report
import prose_risks as prose
import ensemble_runtime as ensemble
import chapter_tools as chapters


class DialogueRhythm(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.p = project(Path(temp.name))

    def clues(self, text):
        return [f for f in prose.scan(self.p, 'V01-C01', text)['findings']
                if f['rule_id'].startswith('dialogue_')]

    def test_quoted_clues_have_exact_original_offsets(self):
        cases = [('“我……没答应。”', 'dialogue_pause', '……'),
                 ('「别碰——」', 'dialogue_pause', '——'),
                 ('『我、我没答应。』', 'dialogue_restart', '我、我'),
                 ('"我...没答应。"', 'dialogue_pause', '...'),
                 ('"我...我没答应。"', 'dialogue_restart', '我...我'),
                 ('“不不不，我不去。”', 'dialogue_restart', '不不不'),
                 ('“别动！别动！”', 'dialogue_restart', '别动！别动'),
                 ('“怎么会？！”', 'dialogue_punctuation_stack', '？！')]
        for text, rule, quote in cases:
            with self.subTest(text=text):
                body = '🧪雨声还在。\r\n' + text + '门没有开。'
                findings = self.clues(body)
                self.assertTrue(any(f['rule_id'] == rule and f['quote'] == quote for f in findings))
                for finding in findings:
                    self.assertEqual(body[finding['start']:finding['end']], finding['quote'])
                    self.assertEqual(finding['category'], 'flattened_voice')
                self.assertEqual(findings, self.clues(body))

    def test_narration_plain_answers_and_lexical_reduplication_are_not_new_clues(self):
        for text in ['他在纸上写下……与——，不，不，不是台词。',
                     '“收到。”“退后！”“爸爸来了。”“人人有份。”',
                     "‘我……我、我没答应！’", '“门没开。”他在门外……',
                     '他只说“没有”，不，不，别在叙述中找口吃。']:
            with self.subTest(text=text):
                self.assertEqual(self.clues(text), [])

    def test_first_clue_per_kind_and_no_long_utterance_truncation(self):
        text = '“' + '路还没走完，' * 800 + '我……我……不能去？！”'
        findings = self.clues(text)
        self.assertEqual({f['rule_id'] for f in findings},
                         {'dialogue_pause', 'dialogue_restart', 'dialogue_punctuation_stack'})
        self.assertEqual(len(findings), 3)
        self.assertEqual(next(f['start'] for f in findings if f['rule_id'] == 'dialogue_pause'),
                         text.index('……'))
        with self.assertRaisesRegex(ValueError, '256'):
            self.clues('“……。”\n' * 257)

    def test_intentional_is_allowed_but_omissions_uncertainty_and_partial_cites_fail(self):
        text = '“我……我、我没答应？！”'
        report = clear_report(self.p, text)
        self.assertGreaterEqual(len(report['findings']), 3)
        prose.verify_report(self.p, 'V01-C01', text, report)
        bad = copy.deepcopy(report)
        bad['findings'].pop()
        with self.assertRaises(ValueError): prose.verify_report(self.p, 'V01-C01', text, bad)
        bad = copy.deepcopy(report)
        bad['findings'][0]['disposition'] = 'uncertain'
        with self.assertRaises(ValueError): prose.verify_report(self.p, 'V01-C01', text, bad)
        bad = copy.deepcopy(report)
        f = prose.scan(self.p, 'V01-C01', text)['findings'][0]
        bad['findings'][0]['citations'] = [{'quote':text[f['start']], 'start':f['start'], 'end':f['start']+1}]
        with self.assertRaisesRegex(ValueError, '覆盖'): prose.verify_report(self.p, 'V01-C01', text, bad)
        with self.assertRaisesRegex(ValueError, '重扫'): prose.verify_report(self.p, 'V01-C01', text+'门开了。', report)

    def test_builtin_clue_protection_is_exact_and_not_an_exemption(self):
        text = '“我……没答应。”'
        f = self.clues(text)[0]
        put(self.p/'prose_risks.json', {'schema_version':'1', 'entries':[], 'protections':[
            {'id':'keep-pause', 'chapter_id':'V01-C01', 'rule_id':f['rule_id'],
             'candidate_sha256':prose.scan(self.p, 'V01-C01', text)['candidate_sha256'],
             'quote':f['quote'], 'start':f['start'], 'end':f['end'],
             'reason':'协议夹具：此处有意停顿', 'author_quote':'协议夹具：保留这个停顿'}]})
        self.assertEqual(self.clues(text)[0]['protected_by'], ['keep-pause'])
        self.assertEqual(self.clues(text+'门开了。')[0]['protected_by'], [])
        report = clear_report(self.p, text)
        report['findings'][0]['disposition'] = 'uncertain'
        with self.assertRaises(ValueError): prose.verify_report(self.p, 'V01-C01', text, report)

    def test_private_entries_cannot_shadow_builtin_rules(self):
        row = copy.deepcopy(prose.corpus(self.p)['entries'][0])
        row['id'] = 'dialogue_pause'
        put(self.p/'prose_risks.json', {'schema_version':'1', 'entries':[row], 'protections':[]})
        with self.assertRaisesRegex(ValueError, '保留'): prose.corpus(self.p)

    def test_editor_packet_covers_flatness_and_overuse_even_with_zero_clues(self):
        packet = prose.review_packet(self.p, 'V01-C01', '“收到。”')
        self.assertEqual(packet['scan']['findings'], [])
        required = packet['instructions'] + packet['scan']['category_requirements']['flattened_voice']
        for phrase in ('省略号', '结巴', '重复', '过平', '堆叠', '零命中'):
            self.assertIn(phrase, required)
        packet = prose.review_packet(self.p, 'V01-C01', '“我……我没答应？！”')
        self.assertEqual(set(packet['dialogue_rhythm_rules']),
                         {'dialogue_pause', 'dialogue_restart', 'dialogue_punctuation_stack'})

    def _to_compose(self, label='one', hour=10):
        config, scene = scene_data(label=label, hour=hour)
        sid = ensemble.start(self.p, config, scene)['ensemble_id']
        while ensemble.status(self.p, sid)['stage'] != 'compose':
            packet = ensemble.packet(self.p, sid)
            reply = response(packet)
            if packet['role'] == 'actor':
                for word in ('省略号', '结巴', '重复', '不设配额'):
                    self.assertIn(word, packet['system'])
                reply['speech'] = '我……我、我没答应！'
            ensemble.respond(self.p, sid, reply, 'synthetic_test')
        return sid

    def test_actor_compose_and_assembly_preserve_punctuation_and_repetitions(self):
        speech = '我……我、我没答应！'
        first = self._to_compose()
        packet = ensemble.packet(self.p, first)
        self.assertIn('省略号', packet['system'])
        good = response(packet)
        for replacement in ('我没答应！', '我…我、我没答应！', '我……我没答应！'):
            bad = copy.deepcopy(good)
            bad['text'] = bad['text'].replace(speech, replacement, 1)
            with self.assertRaisesRegex(ValueError, '对白'):
                ensemble.respond(self.p, first, bad, 'synthetic_test')
        ensemble.respond(self.p, first, good, 'synthetic_test')
        second = self._to_compose('two', 11)
        packet = ensemble.packet(self.p, second)
        ensemble.respond(self.p, second, response(packet), 'synthetic_test')
        aid = chapters.assembly_plan(self.p, 'V01-C01', {'scene_ids':[first, second]})['assembly_id']
        packet = chapters.assembly_packet(self.p, aid)
        self.assertIn('省略号', packet['system'])
        for scene in packet['input']['scenes']:
            self.assertEqual(scene['accepted_speech'], [speech, speech])
        good = {'request_id':packet['request_id'],
                'sections':[{'ensemble_id':s['ensemble_id'], 'text':s['text']} for s in packet['input']['scenes']],
                'transitions':['随后雨停了。']}
        for replacement in ('我没答应！', '我…我、我没答应！', ''):
            bad = copy.deepcopy(good)
            bad['sections'][0]['text'] = bad['sections'][0]['text'].replace(speech, replacement, 1)
            with self.assertRaisesRegex(ValueError, '对白'):
                chapters.assembly_submit(self.p, aid, bad, 'synthetic_test')
        chapters.assembly_submit(self.p, aid, good, 'synthetic_test')
