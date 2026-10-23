"""Production budgets and evidence coverage, not literary-quality certification."""
import copy
import tempfile
import unittest
from pathlib import Path
from tests.support import project, put
import creative_workflow as flow
import writing_spec as writing


def configured(p, single=False, origin='synthetic_test'):
    units = [{'id': 'P1', 'purpose': '核对登记并决定下一步', 'range': {'min': 3, 'max': 6},
              'parts': [{'id': 'A', 'scene_id': 'one', 'order': 1, 'purpose': '核对登记', 'range': {'min': 3, 'max': 6}}]},
             {'id': 'P2', 'purpose': '回应分歧并承担后果', 'range': {'min': 3, 'max': 6},
              'parts': [{'id': 'B', 'scene_id': 'two', 'order': 2, 'purpose': '回应分歧', 'range': {'min': 3, 'max': 6}}]}]
    value = writing.template_value()
    value['origin'] = origin
    if single:
        units = units[:1]; units[0]['range'] = {'min': 1, 'max': 20000}; units[0]['parts'][0]['range'] = {'min': 1, 'max': 20000}
    value['chapters'] = [{'chapter_id': 'V01-C01', 'range': {'min': 1 if single else 6, 'max': 20000 if single else 10},
        'plot_units': units, 'detail_requirements': [], 'setups': [], 'setup_strategy': '本章核对既有信息，无新增长线伏笔；不把原有疑问伪称已解。'}]
    put(p / 'writing_spec.json', value)
    return value


def mapped(p, text='甲乙丙丁戊己', split=3):
    return writing.make_map(p, 'V01-C01', text, [{'part_id': 'A', 'start': 0, 'end': split}, {'part_id': 'B', 'start': split, 'end': len(text)}])


