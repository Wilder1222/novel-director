from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.agents/skills/novel-director'
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(SKILL / 'scripts'))


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def project(base):
    dest = base / 'books/test-book'
    shutil.copytree(SKILL / 'assets/project-template', dest)
    # Existing tests deliberately represent an unconfigured legacy project.
    (dest / 'writing_spec.json').unlink(missing_ok=True)
    put(dest / 'characters.json', {'characters': [
        {'id': k, 'name': name, 'birth_date': '1990-01-01', 'role': 'core',
         'voice': '先问再答', 'motive': '送回失物'} for k, name in [('a', '阿岚'), ('b', '柏宁')]]})
    put(dest / 'chapters.json', {'chapters': [
        {'id': f'V01-C{i:02}', 'volume': 1, 'number': i, 'pov': 'a', 'history_id': 'H0',
         'in_world_at': f'2026-01-{i:02}T10:00:00', 'goal': '核实失物', 'conflict': '记录不全',
         'change': '决定实地核对', 'summary': f'第{i}章已发生的公开行动。'} for i in range(1, 6)]})
    p = json.loads((dest / 'project.json').read_text(encoding='utf-8'))
    p.update(age_anchor_date='2026-01-01', expected_ages={}, time_rules={})
    put(dest / 'project.json', p)
    return dest


def workspace(base):
    p = project(base)
    shutil.copytree(ROOT / 'templates/studio', base / '.studio')
    shutil.copytree(ROOT / '.codex', base / '.codex', ignore=shutil.ignore_patterns('local_*'))
    put(base / '.studio/workspace.json', {'active_project': 'books/test-book', 'auto_publish': False})
    return p


def scene_data(chapter='V01-C01', label='one', hour=10):
    config = {'schema_version': '0.7', 'core_ids': ['a', 'b'], 'profiles': {}, 'instances': [], 'max_packet_chars': 24000}
    for cid in ('a', 'b'):
        config['profiles'][cid] = {'name': cid, 'voice': '简洁', 'values': '守约', 'abilities': '常识', 'limits': '无特权'}
        config['instances'].append({'id': cid + '_now', 'character_id': cid, 'history_id': 'H0',
            'from_at': '2026-01-01T00:00:00', 'to_at': '2026-01-06T23:00:00', 'age': 36,
            'goal': '确认归还方式', 'private_fear': cid + '_PRIVATE', 'relationship_view': '谨慎',
            'knowledge': [
                {'id': cid + '_public', 'text': '失物在柜台', 'kind': 'fact', 'source': 'synthetic_test', 'known_from_step': 0, 'can_disclose': True},
                {'id': cid + '_secret', 'text': cid + '_SECRET', 'kind': 'belief', 'source': 'synthetic_test', 'known_from_step': 0, 'can_disclose': False},
                {'id': cid + '_future', 'text': cid + '_FUTURE', 'kind': 'fact', 'source': 'synthetic_test', 'known_from_step': 9, 'can_disclose': True}]})
    scene = {'id': label, 'chapter_id': chapter, 'history_id': 'H0', 'at': f'2026-01-01T{hour:02}:00:00',
        'cast': ['a_now', 'b_now'], 'pov_instance': 'a_now', 'steps': {'a_now': 0, 'b_now': 0},
        'turn_order': ['a_now', 'b_now'], 'location': '雨棚', 'public_brief': '失物待领',
        'director_goal': 'DIRECTOR_SECRET', 'reader_brief': '第三人称限知，日常场景。'}
    return config, scene


def response(packet, label='one'):
    rid = packet['request_id']
    if packet['role'] == 'actor':
        aid = packet['input']['instance_id']
        return {'request_id': rid, 'actor_id': aid, 'speech': f'{label}-{aid}：先看登记。',
            'action_intent': '把登记簿推到柜边', 'private_intent': aid + '_INTENT',
            'used_fact_ids': [], 'disclosed_fact_ids': []}
    if packet['role'] == 'resolve':
        return {'request_id': rid, 'accept': True, 'reason': '可观察', 'result': '登记簿停在柜边。',
            'observers': ['a_now', 'b_now'], 'reader_visible': True, 'end_scene': False}
    words = [x['speech'] for x in packet['input']['events'] if x.get('speech')]
    return {'request_id': rid, 'text': '雨停在屋檐外，阿岚把湿伞留在门边，翻开了登记簿。' + ''.join('“' + s + '”' for s in words) + '两个人对照记录，没有急着下结论。'}


def complete(p, label='one', hour=10):
    import ensemble_runtime as e
    config, scene = scene_data(label=label, hour=hour)
    sid = e.start(p, config, scene)['ensemble_id']
    while e.status(p, sid)['stage'] != 'complete':
        packet = e.packet(p, sid)
        e.respond(p, sid, response(packet, label), source='synthetic_test')
    return sid


def profile():
    return {'schema_version': '1', 'status': 'confirmed', 'reader_safe': True,
        'confirmation': '测试夹具：作者明确确认以下文风范围，不代表真实作者批准。',
        'narration': 'third_person_limited', 'genres': ['realism'],
        'rules': ['观察先于解释，保留人物沉默。'],
        'examples': [{'prefer': '她把信重新折好。', 'avoid': '她感到一种无法言说的情绪。', 'reason': '以动作承载情绪。'}]}
