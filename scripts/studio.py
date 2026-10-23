#!/usr/bin/env python3
"""Codex workspace helpers. No network, model calls, automatic approval or publication."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import tomllib
from typing import Any
from uuid import uuid4

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path.cwd()
INTENTS = ('explore', 'plan', 'draft', 'revise', 'review', 'learn', 'adapt', 'develop')


def _redirect(path: Path) -> bool:
    if path.is_symlink():
        return True
    return path.exists() and bool(getattr(path.stat(follow_symlinks=False), 'st_file_attributes', 0) & 0x400)


def author_workspace(root: Path) -> None:
    for component in (root.absolute(), *root.absolute().parents):
        if _redirect(component):
            raise ValueError('作者工作区不接受符号链接或junction路径')
    if (SOURCE_ROOT / 'plugin.json').exists() and root.resolve().is_relative_to(SOURCE_ROOT.resolve()):
        raise ValueError('不能把插件安装目录作为作者工作区；用 --workspace 指定外部作者目录')


def child(root: Path, relative: str) -> Path:
    """Resolve workspace paths without following any symlink component."""
    rel = Path(relative)
    if not isinstance(relative, str) or not relative or rel.is_absolute() or '..' in rel.parts or ':' in relative or '\x00' in relative:
        raise ValueError('只接受不含 .. 的工作区相对路径')
    root = root.resolve()
    current = root
    for part in rel.parts:
        current = current / part
        if _redirect(current):
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
    author_workspace(root)
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
        'stage_policy': 'required',
        'canon_effect': 'none', 'next': 'Codex reads input and writes scoped brief.md',
    }
    write_new(folder / 'task.json', info)
    (folder / 'brief.md').write_text(
        '# 创作任务\n\n状态：待 Codex 根据作者原话填写，不是正式设定。\n\n'
        '## 本轮目标\n\n## 已确认约束\n\n## 工作假设\n\n## 交付物与非目标\n\n'
        '## 依赖和完成标准\n\n## 角色分工\n\n## 批准边界\n', encoding='utf-8')
    workspace = read_object(child(root, '.studio/workspace.json'))
    workspace['active_task'] = task_id
    replace_json(child(root, '.studio/workspace.json'), workspace)
    return {**info, 'folder': str(folder.relative_to(root.resolve()))}


def replace_json(path: Path, value: Any) -> None:
    """Atomic replacement for mutable pointers, never for immutable checkpoints."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.studio-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def task_info(root: Path, task_id: str | None = None) -> tuple[Path, dict]:
    task_id = task_id or read_object(child(root, '.studio/workspace.json')).get('active_task')
    if not isinstance(task_id, str) or not re.fullmatch(r'task-[a-f0-9]{16}', task_id):
        raise ValueError('没有有效的当前任务；指定已存在的 task ID')
    folder = child(root, '.studio/tasks/' + task_id)
    task = read_object(folder / 'task.json')
    if task.get('id') != task_id or sha((folder / 'input.md').read_bytes()) != task.get('input_sha256'):
        raise ValueError('任务身份或作者原话已改变')
    if child(root, task['project']) != project_path(root):
        raise ValueError('任务不属于当前书；显式切回原项目后恢复')
    return folder, task


def _artifact(root: Path, relative: str) -> dict:
    path = child(root, relative)
    if not path.is_file():
        raise ValueError('任务产物不是已有文件：' + relative)
    return {'path': path.relative_to(root.resolve()).as_posix(), 'sha256': sha(path.read_bytes())}


