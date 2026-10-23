# Codex 宿主接线协议

这是项目级集成，不是 Python 里一个虚构的 Codex SDK 调用。Codex 主会话本身就是宿主，
使用它实际提供的子代理工具完成 delegate/wait，再将返回值交回既有 V0.7 状态机。

## 一次性能力验证
1. 在新会话检查根指令、两项 Skill、当前书实际注册的自定义角色可用性。客户端不同，不假定配置自动加载成功。
2. 主会话先 `doctor`；此命令只检查本地文件和配置，不会启动任何模型。
3. 通过真实工具建立测试子线程。只发没有小说秘密的包，记录工具返回的真实线程 ID。
4. 验证子线程不继承作者聊天，且不能加载全书资料。若宿主提供禁工具或受限文件环境，按其实际能力配置。
   若只提供 read-only，不够证明读取隔离。不要把提示词中的“不要使用工具”当成权限封锁。
5. 保存实际验证到 .studio/host-probes/，包括客户端版本、可用工具、输入边界、限制与测试结论。
   若无法确认干净上下文，阻塞该角色调用，而非在主线程假演。可继续非角色任务。

本包角色文件包含 read-only 与不使用工具指令，目的是减少误写；不提供操作系统级的保密边界。
不声称与 V0.7 理想的 tools=[] / replace_context=True 宿主条件完全等价。能否满足须在实际 Codex 验证。
不复制父会话给角色；不复用带有其他 instance、history 或 narrator phase 历史的会话。
角色是稳定的职责与数据分区，不要求一个远程 thread 永远在线。每个包可新建干净线程，返回后关闭。
npc_pool 共享配置和逻辑 worker，同一时刻只处理一个普通人物；切换人物不可携带前一人的秘密。

## 接线
- engine `ensemble-start` 创建排练；返回实际 id。
- `studio.py packet <id>`：读取引擎过滤 packet、映射 custom_agent_name、提供委派要求；只读。
- Codex 使用实际原生工具委派指定角色，传入 packet 本体。不提供根目录扫描指令。
- 保存角色的原始 response.json（不是自己改写后的版本）和实际 receipt.json。
- `studio.py accept <id> --response <path> --receipt <path>`：检查回执关联，调用原 engine.respond。
- 再 packet 获取下一依赖阶段；直到 complete，按已有 ensemble-handoff 提交候选。
- `host_supplied` 只说明来源声明；回执不是模型供应商认证。人工篡改工作区可以伪造日志，不能据此声称防伪。

## 回执
```json
{"request_id":"从当前packet取得", "worker_id":"从当前packet取得", "host_thread_id":"原生工具返回的真实值"}
```
只在真实调用后填写。单元测试直接调用纯逻辑函数，不把测试回执计作真实调用。

## 作者与系统批准
Codex 工具的 shell/文件权限批准属于执行权限，不等于作者批准小说。
原引擎 run-approve / run-publish 仍需作者针对具体版本的明确指令；cross_review 不是人类盲评。
首次启动不自动改动全书设定或运行示例排练；写作任务明确时才启动相关角色。

## 原生能力缺口
没有实际子代理工具：报告缺口；不要把一份带多个人名的回答登记为 ensemble。
无清洁上下文：该人物调用不能标严格隔离；需要经核验的独立线程/受限环境适配。
角色配置、脚本自检或研究子代理调用次数不能代替人物引擎的真实隔离验证；当前运行结果以工作区探针记录为准。

## v0.8 探针记录与委派门槛

使用`python3 scripts/studio.py probe-record --input .studio/probe-input.json`登记；
`probe-status`读取状态。记录client、version、transport、tools（人物子调用实际可用工具列表）、
source（observed/synthetic_test）、带时区observed_at、checks与evidence_paths（实际工作区内日志路径数组）。
checks恰含clean_context、tools_disabled、instance_partition、phase_partition四个布尔观察。
每项都须由实际宿主实验支持；没有权限证据就填false。不能把行为指令当tools_disabled=true。

记录保存实际日志摘要、当前书与本地角色/配置指纹；有效期7天。宿主/模型工具环境改变也须主动重验，
本地脚本无法自动读取远程权限。`packet`在缺失、合成、过期或条件不足时不返回可委派包；
`packet ENS --inspect`只供检查，不能绕过正式委派要求。`accept --source host_supplied`也检查此门槛。
synthetic_test可验证本地状态机，但不能被计作真实角色调用。

探针依然只是host_reported_not_attested，本地管理员可改日志；它不创建沙箱、不禁用工具、不构成远程认证。
当前Codex如果只能提供fork_turns=none但仍给子代理文件工具，应如实记录clean_context与tools_disabled的区别，
暂停严格人物委派。独立研究/审查仍可按原授权执行，不能冒称已通过小说秘密隔离。
