from pathlib import Path
import copy
import json
import tempfile
import unittest
from tests.support import ROOT, workspace, put, complete, scene_data, response, profile
import studio
import ensemble_runtime as e


class Extensions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.p = workspace(self.root)

    def test_checkpoint_resume_and_artifact_drift(self):
        task = studio.intake(self.root, '继续核查', 'plan')['id']
        artifact = self.root / '.studio/note.md'; artifact.write_text('原记录', encoding='utf-8')
        studio.checkpoint(self.root, task, {'status': 'active', 'stage': 'planning', 'next_action': '检查章卡', 'artifacts': ['.studio/note.md']})
        self.assertEqual(studio.resume(self.root)['id'], task)
        artifact.write_text('已改变', encoding='utf-8')
        with self.assertRaises(ValueError): studio.resume(self.root)

    def test_resume_rejects_project_switch(self):
        task = studio.intake(self.root, '继续核查', 'plan')['id']
        studio.checkpoint(self.root, task, {'status': 'active', 'stage': 'planning', 'next_action': '检查'})
        put(self.root / '.studio/workspace.json', {'active_project': 'books/other', 'active_task': task})
        with self.assertRaises((ValueError, OSError)): studio.resume(self.root)

    def test_resume_rejects_stale_request(self):
        c, sc = scene_data(); sid = e.start(self.p, c, sc)['ensemble_id']
        task = studio.intake(self.root, '写场景', 'draft')['id']
        studio.checkpoint(self.root, task, {'status': 'active', 'stage': 'actor', 'next_action': '委派', 'ensemble_ids': [sid]})
        packet = e.packet(self.p, sid); e.respond(self.p, sid, response(packet), 'synthetic_test')
        with self.assertRaises(ValueError): studio.resume(self.root)

    def test_checkpoint_rejects_path_traversal(self):
        task = studio.intake(self.root, '写场景', 'draft')['id']
        with self.assertRaises(ValueError): studio.checkpoint(self.root, task, {'status': 'active', 'stage': 'plan', 'next_action': '检查', 'artifacts': ['../outside']})

    def test_role_registration_is_project_bound_and_dedicated(self):
        studio.register_role(self.root, 'a', 'local_a')
        with self.assertRaises(ValueError): studio.register_role(self.root, 'b', 'local_a')
        with self.assertRaises((ValueError, FileExistsError)): studio.register_role(self.root, 'a', 'local_a')
        self.assertEqual(studio.role_mapping(self.root)['core:a'], 'local_a')
        self.assertNotIn('core:chen-xu', studio.role_mapping(self.root))

    def test_synthetic_probe_cannot_authorize_dispatch(self):
        ev = self.root / '.studio/probe.txt'; ev.write_text('synthetic_test', encoding='utf-8')
        data = {'client': 'test', 'version': '1', 'transport': 'fake', 'tools': [], 'source': 'synthetic_test',
                'observed_at': '2026-10-21T00:00:00+00:00', 'checks': {'clean_context': True, 'tools_disabled': True, 'instance_partition': True, 'phase_partition': True}, 'evidence_paths': ['.studio/probe.txt']}
        studio.record_probe(self.root, data)
        self.assertFalse(studio.host_status(self.root)['eligible'])

    def test_unverified_packet_is_inspection_only(self):
        studio.register_role(self.root, 'a', 'local_a')
        c, sc = scene_data(); sid = e.start(self.p, c, sc)['ensemble_id']
        result = studio.dispatch(self.root, sid)
        self.assertEqual(result['execution_status'], 'blocked_host_capabilities')
        self.assertNotIn('packet', result)

    def test_receipt_wrong_worker_rejected(self):
        c, sc = scene_data(); sid = e.start(self.p, c, sc)['ensemble_id']; p = e.packet(self.p, sid)
        with self.assertRaises(ValueError): studio.check_receipt(p, response(p), {'request_id': p['request_id'], 'worker_id': 'npc-pool', 'host_thread_id': 'synthetic_test'})

    def test_style_only_compose_and_config_unchanged(self):
        import writing_profile as wp
        put(self.p / 'writing_profile.json', profile())
        c, sc = scene_data(); original = copy.deepcopy(c); sid = e.start(self.p, c, sc)['ensemble_id']
        while e.status(self.p, sid)['stage'] != 'compose':
            p = e.packet(self.p, sid); self.assertNotIn('writing_profile', p['input'])
            e.respond(self.p, sid, response(p), 'synthetic_test')
        self.assertEqual(c, original)
        self.assertEqual(e.packet(self.p, sid)['input']['writing_profile']['rules'], profile()['rules'])
        self.assertNotIn('confirmation', e.packet(self.p, sid)['input']['writing_profile'])

    def test_candidate_profile_not_projected(self):
        import writing_profile as wp
        value = profile(); value['status'] = 'candidate'; put(self.p / 'writing_profile.json', value)
        self.assertIsNone(wp.projection(self.p))

    def test_profile_private_unknown_and_unsupported_mode_rejected(self):
        import writing_profile as wp
        for field, val in [('reader_safe', False), ('secret', '未来谜底'), ('narration', 'omniscient')]:
            with self.subTest(field=field):
                data = profile(); data[field] = val; put(self.p / 'writing_profile.json', data)
                with self.assertRaises(ValueError): wp.projection(self.p)

    def test_multiscene_one_candidate_and_replay(self):
        import chapter_tools as ct
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        asm = ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})['assembly_id']
        p = ct.assembly_packet(self.p, asm)
        self.assertNotIn('DIRECTOR_SECRET', json.dumps(p))
        reply = {'request_id': p['request_id'], 'sections': [{'ensemble_id': x['ensemble_id'], 'text': x['text']} for x in p['input']['scenes']], 'transitions': ['一小时后，他们走到楼下。']}
        result = ct.assembly_submit(self.p, asm, reply, source='synthetic_test')
        self.assertEqual(result['state'], 'drafted')
        self.assertFalse((self.p / 'manuscript/V01-C01.md').exists())
        with self.assertRaises(ValueError): ct.assembly_submit(self.p, asm, reply)

    def test_assembly_duplicate_or_reverse_order_rejected(self):
        import chapter_tools as ct
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        for ids in ([a, a], [b, a]):
            with self.subTest(ids=ids), self.assertRaises(ValueError): ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': ids})

    def test_assembly_omissions_and_source_drift_rejected(self):
        import chapter_tools as ct
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        asm = ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})['assembly_id']; p = ct.assembly_packet(self.p, asm)
        bad = {'request_id': p['request_id'], 'sections': [{'ensemble_id': a, 'text': '漏场和对白' * 10}], 'transitions': ['']}
        with self.assertRaises(ValueError): ct.assembly_submit(self.p, asm, bad)
        (self.p / 'style.md').write_text('已更改', encoding='utf-8')
        with self.assertRaises(ValueError): ct.assembly_packet(self.p, asm)

    def test_arc_bound_quotes_and_range(self):
        import chapter_tools as ct
        ids = ['V01-C01', 'V01-C02', 'V01-C03']
        for cid in ids: (self.p / 'manuscript').mkdir(exist_ok=True); (self.p / f'manuscript/{cid}.md').write_text(cid + '她把信折好，放回桌上。' * 4, encoding='utf-8')
        packet = ct.arc_packet(self.p, ids)
        report = {'request_id': packet['request_id'], 'reviewer_type': 'self_review', 'issues': [], 'summary_citations': [{'chapter_id': cid, 'quote': cid} for cid in ids]}
        self.assertTrue(ct.arc_accept(self.p, packet, report)['citations_verified'])
        bad = copy.deepcopy(report); bad['summary_citations'][0]['quote'] = '不存在'
        with self.assertRaises(ValueError): ct.arc_accept(self.p, packet, bad)
        with self.assertRaises(ValueError): ct.arc_packet(self.p, ['V01-C01', 'V01-C03', 'V01-C04'])
