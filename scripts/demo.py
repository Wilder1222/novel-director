"""Offline synthetic_test artifacts. Never calls a model, approves, or publishes."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.support import workspace, put, profile, complete, project as make_project
import studio
import chapter_tools as chapter
import creative_workflow as flow
import ensemble_runtime as ensemble


def run(dest):
    dest = dest.expanduser().absolute()
    if dest.exists():
        raise FileExistsError('演示只接受全新目录，拒绝覆盖')
    dest.mkdir(parents=True)
    project = workspace(dest)
    put(project / 'writing_profile.json', profile())
    task = studio.intake(dest, 'synthetic_test：两场组章及跨章证据演示，不是真实小说任务。', 'develop')
    studio.register_role(dest, 'a', 'local_demo_a')
    studio.register_role(dest, 'b', 'local_demo_b')
    first = complete(project, 'one', 10)
    second = complete(project, 'two', 11)
    aid = chapter.assembly_plan(project, 'V01-C01', {'scene_ids': [first, second]})['assembly_id']
    packet = chapter.assembly_packet(project, aid)
    put(dest / '.studio/chapter-packet.json', packet)
    response = {'request_id': packet['request_id'],
                'sections': [{'ensemble_id': x['ensemble_id'], 'text': x['text']} for x in packet['input']['scenes']],
                'transitions': ['一小时后，他们把记录带到楼下，继续核对。']}
    result = chapter.assembly_submit(project, aid, response, source='synthetic_test')
    run_dir, manifest = flow._manifest(project, result['run_id'])
    put(dest / '.studio/review.json', {'reviewer_type': 'agent', 'issues': [], 'summary_citations': [{'quote': '一小时后，他们把记录带到楼下，继续核对。'}], 'source': 'synthetic_test'})
    flow.review(project, result['run_id'], dest / '.studio/review.json')
    (dest / '.studio/chapter-candidate.md').write_bytes((run_dir / manifest['current_candidate']).read_bytes())
    # Separate fixture: manuscript files are explicit synthetic input, not published by the tool.
    arc_project = make_project(dest / 'arc-fixture')
    ids = [f'V01-C{i:02}' for i in range(1, 4)]
    for cid in ids:
        path = arc_project / f'manuscript/{cid}.md'; path.parent.mkdir(exist_ok=True)
        path.write_text(f'{cid}（synthetic_test）\n她逐行核对记录。缺失的条目仍然空着，不能因为需要答案就补写。\n', encoding='utf-8')
    arc = chapter.arc_packet(arc_project, ids)
    put(dest / '.studio/arc-packet.json', arc)
    report = {'request_id': arc['request_id'], 'reviewer_type': 'self_review', 'issues': [],
              'summary_citations': [{'chapter_id': cid, 'quote': cid} for cid in ids]}
    arc_result = chapter.arc_accept(arc_project, arc, report)
    summary = {'source': 'synthetic_test', 'model_calls': 0, 'author_approval': False, 'published': False,
               'scenes': [ensemble.status(project, first), ensemble.status(project, second)],
               'assembly': result, 'arc': arc_result, 'formal_chapter_created': (project / 'manuscript/V01-C01.md').exists(),
               'host_eligible': studio.host_status(dest)['eligible'],
               'notice': 'Only engineering fixtures; not real narrator/actor writing, reader acceptance, or strict host isolation.'}
    put(dest / '.studio/summary.json', summary)
    studio.checkpoint(dest, task['id'], {'status': 'blocked', 'stage': 'legacy_synthetic_demo_complete',
                      'stop_reason': '历史v0.8组件演示未运行v0.9阶段门槛；不得冒充当前任务全部核验通过。',
                      'next_action': '工程演示结束；没有作者作品验收。', 'run_id': result['run_id'],
                      'ensemble_ids': [first, second], 'artifacts': ['.studio/chapter-candidate.md', '.studio/arc-packet.json', '.studio/summary.json']})
    studio.resume(dest)
    return {'summary': str(dest / '.studio/summary.json'), 'candidate': str(dest / '.studio/chapter-candidate.md'), 'source': 'synthetic_test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=False, indent=2))