def _runtime_snapshot(root: Path, spec: dict) -> dict:
    runtime = engine(root)
    project = project_path(root)
    ensembles = {}
    ids = spec.get('ensemble_ids', [])
    if not isinstance(ids, list) or len(ids) > 64 or len(set(ids)) != len(ids):
        raise ValueError('ensemble_ids 必须为不重复的数组，最多64项')
    for sid in ids:
        state = runtime.status(project, sid)
        ensembles[sid] = {'stage': state['stage'], 'accepted_responses': state['accepted_responses'],
                          'request_id': runtime.packet(project, sid)['request_id'] if state['stage'] != 'complete' else None}
    run = None
    if spec.get('run_id'):
        folder, manifest = runtime.flow._manifest(project, spec['run_id'])
        runtime.flow._check_contract(folder, manifest)
        run = {'id': spec['run_id'], 'state': manifest['status'],
               'manifest_sha256': sha((folder / 'manifest.json').read_bytes())}
        for key, expected_key in (('current_candidate', 'candidate_sha'), ('latest_review', 'review_sha256')):
            if manifest.get(key):
                actual = sha((folder / manifest[key]).read_bytes())
                if actual != manifest.get(expected_key):
                    raise ValueError('Run正文或审稿文件与清单不符')
                run[key] = actual
    return {'project_signature': runtime.flow.signature(project), 'ensembles': ensembles, 'run': run}


def checkpoint(root: Path, task_id: str, spec: dict) -> dict:
    folder, task = task_info(root, task_id)
    required = {'status', 'stage', 'next_action'}
    if not isinstance(spec, dict) or not required <= spec.keys() or spec.keys() - required - {'artifacts', 'run_id', 'ensemble_ids', 'awaiting_author_scope', 'stop_reason'}:
        raise ValueError('checkpoint 字段不完整或包含未知字段')
    if spec['status'] not in ('active', 'awaiting_author', 'blocked', 'completed'):
        raise ValueError('无效任务状态')
    if spec['status'] == 'completed' and task.get('stage_policy') == 'required' and not task.get('pipeline_id'):
        raise ValueError('新任务必须先绑定阶段流程并核验，不能只用checkpoint自报完成')
    if task.get('pipeline_id'):
        stages = _stages(root).status(project_path(root), task['pipeline_id'])
        if spec['status'] == 'completed' and not stages['complete']:
            raise ValueError('阶段产物尚未全部核验，不能把任务标成completed')
    for key in ('stage', 'next_action'):
        if not isinstance(spec[key], str) or not spec[key].strip() or len(spec[key]) > 4000:
            raise ValueError(key + ' 必须为非空短文本')
    artifacts = spec.get('artifacts', [])
    if not isinstance(artifacts, list) or len(artifacts) > 256:
        raise ValueError('artifacts 必须为数组，最多256项')
    frozen = {'task_id': task_id, 'project': task['project'], 'input_sha256': task['input_sha256'],
              'at': datetime.now(timezone.utc).isoformat(), 'spec': spec,
              'artifacts': [_artifact(root, name) for name in artifacts], 'runtime': _runtime_snapshot(root, spec)}
    if task.get('pipeline_id'):
        frozen['pipeline'] = stages
    relative = f'checkpoints/checkpoint-{uuid4().hex}.json'
    write_new(child(root, f'.studio/tasks/{task_id}/' + relative), frozen)
    task.update(status=spec['status'], stage=spec['stage'], next=spec['next_action'], checkpoint=relative)
    replace_json(folder / 'task.json', task)
    return {'id': task_id, 'checkpoint': relative, 'status': task['status']}


def resume(root: Path, task_id: str | None = None) -> dict:
    folder, task = task_info(root, task_id)
    if task.get('pipeline_id'):
        task = {**task, 'pipeline': _stages(root).status(project_path(root), task['pipeline_id'])}
    if not task.get('checkpoint'):
        return {**task, 'resume_status': 'needs_initial_checkpoint', 'automatic_action': False}
    cp = read_object(child(root, folder.relative_to(root.resolve()).as_posix() + '/' + task['checkpoint']))
    if cp['task_id'] != task['id'] or cp['project'] != task['project'] or cp['input_sha256'] != task['input_sha256']:
        raise ValueError('checkpoint 不属于该任务或原话版本')
    if task.get('pipeline_id') and cp.get('pipeline') != task['pipeline']:
        return {**task, 'recorded_status': task['status'], 'status': 'needs_revalidation',
                'resume_status': 'needs_stage_revalidation', 'automatic_action': False,
                'notice': '阶段作品/核验已推进或过期，旧checkpoint不能代表当前完成；核对实际阶段后保存新checkpoint。'}
    for item in cp['artifacts']:
        if _artifact(root, item['path']) != item:
            raise ValueError('任务产物已变化：' + item['path'])
    if _runtime_snapshot(root, cp['spec']) != cp['runtime']:
        raise ValueError('项目/稿件/角色请求已推进或变化；核对实际进度后创建新 checkpoint，禁止重放')
    return {**task, 'resume_status': 'ready', 'checkpoint_state': cp,
            'automatic_action': False, 'notice': '只恢复文件状态，不恢复人物旧聊天、不调用模型、不批准。'}


