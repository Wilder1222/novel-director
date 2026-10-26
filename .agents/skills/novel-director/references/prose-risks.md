# 反AI味：原创编辑案例与上下文复审

按[自述、练习与晋升铺垫](interiority-progression.md)规划有关章节：在章卡明确关键自省、具体尝试/反馈/调整、晋升前证/门槛与前后差异，用已有detail_requirements和setups登记过程/铺垫；重复稳定过程可概述，不强制每章修炼或突破，未知设定保持候选。人物/成稿只拿当前可知或可展示的材料，未来回收答案不下发。

用途是查空泛、重复和失真，保护作者文风；不输出AI率、不鉴定作者、不承诺规避检测。先读当前书已确认文风、POV和人物声音。
公共`assets/prose-risk-corpus.json`版本1.5.0有56条原创合成对照，前32条八类各4条，另4条补称呼与情境对白、6条补对白与行为联合表达、6条补对白语气节奏、4条补人物关系/任务与条件口头禅、4条补小说对白密度；八类为：空泛处境、情绪复述、重复解释、失准修饰、机械动作、无功能细节、统一升华、声音同质；其中声音同质23例、机械动作9例，其余各4例。
每条有context/bad/revision/why/preserves/exceptions/valid_example/cues/source；不是从小说摘句或轻改后冒称原创。
对白按[联合创作](dialogue-embodiment.md)核语气词/停顿、表情和动作与场景目标及情绪关系是否联动；不按数量打分。案例改词只用于未锁定草稿或显式修订，不能作为compose擅改speech的授权。
只按当前任务载入命中的公共规则卡，不必整库塞提示词。

## 先定位，再读实际上下文

确定性scan查有限字面线索、完整句/段重复，以及下述对白节奏线索，返回正文SHA、语料/保护/检查器/参数版本、准确范围/原句、stable finding ID。
命中不直接阻断，短句、少形容词、动作替代心理均非普遍优越；有意重复、口头禅、直接抒情、诗性含混、繁复文风、必要概述均可能合理。
例如“攥拳”不能为省字把两次动作合成一次，“我完全理解您的感受”不能擅删程度、敬意与人际表态。
改写不得暗添动作、物件、动机、时序、视角知识或确凿未来；已有信息不够时提缺口，不编细节填充。
工资“未领取”不能改成“已经损失”。语料preserves字段只是一项声明，独立审查仍须逐例比较。

零命中也须全章八类语境复审。flattened_voice要核情境需要却语句过平、人人相同的结巴/断续、重复是否承担强调或改口，以及无功能符号堆叠；不设配额，不从符号自动读心。克制、完整短答和稳定口吃可以成立。规则卡是当前语境下的编辑示例，不能把其中revision直接套给不同人物。
句子如果属于角色对白、引述、反讽、既有意象或作者确认文风，说明其具体作用后可合理保留。

新增三个内置规则均归flattened_voice：`dialogue_pause`定位省略号（…或三个以上ASCII句点）/破折号；`dialogue_restart`定位由标点分开的1–8汉字重复或同字连续三次以上；`dialogue_punctuation_stack`定位连续两个以上问叹符号。匹配配对的“”、直双引号、「」和『』，每一引语每类只定位第一处；原文及码点不归一化，不代表每次停顿都已标出。常规“爸爸”“人人”及单个叹号不产生这些线索。单引号、无引号、特殊嵌套、英文词重启或超出模式的改口仍须读全文；引号内也可能是物名/引文，允许false_positive。命中不是判错，合理结巴/重复可intentional保留。

editor packet的`dialogue_rhythm_rules`只解释实际命中的内置线索，类别说明与instructions仍要求零命中审查。三条ID与repeat_paragraph/repeat_sentence均为保留ID，书内entries不得抢用；如旧书内自定义ID冲突，应由主会话明确报告并另取ID，不自动改私有资料。protections可绑定这些内置规则，但保护仍不等于自动通过。

flattened_voice还须结合本人当前任务、单向关系看法、性格/价值、常态与当场语气、口头禅的使用/回避条件核称呼、分寸、句式和策略。对不同对象换语体不自动判人格改变；谨慎不必结巴，温和不必每次低声，未出现口头禅不判错。角色私密speech_style不自动投影给editor/narrator，主会话只提供当场安全对照；缺资料保留未知，不靠读心补齐。

## 实际产物与报告

按[小说对白密度](dialogue-density.md)从交流段→场景→整章核直接对白/概述、变化处反应与后果、时空/身体锚点及整体节奏。高密度或长独白有作用可保留，闲聊也可承载关系/氛围/趣味；不按比例/连续句数判错、不要求每句推进情节、不用逐句动作或随机插景凑平衡。问题须给实际交流范围、缺失作用和权限内修订方向；已采纳speech仍不得在compose为降密度删改、概述或拆串。当前没有数值密度分类器；零命中照样复审，缺对照保留不确定。

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
