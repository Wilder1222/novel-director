"""Offline stage protocol fixture. Scripted judgments are NOT literary review."""
from pathlib import Path
import argparse
import json
import studio

SAMPLES = {
    'brief': {
        'goal': '只讨论雨棚重逢的冲突选择，交付两个备选，不写正文。',
        'constraints': '不修改正式设定；尚未决定的人物关系均保持候选。',
        'assumptions': '假定双方想核对登记；作者尚未确认，后续可替换。',
        'acceptance': '比较目标、阻碍和选择代价，交付仍待作者选择的备选。'},
    'concept': {
        'alternatives': '备选A：双方争取同一份登记簿；备选B：各有半份记录，需要先交换可核实的信息。',
        'tradeoffs': 'A冲突集中但易让一方只负责阻挠；B给双方行动空间，但必须明确各自缺失的信息。',
        'open_choices': '作者尚未选择A或B；下次只确认冲突和信息边界，不自动扩写。'},
    'delivery': {
        'deliverables': '本轮交付任务简报、两项冲突备选与取舍，全部为候选。',
        'verification': '工程夹具逐项核对作品引文、阶段顺序与版本，不代表真实独立文学审查。',
        'remaining': '人物关系与具体信息分配尚待作者选择；这是探讨交付的开放选项，不是被隐藏的执行缺陷。',
        'next_action': '停止在备选交付；无作者批准、无正式设定修改、无正文发布。'},
}


def run(dest):
    dest = dest.expanduser().absolute()
    studio.author_workspace(dest)
    if dest.exists(): raise FileExistsError('演示需要全新目录，拒绝覆盖')
    studio.initialize(dest, '阶段流程合成演示')
    raw = 'synthetic_test：只讨论雨棚重逢，给两个备选，不写正文。'
    task = studio.intake(dest, raw, 'explore'); tid = task['id']
    studio.stage_start(dest, tid, {'profile': 'explore', 'mode': 'synthetic_test', 'author_input': raw,
        'requirements': [{'id': 'R1', 'text': '只交备选，不写正文', 'quote': '不写正文'}], 'scope': [], 'context_files': []})
    for stage, sections in SAMPLES.items():
        work = '# synthetic_test：脚本固定作品\n\n' + '\n\n'.join(sections.values())
        items = [{'id': name, 'section': name, 'quote': quote, 'meaning': '本阶段实际作品的对应维度。'} for name, quote in sections.items()]
        studio.stage_action(dest, tid, 'submit', stage, spec={'work': work, 'items': items,
            'producer': {'worker_id': 'fixture_producer', 'invocation_id': stage + ':produce'}})
        packet = studio.stage_action(dest, tid, 'packet', stage)
        studio.write_new(dest / f'.studio/{stage}-packet.json', packet)
        quotes = {'item:' + x['id']: x['quote'] for x in items}
        report = {'packet_sha256': packet['packet_sha256'], 'read_sha256': packet['work_sha256'],
            'checks': [{'target': target, 'verdict': 'pass', 'reason': '固定合成协议夹具，只验证引文与状态分支。',
                'citations': [{'quote': quotes.get(target, items[0]['quote'])}]} for target in packet['review_targets']],
            'unresolved': [], 'limitations': '固定脚本判断，不是模型阅读、作者认可或外部验收。'}
        receipt = {'source': 'synthetic_test', 'worker_id': 'fixture_reviewer', 'invocation_id': stage + ':review',
                   'host_thread_id': None, 'context_claim': 'scripted_fixture_only'}
        studio.stage_action(dest, tid, 'review', stage, report=report, receipt=receipt)
    result = studio.stage_action(dest, tid, 'status')
    studio.write_new(dest / '.studio/stage-demo-result.json', result)
    studio.checkpoint(dest, tid, {'status': 'completed', 'stage': 'delivery', 'next_action': '合成协议演示结束，无文学验收或发布。',
                                 'artifacts': ['.studio/stage-demo-result.json']})
    studio.resume(dest, tid)
    return {'result': str(dest / '.studio/stage-demo-result.json'), 'source': 'synthetic_test',
            'model_calls': 0, 'author_approved': False, 'published': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    print(json.dumps(run(parser.parse_args().output), ensure_ascii=False, indent=2))
