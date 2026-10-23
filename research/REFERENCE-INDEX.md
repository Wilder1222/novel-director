# 当前15部作品细读索引

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

## 逐部细读

- [剑来：20个完整平台章六维、跨章链与6技巧](reading/jianlai.md)
- [天下长宁：20个完整平台章六维、跨章链与6技巧](reading/tianxia-changning.md)
- [雪中悍刀行：20个完整平台章六维、跨章链与6技巧](reading/xuezhong.md)
- [逆天邪神：20个完整平台章六维、跨章链与6技巧](reading/nitian.md)
- [永夜君王：20个完整平台章六维、跨章链与6技巧](reading/yongye.md)
- [一剑独尊：20个完整平台章六维、跨章链与6技巧](reading/yijian.md)
- [锦衣春秋：20个完整平台章六维、跨章链与6技巧](reading/jinyi.md)
- [日月风华：20个完整平台章六维、跨章链与6技巧](reading/riyue.md)
- [剑仙在此：20个完整平台章六维、跨章链与6技巧](reading/jianxian.md)
- [微微一笑很倾城：21个完整平台章六维、跨章链与6技巧](reading/weiwei.md)
- [苟在女魔头身边偷偷修炼：20个完整平台章六维、跨章链与6技巧](reading/gounv.md)
- [诛仙：20个完整平台章六维、跨章链与6技巧](reading/zhuxian.md)
- [青山：20个完整平台章六维、跨章链与6技巧](reading/qingshan.md)
- [俗仙：20个完整平台章六维、跨章链与6技巧](reading/suxian.md)
- [十日终焉：20个完整平台章六维、跨章链与6技巧](reading/shiri-zhongyan.md)

[90项技巧总索引](TECHNIQUE-INDEX.md) · [实际来源/分析绑定清单](samples/2026-10-22-reference-study-samples.json) · [采集与方法报告](2026-10-22-v0.11-library.md) · [指定作品状态与版本限制](REQUESTED-REFERENCES.md)

```bash
python3 .agents/skills/novel-director/scripts/novel.py reference-read --book shiri-zhongyan --chapter 20
python3 .agents/skills/novel-director/scripts/novel.py reference-techniques --book shiri-zhongyan
python3 .agents/skills/novel-director/scripts/novel.py reference-search --genre xianxia --status collected
python3 .agents/skills/novel-director/scripts/novel.py reference-show yongye
python3 .agents/skills/novel-director/scripts/novel.py reference-techniques --book gounv --dimension character
python3 .agents/skills/novel-director/scripts/novel.py reference-read --book weiwei --chapter 26
python3 .agents/skills/novel-director/scripts/novel.py reference-check
```

其他6份旧采集/受阻元数据不计入上述细读：最强狂兵、我有一座冒险屋、红楼梦原50章/回保留原范围，红楼梦不称热门网文；陆少两平台、罪恶调查局保留原缺口。旧十日终焉50条目录证据仍原样保留，不计入新增20章第三方同站正文。
