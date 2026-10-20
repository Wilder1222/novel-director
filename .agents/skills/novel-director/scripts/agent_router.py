"""Static, inspectable routes. Routing returns role contracts; it does not run models."""
from __future__ import annotations
from pathlib import Path
import json


def route(task:str,root:Path|None=None):
    root=root or Path(__file__).resolve().parents[1]
    routes=json.loads((root/'agents'/'routes.json').read_text(encoding='utf8'))
    roles=json.loads((root/'agents'/'roles.json').read_text(encoding='utf8'))
    mapping={r['id']:r for r in roles['roles']}
    if task not in routes:raise ValueError('未知 Agent 任务: '+task)
    obj=routes[task]
    for ref in obj['refs']:
        if not (root/ref).is_file():raise FileNotFoundError(f'任务引用缺失 {ref}')
    return {'task':task,'status':'route_only_external_host_must_execute','roles':[mapping[r] for r in obj['roles']],
            'deliverables':obj['artifacts'],'load_references':obj['refs'],
            'instruction':'Agent 根据本路由读取最少所需参考资料；文件脚本不会自主调用 LLM。'}
