# 当前公开交付核验

当前版本为Novel Director0.11.0 / Studio0.4.1。仓库只交付创作工具、空白模板、原创方法分析及必要来源元数据；作者小说、books/、.studio/、runs/、receipts/、本机dist/和完整参考正文均不进入Git提交。

## 来源与版本

当前来源清单为根目录`RELEASE-MANIFEST.json`，由`scripts/release.py`生成并核对。`ENGINE-PROVENANCE.json`和`PUBLIC-SOURCE-MANIFEST.json`保留最初来源档案的真实口径，不能替代当前清单。

当前参考库15部、301条章析、51条跨章链、90张技巧卡，406项当前分析复核。各章有独立语义阅读和不同实际执行者复核记录，不将结构检查当作外部读者或文学质量保证。《十日终焉》采用明确标注的同站第三方前20章快照，转载授权和官方逐字一致未认证；完整正文只供私有研究，不发布。范围及版差见[当前索引](../research/REFERENCE-INDEX.md)。

## 字节与公开范围

- 原研究记录和portable study的JSON以原字节SHA绑定，Git属性与发布器均保留其实际字节；普通文本统一LF。提交前核Git index/tree的实际blob与声明摘要，并从实际tree导出运行读取，避免本机通过但检出后失效。
- 按发布清单明确暂存源码，不用无范围的`git add -A`。核对私有路径、常见密钥模式及所有301份完整参考body的精确字节排除；模式和精确匹配不构成完全敏感信息或版权认证。
- 本机既有167项回归已实际通过；具体发布还核实际Git tree测试、三当前ZIP完整性、细读原SHA及解包运行、原生安装和新宿主发现。每项以实际执行记录为准，不能只拿旧基线代替本次运输和安装核验。
- 2026-10-23已实际删除本工具旧0.8/0.10发布目录及ZIP、旧0.9来源备份共9项；当前软件只保留0.11.0，未创建新备份。研究证据与故事时间线不属于软件备份，遵循[保留规则](RELEASE-POLICY.md)。

## 可重做的离线检查

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 .agents/skills/novel-director/scripts/novel.py reference-check
python -X utf8 .agents/skills/novel-director/scripts/novel.py reference-read --book shiri-zhongyan --chapter 20
python -X utf8 .agents/skills/novel-director/scripts/novel.py reference-techniques --book shiri-zhongyan
```

章长默认在静态模板、动态生成与外部空白初始化中保持3000–6000 LN，剧情默认500–2500。源码和缓存通过结构核验不授权批准或发表作者小说；严格人物读取隔离仍需宿主实际能力证据。

## Git与安装终态

目标远端为`https://github.com/Wilder1222/novel-director.git`的`main`。实际推送成功须查询本地HEAD、origin/main和远端main一致；本文仅记录交付范围和核验入口，确切提交由Git记录提供。

本机插件来源为`C:/Users/ww/plugins/novel-director`，当前缓存为`C:/Users/ww/.codex/plugins/cache/personal/novel-director/0.11.0`。刷新使用原生`codex plugin add novel-director@personal --json`，随后核对来源/缓存/候选包与提交来源，实际读取新参考并用新宿主发现两项Skill。安装成功、模型文学评价与作者批准分别记录。
