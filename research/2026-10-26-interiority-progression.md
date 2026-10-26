# 自述、练习与晋升铺垫：局部增补研究

## sources

核对日2026-10-26。当前源为Director0.12.0/Studio0.4.2，前轮192项通过；这只是基线。当前引擎已有可选pov_interior、scene.allow_pov_interior和visible_events投影；场景成稿开启时也只提供当前POV、读者可见且该POV在观察者内的事件内心。整章accepted_events继续只含id/actor_id/speech/result，不含内心字段；整章可沿用已完成场景正文中获许可的内心，而非自动收到原始内心。使用不可公开knowledge时不能提供pov_interior。resolve看不到private_intent/pov_interior，成稿不能据此新造事实；自由文本仍须语义审查。

既有15部专题继续按原采集/审读范围使用，每部20章以上，不新增小说采集或冒称本轮重读301章。已用reference_library.validate_file重新核对2026-10-22-reference-study-samples.json及原始source/study SHA，15份细读档案结构一致；阶段声明全部15个专题ID并绑定原索引/相邻原始记录，不以元数据验证替代实际历史语义阅读。本轮完整读《诛仙》20章既有章析，重点复核平台9、10、16、17及技巧/局限；复读《天下长宁》既有章析的训练后应用与历史题材方法。仙侠原章来源https://book.qq.com/book-read/750056/10 、https://book.qq.com/book-read/750056/17；本轮没有重新采集这两章原正文。行业背景重新打开中国作家网2026-01-09文章https://www.chinawriter.com.cn/n1/2026/0108/c404027-40641641.html ，是专家年度观察，非实时订阅榜。

本轮实际打开一手写作文章：Brandon Sanderson，Sanderson’s Second Law，https://www.brandonsanderson.com/blogs/blog/sandersons-second-law ，强调能力的限制、成本与人物选择，且作者声明它并非绝对法则；Patricia C. Wrede，Show AND Tell，https://pcwrede.com/pcw-wp/show-and-tell/ ，讨论现场展开与概述的不同作用。这些是创作实践，非统计实验，不推出固定修炼字数/章数或每次晋升必须遭重伤。

## findings

原《诛仙》章析9—10将练习目标、反震与耗时、相反法门的困惑、分期测试、局部进展及人物自责联系；16—17将私授条件、比较之痛、继续练习与器物一次轻动相接。可抽象为：初始能力/所知限制→具体尝试→感觉与结果反馈→理解/选择调整→有限结果。此为局部方法迁移，不复制功法、名词、情节或声音；原作有全知说明，不能因此允许本工具越过限知。一次器物动了不证明全部进阶能力已经成熟，人物自责不等于客观资质判断。

四维设计判断：世界维度让法门来源、门槛、资源、时间、身体及禁忌影响可做之事；情节维度让练习暴露具体难点、改变选择或积累可回溯条件，突破后有有限验证与余波；人物维度自述呈现当前理解、欲望、怀疑、误解和取舍，不由作者宣布人格成长；情感维度保留希望/挫败、关系压力与认知改变，也允许平静练习和暂不领悟。《天下长宁》章析7的交替换弩显示训练应用，但不能据此泛推任何训练有效；历史/日常章节不硬加仙侠境界。

铺垫落在已显露的难点、方法、限制或小结果，后续真正调用/重释才构成回收。沿用现有setups的plant/reinforce/payoff、partial/full及prior真实引文；读者已见不等于人物知道。重复稳定训练可以带节点概述；首次关键方法、卡关调整、越门槛与后果应在有关章卡中明确展开任务，不把每一章写成同一训练流程。

## comparisons

重新打开wgwtest/novel-writing的README、novel-writing/SKILL.md、references/dialogue-and-behavior.md及tests/test_dialogue_behavior_contract.py：https://github.com/wgwtest/novel-writing 。其实际方法区分有作用的行为与纯手续，长篇按当前所需资料加载；测试主要核文件路由/文字契约，不证明生成质量。本会话此前已核CONTRIBUTING与包检查维护约定，本轮未执行对方代码或评价持续维护质量。

重新打开JeroTan/novel-writer-english的README、根SKILL.md、src/skills/writing-techniques/emotional-interiority/SKILL.md、package.json、CHANGELOG.md及test/mcp-story-library.test.js：https://github.com/JeroTan/novel-writer-english 。情绪内观参考要求关键事件有内在回应，对本轮有用；它也倾向把情绪转成身体反馈。本工具不采纳情绪命名一律差或每个重要事件必须补即时内心的绝对写法，保护延后反应、直述和无许可内心的场景。package为1.5.1，最新有日期CHANGELOG条目为1.5.0/2026-08-09，MCP/库存测试不是小说效果评测；未运行。两次猜错子Skill路径返回404，已改读真实根SKILL和准确情绪子Skill，不把404当已读。仅迁移抽象方法，不复制代码或长段文本。

## limits

本轮方案以独立参考、实际提示和现有细节/铺垫契约接入，不新增境界计分器、自动升级、章卡数据Schema或所有题材强制任务。主会话只把本场允许知道和展示的规则/前证投影给对应角色，不转发完整未来回收表。演员不自行成功，裁定不越既定规则，compose不借扩写加新尝试/能力/内心或改变已采纳对白；材料不够回上游。

仅源码交付，无小说定稿/批准、安装或网站同步。源/提示变化会使旧生产依赖按既有机制过期，需重建，不补签。文学判断依赖具体书稿和作者，本轮模型审查与测试不保证自然度，也不等于外部读者验收。
