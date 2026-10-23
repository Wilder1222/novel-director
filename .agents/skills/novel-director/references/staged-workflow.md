# 阶段作品与核验（v0.9起，v0.10补充规格/风格/参考）

## 主会话必须执行

所有新任务按意图选阶段路径；旧任务先读取实际停止点，显式建立流程，不追认不存在的历史通过。每阶段先交作品、再核验、再推进。由主会话保存文件；作者只用自然语言，不填写本页的 JSON。可独立并行研究/审查，正式角色仍按 ensemble 串行依赖和宿主门槛执行。

“正确产物”的操作定义：符合本轮授权、作品完整且可读、必需维度和作者要求逐项覆盖、引文/版本/依赖可核对、语义审查没有 revise/unknown 或未决项。代码不理解小说好坏，不把上述条件说成绝对文学正确。作者批准始终另走现有流程。

| 意图 | 必经阶段与实际产物 |
| --- | --- |
| explore / 构思 | brief 任务简报 → concept 有实质差异的备选与取舍 → delivery 备选交付 |
| plan / 大纲 | brief → design 世界/情节/人物/情感设计 → outline 有因果的有序大纲与伏笔 → delivery |
| draft / 章节 | brief → scene_plan 章卡/场卡/进出状态 → rehearsal 完成排练的可读候选 → draft 完整Run正文 → editorial 六维审稿及处理记录 → delivery |
| revise / 改稿 | brief → diagnosis 原稿全文/证据问题/保护范围 → revision 实际定向修订全文和验收 → editorial → delivery |
| review / 检查 | brief → diagnosis 原文问题与证据（有意歧义与错误分开） → delivery；不自动改稿 |
| learn / 学习 | brief → exercise 原创练习全文 → feedback 原文反馈和复练方案 → delivery |
| adapt / 改编 | brief → adaptation 可拍场景或剧本候选 → adaptation_review 改编核验 → delivery |
| develop / 工具升级 | brief → research 带来源/日期/样本限制的研究 → implementation_plan 契约和验收方案 → implementation 实际源码变更 → validation 实际运行记录 → delivery 安装与交付 |

每阶段必需维度、审查问题由 `assets/stage-contracts.json` 唯一维护。不要机械运行全书流程：只要大纲不写正文，审查不暗中修改作品，练习不升格 canon。章节 draft/revise **一次只管理一章**，多场景可以组章，多章顺序分别核验。批量正式发布未实现。

## 入口与阶段退出

1. Studio intake 保存作者原话，主会话写本轮简报。准备候选章卡等运行所需结构后冻结阶段流程；冻结后修改正式资料会使流程过期，不能静默重签。候选文件可存项目内 `evidence/`，不改正式 canon。
2. `stage-start` 冻结完整原话、逐项要求及其原话引文、路径、章节范围、完整故事签名、源文件存在性/哈希和阶段规则。不是作者批准记录。
3. `stage-submit` 保存不可覆盖的 `work.md`、`index.json`、`seal.json`。作品必须是实际简报、设计、大纲、全文或真实检查报告，不能只交执行清单、标题或 checksum。索引每项含维度、实际作品引文和作用；全部必需维度覆盖。
4. `stage-packet` 输出编辑专用审查包：本阶段全文、条目、逐项核验目标和此前阶段作品。不得把它发给人物执行者。引擎私密 state、全局人物秘密与原始工具权限不进入此包。包超过200000字符就拆任务，不能裁掉尾部继续称通读。
5. 主会话实际调用独立审查任务；审查者对每条 criterion、每个 item，以及 brief/delivery 中每条作者 requirement 返回 pass/revise/unknown、原因、准确引文。不得只扫关键词/标题或复制同一句理由。核查完整作品及来源，模型不能判定时填 unknown。
6. 保存原始审查与实际宿主回执，执行 `stage-review`。脚本验证目标无漏项/重复、引文真实且 item 引文位于对应作品片段、作品/审查包/来源哈希匹配；有未决项或非pass结果不能退出。审查者与生产者 worker/invocation 标识必须不同。同模型审查不是外部读者；回执也不证明身份或清洁上下文。没有真实工具返回 ID 时 `host_thread_id:null`，保留实际任务名。
7. `stage-status` 每次从作品与报告重核，不信 checkpoint 的文字或缓存 PASS。上游作品、审查、正式资料、规则、当前Run正文或审稿变化，依赖它的下游失效。保留历史作品和失败证据，按实际版本重交/重审。

