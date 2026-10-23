"""Parts protocol regressions; fixtures are not external literary acceptance."""
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch
from tests.support import project, put, scene_data, response
from tests.test_writing_spec import configured
import writing_spec as writing
import ensemble_runtime as ensemble
import chapter_tools as chapters
import creative_workflow as flow


def configure_four_parts(p):
    value = configured(p)
    chapter = value['chapters'][0]
    chapter['range'] = {'min': 1, 'max': 40000}
    for index, unit in enumerate(chapter['plot_units']):
        unit['range'] = {'min': 1, 'max': 20000}
        base = deepcopy(unit['parts'][0])
        unit['parts'] = [
            {**base, 'id': 'A1' if index == 0 else 'B1',
             'order': index * 2 + 1, 'range': {'min': 1, 'max': 20000}},
            {**base, 'id': 'A2' if index == 0 else 'B2',
             'order': index * 2 + 2, 'range': {'min': 1, 'max': 20000}},
        ]
    put(p / 'writing_spec.json', value)


def at_compose(p, label='one', hour=10):
    config, scene = scene_data(label=label, hour=hour)
    sid = ensemble.start(p, config, scene)['ensemble_id']
    while ensemble.status(p, sid)['stage'] != 'compose':
        packet = ensemble.packet(p, sid)
        ensemble.respond(p, sid, response(packet, label), 'synthetic_test')
    return sid, ensemble.packet(p, sid)


def complete_parts(p, label, hour, ids):
    sid, packet = at_compose(p, label, hour)
    body = response(packet, label)['text']
    cut = len(body) // 2
    raw = {'request_id': packet['request_id'], 'parts': [
        {'part_id': ids[0], 'text': body[:cut]},
        {'part_id': ids[1], 'text': body[cut:]},
    ]}
    original = deepcopy(raw)
    ensemble.respond(p, sid, raw, 'synthetic_test')
    state = ensemble._load(p, sid)[1]
    assert raw == original
    assert state['calls'][-1]['response_digest'] == ensemble._hash(original)
    return sid, body


def ready_assembly(p):
    configure_four_parts(p)
    a, left = complete_parts(p, 'one', 10, ('A1', 'A2'))
    b, right = complete_parts(p, 'two', 11, ('B1', 'B2'))
    aid = chapters.assembly_plan(p, 'V01-C01', {'scene_ids': [a, b]})['assembly_id']
    packet = chapters.assembly_packet(p, aid)
    left += '她合上登记簿。'
    right += '他把湿伞移到墙边。'
    cut_left, cut_right = len(left) // 2, len(right) // 2
    bridge = '\n\n***\n\n片刻之后。\n\n'
    raw = {'request_id': packet['request_id'],
           'sections': [{'ensemble_id': a, 'text': left},
                        {'ensemble_id': b, 'text': right}],
           'transitions': ['片刻之后。'],
           'parts': [
               {'part_id': 'A1', 'text': left[:cut_left]},
               {'part_id': 'A2', 'text': left[cut_left:] + bridge},
               {'part_id': 'B1', 'text': right[:cut_right]},
               {'part_id': 'B2', 'text': right[cut_right:]},
           ]}
    return aid, raw


def interrupt_final_save(p, aid, raw):
    with patch.object(chapters, '_save', side_effect=OSError('fixture final save failure')):
        try:
            chapters.assembly_submit(p, aid, raw, 'synthetic_test')
        except OSError:
            pass
        else:
            raise AssertionError('fixture did not stop at final save')
    run_id = 'run-' + ensemble._hash({'assembly_id': aid})[:12]
    root, manifest = flow._manifest(p, run_id)
    assert manifest['status'] == 'drafted'
    return run_id, root, manifest


