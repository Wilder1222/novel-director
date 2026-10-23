"""Stage gates check real artifacts and evidence, never literary truth."""
import copy
import tempfile
import unittest
from pathlib import Path
from tests.support import project, workspace, put, scene_data, response
from tests.test_prose_risks import clear_report
import stage_gates as gates
import creative_workflow as flow


def specification(profile='explore', mode='synthetic_test', scope=None):
    return {'profile': profile, 'mode': mode, 'author_input': '只讨论雨棚重逢，不写正文。',
            'requirements': [{'id': 'R1', 'text': '只讨论，不写正文', 'quote': '不写正文'}],
            'scope': scope or [], 'context_files': ['project.json', 'style.md']}


def artifact(stage, **extra):
    items = []
    work = '# 实际阶段作品\n\n'
    for section in gates.catalog()['stages'][stage]['sections']:
        quote = '【' + section + '】：雨棚下先核对登记，不扩大为正式设定或未经授权的正文。'
        work += quote + '\n\n'
        items.append({'id': section, 'section': section, 'quote': quote, 'meaning': '具体内容与约束相互对应。'})
    return {'work': work, 'items': items, 'producer': {'worker_id': 'writer', 'invocation_id': 'write-1'}, **extra}


def report(packet, verdict='pass'):
    checks = []
    for target in packet['review_targets']:
        quote = packet['items'][0]['quote']
        if target.startswith('item:'):
            quote = next(x['quote'] for x in packet['items'] if 'item:' + x['id'] == target)
        citations=[{'quote':quote}]
        if target.startswith('writing:'):
            a,b=packet['writing_scope_spans'][target][0]
            citations=[{'quote':packet['work'][a:b],'start':a,'end':b}]
        if target.startswith('prose:'):
            a,b=packet['prose_scope_spans'][target][0]
            citations=[{'quote':packet['work'][a:b],'start':a,'end':b}]
        checks.append({'target': target, 'verdict': verdict,
                       'reason': '检查了该项的实际内容与限定范围。', 'citations': citations})
    return {'packet_sha256': packet['packet_sha256'], 'checks': checks, 'unresolved': [],
            'limitations': '同模型语义判断可能漏错，不是外部读者验收。',
            'read_sha256': packet['work_sha256']}


def receipt(mode='synthetic_test'):
    return {'source': mode, 'worker_id': 'reviewer', 'invocation_id': 'review-1',
            'host_thread_id': None, 'context_claim': 'task_only'}


def pass_stage(p, pid, stage, **extra):
    gates.submit(p, pid, stage, artifact(stage, **extra))
    packet = gates.packet(p, pid, stage)
    gates.review(p, pid, stage, report(packet), receipt())


