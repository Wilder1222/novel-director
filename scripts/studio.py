#!/usr/bin/env python3
"""Codex workspace helpers. No network, model calls, automatic approval or publication."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
INTENTS = ('explore', 'plan', 'draft', 'revise', 'develop')


def child(root: Path, relative: str) -> Path:
    """Resolve workspace paths without following any symlink component."""
    rel = Path(relative)
    if not relative or rel.is_absolute() or '..' in rel.parts:
        raise ValueError('只接受不含 .. 的工作区相对路径')
    root = root.resolve()
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('拒绝符号链接路径')
    current.resolve().relative_to(root)
    return current


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'{path.name} 必须是 JSON 对象')
    return value


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def project_path(root: Path) -> Path:
    workspace = read_object(child(root, '.studio/workspace.json'))
    project = child(root, workspace['active_project'])
    if not (project / 'project.json').is_file():
        raise ValueError('active_project 必须指向已有小说项目；不自动重建')
    return project


def intake(root: Path, text: str, intent: str) -> dict[str, Any]:
    if intent not in INTENTS:
        raise ValueError('无效任务模式')
    if not text.strip() or '\x00' in text:
        raise ValueError('想法不能为空或包含 NUL')
    if len(text.encode('utf-8')) > 1024 * 1024:
        raise ValueError('想法超过1MiB；请作为资料单独存入项目')
    project = project_path(root)
    task_id = 'task-' + uuid4().hex[:16]
    folder = child(root, '.studio/tasks/' + task_id)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'input.md').write_bytes(text.encode('utf-8'))
    info = {
        'id': task_id, 'intent': intent, 'project': str(project.relative_to(root.resolve())),
        'received_at': datetime.now(timezone.utc).isoformat(),
        'input_sha256': sha(text.encode('utf-8')), 'status': 'received',
        'canon_effect': 'none', 'next': 'Codex reads input and writes scoped brief.md',
    }
    write_new(folder / 'task.json', info)
    (folder / 'brief.md').write_text(
        '# 创作任务\n\n状态：待 Codex 根据作者原话填写，不是正式设定。\n\n'
        '## 本轮目标\n\n## 已确认约束\n\n## 工作假设\n\n## 交付物与非目标\n\n'
        '## 依赖和完成标准\n\n## 角色分工\n\n## 批准边界\n', encoding='utf-8')
    return {**info, 'folder': str(folder.relative_to(root.resolve()))}


def select_role(mapping: dict[str, Any], packet: dict[str, Any]) -> str:
    worker = packet['worker_id']
    name = mapping.get(worker)
    if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', name):
        raise ValueError(f'未注册 worker {worker}；不能把核心角色降级为 npc_pool')
    return name


def check_receipt(packet: dict[str, Any], response: dict[str, Any], receipt: dict[str, Any]) -> None:
    if response.get('request_id') != packet['request_id']:
        raise ValueError('响应不属于当前请求')
    for key in ('request_id', 'worker_id'):
        if receipt.get(key) != packet[key]:
            raise ValueError(f'回执 {key} 不匹配')
    tid = receipt.get('host_thread_id')
    if not isinstance(tid, str) or not tid.strip() or len(tid) > 256 or '\x00' in tid:
        raise ValueError('必须填写实际宿主线程 ID；本检查不能证明其真实性')
    if tid.strip() in ('TODO', 'TBD', 'placeholder', '原生工具返回的真实值'):
        raise ValueError('不能使用占位符作为真实线程 ID')


def engine(root: Path):
    scripts = child(root, '.agents/skills/novel-director/scripts')
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import ensemble_runtime
    return ensemble_runtime


def dispatch(root: Path, ensemble_id: str) -> dict[str, Any]:
    packet = engine(root).packet(project_path(root), ensemble_id)
    name = select_role(read_object(child(root, '.studio/agent-map.json')), packet)
    profile = child(root, f'.codex/agents/{name}.toml')
    if not profile.is_file():
        raise ValueError('角色定义缺失')
    return {
        'custom_agent_name': name, 'profile': str(profile.relative_to(root.resolve())),
        'execution_status': 'awaiting_real_codex_delegation',
        'instruction': '主会话使用真实子代理工具，只发送 packet；先验证干净上下文与工具边界。',
        'security_claim': '配置及提示约束不是硬隔离；本命令没有启动任何 Agent。',
        'packet': packet,
    }


def accept(root: Path, ensemble_id: str, response_path: str, receipt_path: str, *, source: str = 'host_supplied') -> dict[str, Any]:
    if source not in ('host_supplied', 'synthetic_test'):
        raise ValueError('无效来源')
    runtime = engine(root)
    project = project_path(root)
    packet = runtime.packet(project, ensemble_id)
    response = read_object(child(root, response_path))
    receipt = read_object(child(root, receipt_path))
    check_receipt(packet, response, receipt)
    request_id = packet['request_id']
    if not re.fullmatch(r'[a-f0-9]{64}', request_id):
        raise ValueError('引擎请求 ID 格式不符')
    record = {
        'request_id': request_id, 'ensemble_id': ensemble_id, 'receipt': receipt,
        'response_sha256': sha(child(root, response_path).read_bytes()),
        'provenance': 'host_reported_not_attested', 'source': source, 'status': 'pending_engine_validation',
    }
    path = child(root, f'.studio/receipts/{request_id}/{uuid4().hex}.json')
    # Keep each attempt. Engine request binding and locking reject stale replay;
    # a failed attempt must not block a corrected response or erase prior evidence.
    write_new(path, record)
    try:
        result = runtime.respond(project, ensemble_id, response, source=source)
    except Exception as exc:
        write_new(path.with_suffix('.rejected.json'), {'error': str(exc), 'type': type(exc).__name__})
        raise
    write_new(path.with_suffix('.accepted.json'), {'result': result, 'status': 'accepted'})
    return {'engine_result': result, 'receipt': str(path.relative_to(root.resolve())),
            'provenance': 'host_reported_not_attested'}


def doctor(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    roles: list[str] = []
    try:
        project_path(root)
        config = tomllib.loads(child(root, '.codex/config.toml').read_text(encoding='utf-8'))
        if config.get('agents', {}).get('enabled') is not True:
            errors.append('配置未开启 agents')
        for path in sorted(child(root, '.codex/agents').glob('*.toml')):
            if path.is_symlink():
                raise ValueError('角色文件不得为符号链接')
            role = tomllib.loads(path.read_text(encoding='utf-8'))
            for field in ('name', 'description', 'developer_instructions'):
                if not isinstance(role.get(field), str) or not role[field].strip():
                    errors.append(f'{path.name}: 缺少 {field}')
            if role.get('sandbox_mode') != 'read-only':
                errors.append(f'{path.name}: 非预期默认权限')
            roles.append(role.get('name', ''))
        if len(roles) != len(set(roles)):
            errors.append('自定义角色重名')
        for role in read_object(child(root, '.studio/agent-map.json')).values():
            if role not in roles:
                errors.append(f'角色映射无定义: {role}')
        for name in ('novel-studio', 'novel-director'):
            skill = child(root, f'.agents/skills/{name}/SKILL.md').read_text(encoding='utf-8')
            if not skill.startswith('---\n') or f'name: {name}\n' not in skill:
                errors.append(f'Skill 元数据不匹配: {name}')
        provenance = read_object(child(root, 'ENGINE-PROVENANCE.json'))
        for relative, digest in provenance['files'].items():
            path = child(root, '.agents/skills/novel-director/' + relative)
            if not path.is_file() or sha(path.read_bytes()) != digest:
                errors.append(f'引擎文件已改变: {relative}')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return {'local_files_ok': not errors, 'errors': errors, 'custom_roles': roles,
            'runtime_status': 'not_verified_by_this_command', 'native_agent_calls': 0,
            'next': '在实际 Codex 会话验证 Skill/Agent 加载、清洁上下文、真实线程回执。'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    p = sub.add_parser('intake'); p.add_argument('--intent', choices=INTENTS, required=True)
    p = sub.add_parser('packet'); p.add_argument('ensemble_id')
    p = sub.add_parser('accept'); p.add_argument('ensemble_id'); p.add_argument('--response', required=True); p.add_argument('--receipt', required=True); p.add_argument('--source', choices=('host_supplied','synthetic_test'), default='host_supplied')
    args = parser.parse_args()
    try:
        if args.command == 'doctor':
            result = doctor(ROOT)
        elif args.command == 'intake':
            result = intake(ROOT, sys.stdin.read(), args.intent)
        elif args.command == 'packet':
            result = dispatch(ROOT, args.ensemble_id)
        else:
            result = accept(ROOT, args.ensemble_id, args.response, args.receipt, source=args.source)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == 'doctor' and not result['local_files_ok'] else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc), 'type': type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
