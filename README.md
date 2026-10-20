# Novel Director

中文长篇小说创作 Skill 与 Codex 协作入口。

- 创作引擎：novel-director **0.7.0**。
- 自然语言入口：novel-studio / Codex workspace **0.1.0**。
- 写作分工：主线一个 Agent、核心角色各一个 Agent、普通人物共享执行者但隔离角色上下文。
- 支持大纲、角色与世界设定、时间线、记忆检索、审稿引文、定向修订、候选稿和显式审批。

## 发布范围

本包保留两个 Skill、引擎脚本、角色配置、参考指南、空白项目模板及随 Skill 提供的工程演示。
**不包含作者 books/ 中的小说项目、草稿、故事圣经、私人运行记录、调用回执或凭据。**
工程演示及角色配置中的姓名、行动和“秘密”是测试样例，不是正式小说，也不是真实用户秘密。

这次是公开发布整理，不是新的引擎版本。上游源码摘要记录于 PUBLIC-SOURCE-MANIFEST.json。
原开发包中的作品样例、历史测试日志和研究交付报告没有复制到此公开包。
没有擅自添加开源许可证；公开可见不等于授予任意再许可权限。

## 目录

```text
.agents/skills/novel-director/   当前创作引擎和 Skill
.agents/skills/novel-studio/     自然语言入口
.codex/agents/                  示例角色配置
scripts/studio.py              任务归档与角色交接
AGENTS.md                      主会话协作约定
templates/studio/              空白本地状态模板
docs/CODEX-HOST.md              原宿主接入边界说明
```

## 初始化本地创作空间

使用 Python 3.11 或更高版本。以下命令仅适用于新克隆的源码目录；已有 .studio/ 或 books/new-novel 时不要覆盖：

```bash
python3 .agents/skills/novel-director/scripts/novel.py --version
python3 .agents/skills/novel-director/scripts/novel.py skillcheck
python3 .agents/skills/novel-director/scripts/novel.py init books/new-novel --title "未命名小说"
python3 -c "import shutil; shutil.copytree('templates/studio', '.studio')"
python3 scripts/studio.py doctor
```

books/ 和 .studio/ 均被忽略，不会自动进入公开仓库。模板自带的年份、停留时长等参数只是起始模板，并非作者已确认设定。实际写作前按作品调整。角色 TOML 和 agent-map 同样是示例。

在支持该配置的 Codex 中打开目录，让主会话读取 AGENTS.md 和 $novel-studio，先验证真实子代理能力、输入隔离和权限，再开始创作。

## 能力边界

脚本不调用模型、不自动生成小说，不会因运行 doctor 就证明真实多 Agent 已执行。模型生成和委派依赖实际宿主。
同模型自评不能冒充独立读者；候选稿不自动变成正式设定；站点任务服务和自动连续写作执行器尚未在此包中实现。

本次发布检查与此前完整测试区别记录于 docs/PUBLICATION-CHECK.md；不要把历史的测试通过数量冒充本次结果。