def craft_review(p,text):
    import writing_spec as writing
    return {'spec_sha256':writing.load(p)['sha256'],'candidate_sha256':flow.digest(text.encode('utf-8')),
            'checks':[{'id':r['id'],'verdict':'satisfied','rationale':'合成协议夹具，不代表实际文学验收。',
                       'citations':[{'quote':text}]} for r in writing.targets(p,'V01-C01')]}


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.p = project(Path(self.temp.name))
    def tearDown(self): self.temp.cleanup()
    def start(self, **kwargs):
        if kwargs.get('profile') in ('draft','revise'):
            from tests.test_writing_spec import configured
            configured(self.p,single=True,origin='tool_default' if kwargs.get('mode')=='host_supplied' else 'synthetic_test')
        return gates.start(self.p, specification(**kwargs))['pipeline_id']

    def test_order_actual_artifacts_and_complete(self):
        pid = self.start()
        with self.assertRaises(ValueError): gates.submit(self.p, pid, 'concept', artifact('concept'))
        for stage in ('brief', 'concept', 'delivery'): pass_stage(self.p, pid, stage)
        status = gates.status(self.p, pid)
        self.assertTrue(status['complete'])
        self.assertEqual(status['assurance'], 'synthetic_test_only')
        self.assertFalse(status['author_approved'])
        self.assertTrue((self.p / '.novel_stages' / pid / 'brief/v1/work.md').is_file())

    def test_bad_outputs_and_unmapped_requirements_rejected(self):
        bad = specification(); bad['requirements'][0]['quote'] = '作者没说过'
        with self.assertRaises(ValueError): gates.start(self.p, bad)
        pid = self.start()
        for data in (artifact('brief', work='TODO'), artifact('brief', items=[])):
            with self.assertRaises(ValueError): gates.submit(self.p, pid, 'brief', data)
        bad = artifact('brief'); bad['items'][0]['quote'] = '不存在的内容'
        with self.assertRaises(ValueError): gates.submit(self.p, pid, 'brief', bad)

    def test_review_missing_wrong_quotes_unknown_self_and_synthetic(self):
        pid = self.start(mode='host_supplied')
        gates.submit(self.p, pid, 'brief', artifact('brief'))
        packet = gates.packet(self.p, pid, 'brief')
        bad = report(packet); bad['checks'].pop()
        with self.assertRaises(ValueError): gates.review(self.p, pid, 'brief', bad, receipt('host_supplied'))
        bad = report(packet); bad['checks'][0]['citations'] = [{'quote': '捏造引文'}]
        with self.assertRaises(ValueError): gates.review(self.p, pid, 'brief', bad, receipt('host_supplied'))
        with self.assertRaises(ValueError): gates.review(self.p, pid, 'brief', report(packet), receipt())
        badreceipt = receipt('host_supplied'); badreceipt['worker_id'] = 'writer'
        with self.assertRaises(ValueError): gates.review(self.p, pid, 'brief', report(packet), badreceipt)
        gates.review(self.p, pid, 'brief', report(packet, 'unknown'), receipt('host_supplied'))
        self.assertFalse(gates.status(self.p, pid)['stages'][0]['ready'])
        with self.assertRaises(ValueError): gates.submit(self.p, pid, 'concept', artifact('concept'))

    def test_revision_stales_downstream_preserves_prior_evidence(self):
        pid = self.start()
        pass_stage(self.p, pid, 'brief'); pass_stage(self.p, pid, 'concept')
        gates.submit(self.p, pid, 'brief', artifact('brief', work=artifact('brief')['work'] + '范围重新核对。'))
        status = gates.status(self.p, pid)
        self.assertEqual(status['stages'][1]['state'], 'stale')
        self.assertTrue((self.p / '.novel_stages' / pid / 'brief/v1/review-1.json').exists())

    def test_context_change_and_work_tamper_fail_closed(self):
        pid = self.start(); pass_stage(self.p, pid, 'brief')
        (self.p / 'style.md').write_text('新的约束', encoding='utf-8')
        self.assertFalse(gates.status(self.p, pid)['stages'][0]['ready'])
        with self.assertRaises(ValueError): gates.submit(self.p, pid, 'concept', artifact('concept'))

    def test_work_tamper_and_unresolved_blocks(self):
        pid = self.start(); gates.submit(self.p, pid, 'brief', artifact('brief'))
        packet = gates.packet(self.p, pid, 'brief'); data = report(packet); data['unresolved'] = ['原话范围仍有疑问']
        gates.review(self.p, pid, 'brief', data, receipt())
        self.assertFalse(gates.status(self.p, pid)['stages'][0]['ready'])
        path = self.p / '.novel_stages' / pid / 'brief/v1/work.md'
        path.write_text(path.read_text(encoding='utf-8') + '暗改', encoding='utf-8')
        self.assertEqual(gates.status(self.p, pid)['stages'][0]['state'], 'stale')

    def draft_to_candidate(self, mode='synthetic_test'):
        import ensemble_runtime as e
        pid = self.start(profile='draft', scope=['V01-C01'], mode=mode)
        for stage in ('brief', 'scene_plan'):
            gates.submit(self.p, pid, stage, artifact(stage)); packet = gates.packet(self.p, pid, stage)
            gates.review(self.p, pid, stage, report(packet), receipt(mode))
        config, scene = scene_data()
        sid = e.start(self.p, config, scene)['ensemble_id']
        while e.status(self.p, sid)['stage'] != 'complete':
            e.respond(self.p, sid, response(e.packet(self.p, sid)), source=mode)
        candidate = e._load(self.p, sid)[1]['candidate']
        # Sources containing the word synthetic_test are data, not provenance.
        work = artifact('rehearsal')['work'] + '\n' + candidate
        gates.submit(self.p, pid, 'rehearsal', artifact('rehearsal', work=work, sources=[{'kind': 'ensemble', 'ensemble_id': sid}]))
        packet = gates.packet(self.p, pid, 'rehearsal'); gates.review(self.p, pid, 'rehearsal', report(packet), receipt(mode))
        run = flow.start(self.p, 'V01-C01')['run_id']
        draft = self.p / 'draft.md'; draft.write_text(candidate, encoding='utf-8'); flow.submit(self.p, run, draft)
        gates.submit(self.p, pid, 'draft', artifact('draft', work=artifact('draft')['work'] + '\n' + candidate, sources=[{'kind': 'candidate', 'run_id': run}]))
        packet = gates.packet(self.p, pid, 'draft'); gates.review(self.p, pid, 'draft', report(packet), receipt(mode))
        return pid, run, candidate

    def test_complete_draft_current_versions_synthetic_cannot_approve(self):
        pid, run, candidate = self.draft_to_candidate()
        data = {'reviewer_type': 'agent', 'issues': [], 'scores': {dim: {'score': 3, 'evidence': candidate,
                'citations': [{'quote': candidate}]} for dim in flow.SCORE_DIMENSIONS}}
        data['writing_spec_review']=craft_review(self.p,candidate)
        data['prose_risks_review']=clear_report(self.p,candidate)
        path = self.p / 'review.json'; put(path, data); flow.review(self.p, run, path)
        root, m = flow._manifest(self.p, run)
        work = artifact('editorial')['work'] + '\n' + (root / m['latest_review']).read_text(encoding='utf-8')
        pass_stage(self.p, pid, 'editorial', work=work, sources=[{'kind': 'run_review', 'run_id': run}])
        pass_stage(self.p, pid, 'delivery')
        self.assertTrue(gates.status(self.p, pid)['complete'])
        with self.assertRaises(ValueError): flow.approve(self.p, run, 'synthetic_test')
        draft = self.p / 'new.md'; draft.write_text(candidate + '她收好湿伞。', encoding='utf-8'); flow.submit(self.p, run, draft)
        self.assertEqual(gates.status(self.p, pid)['stages'][3]['state'], 'stale')
        with self.assertRaises(ValueError): flow.review(self.p, run, path)

    def test_six_dimensions_actual_full_text_and_provenance(self):
        pid, run, candidate = self.draft_to_candidate(mode='host_supplied')
        path = self.p / 'review.json'; put(path, {'reviewer_type': 'agent', 'issues': [], 'summary_citations': [{'quote': candidate}], 'writing_spec_review':craft_review(self.p,candidate), 'prose_risks_review':clear_report(self.p,candidate)})
        flow.review(self.p, run, path)
        with self.assertRaises(ValueError): gates.submit(self.p, pid, 'editorial', artifact('editorial', sources=[{'kind': 'run_review', 'run_id': run}]))
        with self.assertRaises(ValueError): gates.submit(self.p, pid, 'draft', artifact('draft', sources=[{'kind': 'candidate', 'run_id': run}]))

    def test_known_synthetic_response_cannot_enter_managed_real_execution(self):
        import ensemble_runtime as e
        import chapter_tools as chapter
        pid = self.start(profile='draft', scope=['V01-C01'], mode='host_supplied')
        for stage in ('brief', 'scene_plan'):
            gates.submit(self.p, pid, stage, artifact(stage)); packet = gates.packet(self.p, pid, stage)
            gates.review(self.p, pid, stage, report(packet), receipt('host_supplied'))
        config, scene = scene_data(); sid = e.start(self.p, config, scene)['ensemble_id']
        with self.assertRaises(ValueError): e.respond(self.p, sid, response(e.packet(self.p, sid)), source='synthetic_test')
        self.assertEqual(e.status(self.p, sid)['accepted_responses'], 0)
        # Assembly source is checked before accepting a candidate, even when its
        # selected scene payload would otherwise satisfy the ordinary schema.
        with self.assertRaises(ValueError): gates.assert_response_source(self.p, 'V01-C01', 'synthetic_test')

    def test_revision_binds_formal_baseline_and_allows_initial_review(self):
        original = '她把湿伞留在门边，逐行核对登记簿。最后一行字迹被水洇开，她没有替空白补上答案。'
        manuscript = self.p / 'manuscript/V01-C01.md'; manuscript.parent.mkdir(exist_ok=True); manuscript.write_text(original, encoding='utf-8')
        pid = self.start(profile='revise', scope=['V01-C01'])
        pass_stage(self.p, pid, 'brief')
        with self.assertRaises(ValueError): pass_stage(self.p, pid, 'diagnosis')
        pass_stage(self.p, pid, 'diagnosis', work=artifact('diagnosis')['work'] + '\n' + original,
                   sources=[{'kind': 'baseline', 'path': 'manuscript/V01-C01.md'}])
        run = flow.start(self.p, 'V01-C01')['run_id']; flow.submit(self.p, run, manuscript)
        bad = self.p / 'bad.md'; bad.write_text(original + '另行改写', encoding='utf-8')
        with self.assertRaises(ValueError): flow.submit(self.p, run, bad)
        review = self.p / 'review.json'; put(review, {'reviewer_type': 'agent', 'issues': [], 'summary_citations': [{'quote': original}]})
        flow.review(self.p, run, review)
        self.assertEqual(flow._manifest(self.p, run)[1]['status'], 'reviewed')
        with self.assertRaises(ValueError): gates.submit(self.p, pid, 'revision', artifact('revision', work=artifact('revision')['work'] + '\n' + original, sources=[{'kind': 'candidate', 'run_id': run}]))
        manuscript.write_text(original + '新的正式设定。', encoding='utf-8')
        self.assertFalse(gates.status(self.p, pid)['stages'][1]['ready'])

    def test_review_replay_budget_and_placeholder(self):
        pid = self.start(); gates.submit(self.p, pid, 'brief', artifact('brief'))
        old = gates.packet(self.p, pid, 'brief')
        for _ in range(3): gates.review(self.p, pid, 'brief', report(old, 'revise'), receipt())
        with self.assertRaises(ValueError): gates.review(self.p, pid, 'brief', report(old), receipt())
        gates.submit(self.p, pid, 'brief', artifact('brief'))
        with self.assertRaises(ValueError): gates.review(self.p, pid, 'brief', report(old), receipt())
        for _ in range(1): gates.submit(self.p, pid, 'brief', artifact('brief'))
        with self.assertRaises(ValueError): gates.submit(self.p, pid, 'brief', artifact('brief'))

    def test_legacy_works_managed_scope_cannot_bypass(self):
        old = flow.start(self.p, 'V01-C02'); self.assertEqual(old['state'], 'planned')
        pid = self.start(profile='draft', scope=['V01-C01'])
        with self.assertRaises(ValueError): flow.start(self.p, 'V01-C01')
        pass_stage(self.p, pid, 'brief'); pass_stage(self.p, pid, 'scene_plan')
        run = flow.start(self.p, 'V01-C01')['run_id']
        draft = self.p / 'draft.md'; draft.write_text('雨棚下的两个人逐项核对登记，把仍不确定的名字留在纸上，并约好明早向柜台询问。', encoding='utf-8')
        with self.assertRaises(ValueError): flow.submit(self.p, run, draft)
        with self.assertRaises(ValueError): gates.start(self.p, specification(profile='draft', scope=['V01-C01']))

    def test_scope_known_paths_and_catalog_tamper(self):
        with self.assertRaises(ValueError): self.start(profile='draft', scope=['V99-C99'])
        bad = specification(); bad['context_files'] = ['../project.json']
        with self.assertRaises(ValueError): gates.start(self.p, bad)
        pid = self.start()
        info = self.p / '.novel_stages' / pid / 'contract.json'
        raw = info.read_text(encoding='utf-8'); info.write_text(raw + ' ', encoding='utf-8')
        with self.assertRaises(ValueError): gates.status(self.p, pid)

    def test_bound_checkpoint_cannot_claim_completion(self):
        import studio
        base = Path(self.temp.name) / 'another'; workspace(base)
        task = studio.intake(base, '只讨论雨棚重逢，不写正文。', 'explore')
        with self.assertRaises(ValueError): studio.checkpoint(base, task['id'], {'status': 'completed', 'stage': 'done', 'next_action': '交付'})
        bound = studio.stage_start(base, task['id'], specification())
        with self.assertRaises(ValueError):
            studio.checkpoint(base, task['id'], {'status': 'completed', 'stage': 'done', 'next_action': '交付'})
        resumed = studio.resume(base, task['id'])
        self.assertEqual(resumed['pipeline']['pipeline_id'], bound['pipeline_id'])

    def test_checkpoint_stage_versions_cannot_display_old_completed(self):
        import studio
        base = Path(self.temp.name) / 'another'; p = workspace(base)
        task = studio.intake(base, '只讨论雨棚重逢，不写正文。', 'explore')
        pid = studio.stage_start(base, task['id'], specification())['pipeline_id']
        for stage in ('brief', 'concept', 'delivery'): pass_stage(p, pid, stage)
        studio.checkpoint(base, task['id'], {'status': 'completed', 'stage': 'done', 'next_action': '已交付'})
        self.assertEqual(studio.resume(base, task['id'])['resume_status'], 'ready')
        gates.submit(p, pid, 'brief', artifact('brief'))
        resumed = studio.resume(base, task['id'])
        self.assertEqual(resumed['status'], 'needs_revalidation')
        self.assertEqual(resumed['recorded_status'], 'completed')
        self.assertEqual(resumed['resume_status'], 'needs_stage_revalidation')


if __name__ == '__main__': unittest.main()
