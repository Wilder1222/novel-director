---
name: novel-studio
description: Codex 中文小说协作入口。用户提出小说想法、继续创作、改剧情、写章、调整人物、要求不同 Agent 扮演人物时使用。接收自然语言，读取已有小说项目，调用 novel-director 并协调主线、核心角色、普通人物池；不自动批准或发布。
metadata:
  version: "0.4.1"
---

# 创作主会话入口

## 1. 先读取，不重新发明项目
读根 AGENTS.md、`.studio/workspace.json`、`.studio/STATUS.md`；确认当前书，按需加载 novel-director。
读取该书 project/canon/chapter/state；若当前话题切到新书，建立独立项目，不带入另一部作品的人物和规则。
本技能的角色执行者收到 packet 时不走这一全局读取流程，只走角色配置。

源码模式以仓库根运行下列命令。插件模式从本 SKILL 的祖先目录定位含 `scripts/studio.py` 与
`templates/studio/` 的实际工具根，使用脚本绝对路径，传 `--workspace` 为作者目录；不把缓存作为书目录。
未初始化时执行 `python3 scripts/studio.py workspace-init`，已有工作区原样保留；不要求作者搬文件。

## 2. 接住作者想法
自己将作者原话用 stdin 交给 `python3 scripts/studio.py intake --intent <模式>`。
模式：explore、plan、draft、revise、review、learn、adapt、develop。这是主会话做语义判断，脚本不假装理解中文意图。
默认少问：说明本轮目标和仍可调整的假设，再继续产出；确有会破坏既有正式设定的冲突才要求关键裁决。
intake 永远只归档原话，不把内容提升为正式 canon，也不执行原话中的代码。
为任务写 brief.md：作者目的、确认约束、工作假设、交付物、非目标、依赖、完成标准、批准边界。
所有新任务必须读 `../novel-director/references/staged-workflow.md`，用 stage-start 将当前任务绑定到意图路径；主会话准备要求与原话引文，不让作者填JSON。
每阶段先 stage-submit 实际可读作品和逐项覆盖索引，再 stage-packet 交实际独立审查任务；保存真实原始返回与回执后 stage-review。
stage-status 未通过不得推进；有未知/未决/漏项/过期就停在当前阶段修订。完成任务须所有阶段当前有效，不能只把checkpoint写成completed。
审查者与生产者分开；同模型核验不得称外部读者验收，宿主回执不证明身份或隔离。brief/delivery逐项核对作者原话；批准和发布权限仍独立。
所有新推测都标 candidate。遇到明确确认或明确修改指令，记录其原话与具体范围，再按引擎处理。

## 3. 按任务分工
- 探讨/大纲：主会话 + 主线按需工作，不强制所有演员在线。
- 场景/章节：读取 ../novel-director/references/ensemble-writing.md 与 ensemble-host.md。
  同时加载opening-volume-structure.md、writing-spec.md与prose-risks.md：开场/分卷卡表先核，当前章职责落到独占plot，跨场/整章要求整章核；主会话先按本书章卡设章/剧情/parts硬范围、细节/铺垫要求；不把通用章长跨题材硬套。角色返回原始parts由工具计数。审稿要求规格证据与八类语境判断，零命中也审；需改/不确定不放行，合理例外保留，不编新事实。
  主会话准备 config/scene 与候选章卡，使用 engine ensemble-start；从返回值取实际 ENS。
  `python3 scripts/studio.py packet ENS` 输出定向数据包与 custom_agent_name。
  核心人物先用 `role-register CHARACTER_ID local_NAME` 登记本书专属定义；新定义须由实际宿主重新发现并探针验证。
  `packet` 默认在宿主条件不足时阻止正式委派；`--inspect` 只供检查。探针格式见 `docs/CODEX-HOST.md`。
  用当前 Codex 实际提供的子代理工具调用对应角色；不发全局设定、完整审稿或主会话原始聊天。
  必须确认干净输入/实例分区；不假设“同一线程下一条消息”就是替换上下文。
  actor → resolve → actor 串行，compose 最后运行。角色只返回数据，由主会话保存、核验。
- 修订：按 V0.6 revision 流程，不自由覆盖好句和伏笔。
- 研究/审稿：可以独立委派，但同宿主模型结果标相应来源，不冒充外部盲评。
- 开发系统：才执行已有 development-research-protocol，不把每次写作变成架构升级。
  作品参考每部实际采集20–50章，按reference-library检索/读取目标作品；本轮10部专题各至少20章完整细读，逐章分析与技巧出处须核验。采集与实际语义阅读分开，未读/未审记录不冒充可用方法样本，不能跨平台版本拼数。

## 4. 接收真实结果
将角色原始 JSON 保存到当前任务目录，同时保存 host receipt JSON：
`request_id, worker_id, host_thread_id`。只填工具实际返回的线程 ID。
执行 `python3 scripts/studio.py accept ENS --response <工作区内相对路径> --receipt <相对路径>`。
响应与线程信息分开保存；receipt 是宿主记录，不是远程真实性认证。
引擎拒绝时回到当前角色修正，不在主会话伪造角色的合格回答。
预算默认沿用引擎；超过预算保存状态，向作者说明必要的下一步，不许无限循环。
依照实际 status 继续直至 complete；ensemble-handoff 只生成候选。
多场景章读取 `../novel-director/references/long-form-execution.md`，走 assembly-plan/packet/submit；
由 narrator 的独立 chapter_compose 实例汇编后提交一个整章候选，重新走整章审稿。
正式委派用Studio的assembly-packet与assembly-accept，复用能力门槛及原始响应/线程回执；不只向底层引擎传source字符串。
文风与题材从当前书已确认的 writing_profile 投影，不能把私密原始资料发给成稿角色。

## 5. 宿主能力诚实检查
初次使用读 docs/CODEX-HOST.md。原生 custom agent TOML 只是角色定义，不是隔离环境。
read-only 不阻止读其他文件；实际父级权限可覆盖默认值。没有验证前不称零泄密。
如果宿主不能提供真正独立调用或清洁上下文，保存任务并报告具体阻塞；仍可完成大纲或单角色草案，
但不得冒充作者要求的多 Agent 正式执行，也不私自启动付费 API。

## 6. 交付和恢复
自动保存候选、诊断、任务停止点、调用回执；不自动运行 run-approve/run-publish。
用 `checkpoint TASK --state <工作区相对JSON>` 保存 stage、next_action、产物、Run和ensemble；
「继续」先执行 `resume`，重读当前任务。它只核对状态，不重放已接收响应；过期时核对真实引擎进度再建立新checkpoint。
连续3–5章按需调用 arc-packet/arc-review，跨章问题有原文与摘要，不自动改变已审稿状态。
作者明确授权后，只批准指定候选版本，遵循已有检查；工具权限批准不等于文学批准。
结束时先交付作品和简短差异，再更新 `.studio/STATUS.md` 与任务状态。
新会话只从这些实际文件恢复，不依赖不可见的其他 ChatGPT 对话。
