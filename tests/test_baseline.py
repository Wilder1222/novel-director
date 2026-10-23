from pathlib import Path
import copy
import json
import tempfile
import unittest
from tests.support import ROOT, SKILL, project, put, scene_data, response
import creative_workflow as flow
import ensemble_runtime as ensemble
import evidence_audit as evidence
import directed_revision as revision
import novel
import story_memory


class Baseline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = project(Path(self.tmp.name))

    def reviewed(self):
        run = flow.start(self.p, 'V01-C01')['run_id']
        draft = self.p / 'draft.txt'
        draft.write_text('她把湿伞留在门边，逐行核对登记簿。最后一行字迹被水洇开，她没有替空白补上答案。', encoding='utf-8')
        flow.submit(self.p, run, draft)
        r = self.p / 'review.json'
        put(r, {'reviewer_type': 'agent', 'issues': [], 'summary_citations': [{'quote': '她把湿伞留在门边'}]})
        flow.review(self.p, run, r)
        return run

    def test_synthetic_lifecycle_requires_review_and_approval(self):
        run = self.reviewed()
        with self.assertRaises(ValueError): flow.publish(self.p, run)
        flow.approve(self.p, run, 'synthetic_test')
        self.assertEqual(flow.publish(self.p, run)['state'], 'published')

    def test_candidate_drift_invalidates_approval(self):
        run = self.reviewed(); folder, m = flow._manifest(self.p, run)
        (folder / m['current_candidate']).write_text('已改动的文字', encoding='utf-8')
        with self.assertRaises(ValueError): flow.approve(self.p, run, 'synthetic_test')

    def test_review_drift_invalidates_approval(self):
        run = self.reviewed(); folder, m = flow._manifest(self.p, run)
        (folder / m['latest_review']).write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError): flow.approve(self.p, run, 'synthetic_test')

    def test_style_drift_invalidates_publish(self):
        run = self.reviewed(); flow.approve(self.p, run, 'synthetic_test')
        (self.p / 'style.md').write_text('不同文风', encoding='utf-8')
        with self.assertRaises(ValueError): flow.publish(self.p, run)

    def test_contract_drift_invalidates_publish(self):
        run = self.reviewed(); flow.approve(self.p, run, 'synthetic_test')
        folder, m = flow._manifest(self.p, run)
        (folder / 'contract.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError): flow.publish(self.p, run)

    def test_wrong_or_ambiguous_quote_rejected(self):
        for cite in ({'quote': '不存在'}, {'quote': '同一句'}):
            with self.subTest(cite=cite), self.assertRaises(ValueError): evidence.locate('同一句，同一句。', cite)

    def test_actor_filters_other_private_and_future(self):
        c, sc = scene_data(); sid = ensemble.start(self.p, c, sc)['ensemble_id']
        text = json.dumps(ensemble.packet(self.p, sid), ensure_ascii=False)
        self.assertIn('a_SECRET', text)
        for secret in ('b_SECRET', 'a_FUTURE', 'b_PRIVATE', 'DIRECTOR_SECRET'):
            self.assertNotIn(secret, text)

    def test_request_replay_rejected(self):
        c, sc = scene_data(); sid = ensemble.start(self.p, c, sc)['ensemble_id']
        reply = response(ensemble.packet(self.p, sid)); ensemble.respond(self.p, sid, reply, 'synthetic_test')
        with self.assertRaises(ValueError): ensemble.respond(self.p, sid, reply, 'synthetic_test')

    def test_forbidden_fact_disclosure_rejected(self):
        c, sc = scene_data(); sid = ensemble.start(self.p, c, sc)['ensemble_id']
        r = response(ensemble.packet(self.p, sid)); r.update(used_fact_ids=['a_secret'], disclosed_fact_ids=['a_secret'])
        with self.assertRaises(ValueError): ensemble.respond(self.p, sid, r, 'synthetic_test')

    def test_compose_private_and_dialogue_boundaries(self):
        c, sc = scene_data(); sid = ensemble.start(self.p, c, sc)['ensemble_id']
        while ensemble.status(self.p, sid)['stage'] != 'compose':
            p = ensemble.packet(self.p, sid); ensemble.respond(self.p, sid, response(p), 'synthetic_test')
        p = ensemble.packet(self.p, sid); text = json.dumps(p)
        for secret in ('_SECRET', '_INTENT', 'DIRECTOR_SECRET'): self.assertNotIn(secret, text)
        with self.assertRaises(ValueError): ensemble.respond(self.p, sid, {'request_id': p['request_id'], 'text': '遗漏了对白的场景文字' * 6})

    def test_revision_out_of_scope_rejected(self):
        text = '保留此句。需要修改的句子。' * 3
        plan = {'tasks': [{'id': 'I001', 'scope': [{'start': 5, 'end': 14}]}], 'preserve': []}
        patch = {'plan_sha256': 'hash', 'edits': [{'task_id': 'I001', 'start': 0, 'end': 4, 'old': text[:4], 'new': '替换'}]}
        with self.assertRaises(ValueError): revision._transform(text, plan, 'hash', patch)

    def test_same_chapter_relationship_not_retrievable(self):
        put(self.p / 'relationships.json', {'moments': [{'id': 'r1', 'chapter_id': 'V01-C02', 'pair_ids': ['a', 'b'],
            'from_state': '戒备', 'to_state': 'SAME_CHAPTER_SECRET', 'trigger_action': '交出钥匙', 'status': 'planned'}]})
        story_memory.build(self.p)
        hits = story_memory.search(self.p, 'SAME_CHAPTER_SECRET', 'V01-C02', 'H0', 'a')
        self.assertNotIn('SAME_CHAPTER_SECRET', json.dumps(hits))

    def test_blank_template_has_no_story_date_or_travel_rule(self):
        p = json.loads((SKILL / 'assets/project-template/project.json').read_text(encoding='utf-8'))
        self.assertIsNone(p['age_anchor_date'])
        self.assertEqual(p['time_rules'], {})

    def test_explicit_legacy_rules_still_validate(self):
        p = json.loads((self.p / 'project.json').read_text(encoding='utf-8'))
        p.update(age_anchor_date='2026-01-01', expected_ages={'a': 36}, time_rules={'max_stay_hours': 72})
        put(self.p / 'project.json', p)
        self.assertFalse([x for x in novel.audit(self.p)[0] if x[0] == 'ERROR'])

    def test_expected_age_requires_explicit_anchor(self):
        p = json.loads((self.p / 'project.json').read_text(encoding='utf-8'))
        p.update(age_anchor_date=None, expected_ages={'a': 36}); put(self.p / 'project.json', p)
        self.assertIn('AGE_ANCHOR_REQUIRED', [item[1] for item in novel.audit(self.p)[0]])
