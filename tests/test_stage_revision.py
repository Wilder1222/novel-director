"""Real protocol execution with synthetic assessment data, not external approval."""
import tempfile
import unittest
from pathlib import Path
from tests.support import project, put
from tests.test_stages import specification, artifact, report, receipt, craft_review
from tests.test_prose_risks import clear_report
import creative_workflow as flow
import directed_revision as revision
import stage_gates as gates


def passed(p, pid, stage, **kwargs):
    gates.submit(p, pid, stage, artifact(stage, **kwargs))
    packet = gates.packet(p, pid, stage)
    gates.review(p, pid, stage, report(packet), receipt('host_supplied'))


def fixture(p):
    original = '原来雨棚下的两个人核对登记，把仍不确定的名字留在纸上，约好明早向柜台询问。'
    changed = '此时' + original[2:]
    manuscript = p / 'manuscript/V01-C01.md'; manuscript.parent.mkdir(exist_ok=True)
    manuscript.write_text(original, encoding='utf-8')
    from tests.test_writing_spec import configured
    configured(p,single=True,origin='tool_default')
    spec = specification(profile='revise', mode='host_supplied', scope=['V01-C01'])
    spec['author_input'] = '修订措辞，保留原稿。'
    spec['requirements'] = [{'id': 'R1', 'text': '保护原稿并仅修订措辞', 'quote': '保留原稿'}]
    pid = gates.start(p, spec)['pipeline_id']
    passed(p, pid, 'brief')
    passed(p, pid, 'diagnosis', sources=[{'kind': 'baseline', 'path': 'manuscript/V01-C01.md'}], work=artifact('diagnosis')['work'] + '\n' + original)
    run = flow.start(p, 'V01-C01')['run_id']; flow.submit(p, run, manuscript)
    review_path = p / 'fixture-review.json'
    put(review_path, {'reviewer_type': 'agent', 'issues': [{'severity': 'MINOR', 'code': 'FIXTURE', 'evidence': '仅测试首词替换。', 'citations': [{'quote': original}]}]})
    flow.review(p, run, review_path)
    plan_path = p / 'fixture-plan.json'
    put(plan_path, {'writer_id': 'fixture_writer', 'tasks': [{'issue_index': 0, 'goal': '替换首词', 'acceptance': '仅原来变此时', 'scope': [{'quote': original}]}],
        'preserve': [{'id': 'ending', 'reason': '保护约定', 'citation': {'quote': '约好明早向柜台询问。'}}],
        'quality_checks': [{'id': dim, 'criterion': '代码测试：保护维度'} for dim in revision.QUALITY]})
    planned = revision.plan(p, run, plan_path)
    patch_path = p / 'fixture-patch.json'
    put(patch_path, {'plan_sha256': planned['plan_sha256'], 'edits': [{'task_id': 'I001', 'start': 0, 'end': 2, 'old': '原来', 'new': '此时'}]})
    revision.apply(p, run, planned['revision_id'], patch_path)
    checked = revision.check(p, run)
    evidence = {'rationale': '临时代码测试，不代表真实文学验收。', 'before_citations': [{'quote': original}], 'after_citations': [{'quote': changed}]}
    assessment = {'reviewer_type': 'agent', 'reviewer_id': 'fixture_reviewer', 'origin': 'external_review',
        'before_sha256': checked['before_sha256'], 'after_sha256': checked['after_sha256'], 'plan_sha256': checked['plan_sha256'],
        'results': [{'task_id': 'I001', 'verdict': 'resolved', **evidence}],
        'quality_checks': [{'id': dim, 'verdict': 'preserved', **evidence} for dim in revision.QUALITY]}
    assessment_path = p / 'fixture-assessment.json'; put(assessment_path, assessment)
    revision.check(p, run, assessment_path)
    passed(p, pid, 'revision', sources=[{'kind': 'candidate', 'run_id': run}], work=artifact('revision')['work'] + '\n' + changed)
    put(review_path, {'reviewer_type': 'agent', 'issues': [], 'scores': {dim: {'score': 4, 'evidence': '测试数据', 'citations': [{'quote': changed}]} for dim in flow.SCORE_DIMENSIONS},'writing_spec_review':craft_review(p,changed),'prose_risks_review':clear_report(p,changed)})
    flow.review(p, run, review_path)
    root, m = flow._manifest(p, run)
    passed(p, pid, 'editorial', sources=[{'kind': 'run_review', 'run_id': run}], work=artifact('editorial')['work'] + '\n' + (root / m['latest_review']).read_text(encoding='utf-8'))
    passed(p, pid, 'delivery')
    return pid, run, original, changed, manuscript, assessment_path, assessment


class RevisionStages(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.p = project(Path(self.temp.name))

    def test_complete_revision_preserves_original_and_backup(self):
        pid, run, original, changed, path, _, _ = fixture(self.p)
        self.assertTrue(gates.status(self.p, pid)['complete'])
        self.assertEqual(path.read_text(encoding='utf-8'), original)
        flow.approve(self.p, run, 'fixture_author'); flow.publish(self.p, run, replace=True)
        self.assertEqual(path.read_text(encoding='utf-8'), changed)
        backups = list((self.p / 'manuscript/.history').glob('V01-C01.*.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding='utf-8'), original)

    def test_reassessment_invalidates_revision_and_dependents(self):
        pid, run, original, _, path, apath, assessment = fixture(self.p)
        assessment['results'][0]['verdict'] = 'unresolved'; put(apath, assessment)
        self.assertFalse(revision.check(self.p, run, apath)['revision_gate_ready'])
        rows = {x['stage']: x for x in gates.status(self.p, pid)['stages']}
        self.assertTrue(rows['diagnosis']['ready'])
        for stage in ('revision', 'editorial', 'delivery'):
            self.assertEqual(rows[stage]['state'], 'stale')
        with self.assertRaises(ValueError): flow.review(self.p, run, self.p / 'fixture-review.json')
        with self.assertRaises(ValueError): flow.approve(self.p, run, 'fixture_author')
        self.assertEqual(path.read_text(encoding='utf-8'), original)
