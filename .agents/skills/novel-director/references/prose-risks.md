# 反AI味：原创编辑案例与上下文复审

用途是查空泛、重复和失真，保护作者文风；不输出AI率、不鉴定作者、不承诺规避检测。先读当前书已确认文风、POV和人物声音。
公共`assets/prose-risk-corpus.json`有36条原创合成对照，前32条八类各4条，另4条补称呼与情境对白；八类为：空泛处境、情绪复述、重复解释、失准修饰、机械动作、无功能细节、统一升华、声音同质；其中声音同质8例，其余各4例。
每条有context/bad/revision/why/preserves/exceptions/valid_example/cues/source；不是从小说摘句或轻改后冒称原创。
只按当前任务载入命中的公共规则卡，不必整库塞提示词。

## 先定位，再读实际上下文

确定性scan只查有限字面线索、完整句/段重复，返回正文SHA、语料/保护/检查器/参数版本、准确范围/原句、stable finding ID。
命中不直接阻断，短句、少形容词、动作替代心理均非普遍优越；有意重复、口头禅、直接抒情、诗性含混、繁复文风、必要概述均可能合理。
例如“攥拳”不能为省字把两次动作合成一次，“我完全理解您的感受”不能擅删程度、敬意与人际表态。
改写不得暗添动作、物件、动机、时序、视角知识或确凿未来；已有信息不够时提缺口，不编细节填充。
工资“未领取”不能改成“已经损失”。语料preserves字段只是一项声明，独立审查仍须逐例比较。

零命中也须全章八类语境复审。规则卡是当前语境下的编辑示例，不能把其中revision直接套给不同人物。
句子如果属于角色对白、引述、反讽、既有意象或作者确认文风，说明其具体作用后可合理保留。

## 实际产物与报告

```bash
python3 .agents/skills/novel-director/scripts/novel.py prose-corpus-check BOOK
python3 .agents/skills/novel-director/scripts/novel.py prose-scan BOOK V01-C01 draft.md --out scan.json
python3 .agents/skills/novel-director/scripts/novel.py prose-packet BOOK V01-C01 draft.md --out editor-packet.json
python3 .agents/skills/novel-director/scripts/novel.py prose-report-check BOOK V01-C01 draft.md report.json
```

packet是editor-only，含当前全文、扫描、已安全投影的文风、命中公共卡；不是actor包。
报告形状：`{scan_id,categories:[{id,verdict,rationale,citations}],findings:[{id,disposition,rationale,citations}]}`。
categories精确覆盖八类，verdict为clear/needs_revision/uncertain；findings精确覆盖本次所有命中，
disposition为intentional/false_positive/needs_revision/uncertain。每项有具体理由和当前原文证据；线索证据至少完整包含命中。
`intentional/false_positive`允许保留，不能靠命中数判差；需改/不确定虽可保存审稿，但阻断出口。
需改项放入Run issue的`prose_targets:["category:ID","finding:ID"]`（只填实际相关ID），由审查者给severity，不自动把字面命中标MAJOR。
修改后须对新候选重扫、重审；“登记需改”不是问题已闭合。Run主报告用`prose_risks_review`承载上述对象。

已启用writing_spec的Run在start冻结公共/私有语料、保护、检查器和扫描参数；submit/review/阶段/approve/publish重核。
正文或这些依赖改版，旧报告不可沿用。draft/revision阶段另要求独立逐类/逐命中判断；editorial核完整Run报告。
结构和证据覆盖通过，不等于外部读者满意；宿主回执不认证身份。

## 书内扩展与保护

`prose-template BOOK`拒绝覆盖，创建`prose_risks.json:{schema_version:"1",entries:[],protections:[]}`。
主会话从作者自然语言整理当前书的原创案例，字段与公共案例相同；不自动挖掘私有书稿、上传或写入公共包。
仅字面cues，不执行用户正则/代码；合计最多512案例，256保护，正文最多200000码点、扫描最多256线索，超限明确失败不静默截断。
保护记录含id/chapter_id/rule_id/candidate_sha256/quote/start/end/reason/author_quote；author_quote须实际原话，不能模型自封确认。
精确匹配只在该正文与规则下标注protected_by，**仍须语境审查**，不是全局豁免。正文变化后保护失配，重新判断。
私有原案例/确认原话不自动投影到writer或editor，主会话仅提供当前安全语境说明；公共规则卡可按命中载入。
旧未配置writing_spec流程保持兼容，但不能称已通过本轮反AI味门槛。科幻、武侠、言情等检查侧重来自具体书，不强塞统一干净短句风格。