def _mapping_path(root: Path) -> Path:
    identity = project_path(root).relative_to(root.resolve()).as_posix()
    return child(root, '.studio/roles/' + sha(identity.encode('utf-8'))[:20] + '.json')


def _stages(root):
    engine(root)
    import stage_gates
    return stage_gates


def stage_start(root, task_id, spec):
    folder, task = task_info(root, task_id)
    if task.get('pipeline_id'):
        if spec.get('supersedes') != task['pipeline_id']:
            raise ValueError('任务已有阶段流程，显式supersedes才能替代，不伪造历史通过')
    if spec.get('author_input') != (folder / 'input.md').read_text(encoding='utf-8'):
        raise ValueError('阶段流程必须使用该任务完整作者原话')
    if task['intent'] != spec.get('profile'):
        raise ValueError('阶段路径必须匹配intake意图')
    result = _stages(root).start(project_path(root), spec)
    task.update(pipeline_id=result['pipeline_id'], status='active', stage='brief', next='提交并核验任务简报')
    replace_json(folder / 'task.json', task)
    return result


def stage_action(root, task_id, action, stage=None, spec=None, report=None, receipt=None):
    _, task = task_info(root, task_id)
    if not task.get('pipeline_id'): raise ValueError('先stage-start，不自动补造旧阶段')
    api = _stages(root); project = project_path(root); pid = task['pipeline_id']
    if action == 'status': return api.status(project, pid)
    if action == 'packet': return api.packet(project, pid, stage)
    if action == 'submit': return api.submit(project, pid, stage, spec)
    if action == 'review': return api.review(project, pid, stage, report, receipt)
    raise ValueError('未知阶段操作')


def role_mapping(root: Path) -> dict:
    path = _mapping_path(root)
    if path.exists():
        return read_object(path)
    # Unbound legacy core IDs cannot establish book identity: IDs can collide.
    legacy = read_object(child(root, '.studio/agent-map.json'))
    return {key: value for key, value in legacy.items() if not key.startswith('core:')}


def adopt_legacy_roles(root: Path) -> dict:
    path = _mapping_path(root)
    if path.exists():
        raise ValueError('本书已有映射，不覆盖')
    legacy = read_object(child(root, '.studio/agent-map.json'))
    known = {x['id'] for x in read_object(project_path(root) / 'characters.json')['characters']}
    core = {k: v for k, v in legacy.items() if k.startswith('core:')}
    if any(k[5:] not in known for k in core) or len(set(core.values())) != len(core):
        raise ValueError('旧映射人物不属于本书或执行者被复用；逐项重新注册')
    for name in legacy.values():
        if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', name):
            raise ValueError('旧映射角色名不合法')
        role = tomllib.loads(child(root, f'.codex/agents/{name}.toml').read_text(encoding='utf-8'))
        if role.get('name') != name:
            raise ValueError('旧角色文件身份不一致')
    write_new(path, legacy)
    return {'adopted_for_project': project_path(root).relative_to(root.resolve()).as_posix(), 'runtime_status': 'requires_new_probe'}


