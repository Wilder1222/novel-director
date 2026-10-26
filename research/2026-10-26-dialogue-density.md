# 小说对白密度与叙述组织：局部研究

## sources
日期2026-10-26。当前源码Director0.12.0/Studio0.4.2，语料1.4.0/52例，前任务189项完整回归为已核基线。本轮已核实际代码：actor按预排轮次提案，resolve可end_scene，compose及整章锁定已采纳speech的连续原串/顺序/次数；没有对白比例自动分类器，不能宣称已有。

本轮打开作者一手文章：Patricia C. Wrede，Show AND Tell，https://pcwrede.com/pcw-wp/show-and-tell/ ，讨论在故事中有选择地概述非关键事件、例行讨论和可预期决策；All together at once，https://pcwrede.com/pcw-wp/all-together-at-once/ ，讨论行动/描写/对白在叙事中的整体组织，允许对白成为优势手段，也反对用随机描写块拼接成小说。这是创作实践，不是小说对白比例实验，不能导出统一数值阈值。

既有近12个月行业语境来源仍为本会话已核的中国作家网/中华读书报2026-01-09页，https://www.chinawriter.com.cn/n1/2026/0108/c404027-40641641.html ，仅作综合影响力/题材背景。沿用research/reading/tianxia-changning.md与jianlai.md各原20章章析，复核方法范围，不新增采集或冒称本轮重读原小说；此前十部专题及301章总库仍按各自原证据范围表述。

## findings
已证事实：作者文章承认概述与现场展开各有用途，且对白、描写、行动不能简单分块堆放。设计推断：密度判断应看这一段交流的作用、读者能否定位人物与压力、重要变化是否有承接，以及整章是否单一模式；引号多或连续发言多不自动是错。直接对白适合决定、交锋、潜台词和独特声音，寒暄/手续/重复已知信息可选择概述，但日常闲聊也可能承担关系、氛围或趣味，不全删。

四维迁移：世界维度保留空间、时限、身体和物件条件，不用无关景物凑叙述；情节维度在选择/信息/关系变化处安排节拍，让重要变化落到人物回应和后果；人物维度保护发言者意图与自主权，不为降密度替角色删承诺或改选择；情感维度允许POV感受和沉默形成余波，但内心须已有权限，不句句贴情绪标签。

既有章析对照：《天下长宁》第16–17章在亲近闲谈与紧急号令之间切换，说明轻松交流与任务压力可改变叙述节奏；《剑来》care-beneath-bluster方法指出话语姿态与具体动作可共同体现关系。此处仅据原章析做局部推断，不统计全文对白比例，不把章析当本轮小说细读。原创练习：已知两人电话约定九点东门交接，未锁定草稿可概述约定，把直接对白留给当场是否延期的选择；不能提前写对方已同意。

## comparisons
本轮重开wgwtest/novel-writing的对白行为参考： https://raw.githubusercontent.com/wgwtest/novel-writing/main/novel-writing/references/dialogue-and-behavior.md 。它以交流单元审人物目标和策略，允许快速无标签对答，并明确动作密度不是质量目标；可迁移语境检查，不能变成每句必须推动情节。JeroTan/novel-writer-english的标点技巧定义： https://raw.githubusercontent.com/JeroTan/novel-writer-english/main/src/skills/writing-techniques/punctuation-emotional-effect/SKILL.md ，支持按声线/场景控制停顿与强度；它并不提供小说对白比例证据，不能拿标点规则替代场景组织。

本会话同日此前已读两库README/主SKILL、wgwtest的tests/test_dialogue_behavior_contract.py与CONTRIBUTING、JeroTan的package.json/CHANGELOG和test/mcp-story-library.test.js：前者偏规则路由文本断言；后者偏MCP/文件流程，package1.5.1与最近有日期CHANGELOG1.5.0（2026-08-09）不同。均未执行对方代码、不据其测试证明小说效果或维护质量，不复制其代码、长段文字或在世作者独特文风。

## limits
实现应先在场景卡判断哪些交流现场展开、哪些既定过程可概述；演员不为填满轮次轮流解释，resolve仅在真实场景目的完成且无关键未决时可提前结束。成稿用已许可材料编织小说叙述，整章回查节奏，不能靠随机插景/动作降低表面比例。

已采纳speech不能在compose压缩成间接引语或删改，必须回场景设计/新排练或显式修订；摘要只用于未锁定且有事实依据的材料。没有自动阈值或质量保证，零字面命中也要语境审查，定位问题须说明哪段交流缺失何种作用、影响什么、怎样在权限内修改。模型审查、结构测试与外部读者/作者验收分开，本轮不写小说或自动发布。