class PartsReview(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.p = project(Path(temp.name))

    def test_unicode_drift_rejected_without_rewriting_state_or_response(self):
        configured(self.p, single=True)
        sid, packet = at_compose(self.p)
        raw = {'request_id': packet['request_id'], 'parts': [
            {'part_id': 'A', 'text': response(packet)['text']},
        ]}
        original = deepcopy(raw)
        path = ensemble._folder(self.p, sid) / 'state.json'
        before = path.read_bytes()
        with patch.object(writing.unicodedata, 'unidata_version', 'CHANGED'):
            with self.assertRaisesRegex(ValueError, 'Unicode'):
                ensemble.respond(self.p, sid, raw, 'synthetic_test')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(raw, original)
        self.assertEqual(ensemble.status(self.p, sid)['stage'], 'compose')

    def test_exact_rewrite_parts_preserve_original_response_digest(self):
        aid, raw = ready_assembly(self.p)
        original = deepcopy(raw)
        result = chapters.assembly_submit(self.p, aid, raw, 'synthetic_test')
        state = chapters._load(self.p, aid)[1]
        self.assertEqual(raw, original)
        self.assertEqual(state['response_digest'], ensemble._hash(original))
        self.assertEqual(result['state'], 'drafted')
        writing.assert_run(self.p, result['run_id'])

    def test_mismatch_and_wrong_scene_rejected_before_attempt_or_run(self):
        aid, raw = ready_assembly(self.p)
        folder = chapters._folder(self.p, aid)
        before = (folder / 'state.json').read_bytes()
        mismatched = deepcopy(raw)
        mismatched['parts'][0]['text'] += '额外字'
        wrong_scene = deepcopy(raw)
        stolen = wrong_scene['parts'][1]['text'][-1:]
        wrong_scene['parts'][1]['text'] = wrong_scene['parts'][1]['text'][:-1]
        wrong_scene['parts'][2]['text'] = stolen + wrong_scene['parts'][2]['text']
        # The stolen character is from the separator, so use an actual scene
        # character instead: move the final left-section character and bridge.
        left = raw['sections'][0]['text']
        bridge = '\n\n***\n\n片刻之后。\n\n'
        left_cut = len(raw['parts'][0]['text'])
        wrong_scene['parts'][1]['text'] = left[left_cut:-1]
        wrong_scene['parts'][2]['text'] = left[-1:] + bridge + raw['parts'][2]['text']
        for bad in (mismatched, wrong_scene):
            original = deepcopy(bad)
            with self.assertRaises(ValueError):
                chapters.assembly_submit(self.p, aid, bad, 'synthetic_test')
            self.assertEqual(bad, original)
            self.assertEqual((folder / 'state.json').read_bytes(), before)
            self.assertFalse(list(folder.glob('attempt-*')))
            self.assertFalse((self.p / '.novel_runs').exists())

    def test_corrupt_recovery_map_rejected_without_accepting_response(self):
        aid, raw = ready_assembly(self.p)
        original = deepcopy(raw)
        run_id, root, manifest = interrupt_final_save(self.p, aid, raw)
        (root / manifest['content_map']).write_text('{}', encoding='utf-8')
        state_path = chapters._folder(self.p, aid) / 'state.json'
        before = state_path.read_bytes()
        with self.assertRaisesRegex(ValueError, '映射'):
            chapters.assembly_submit(self.p, aid, raw, 'synthetic_test')
        self.assertEqual(state_path.read_bytes(), before)
        self.assertEqual(raw, original)
        self.assertIsNone(chapters._load(self.p, aid)[1].get('response_digest'))

    def test_valid_but_different_recovery_map_rejected(self):
        aid, raw = ready_assembly(self.p)
        original = deepcopy(raw)
        run_id, root, manifest = interrupt_final_save(self.p, aid, raw)
        alternate = deepcopy(raw['parts'])
        shifted = alternate[1]['text'][:1]
        alternate[0]['text'] += shifted
        alternate[1]['text'] = alternate[1]['text'][1:]
        same_body = (root / manifest['current_candidate']).read_text(encoding='utf-8')
        self.assertEqual(''.join(x['text'] for x in alternate), same_body)
        flow.submit(self.p, run_id, root / manifest['current_candidate'],
                    content_map={'parts': alternate})
        writing.assert_run(self.p, run_id)  # Valid map, not the original partition.
        state_path = chapters._folder(self.p, aid) / 'state.json'
        before = state_path.read_bytes()
        with self.assertRaisesRegex(ValueError, '映射'):
            chapters.assembly_submit(self.p, aid, raw, 'synthetic_test')
        self.assertEqual(state_path.read_bytes(), before)
        self.assertEqual(raw, original)
        self.assertIsNone(chapters._load(self.p, aid)[1].get('response_digest'))

    def test_unchanged_recovery_keeps_original_response_digest(self):
        aid, raw = ready_assembly(self.p)
        original = deepcopy(raw)
        run_id, _, _ = interrupt_final_save(self.p, aid, raw)
        result = chapters.assembly_submit(self.p, aid, raw, 'synthetic_test')
        self.assertEqual(result['run_id'], run_id)
        self.assertEqual(raw, original)
        self.assertEqual(chapters._load(self.p, aid)[1]['response_digest'],
                         ensemble._hash(original))
        self.assertEqual(len(list((self.p / '.novel_runs').glob('run-*'))), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