确定性结构通过、证据覆盖完整、语义审查满意、作者批准分别记录。系统永远返回 `literary_truth_verified:false`、`author_approved:false`。synthetic_test 可以测试阶段状态机，但永远不能从托管流程批准或发布。

## 产物来源和底层门槛

- 新draft/revise在start前必须有[当前章硬规格](writing-spec.md)；场景计划产物自动附可读预算。draft/revision额外逐项核人物/事件/细节/铺垫以及[八类风格与全部命中](prose-risks.md)，证据来自对应实际正文范围；命中审查至少完整包含命中，不能只引单字。审稿仍核当前全部报告，登记需改不能当已解决。
- 工具研究声明`reference_books`时，research sources须有`reference_samples`实际数据；当前schema2逐部20–50章、原始来源与清洗计数绑定，不能换URL/改章号拼平台。旧schema1只核原50章记录。声明10部细读专题须有study_contract，逐部至少20章真实分析与不同实际执行者审查、带章段出处的六维技巧。独立检查采集覆盖和语义结论范围，详[参考库](reference-library.md)。不声明实际采用作品不能规避作者要求，范围真实性仍需审查。

- rehearsal 必须绑定已 complete、同章的真实 ensemble，作品包含其完整可读 candidate。登记过场次时，必须全部覆盖且顺序相符。同场不同排练不能重复计数。真实流程的调用来源须全为 host_supplied；这仍不是隔离证明，Studio 原有能力探针继续生效。
- draft/revision 必须绑定实际 Run candidate，并在作品中包含候选全文；不是外部自称的“已写完”。当前候选换版立即使旧阶段过期。revision 还须从已诊断基线经 revision-plan/apply/check 派生并满足其既有验收，不能自由覆盖新稿。
- revise diagnosis 绑定原稿：`baseline` 来源为当前正式 manuscript 路径，或已有 Run 的候选（保存历史版本，不跟随其 current 指针）。包含原稿全文。可在 diagnosis 后新建 Run，首次提交同一原稿、审出问题，再执行定向修订；原稿初审的特殊入口只允许基线哈希，不允许新稿绕过 revision 阶段。
- editorial 绑定当前 Run 真实审稿全文；全部六维 scores 均有原文证据，不适用维度说明理由；BLOCKING/MAJOR 未闭合不能退出。尚存 MINOR/模型局限必须在报告与交付显式说明，审查者判断是否可接受。
- implementation/validation 至少绑定一个项目内实际文件：可归档源码差异/实际执行日志到 `evidence/`。源文件变动后核验过期。研究 URL 与创作事实仍须实际打开核对，脚本不负责联网认证。
- 新 Run/排练需 scene_plan 通过，交正文需 rehearsal 通过，常规审稿需 draft/revision 通过。作者批准/发布还需 delivery 全通过且当前候选、当前审稿均匹配。直接调用底层 Run/ensemble/assembly 也受已绑定章节门槛约束。
- 未绑定旧章节返回 legacy_unverified，维持原引擎能力，不声称其已通过阶段核验。阶段机制防止正常工具路径误跳，不是防止本地文件所有者恶意改写代码/身份的安全系统。

## 命令和数据（主会话生成）

源码模式：

```powershell
python scripts/studio.py stage-start TASK --spec .studio/tasks/TASK/stages.json
python scripts/studio.py stage-submit TASK brief --spec .studio/tasks/TASK/brief-product.json
python scripts/studio.py stage-packet TASK brief
python scripts/studio.py stage-review TASK brief --report .studio/tasks/TASK/brief-review.json --receipt .studio/tasks/TASK/brief-receipt.json
python scripts/studio.py stage-status TASK
```