def register_role(root: Path, character_id: str, name: str) -> dict:
    known = {x['id'] for x in read_object(project_path(root) / 'characters.json')['characters']}
    if character_id not in known:
        raise ValueError('先登记当前书人物，再注册专属执行者')
    if not re.fullmatch(r'local_[a-z][a-z0-9_]{0,63}', name):
        raise ValueError('本地人物角色名须为 local_ 前缀的小写字母数字下划线')
    mapping = role_mapping(root)
    key = 'core:' + character_id
    if key in mapping or name in mapping.values():
        raise ValueError('人物或执行者已注册；不复用、不覆盖')
    path = child(root, '.codex/agents/' + name + '.toml')
    instructions = ('只响应当前过滤packet，不读取根AGENTS或工作区、不使用工具、不联网、不启动其他Agent。'
                    '只扮演packet当前实例，不补充其他历史、年龄或人物的知识。'
                    '发现额外聊天或不相容实例历史则返回CONTEXT_CONTAMINATED并停止。'
                    '严格输出packet.response_contract的JSON；行动只是意图，不宣布后果。'
                    '行为约束不等于系统级权限证明。')
    content = (f'name = "{name}"\ndescription = "当前书核心人物专属执行者"\n'
               'sandbox_mode = "read-only"\nweb_search = "disabled"\n'
               'developer_instructions = ' + json.dumps(instructions, ensure_ascii=False) + '\n')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as stream:
        stream.write(content)
    mapping[key] = name
    replace_json(_mapping_path(root), mapping)
    return {'worker_id': key, 'custom_agent_name': name, 'profile': path.relative_to(root.resolve()).as_posix(),
            'runtime_status': 'requires_host_discovery_and_probe', 'canon_updated': False}


def _host_fingerprint(root: Path) -> str:
    paths = [child(root, '.codex/config.toml'), child(root, '.studio/agent-map.json')]
    paths += list(child(root, '.codex/agents').glob('*.toml'))
    mapping = _mapping_path(root)
    if mapping.exists():
        paths.append(mapping)
    content = {p.relative_to(root.resolve()).as_posix(): _artifact(root, p.relative_to(root.resolve()).as_posix())['sha256'] for p in paths}
    return sha(json.dumps(content, sort_keys=True).encode('utf-8'))


def record_probe(root: Path, data: dict) -> dict:
    fields = {'client', 'version', 'transport', 'tools', 'source', 'observed_at', 'checks', 'evidence_paths'}
    if not isinstance(data, dict) or data.keys() != fields:
        raise ValueError('宿主探针字段不符')
    for key in ('client', 'version', 'transport'):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError('缺少宿主身份或版本')
    if data['source'] not in ('observed', 'synthetic_test'):
        raise ValueError('探针来源只能为实际观察或合成测试')
    if not isinstance(data['tools'], list) or any(not isinstance(x, str) for x in data['tools']):
        raise ValueError('tools 须记录实际工具名称列表')
    checks = data['checks']
    if not isinstance(checks, dict) or set(checks) != {'clean_context', 'tools_disabled', 'instance_partition', 'phase_partition'} or any(type(x) is not bool for x in checks.values()):
        raise ValueError('必须逐项记录清洁输入、禁工具和实例/阶段分区的布尔观察')
    observed = datetime.fromisoformat(data['observed_at'])
    if observed.tzinfo is None:
        raise ValueError('探针日期必须带时区')
    if not isinstance(data['evidence_paths'], list) or not data['evidence_paths']:
        raise ValueError('必须有实际探针记录文件')
    record = {**data, 'evidence': [_artifact(root, p) for p in data['evidence_paths']],
              'host_fingerprint': _host_fingerprint(root), 'project': project_path(root).relative_to(root.resolve()).as_posix(),
              'provenance': 'host_reported_not_attested'}
    relative = '.studio/host-probes/probe-' + uuid4().hex + '.json'
    write_new(child(root, relative), record)
    replace_json(child(root, '.studio/host-probes/latest.json'), {'path': relative, 'sha256': sha(child(root, relative).read_bytes())})
    return {'saved': relative, 'provenance': record['provenance']}


