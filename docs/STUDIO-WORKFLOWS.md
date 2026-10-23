# Studio 任务恢复与人物注册

v0.9 新任务先按[阶段流程](../.agents/skills/novel-director/references/staged-workflow.md)执行 stage-start/submit/packet/review/status。
completed checkpoint 对已绑定流程强制核对全部阶段；resume 附带当前阶段状态。旧 checkpoint 不追认阶段通过。

Python 3.11+，源码仓库根运行。插件安装后使用实际工具根的scripts/studio.py绝对路径，并传`--workspace <作者目录>`。
代码来自工具安装目录；books/.studio来自作者目录，不把作品写入插件缓存。

## 初始化与继续

`workspace-init`只初始化缺失工作区；已有.studio即返回保留，不覆盖。配置和默认角色只补不存在的文件，不改作者模型或权限。
intake保持stdin原话，创建任务并设置active_task；旧任务仍在。

```bash
python3 scripts/studio.py workspace-init
python3 scripts/studio.py checkpoint TASK --state .studio/checkpoint-input.json
python3 scripts/studio.py resume
python3 scripts/studio.py task-status TASK
```

TASK用实际返回值。checkpoint输入最小形状：

```json
{"status":"active","stage":"planning","next_action":"核对章卡后准备场景包","artifacts":[".studio/tasks/实际TASK/brief.md"],"ensemble_ids":[],"awaiting_author_scope":""}
```

可选run_id、stop_reason；status可为active/awaiting_author/blocked/completed。checkpoint追加不可覆盖快照；task.json仅更新当前指针。
resume核对原话、书、项目源签名、产物、Run清单和当前请求；不重放、不调用模型、不审批。实际引擎已推进时先核对后保存新checkpoint。
没有checkpoint的旧任务报告needs_initial_checkpoint，不伪造恢复进度。正常主会话的工作区写入是串行的；不支持多个主会话并发修改同一任务。

## 当前书核心人物注册

```bash
python3 scripts/studio.py role-register CHARACTER_ID local_ACTOR_NAME
```

ID必须来自当前书characters.json；角色名改成实际小写名。创建`.codex/agents/local_*.toml`（Git忽略），
映射存`.studio/roles/<项目路径摘要>.json`。一个核心人物一个专属定义，重复映射/复用角色/覆盖均拒绝。
旧全局agent-map的通用项仍兼容；核心项须核实人物与定义后显式执行role-adopt-legacy，绑定当前书。不能仅凭同名人物ID继承。默认模板只注册narrator与npc-pool。
角色文件创建成功不等于当前宿主已发现；重新发现并做实际能力探针后才可正式调用。
同一人物不同年龄/历史与narrator不同phase仍使用不同清洁输入；不要把profile注册当成隔离证明。
