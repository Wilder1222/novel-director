from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from tests.support import workspace, project, put, profile, scene_data, response, complete
import chapter_tools as ct
import ensemble_runtime as e
import creative_workflow as flow
import evidence_audit
import story_memory as memory
import studio


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.p = workspace(self.root)

    def test_missing_optional_profile_preserves_legacy_signature(self):
        paths = set(evidence_audit.PROJECT_SOURCES)
        state = {name: flow.digest((self.p / name).read_bytes()) if (self.p / name).exists() else '-' for name in sorted(paths)}
        old = flow.digest(json.dumps(state, sort_keys=True).encode('utf8'))
        self.assertEqual(flow.signature(self.p), old)

    def test_missing_optional_profile_preserves_legacy_packet(self):
        c, sc = scene_data(); sid = e.start(self.p, c, sc)['ensemble_id']; _, state = e._load(self.p, sid)
        self.assertNotIn('writing_profile', state)
        expected = e._build_packet(copy.deepcopy(state))
        self.assertEqual(e.packet(self.p, sid), expected)
        self.assertEqual(state['config'], c)

    def test_memory_import_rejects_same_or_future_step(self):
        sid = complete(self.p); snap = e.export_memory(self.p, sid); c, sc = scene_data(label='next')
        with self.assertRaises(ValueError): e.start(self.p, c, sc, [snap])
        sc['steps'] = {'a_now': 1, 'b_now': 1}
        self.assertEqual(e.start(self.p, c, sc, [snap])['stage'], 'actor')

    def test_same_worker_different_age_has_distinct_memory_key(self):
        c, sc = scene_data(); a = copy.deepcopy(c['instances'][0]); a.update(id='a_older', age=45)
        c['instances'].append(a)
        self.assertNotEqual(e.memory_key(c, 'a_now'), e.memory_key(c, 'a_older'))

    def test_secret_memory_never_in_writer_results(self):
        put(self.p / 'memory_docs.json', {'memories': [
            {'id': 'hidden', 'text': 'SPOILER_HIDDEN', 'visibility': 'author_only', 'history_id': 'global', 'status': 'confirmed'},
            {'id': 'other-pov', 'text': 'SPOILER_OTHER', 'visibility': 'pov_private', 'allowed_povs': ['b'], 'reveal_chapter': 'V01-C01', 'history_id': 'H0', 'status': 'confirmed'},
            {'id': 'future', 'text': 'SPOILER_FUTURE', 'visibility': 'reader', 'reveal_chapter': 'V01-C05', 'history_id': 'H0', 'status': 'confirmed'}]})
        memory.build(self.p)
        hits = memory.search(self.p, 'SPOILER', 'V01-C02', 'H0', 'a')
        self.assertNotIn('SPOILER', json.dumps(hits))

    def test_budget_does_not_silently_drop_style(self):
        v = profile(); v['rules'] = ['规则' * 400] * 20; put(self.p / 'writing_profile.json', v)
        c, sc = scene_data(); c['max_packet_chars'] = 3500
        # Invalid oversized calibration fails before creating a usable run.
        with self.assertRaises(ValueError): e.start(self.p, c, sc)

    def test_completed_assembly_rejects_missing_dialogue(self):
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        aid = ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})['assembly_id']; packet = ct.assembly_packet(self.p, aid)
        reply = {'request_id': packet['request_id'], 'sections': [{'ensemble_id': item['ensemble_id'], 'text': '遗漏对白但长度够用的叙述文字。' * 5} for item in packet['input']['scenes']], 'transitions': ['']}
        with self.assertRaises(ValueError): ct.assembly_submit(self.p, aid, reply)

    def test_assembly_rejects_incomplete_and_wrong_chapter(self):
        a = complete(self.p, 'one', 10); c, sc = scene_data(label='two', hour=11)
        b = e.start(self.p, c, sc)['ensemble_id']
        with self.assertRaises(ValueError): ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})
        with self.assertRaises(ValueError): ct.assembly_plan(self.p, 'V01-C02', {'scene_ids': [a, b]})

    def test_assembly_enforces_registered_scene_list(self):
        put(self.p / 'scenes.json', {'scenes': [
            {'id': 'one', 'chapter_id': 'V01-C01', 'order': 1}, {'id': 'two', 'chapter_id': 'V01-C01', 'order': 2},
            {'id': 'three', 'chapter_id': 'V01-C01', 'order': 3}]})
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        with self.assertRaises(ValueError): ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})

    def arc(self):
        ids = ['V01-C01', 'V01-C02', 'V01-C03']
        for cid in ids:
            path = self.p / f'manuscript/{cid}.md'; path.parent.mkdir(exist_ok=True); path.write_text(cid + '失物已归还。' * 12, encoding='utf-8')
        packet = ct.arc_packet(self.p, ids)
        report = {'request_id': packet['request_id'], 'reviewer_type': 'cross_review', 'issues': [], 'summary_citations': [{'chapter_id': cid, 'quote': cid} for cid in ids]}
        return packet, report

    def test_arc_rejects_out_of_scope_and_old_source(self):
        packet, report = self.arc(); report['summary_citations'][0]['chapter_id'] = 'V01-C05'
        with self.assertRaises(ValueError): ct.arc_accept(self.p, packet, report)
        packet, report = self.arc(); (self.p / 'manuscript/V01-C01.md').write_text('新版本', encoding='utf-8')
        with self.assertRaises(ValueError): ct.arc_accept(self.p, packet, report)

    def test_arc_requires_reading_evidence_for_every_chapter(self):
        packet, report = self.arc(); report['summary_citations'].pop()
        with self.assertRaises(ValueError): ct.arc_accept(self.p, packet, report)

    def test_arc_budget_and_authority(self):
        packet, report = self.arc()
        with self.assertRaises(ValueError): ct.arc_packet(self.p, packet['scope'], 100)
        result = ct.arc_accept(self.p, packet, report)
        self.assertFalse(result['run_states_changed'])
        self.assertFalse((self.p / '.novel_runs').exists())

    def test_probe_expiry_permissions_fingerprint_and_evidence(self):
        path = self.root / '.studio/probe-log.txt'; path.write_text('synthetic_fixture_observation', encoding='utf-8')
        data = {'client': 'fixture', 'version': '1', 'transport': 'fixture', 'tools': [], 'source': 'observed',
                'observed_at': datetime.now(timezone.utc).isoformat(), 'checks': dict.fromkeys(('clean_context', 'tools_disabled', 'instance_partition', 'phase_partition'), True),
                'evidence_paths': ['.studio/probe-log.txt']}
        # The fixture tests declarations only, not a real runtime capability.
        studio.record_probe(self.root, data); self.assertTrue(studio.host_status(self.root)['eligible'])
        data['observed_at'] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        studio.record_probe(self.root, data); self.assertFalse(studio.host_status(self.root)['eligible'])
        data['observed_at'] = datetime.now(timezone.utc).isoformat(); data['tools'] = ['exec_command']
        studio.record_probe(self.root, data); self.assertFalse(studio.host_status(self.root)['eligible'])
        data['tools'] = []; studio.record_probe(self.root, data)
        path.write_text('changed', encoding='utf-8'); self.assertFalse(studio.host_status(self.root)['eligible'])
        studio.record_probe(self.root, data); studio.register_role(self.root, 'a', 'local_a')
        self.assertFalse(studio.host_status(self.root)['eligible'])

    def test_core_role_cannot_be_npc_fallback(self):
        with self.assertRaises(ValueError): studio.select_role({'npc-pool': 'npc_pool'}, {'worker_id': 'core:a'})

    def test_bad_role_filename_and_unknown_character(self):
        with self.assertRaises(ValueError): studio.register_role(self.root, 'unknown', 'local_ghost')
        with self.assertRaises(ValueError): studio.register_role(self.root, 'a', '../escape')

    def test_checkpoint_detects_corrupt_input_and_source(self):
        task = studio.intake(self.root, '继续', 'plan')['id']
        studio.checkpoint(self.root, task, {'status': 'active', 'stage': 'plan', 'next_action': '检查'})
        (self.p / 'style.md').write_text('changed', encoding='utf-8')
        with self.assertRaises(ValueError): studio.resume(self.root)
        (self.root / f'.studio/tasks/{task}/input.md').write_text('伪造', encoding='utf-8')
        with self.assertRaises(ValueError): studio.resume(self.root)

    def test_checkpoint_detects_unlisted_candidate_drift(self):
        run = flow.start(self.p, 'V01-C01')['run_id']
        draft = self.p / 'draft.txt'; draft.write_text('候选原文' * 20, encoding='utf-8')
        flow.submit(self.p, run, draft)
        task = studio.intake(self.root, '继续改稿', 'revise')['id']
        studio.checkpoint(self.root, task, {'status': 'active', 'stage': 'draft', 'next_action': '审稿', 'run_id': run})
        folder, m = flow._manifest(self.p, run); (folder / m['current_candidate']).write_text('原文已变', encoding='utf-8')
        with self.assertRaises(ValueError): studio.resume(self.root)

    def test_unbound_legacy_map_never_adopts_colliding_character_id(self):
        put(self.root / '.studio/agent-map.json', {'narrator': 'narrator', 'npc-pool': 'npc_pool', 'core:a': 'old_book_actor'})
        self.assertNotIn('core:a', studio.role_mapping(self.root))

    def test_explicit_scene_list_cannot_override_registered_list(self):
        put(self.p / 'scenes.json', {'scenes': [{'id': name, 'chapter_id': 'V01-C01', 'order': i} for i, name in enumerate(('one', 'two', 'three'))]})
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        with self.assertRaises(ValueError): ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b], 'expected_scene_ids': ['one', 'two']})

    def test_time_order_uses_parsed_datetime(self):
        a = complete(self.p, 'one', 11); c, sc = scene_data(label='two', hour=10); sc['at'] = '20260101T10:00:00'
        b = e.start(self.p, c, sc)['ensemble_id']
        while e.status(self.p, b)['stage'] != 'complete':
            pkt = e.packet(self.p, b); e.respond(self.p, b, response(pkt, 'two'), 'synthetic_test')
        with self.assertRaises(ValueError): ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})

    def test_assembly_retry_after_final_save_failure_has_one_run(self):
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        aid = ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})['assembly_id']; pkt = ct.assembly_packet(self.p, aid)
        reply = {'request_id': pkt['request_id'], 'sections': [{'ensemble_id': x['ensemble_id'], 'text': x['text']} for x in pkt['input']['scenes']], 'transitions': ['']}
        with patch.object(ct, '_save', side_effect=OSError('injected failure')):
            with self.assertRaises(OSError): ct.assembly_submit(self.p, aid, reply, 'synthetic_test')
        result = ct.assembly_submit(self.p, aid, reply, 'synthetic_test')
        self.assertEqual(result['state'], 'drafted')
        self.assertEqual(len(list((self.p / '.novel_runs').glob('run-*'))), 1)

    def test_assembly_retry_after_run_initialization_failure(self):
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        aid = ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})['assembly_id']; pkt = ct.assembly_packet(self.p, aid)
        reply = {'request_id': pkt['request_id'], 'sections': [{'ensemble_id': x['ensemble_id'], 'text': x['text']} for x in pkt['input']['scenes']], 'transitions': ['']}
        original = flow.atomic_write
        def fail_manifest(path, text, replace=False):
            if path.name == 'manifest.json':
                raise OSError('injected initialization failure')
            return original(path, text, replace)
        with patch.object(flow, 'atomic_write', side_effect=fail_manifest):
            with self.assertRaises(OSError): ct.assembly_submit(self.p, aid, reply, 'synthetic_test')
        self.assertEqual(ct.assembly_submit(self.p, aid, reply, 'synthetic_test')['state'], 'drafted')
        self.assertEqual(len(list((self.p / '.novel_runs').glob('run-*'))), 1)

    def test_arc_generation_and_accept_budget_agree(self):
        packet, report = self.arc()
        with self.assertRaises(ValueError): ct.arc_packet(self.p, packet['scope'], budget=ct.MAX_CHARS + 1)

    def test_studio_assembly_gate_and_synthetic_receipt(self):
        a = complete(self.p, 'one', 10); b = complete(self.p, 'two', 11)
        aid = ct.assembly_plan(self.p, 'V01-C01', {'scene_ids': [a, b]})['assembly_id']
        self.assertEqual(studio.dispatch_assembly(self.root, aid)['execution_status'], 'blocked_host_capabilities')
        pkt = studio.dispatch_assembly(self.root, aid, inspect=True)['packet']
        reply = {'request_id': pkt['request_id'], 'sections': [{'ensemble_id': x['ensemble_id'], 'text': x['text']} for x in pkt['input']['scenes']], 'transitions': ['']}
        put(self.root / '.studio/response.json', reply)
        put(self.root / '.studio/receipt.json', {'request_id': pkt['request_id'], 'worker_id': 'narrator', 'host_thread_id': 'synthetic_test_not_a_real_thread'})
        with self.assertRaises(ValueError): studio.accept_assembly(self.root, aid, '.studio/response.json', '.studio/receipt.json')
        result = studio.accept_assembly(self.root, aid, '.studio/response.json', '.studio/receipt.json', source='synthetic_test')
        self.assertEqual(result['engine_result']['state'], 'drafted')
        self.assertEqual(json.loads((self.root / result['receipt']).read_text(encoding='utf-8'))['source'], 'synthetic_test')

    def test_checkpoint_review_drift_is_rejected(self):
        run = flow.start(self.p, 'V01-C01')['run_id']
        draft = self.p / 'draft.txt'; draft.write_text('候选原文' * 20, encoding='utf-8'); flow.submit(self.p, run, draft)
        put(self.p / 'review.json', {'reviewer_type': 'agent', 'issues': [], 'summary_citations': [{'quote': '候选原文', 'start': 0, 'end': 4}]})
        flow.review(self.p, run, self.p / 'review.json')
        task = studio.intake(self.root, '继续改稿', 'revise')['id']
        studio.checkpoint(self.root, task, {'status': 'active', 'stage': 'review', 'next_action': '复核', 'run_id': run})
        folder, manifest = flow._manifest(self.p, run); (folder / manifest['latest_review']).write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError): studio.resume(self.root)

    def test_legacy_adoption_is_explicit_and_book_bound(self):
        (self.root / '.codex/agents/old_actor.toml').write_text('name = "old_actor"\n', encoding='utf-8')
        put(self.root / '.studio/agent-map.json', {'narrator': 'narrator', 'npc-pool': 'npc_pool', 'core:a': 'old_actor'})
        studio.adopt_legacy_roles(self.root)
        self.assertEqual(studio.role_mapping(self.root)['core:a'], 'old_actor')
        other = project(self.root / 'other')
        put(self.root / '.studio/workspace.json', {'active_project': other.relative_to(self.root).as_posix()})
        self.assertNotIn('core:a', studio.role_mapping(self.root))