def host_status(root: Path) -> dict:
    reasons = []
    try:
        pointer = read_object(child(root, '.studio/host-probes/latest.json'))
        path = child(root, pointer['path'])
        if sha(path.read_bytes()) != pointer['sha256']:
            raise ValueError('宿主记录已改变')
        record = read_object(path)
        if record['source'] != 'observed': reasons.append('合成测试不能授权正式角色委派')
        if not all(record['checks'].values()): reasons.append('清洁输入/禁工具/实例或阶段分区未全部满足')
        if record['tools']: reasons.append('人物调用仍有工具权限')
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(record['observed_at'])).total_seconds()
        if not 0 <= elapsed <= 7 * 86400: reasons.append('探针日期在未来或已超过7天')
        if record['host_fingerprint'] != _host_fingerprint(root): reasons.append('宿主配置或角色已变化，须重新验证')
        if record['project'] != project_path(root).relative_to(root.resolve()).as_posix(): reasons.append('探针属于其他书')
        for item in record['evidence']:
            if _artifact(root, item['path']) != item: reasons.append('探针证据文件已改变')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reasons.append('没有可用探针：' + str(exc))
    return {'eligible': not reasons, 'reasons': reasons, 'verification': 'host_reported_not_attested',
            'notice': '本记录不创建沙箱、不禁用工具，也不是供应商认证。宿主改变后须重新验证。'}


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
    # Code belongs to the installed tool, while writing data belongs to --workspace.
    scripts = child(SOURCE_ROOT, '.agents/skills/novel-director/scripts')
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import ensemble_runtime
    return ensemble_runtime


def dispatch(root: Path, ensemble_id: str, *, inspect: bool = False) -> dict[str, Any]:
    packet = engine(root).packet(project_path(root), ensemble_id)
    return delegation_view(root, packet, inspect=inspect)


def delegation_view(root: Path, packet: dict, *, inspect: bool = False) -> dict:
    name = select_role(role_mapping(root), packet)
    profile = child(root, f'.codex/agents/{name}.toml')
    if not profile.is_file():
        raise ValueError('角色定义缺失')
    role = tomllib.loads(profile.read_text(encoding='utf-8'))
    if role.get('name') != name:
        raise ValueError('角色文件名与 TOML name 不一致')
    capabilities = host_status(root)
    result = {
        'custom_agent_name': name, 'profile': str(profile.relative_to(root.resolve())),
        'execution_status': 'awaiting_real_codex_delegation' if capabilities['eligible'] else 'blocked_host_capabilities',
        'instruction': '主会话使用真实子代理工具，只发送 packet；先验证干净上下文与工具边界。',
        'security_claim': '配置及提示约束不是硬隔离；本命令没有启动任何 Agent。',
        'host_capabilities': capabilities,
    }
    if capabilities['eligible'] or inspect:
        result['packet'] = packet
    if inspect:
        result['execution_status'] = 'inspection_only'
    return result


def dispatch_assembly(root: Path, assembly_id: str, *, inspect: bool = False) -> dict:
    engine(root)
    import chapter_tools
    return delegation_view(root, chapter_tools.assembly_packet(project_path(root), assembly_id), inspect=inspect)


def accept_assembly(root: Path, assembly_id: str, response_path: str, receipt_path: str, *, source: str = 'host_supplied') -> dict:
    engine(root)
    import chapter_tools
    if source not in ('host_supplied', 'synthetic_test'):
        raise ValueError('无效来源')
    if source == 'host_supplied' and not host_status(root)['eligible']:
        raise ValueError('宿主能力未满足；不能执行真实整章委派交接')
    project = project_path(root)
    packet = chapter_tools.assembly_packet(project, assembly_id)
    response = read_object(child(root, response_path)); receipt = read_object(child(root, receipt_path))
    check_receipt(packet, response, receipt)
    path = child(root, f'.studio/receipts/{packet["request_id"]}/{uuid4().hex}.json')
    write_new(path, {'request_id': packet['request_id'], 'assembly_id': assembly_id, 'receipt': receipt,
                     'source': source, 'response_sha256': sha(child(root, response_path).read_bytes()),
                     'provenance': 'host_reported_not_attested'})
    try:
        result = chapter_tools.assembly_submit(project, assembly_id, response, source=source)
    except Exception as exc:
        write_new(path.with_suffix('.rejected.json'), {'error': str(exc), 'type': type(exc).__name__})
        raise
    write_new(path.with_suffix('.accepted.json'), {'result': result, 'status': 'accepted'})
    return {'engine_result': result, 'receipt': path.relative_to(root.resolve()).as_posix(), 'provenance': 'host_reported_not_attested'}


