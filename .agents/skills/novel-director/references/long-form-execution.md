# 文风、整章和跨章执行契约（v0.8）

源码示例以仓库根为 cwd。独立安装时用实际 Skill 绝对目录下的 scripts/novel.py 替换脚本前缀，书目录仍是作者项目。

## 文风校准与题材

```bash
python3 .agents/skills/novel-director/scripts/novel.py profile-template books/new-novel
python3 .agents/skills/novel-director/scripts/novel.py profile-check books/new-novel
```

模板只创建 candidate，不覆写。主会话从作者授权的短样本提炼叙述距离、句式节奏、对白、解释和意象倾向；
把样本来源与范围保存在 calibration，规则和短正反例与原话分开。作者确认具体范围后才写 confirmed、confirmation；
明确 reader_safe 后只投影白名单，不把原样本全文、确认原话或校准笔记发给角色。禁止模型自封作者批准。

```json
{
  "schema_version": "1",
  "status": "candidate",
  "reader_safe": false,
  "confirmation": "",
  "narration": "third_person_limited",
  "genres": ["realism"],
  "rules": ["候选建议：以人物可观察动作承载情绪，保留有作用的沉默。"],
  "examples": [{"prefer": "她把信重新折好。", "avoid": "她感到一种无法言说的情绪。", "reason": "只是可讨论的局部方法，不是所有情境的禁令。"}],
  "calibration": {"source_refs": [], "scope": "待作者确认", "limits": "不能由样本推断全部偏好"}
}
```

genres可组合：realism、romance、mystery、fantasy、science_fiction、historical。题材标签只改变检查侧重，不自行强制爽点、失败次数、反转或恋爱；作者本次明确要求的开场/分卷/大小高潮与爽点依opening-volume-structure.md执行，不因此强制章章高潮。
narration支持first_person / third_person_limited；全知叙述目前不在角色包引擎能力内。
配置只在compose出现，actor/resolve不接收。缺省无配置时旧packet形状与摘要保持原状。新增/修改配置会使依赖旧源的审批或排练失效。
reader_safe是人工声明，白名单不提供自由文本语义防泄密保证，仍需审查。

## 多场景成章

先完成同章各场，不逐场ensemble-handoff冒充整章。spec中的scene_ids为真实ENS，顺序由本章方案确定；
expected_scene_ids可明确应有的场景ID。若scenes.json已登记该章场次，引擎额外核对完整有序清单；未登记时只能验证作者所选范围，不能知道是否少规划了一场。

```bash
python3 .agents/skills/novel-director/scripts/novel.py assembly-plan books/new-novel V01-C01 scene-selection.json
python3 scripts/studio.py assembly-packet ASM
python3 scripts/studio.py assembly-accept ASM --response .studio/narrator-response.json --receipt .studio/narrator-receipt.json
```

上例ASM必须替换为plan实际返回值。selection形状为`{"scene_ids":["实际ENS1","实际ENS2"]}`。
正式宿主使用Studio的assembly-packet/assembly-accept，复用人物委派的能力门槛与真实回执；
引擎novel.py的assembly-packet/assembly-submit保留给手工/合成/自备宿主适配器，不因source字符串就证明真实委派。
独立Director包不含Studio时，自备宿主也须实际核对相同的清洁输入/禁工具/分区和来源。
packet只含已完成候选、公开对白、时点/地点与安全文风；不含director_goal、其他角色私心或排练self_notes。
唯一narrator用独立chapter_compose上下文，返回：

```json
{"request_id":"当前包实际ID","sections":[{"ensemble_id":"实际ENS1","text":"该场完整候选正文"},{"ensemble_id":"实际ENS2","text":"该场完整候选正文"}],"transitions":["场间连接；可为空表示直接场景切分。"]}
```

核验场序、历史/POV、摘要、漏场和对白。脚本不能证明行动或情绪已自然承接，整章审稿需读原文，核对场前状态—选择—场后余波与转场。
submit只创建一个drafted Run，沿用审稿、定向修改、作者批准；不是发布。重放拒绝。异常中断可能留未发布Run或attempt，先核对后处理，不盲目清锁或覆盖。

## 跨章回顾

```bash
python3 .agents/skills/novel-director/scripts/novel.py arc-packet books/new-novel --chapter V01-C01 --chapter V01-C02 --chapter V01-C03 --out arc-packet.json
python3 .agents/skills/novel-director/scripts/novel.py arc-review books/new-novel arc-packet.json arc-report.json
```

需要3–5个有序连续且已有manuscript文件的章节，只读取所选原文，不加载未来谜底。默认100000字符预算，可设1–200000；超额拒绝，不裁章，接收复用相同预算。
报告含request_id、reviewer_type（self_review/cross_review/human）、issues与summary_citations。
每个issue含classification（error/risk/taste）、explanation、citations；每条citation含chapter_id、quote，重复引文须start/end，可附sha256。
summary_citations必须逐章举证。跨章矛盾通常须至少引用发生冲突的两章；只有一处证据时说明缺少哪一环，不能把推断写成确定错误。
脚本核验引文与版本，审查者负责论证；不会自动修改Run、正文或Canon。原文重复仅作risk提示，允许有意复沓；不生成客观文学总分。

同章稍后关系结果不进入writer记忆；场景之间只传该实例在前场真实观察到的排练记忆，不从当章最终关系台账倒灌。
