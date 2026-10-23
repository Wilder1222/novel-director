# 热门作品参考：采集、细读与技巧索引

作者当前要求每部实际采集20–50章、至少20章完整细读；基础专题至少10部、以历史/玄幻/仙侠为主。schema2拒绝19或51章，同书跨平台版次不能充多部或拼数；旧schema1仅保留原50章证据范围。正常公开完整正文才计数，目录、公告、锁章、预览和不可可靠解读正文均不计，不绕过访问限制。

每章有事件、人物、情感、细节、铺垫、承接六字段，以及两处不同正文段8–12字符短锚。技巧覆盖world/plot/character/emotion/detail/setup，各有方法、前提、局限、原创练习及章段出处。作者作话、网页噪音和叙述插话分开，不能混成故事证据；人物所知、叙述者所知与读者所知不混用。采集、语义阅读、复核、作者认可分别记录；未读后续仅标待回收，不据全书记忆补结局。

权威源是research/samples当前清单及其source_record、study_record绑定，运行scripts/build_reference_library.py生成按书投影。内容、身份、URL、短锚或计数元数据改变使旧复核失效；SHA是完整性检查，不认证来源身份或文学真理。完整版权正文仅在私有研究任务，不进公共包；公开内容为少量短锚、原创分析和方法出处。检索时只加载目标书，reading_focus方向不冒充已验证方法。

当前excluded_authors含天蚕土豆，sample/catalog/search/show/study入口均核作者，换ID/混摘要不能绕过；旧无排除政策样本兼容，不追认其为当前采用。研究阶段须声明实际reference_books并绑定reference_samples及完整档案。作者小说与软件发布边界遵循现有流程。

## 当前专题

截至2026-10-23，当前15部不同作品完成301个完整公开平台正文槽位的采集与模型细读，形成301条逐章六维分析、51条跨章变化链、90张技巧卡；不同实际执行者对当前payload完成406项复核，无分析未决项。模型阅读与同模型复核不是外部读者验收或作者批准。

题材分布：历史3部、玄幻6部、仙侠4部、言情1部、悬疑1部。官网累计点击、推荐、收藏与作者指定是不同选用依据，不称实时榜位。开篇取样、平台可访问性和作者重叠影响代表性，不能据此推断畅销因果。

原10部专题中的《元尊》已按作者“不要天蚕土豆的书”退出当前源、索引与交付投影，由《永夜君王》20章替换。额外完成并复核的指定参考逐部加入当前专题，不覆盖原9书已核原记录。未完成作品不充数。

《微微一笑很倾城》采用平台1、2、3、5—14、19—26共21槽位，覆盖Part1—20；20/21是Part15上下接续，不称21个独立Part或连续平台1—20。《诛仙》若列入表中，采用QQ750056平台2—21，对应故事1—20；平台1序章排除，不拼起点或纸质版。

《十日终焉》采用无忧书城同站前20章网页工具快照；非官方校定、转载授权未认证，首章人数等异文保留，不与番茄或纸书混合。全文只私有，方法仅对本20章负责。

|ID|作品 / 作者|研究题材|完整采集 / 模型细读|技巧|
|---|---|---|---|---|
|jianlai|《剑来》 / 烽火戏诸侯|仙侠|20 / 20|6|
|tianxia-changning|《天下长宁》 / 知白|历史|20 / 20|6|
|xuezhong|《雪中悍刀行》 / 烽火戏诸侯|玄幻|20 / 20|6|
|nitian|《逆天邪神》 / 火星引力|玄幻|20 / 20|6|
|yongye|《永夜君王》 / 烟雨江南|玄幻|20 / 20|6|
|yijian|《一剑独尊》 / 青鸾峰上|玄幻|20 / 20|6|
|jinyi|《锦衣春秋》 / 沙漠|历史|20 / 20|6|
|riyue|《日月风华》 / 沙漠|历史|20 / 20|6|
|jianxian|《剑仙在此》 / 乱世狂刀|玄幻|20 / 20|6|
|weiwei|《微微一笑很倾城》 / 顾漫|言情|21 / 21|6|
|gounv|《苟在女魔头身边偷偷修炼》 / 怕辣的红椒|仙侠|20 / 20|6|
|zhuxian|《诛仙》 / 萧鼎|仙侠|20 / 20|6|
|qingshan|《青山》 / 会说话的肘子|玄幻|20 / 20|6|
|suxian|《俗仙》 / 流浪的蛤蟆|仙侠|20 / 20|6|
|shiri-zhongyan|《十日终焉》 / 杀虫队队员|悬疑|20 / 20|6|

## 按需读取

```bash
python3 .agents/skills/novel-director/scripts/novel.py reference-read --book shiri-zhongyan --chapter 20
python3 .agents/skills/novel-director/scripts/novel.py reference-techniques --book shiri-zhongyan
python3 .agents/skills/novel-director/scripts/novel.py reference-search --genre xianxia --status collected
python3 .agents/skills/novel-director/scripts/novel.py reference-show yongye
python3 .agents/skills/novel-director/scripts/novel.py reference-techniques --book gounv --dimension character
python3 .agents/skills/novel-director/scripts/novel.py reference-read --book weiwei --chapter 26
python3 .agents/skills/novel-director/scripts/novel.py reference-check
```

指定作品状态与版本限制见完整workspace的research/REQUESTED-REFERENCES.md；其他旧元数据单列，不冒充当前细读。