def accept(root: Path, ensemble_id: str, response_path: str, receipt_path: str, *, source: str = 'host_supplied') -> dict[str, Any]:
    if source not in ('host_supplied', 'synthetic_test'):
        raise ValueError('无效来源')
    if source == 'host_supplied' and not host_status(root)['eligible']:
        raise ValueError('宿主能力未满足；不导入声称正式角色委派的结果')
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
            if role.get('name') != path.stem:
                errors.append(f'{path.name}: 文件名与 name 不一致')
            for field in ('name', 'description', 'developer_instructions'):
                if not isinstance(role.get(field), str) or not role[field].strip():
                    errors.append(f'{path.name}: 缺少 {field}')
            if role.get('sandbox_mode') != 'read-only':
                errors.append(f'{path.name}: 非预期默认权限')
            roles.append(role.get('name', ''))
        if len(roles) != len(set(roles)):
            errors.append('自定义角色重名')
        for role in role_mapping(root).values():
            if role not in roles:
                errors.append(f'角色映射无定义: {role}')
        for name in ('novel-studio', 'novel-director'):
            skill = child(SOURCE_ROOT, f'.agents/skills/{name}/SKILL.md').read_text(encoding='utf-8')
            if not skill.startswith('---\n') or f'name: {name}\n' not in skill:
                errors.append(f'Skill 元数据不匹配: {name}')
        if child(SOURCE_ROOT, 'RELEASE-MANIFEST.json').exists():
            import release
            errors.extend('当前源码已改变: ' + name for name in release.verify(SOURCE_ROOT))
        else:
            provenance = read_object(child(SOURCE_ROOT, 'ENGINE-PROVENANCE.json'))
            for relative, digest in provenance['files'].items():
                path = child(SOURCE_ROOT, '.agents/skills/novel-director/' + relative)
                if not path.is_file() or sha(path.read_bytes().replace(b'\r\n', b'\n')) != digest:
                    errors.append(f'引擎文件已改变: {relative}')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return {'local_files_ok': not errors, 'errors': errors, 'custom_roles': roles,
            'runtime_status': 'not_verified_by_this_command', 'native_agent_calls': 0,
            'source_hash_policy': 'utf8-lf (source only; manuscript evidence stays byte-exact)',
            'host_capabilities': host_status(root),
            'next': '在实际 Codex 会话验证 Skill/Agent 加载、清洁上下文、真实线程回执。'}