独立 Director 安装用本 Skill 内 `scripts/novel.py stage-start PROJECT --spec SPEC`；其余 `stage-* PROJECT PIPELINE STAGE ...`。插件用脚本绝对路径，Studio 传 `--workspace 作者目录`。`stage-packet` 支持 `--out` 输出全量审查包，拒绝覆盖。不要依赖可能被 UI 截断的终端输出完成审查。

start spec：

```json
{"profile":"plan","mode":"host_supplied","author_input":"只做雨棚重逢大纲，不写正文。","requirements":[{"id":"R1","text":"只交大纲","quote":"不写正文"}],"scope":[],"context_files":["style.md"]}
```

submit spec：`work` 为作品全文，`items` 每项 `id/section/quote/meaning`，重复引文加 Unicode codepoint `start/end`；`producer` 为实际 `worker_id/invocation_id`。可选 `sources`：`{"kind":"file","path":"evidence/check.log.md"}`、`{"kind":"ensemble","ensemble_id":"..."}`、`{"kind":"candidate","run_id":"..."}`、`{"kind":"run_review","run_id":"..."}`、`{"kind":"reference_samples","path":"evidence/samples.json"}`、`{"kind":"baseline","path":"manuscript/V01-C01.md"}` 或 baseline+run_id。项目外路径、隐藏通用文件来源、链接/junction 均拒绝。

review 必需 `packet_sha256/read_sha256/checks/unresolved/limitations`，checks 每项 `target/verdict/reason/citations`。receipt 必需 `source/worker_id/invocation_id/host_thread_id/context_claim`。`context_claim`只是声明，不能当隔离证据。真实 source=host_supplied，合成 source=synthetic_test；不接受 human/external 标签冒充身份。

`read_sha256` 取审查包的 `work_sha256`；`packet_sha256` 取同名字段。以下只示例一条检查，实际报告必须覆盖包中**全部** review_targets，值与引文由真实阅读产生：

```json
{"packet_sha256":"包内实际值","read_sha256":"包内work_sha256实际值","checks":[{"target":"criterion:scope","verdict":"pass","reason":"逐项对比作者原话后，交付范围一致；具体说明依据。","citations":[{"quote":"作品中的确切原文","start":0,"end":9}]}],"unresolved":[],"limitations":"说明此次审查未能证明的内容。"}
```

上例 start/end 仅展示字段形状，实际必须是原文 Unicode codepoint 范围；唯一引文可省略，重复引文不能省略。回执最小示例（主会话填写真实工具返回）：

```json
{"source":"host_supplied","worker_id":"实际独立审查任务名","invocation_id":"本次实际调用标识","host_thread_id":null,"context_claim":"仅据任务包审查；没有证明文件读取隔离"}
```

## 失败与恢复

新 intake 任务必须先绑定阶段流程才能完成；旧的无阶段任务保持兼容但不追认通过。阶段版本或核验推进后，resume 将旧 completed/ready 降为 needs_revalidation/needs_stage_revalidation，并保留 recorded_status 供核对，不能沿用旧快照自报完成。

每阶段最多3个作品版本、每版3次有效审查；失败记录保留。预算耗尽停止，归档问题和新策略，显式建立替代流程，不能后台无限重试。替代传 `supersedes:旧PIPELINE`；旧流程历史保留但不再能控制章节。上游有改动时先重交上游作品，依次重交受影响下游，不只重写 PASS。正式资料签名改变或规则升级需新流程，不自动迁移旧结论。

Studio checkpoint 为 completed 时，已绑定流程必须全部当前有效。resume 只报告真实阶段和旧快照是否过期，不调用模型、不重放角色响应。正文发表后正式资料签名变化会让创作流程显示历史过期，发布回执保留；这不抹除实际出版事件。主会话在发布前保存交付/批准记录，发布后按实际状态收尾，不把旧创作门槛改造成永久通过。
