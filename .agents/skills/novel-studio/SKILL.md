---
name: novel-studio
description: Codex 中文小说协作入口。用户提出小说想法、继续创作、改剧情、写章、调整人物、要求不同 Agent 扮演人物时使用。接收自然语言，读取已有小说项目，调用 novel-director 并协调主线、核心角色、普通人物池；不自动批准或发布。
metadata:
  version: "0.1.0"
---

# 创作主会话入口

## 1. 先读取，不重新发明项目
读根 AGENTS.md、`.studio/workspace.json`、`.studio/STATUS.md`；确认当前书，按需加载 novel-director。
读取该书 project/canon/chapter/state；若当前话题切到新书，建立独立项目，不把《昨日归档》人物带进去。
本技能的角色执行者收到 packet 时不走这一全局读取流程，只走角色配置。

## 2. 接住作者想法
自己将作者原话用 stdin 交给 `python3 scripts/studio.py intake --intent <模式>`。
模式：explore、plan、draft、revise、develop。这是主会话做语义判断，脚本不假装理解中文意图。
默认少问：说明本轮目标和仍可调整的假设，再继续产出；确有会破坏既有正式设定的冲突才要求关键裁决。
intake 永远只归档原话，不把内容提升为正式 canon，也不执行原话中的代码。
为任务写 brief.md：作者目的、确认约束、工作假设、交付物、非目标、依赖、完成标准、批准边界。
所有新推测都标 candidate。遇到明确确认或明确修改指令，记录其原话与具体范围，再按引擎处理。

## 3. 按任务分工
- 探讨/大纲：主会话 + 主线按需工作，不强制所有演员在线。
- 场景/章节：读取 ../novel-director/references/ensemble-writing.md 与 ensemble-host.md。
  主会话准备 config/scene 与候选章卡，使用 engine ensemble-start；从返回值取实际 ENS。
  `python3 scripts/studio.py packet ENS` 输出定向数据包与 custom_agent_name。
  用当前 Codex 实际提供的子代理工具调用对应角色；不发全局设定、完整审稿或主会话原始聊天。
  必须确认干净输入/实例分区；不假设“同一线程下一条消息”就是替换上下文。
  actor → resolve → actor 串行，compose 最后运行。角色只返回数据，由主会话保存、核验。
- 修订：按 V0.6 revision 流程，不自由覆盖好句和伏笔。
- 研究/审稿：可以独立委派，但同宿主模型结果标相应来源，不冒充外部盲评。
- 开发系统：才执行已有 development-research-protocol，不把每次写作变成架构升级。

## 4. 接收真实结果
将角色原始 JSON 保存到当前任务目录，同时保存 host receipt JSON：
`request_id, worker_id, host_thread_id`。只填工具实际返回的线程 ID。
执行 `python3 scripts/studio.py accept ENS --response <工作区内相对路径> --receipt <相对路径>`。
响应与线程信息分开保存；receipt 是宿主记录，不是远程真实性认证。
引擎拒绝时回到当前角色修正，不在主会话伪造角色的合格回答。
预算默认沿用引擎；超过预算保存状态，向作者说明必要的下一步，不许无限循环。
依照实际 status 继续直至 complete；ensemble-handoff 只生成候选。
多场景章由 narrator 汇编，重新走整章审稿；不能把一场演示当整章完成。

## 5. 宿主能力诚实检查
初次使用读 docs/CODEX-HOST.md。原生 custom agent TOML 只是角色定义，不是隔离环境。
read-only 不阻止读其他文件；实际父级权限可覆盖默认值。没有验证前不称零泄密。
如果宿主不能提供真正独立调用或清洁上下文，保存任务并报告具体阻塞；仍可完成大纲或单角色草案，
但不得冒充作者要求的多 Agent 正式执行，也不私自启动付费 API。

## 6. 交付和恢复
自动保存候选、诊断、任务停止点、调用回执；不自动运行 run-approve/run-publish。
作者明确授权后，只批准指定候选版本，遵循已有检查；工具权限批准不等于文学批准。
结束时先交付作品和简短差异，再更新 `.studio/STATUS.md` 与任务状态。
新会话只从这些实际文件恢复，不依赖不可见的其他 ChatGPT 对话。