def initialize(root: Path, title: str = '未命名小说') -> dict:
    """Explicit first-use scaffolding, preserving every existing workspace file."""
    author_workspace(root)
    if child(root, '.studio').exists():
        return {'status': 'existing_workspace_preserved', 'workspace': str(root)}
    project = child(root, 'books/new-novel')
    if not project.exists():
        shutil.copytree(SOURCE_ROOT / '.agents/skills/novel-director/assets/project-template', project)
        meta = read_object(project / 'project.json'); meta['title'] = title
        replace_json(project / 'project.json', meta)
    elif not (project / 'project.json').is_file():
        raise ValueError('books/new-novel 已存在但不是项目；不覆盖')
    shutil.copytree(SOURCE_ROOT / 'templates/studio', child(root, '.studio'))
    config = child(root, '.codex/config.toml')
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE_ROOT / '.codex/config.toml', config)
    for role in ('narrator', 'npc_pool', 'continuity_editor'):
        path = child(root, f'.codex/agents/{role}.toml')
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_ROOT / f'.codex/agents/{role}.toml', path)
    gitignore = child(root, '.gitignore')
    existing = gitignore.read_text(encoding='utf-8') if gitignore.exists() else ''
    private_rules = ('/books/', '/.studio/', '/.codex/agents/local_*.toml')
    missing = [rule for rule in private_rules if rule not in existing.splitlines()]
    if missing:
        with gitignore.open('a', encoding='utf-8', newline='') as stream:
            stream.write(('\n' if existing and not existing.endswith('\n') else '') + '\n'.join(missing) + '\n')
    return {'status': 'initialized', 'workspace': str(root), 'project': 'books/new-novel', 'author_content_generated': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=ROOT, help='作者工作区；默认当前目录，不写入安装缓存')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    p = sub.add_parser('workspace-init'); p.add_argument('--title', default='未命名小说')
    p = sub.add_parser('intake'); p.add_argument('--intent', choices=INTENTS, required=True)
    p = sub.add_parser('packet'); p.add_argument('ensemble_id'); p.add_argument('--inspect', action='store_true')
    p = sub.add_parser('accept'); p.add_argument('ensemble_id'); p.add_argument('--response', required=True); p.add_argument('--receipt', required=True); p.add_argument('--source', choices=('host_supplied','synthetic_test'), default='host_supplied')
    p = sub.add_parser('assembly-packet'); p.add_argument('assembly_id'); p.add_argument('--inspect', action='store_true')
    p = sub.add_parser('assembly-accept'); p.add_argument('assembly_id'); p.add_argument('--response', required=True); p.add_argument('--receipt', required=True); p.add_argument('--source', choices=('host_supplied','synthetic_test'), default='host_supplied')
    p = sub.add_parser('checkpoint'); p.add_argument('task_id'); p.add_argument('--state', required=True)
    p = sub.add_parser('stage-start'); p.add_argument('task_id'); p.add_argument('--spec', required=True)
    p = sub.add_parser('stage-status'); p.add_argument('task_id')
    for command in ('stage-packet', 'stage-submit', 'stage-review'):
        p = sub.add_parser(command); p.add_argument('task_id'); p.add_argument('stage')
        if command == 'stage-submit': p.add_argument('--spec', required=True)
        if command == 'stage-packet': p.add_argument('--out')
        if command == 'stage-review':
            p.add_argument('--report', required=True); p.add_argument('--receipt', required=True)
    for command in ('resume', 'task-status'):
        p = sub.add_parser(command); p.add_argument('task_id', nargs='?')
    p = sub.add_parser('role-register'); p.add_argument('character_id'); p.add_argument('name')
    sub.add_parser('role-adopt-legacy')
    p = sub.add_parser('probe-record'); p.add_argument('--input', required=True)
    sub.add_parser('probe-status')
    args = parser.parse_args()
    try:
        root = args.workspace.expanduser().resolve()
        if args.command == 'doctor':
            result = doctor(root)
        elif args.command == 'workspace-init': result = initialize(root, args.title)
        elif args.command == 'intake':
            result = intake(root, sys.stdin.read(), args.intent)
        elif args.command == 'packet':
            result = dispatch(root, args.ensemble_id, inspect=args.inspect)
        elif args.command == 'accept':
            result = accept(root, args.ensemble_id, args.response, args.receipt, source=args.source)
        elif args.command == 'assembly-packet': result = dispatch_assembly(root, args.assembly_id, inspect=args.inspect)
        elif args.command == 'assembly-accept': result = accept_assembly(root, args.assembly_id, args.response, args.receipt, source=args.source)
        elif args.command == 'checkpoint': result = checkpoint(root, args.task_id, read_object(child(root, args.state)))
        elif args.command == 'stage-start': result = stage_start(root, args.task_id, read_object(child(root, args.spec)))
        elif args.command.startswith('stage-'):
            result = stage_action(root, args.task_id, args.command[6:], getattr(args, 'stage', None),
                spec=read_object(child(root, args.spec)) if getattr(args, 'spec', None) else None,
                report=read_object(child(root, args.report)) if getattr(args, 'report', None) else None,
                receipt=read_object(child(root, args.receipt)) if getattr(args, 'receipt', None) else None)
        elif args.command in ('resume', 'task-status'): result = resume(root, args.task_id)
        elif args.command == 'role-register': result = register_role(root, args.character_id, args.name)
        elif args.command == 'role-adopt-legacy': result = adopt_legacy_roles(root)
        elif args.command == 'probe-record': result = record_probe(root, read_object(child(root, args.input)))
        else: result = host_status(root)
        if args.command == 'stage-packet' and args.out:
            engine(root).flow.atomic_write(child(root, args.out), json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == 'doctor' and not result['local_files_ok'] else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc), 'type': type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