class WritingSpecs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.p = project(Path(self.temp.name))

    def test_current_chapter_defaults_match_static_project_template(self):
        import json
        value = writing.template_value()
        self.assertEqual(value['defaults']['chapter_range'], {'min': 3000, 'max': 6000})
        self.assertEqual(value['defaults']['plot_range'], {'min': 500, 'max': 2500})
        static = Path(writing.__file__).resolve().parents[1] / 'assets/project-template/writing_spec.json'
        self.assertEqual(json.loads(static.read_text(encoding='utf-8')), value)
        self.assertEqual(value['origin'], 'tool_default')

    def _current_chapter_candidate(self, length):
        value = writing.template_value()
        value['origin'] = 'synthetic_test'
        units = []
        for index in range(3):
            units.append({'id': f'P{index}', 'purpose': '合成预算边界验证',
                'range': {'min': 500, 'max': 2500},
                'parts': [{'id': f'A{index}', 'scene_id': f'scene{index}', 'order': index + 1,
                           'purpose': '验证实际计数而非模型填写字数', 'range': {'min': 500, 'max': 2500}}]})
        value['chapters'] = [{'chapter_id': 'V01-C01', 'range': value['defaults']['chapter_range'],
            'plot_units': units, 'detail_requirements': [], 'setups': [], 'setup_strategy': '合成计数验证，无小说铺垫主张。'}]
        put(self.p / 'writing_spec.json', value)
        lengths = [length // 3, length // 3, length - 2 * (length // 3)]
        return {'parts': [{'part_id': f'A{i}', 'text': ('甲', '乙', '丙')[i] * n} for i, n in enumerate(lengths)]}

    def test_current_chapter_range_accepts_both_endpoints(self):
        for length in (3000, 6000):
            with self.subTest(length=length):
                payload = self._current_chapter_candidate(length)
                text = ''.join(part['text'] for part in payload['parts'])
                self.assertEqual(writing.check(self.p, 'V01-C01', text, payload)['chapter_count'], length)

    def test_current_chapter_range_rejects_one_character_outside(self):
        for length in (2999, 6001):
            with self.subTest(length=length):
                payload = self._current_chapter_candidate(length)
                text = ''.join(part['text'] for part in payload['parts'])
                with self.assertRaisesRegex(ValueError, '章节实际'):
                    writing.check(self.p, 'V01-C01', text, payload)

    def test_counter_and_inclusive_bounds(self):
        self.assertEqual(writing.count('甲，乙 A12 e\u0301🙂\n'), 6)
        configured(self.p)
        result = writing.check(self.p, 'V01-C01', '甲乙丙丁戊己', mapped(self.p))
        self.assertEqual(result['chapter_count'], 6)
        self.assertEqual(result['plot_counts'], {'P1': 3, 'P2': 3})
        self.assertFalse(result['literary_quality_proven'])
        for text, split in [('甲乙丙丁戊', 3), ('甲乙丙丁戊己庚辛壬癸子', 5)]:
            with self.assertRaises(ValueError): writing.check(self.p, 'V01-C01', text, mapped(self.p, text, split))

    def test_raw_parts_compile_without_writer_hash_or_offsets(self):
        configured(self.p)
        parts = [{'part_id':'A','text':'甲乙丙\n'}, {'part_id':'B','text':'丁戊己'}]
        text, cm = writing.compile_parts(self.p,'V01-C01',parts)
        self.assertEqual(text,'甲乙丙\n丁戊己')
        self.assertEqual(cm['segments'][1]['start'],4)
        self.assertEqual(writing.check(self.p,'V01-C01',text,{'parts':parts})['chapter_count'],6)
        for bad in (parts[::-1], parts[:1], parts+[parts[0]]):
            with self.assertRaises(ValueError): writing.compile_parts(self.p,'V01-C01',bad)
        with self.assertRaises(ValueError): writing.check(self.p,'V01-C01','甲乙丙丁戊己',{'parts':parts})

    def test_chapter_pass_does_not_hide_bad_plot(self):
        configured(self.p)
        with self.assertRaises(ValueError): writing.check(self.p, 'V01-C01', '甲乙丙丁戊己', mapped(self.p, split=2))

    def test_map_coverage_hash_ids_and_unicode(self):
        configured(self.p); text = '甲乙丙丁戊己'; base = mapped(self.p)
        for change in ('overlap', 'tail', 'hash', 'unknown', 'unicode'):
            value = copy.deepcopy(base)
            if change == 'overlap': value['segments'][1]['start'] = 2
            elif change == 'tail': value['segments'][-1]['end'] = 5
            elif change == 'hash': value['candidate_sha256'] = '0' * 64
            elif change == 'unknown': value['segments'][0]['part_id'] = 'unknown'
            else: value['unicode_version'] = '0.0'
            with self.assertRaises(ValueError, msg=change): writing.check(self.p, 'V01-C01', text, value)
        with self.assertRaises(ValueError): writing.check(self.p, 'V01-C01', text, None)
        with self.assertRaises(ValueError): writing.check(self.p, 'V01-C01', '# 章标题\n'+text)
        with self.assertRaises(ValueError): writing.check(self.p, 'V01-C01', text+'\nPS:作者附言')

    def test_impossible_budget_and_private_fields(self):
        value = configured(self.p)
        value['chapters'][0]['range'] = {'min': 20, 'max': 30}
        with self.assertRaises(ValueError): writing.validate(self.p, value)
        value = configured(self.p); value['chapters'][0]['setups'] = [{'id': 'F1', 'scope': 'P1', 'operation': 'plant', 'criterion': '看见一处现象', 'prior': [], 'author_only_intent': '未来真凶'}]
        with self.assertRaises(ValueError): writing.validate(self.p, value)

    def test_scene_checks_only_its_parts(self):
        configured(self.p)
        value = writing.make_map(self.p, 'V01-C01', '甲乙丙', [{'part_id': 'A', 'start': 0, 'end': 3}])
        result = writing.check(self.p, 'V01-C01', '甲乙丙', value, scene_id='one')
        self.assertEqual(result['part_counts'], {'A': 3})
        self.assertEqual(result['scope'], 'scene:one')
        with self.assertRaises(ValueError): writing.check(self.p, 'V01-C01', '甲乙丙', value)

    def test_run_requires_map_and_rechecks_candidate(self):
        configured(self.p)
        run = flow.start(self.p, 'V01-C01')['run_id']
        text = '甲乙丙丁戊己' + '，。！' * 12
        path = self.p / 'draft.md'; path.write_text(text, encoding='utf-8')
        with self.assertRaises(ValueError): flow.submit(self.p, run, path)
        value = mapped(self.p, text)
        flow.submit(self.p, run, path, content_map=value)
        checked = writing.assert_run(self.p, run)
        self.assertEqual(checked['chapter_count'], 6)
        root, manifest = flow._manifest(self.p, run)
        self.assertTrue((root / manifest['content_map']).exists())
        (root / manifest['content_map']).write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError): writing.assert_run(self.p, run)

    def test_missing_spec_legacy_signature_unchanged(self):
        before = flow.signature(self.p)
        self.assertIsNone(writing.load(self.p))
        self.assertEqual(flow.signature(self.p), before)
        configured(self.p)
        self.assertNotEqual(flow.signature(self.p), before)

    def test_semantics_full_coverage_and_scope(self):
        configured(self.p)
        text = '甲乙丙丁戊己'; content_map = mapped(self.p)
        rules = writing.targets(self.p, 'V01-C01')
        result = {'spec_sha256': writing.load(self.p)['sha256'], 'candidate_sha256': flow.digest(text.encode()),
                  'checks': [{'id': r['id'], 'verdict': 'satisfied', 'rationale': '合成协议分支，不代表文学验收。',
                              'citations': [{'quote': '丁戊己' if r['scope'] == 'P2' else '甲乙丙'}]} for r in rules]}
        writing.verify_review(self.p, 'V01-C01', text, content_map, result)
        bad = copy.deepcopy(result); bad['checks'].pop()
        with self.assertRaises(ValueError): writing.verify_review(self.p, 'V01-C01', text, content_map, bad)
        bad = copy.deepcopy(result); bad['checks'][0]['verdict'] = 'uncertain'
        with self.assertRaises(ValueError): writing.verify_review(self.p, 'V01-C01', text, content_map, bad)
        bad = copy.deepcopy(result)
        for row in bad['checks']:
            if row['id'].endswith('P2:causality'): row['citations'] = [{'quote': '甲乙丙'}]
        with self.assertRaises(ValueError): writing.verify_review(self.p, 'V01-C01', text, content_map, bad)

    def test_local_patch_remaps_but_cross_part_requires_new_map(self):
        configured(self.p); before = '甲乙丙丁戊己'; cm = mapped(self.p)
        after = '甲乙丙庚丁戊己'
        changed = writing.remap(self.p, 'V01-C01', before, after, cm, [{'start': 2, 'end': 3, 'new': '丙庚'}])
        self.assertEqual(changed['segments'][0]['end'], 4)
        writing.check(self.p, 'V01-C01', after, changed)
        with self.assertRaises(ValueError): writing.remap(self.p, 'V01-C01', before, '甲乙戊己', cm, [{'start': 2, 'end': 4, 'new': ''}])
