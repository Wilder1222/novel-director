# V0.6 证据驱动的定向重写

## 何时使用

已有本章候选稿与引文核验通过的审稿，要针对一组具体问题修订。不是从零写章，不是自动把整本书重写一遍。宿主/作者提供替换文字；脚本不调用LLM、不训练模型、不联网。

## 三层完成标准

1. **机械正确**：补丁基于原稿，坐标/原文/哈希一致；每个目标都有修改；范围外一字不动；精确保护段不受触碰。
2. **语义验收声明**：每个问题的解决判断及六类保全判断有前后原文引用。脚本只核验引用，判断可能仍然错误。
3. **发表决定**：新的整章审稿 + 定向修订验收 + 用户显式批准后方可发布；不把改字量、平均分或引用存在当作品质量证明。

## 先处理最大问题，再决定局部改哪里

先区分确定矛盾、可能问题、审美选择。不要为满足模板而消灭作者有意保留的沉默、含混、平静结尾。优先因果/世界规则，再人物动机与关系，最后词句。所有BLOCKING必须纳入计划；其他问题允许分批，但原审稿与未选项索引保留在计划中。

对每个问题填写：读者当前会怎样理解；作者原本希望怎样理解；哪一个行动、信息或关系需要变化；允许修改的精确原文；这次不能损失什么。目标不能仅写‘更精彩’或‘更有文学性’。

## 六维保全是待评问题，不是六个分数

- world：保留规则的限制与代价，不把hypothesis改成confirmed；调查资料应影响选择，不堆术语。
- plot：保留本章要推进的问题；信息、认知与关系进展都可有效，不强制每章惊天反转。
- characters：人物愿望、压力下选择和能力边界不因润色而被抹平；不要给人人加口癖。
- emotion：具体行为促成有限信任。共同风险不是相爱的自动证明，未来婚礼也不是此刻感情事实。
- mystery：线索仍可见、误导有依据、不偷泄后文谜底；保留句子只是一层辅助，不证明周围上下文没泄底。
- prose：观察视角、潜台词、中文节奏与人物声音；有意直白或留白须保留设计理由。

## CLI步骤

```bash
python3 .agents/skills/novel-director/scripts/novel.py run-start PROJECT V01-C01
python3 .agents/skills/novel-director/scripts/novel.py run-submit PROJECT RUN before.md
python3 .agents/skills/novel-director/scripts/novel.py run-review PROJECT RUN initial-review.json
python3 .agents/skills/novel-director/scripts/novel.py revision-plan PROJECT RUN revision-spec.json
python3 .agents/skills/novel-director/scripts/novel.py revision-apply PROJECT RUN REV patch.json
python3 .agents/skills/novel-director/scripts/novel.py revision-check PROJECT RUN
python3 .agents/skills/novel-director/scripts/novel.py revision-check PROJECT RUN --assessment assessment.json
python3 .agents/skills/novel-director/scripts/novel.py run-review PROJECT RUN new-full-review.json
# 只有真实用户明确批准这份正文时才执行后两步
python3 .agents/skills/novel-director/scripts/novel.py run-approve PROJECT RUN --by AUTHOR
python3 .agents/skills/novel-director/scripts/novel.py run-publish PROJECT RUN
```

`revision-check`只读检查无报告时正常返回JSON（退出0），但revision_gate_ready=false；脚本调用者必须读取这个字段，不能把退出0当作质量通过。输入错误/过期/越界返回退出2。--assessment会在Run内保存验收版本，但不是批准。

## revision-spec.json

```json
{
  "writer_id": "actual-writer-label",
  "tasks": [{
    "issue_index": 0,
    "goal": "补出有限协作的行动依据",
    "acceptance": "尚未完全相信，却愿意先核实一条证据",
    "scope": [{"quote": "需要改写的原文。"}]
  }],
  "preserve": [{
    "id": "key-clue", "reason": "保留伏笔",
    "citation": {"quote": "必须保留的原文。"}
  }],
  "quality_checks": [
    {"id": "world", "criterion": "不新增穿越能力"},
    {"id": "plot", "criterion": "调查任务继续推进"},
    {"id": "characters", "criterion": "两人能力保持有限"},
    {"id": "emotion", "criterion": "仅建立一次有限合作"},
    {"id": "mystery", "criterion": "不泄露钥匙谜底"},
    {"id": "prose", "criterion": "保留克制的中文声音"}
  ]
}
```

issue_index为原审稿issues数组0起始索引。运行生成I001等task_id。重复句必须加start/end；所有位置均是UTF-8解码后的Unicode code points，不是UTF-8字节或JavaScript UTF-16长度。索引均指**修订前原文**，后续补丁不能使用已替换后的偏移。

## patch.json

每个edit包含task_id/start/end/old/new，根字段还有plan_sha256。全部替换先核验后组合，允许删除（new为空），不允许old为空或纯零宽插入。插入用替换一个非空锚段并在new里保留该锚段。任何改动与preserve区间相交即拒绝，包括‘删掉再补回’。有意需要修改保护段时应由作者重新设定范围，而不是关闭校验。

补丁必须覆盖所有已选任务；重叠补丁、虚假old、无实际变化、越界、多余键、过期计划、超过4MiB的记录会被拒绝。大规模结构重写不适合拆成海量局部补丁，应新建Run、重新设计章卡。

## assessment.json

根字段：reviewer_type（human/agent）、reviewer_id、origin、before_sha256、after_sha256、plan_sha256、results、quality_checks。

results每项：task_id、verdict（resolved/partially_resolved/unresolved/uncertain）、rationale、before_citations、after_citations。

quality_checks每项：id（上述六类）、verdict（preserved/regressed/uncertain）、rationale、before_citations、after_citations。

每组前后citations均引用相应正文中的真实句子，可加start/end/sha256消歧。缺席类判断引用相关完整场景后说明局限，不能编造一条‘不存在的话’作为证据。只有关键词还在不证明信息仍被公平呈现。

origin=external_review/self_review/synthetic_test。当前同一助手自行重写再评，必须写self_review，不能仅换角色名冒充外部独立意见。测试数据写synthetic_test。只有external_review、全部任务resolved且六维preserved，才满足额外修订门槛。此字段与reviewer_id仍是声明，不是身份鉴权；人类或独立模型也可能判断错误。

## 持久化与版本

计划、补丁、原稿/新稿、验收记录分别保存。应用后candidate-v1仍在，candidate-v2是待审稿；旧批准失效。计划绑定来源签名、原审稿与原文摘要；审稿或设定变化则拒绝复用旧计划。批准后不得替换验收；发布前重验。普通run-submit不能绕过已绑定的定向修订，如要自由改写必须另开Run。

项目Schema保持0.4；复用V0.5的基础Run契约版本，不因包版本升级让既有未绑定定向修订的V0.5 Run自动失效。新增的revision schema为0.6。V0.4旧Run仍遵从V0.5迁移要求。

## 上下文与安全边界

plan.json是作者专用，可能含原审稿中的后文信息；writer-brief.md不自动复制原审稿评论、canon引文或全书影响图，只列当前作者明示的目标、范围与保护项。目标里仍可能有人手写入剧透，应再检查，不能宣称自动完成语义防剧透。

不接受符号链接、内部路径穿越或可执行代码；本地单写者流程，不提供跨进程事务锁或远程授权。哈希是意外漂移检测，不是抵抗有本地写权限攻击者的签名。发布后要修改作品应新建Run；revision-check用于发表前验收，发表引起项目签名变化后不复用旧Run重新验收。
