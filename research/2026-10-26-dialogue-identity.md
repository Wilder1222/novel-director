# 关系、任务与人物声线：对白局部研究

## sources
日期2026-10-26。当前源码Director0.12.0/Studio0.4.2、语料1.3.0/48例；前一任务181项全量与修例后25项回归已经实际通过，本轮不追认新测试结果。已核actor实际上有自己的profile、goal、relationship_view、observations，resolve只有可观察提案，不具备人物完整私密档案。

本轮重新打开Open University的Start writing fiction 1.5： https://www.open.edu/openlearn/history-the-arts/creative-writing/start-writing-fiction/content-section-1.5 ，其公开课程要求了解人物说话方式如何随情境、心境与意图变化，亦强调人物矛盾。重新核作者一手说明Patricia C. Wrede，Dialog（2010-05-05），https://pcwrede.com/pcw-wp/dialog/ 。两者是教学/创作实践，不是长篇自然度实验。

本会话同日已核近期行业页（2026-01-09）https://www.chinawriter.com.cn/n1/2026/0108/c404027-40641641.html ，仅作题材及综合影响力背景，不改称即时订阅榜。本轮只读既有research/reading/tianxia-changning.md与jianlai.md相关章析/方法，各自原20章采集与细读证据沿用原记录，不新增作品、不冒称重新阅读全文或重读301章。此前十部专题原采集与审查记录仍按原范围有效。

## findings
已证事实：课程把稳定人物描写与随情境改变的说话方式并列；Wrede说明小说选择性组织口语，节奏和具体说法构成差别。设计推断：性格/常态声线是起点，当前对象、关系看法、任务、所见回应及身体情绪决定这一轮怎样说；口头禅是可用表达习惯，使用、变体或收住均可能成立，不能用出现次数鉴定一致性。

四维迁移：世界维度让身份/礼仪/资源和身体限制约束语体，不从职位自动推断真实亲疏；情节维度以本人当前goal与对方回应决定追问、协商、回避或拒绝，不让角色按主线秘密交代信息；人物维度使性格、价值观、词汇/句式和口头禅相互支持，内向不等同永远结巴，强硬也可对特定人请求；情感维度保留单向关系、误读与未解决的关系余波，不给另一方补好感。

既有章析对照：《剑来》care-beneath-bluster（第4章P34、第8章P101）讨论口头姿态与具体关系下动作的差异；《天下长宁》care-reinterprets-cold-behavior（第2章P38、第3章P48/P53）讨论同一行为在保护分工中的重释。仅借已有章析的方法边界，不复制情节、不推断全文口头禅分布。原创练习：同一谨慎检修员分别向熟悉搭档和正式接班人请求等十分钟，保留同一请求事实与任务，按既有关系调整称呼和分寸，不自动给第二人套用亲昵口癖。

## comparisons
本轮重新打开两个真实开源参考：wgwtest/novel-writing的novel-writing/references/dialogue-and-behavior.md，https://raw.githubusercontent.com/wgwtest/novel-writing/main/novel-writing/references/dialogue-and-behavior.md ，以交流目标、对象、策略变化组织行为；JeroTan/novel-writer-english的src/skills/writing-techniques/punctuation-emotional-effect/SKILL.md，https://raw.githubusercontent.com/JeroTan/novel-writer-english/main/src/skills/writing-techniques/punctuation-emotional-effect/SKILL.md ，要求表达手段与人物声线、当前压力相合。

两库README、根SKILL、测试和维护文件已在本会话上一任务同日只读核对：前者tests/test_dialogue_behavior_contract.py主要断言规则文本/路由存在，CONTRIBUTING要求规则示例文档同步；后者package.json为1.5.1，CHANGELOG最新有日期版本1.5.0（2026-08-09），test/mcp-story-library.test.js偏文件/MCP流程。均未运行对方测试，不将源码存在或版本记录当写作效果/维护质量证明。只迁移语境诊断思想，不复制代码、独特文风或原文长段。

## limits
方案推荐向人物profile添加可选speech_style，承载稳定性格、常态语气、语言习惯及带when/avoid_when的catchphrases，仍由主会话整理候选来源。不增加固定每句输出的分析字段，不自动生成或确认人物设定；旧voice字符串和实例goal/relationship_view继续生效，缺信息保留未知。

必须保护自己的关系看法和习惯不外泄。不能为了narrator核人设把私密profile全发给resolve或compose；人物选择在speech中表达了什么，成稿才保留什么，语气/动作仍经裁定。编辑核对由主会话按当场授权提供安全对照，不能用私密总账替代。零命中仍查关系/任务/声线和口癖机械性，允许不用口癖、刻意克制或有依据的反差；自动规则不判定这些语义是否优秀。
