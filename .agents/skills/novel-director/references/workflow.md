# V0.5 Agent 角色路由、写作工作流、剧本转化与训练

该版本提供**可执行文件工作流**及 Agent 任务契约；外部宿主负责真正的大模型生成、联网研究、判断作品质量。内置脚本不连接模型、不自动后台工作。

V0.5新增引文、来源摘要与契约核验；旧Run需重新创建。审稿细则以 [evidence-review.md](evidence-review.md) 为准。

## 任务路由

```bash
python3 .agents/skills/novel-director/scripts/novel.py route /path/to/project --task outline
python3 .agents/skills/novel-director/scripts/novel.py route /path/to/project --task chapter
python3 .agents/skills/novel-director/scripts/novel.py route /path/to/project --task screenplay
```

路由读取 `agents/routes.json` 和 `agents/roles.json`，返回需要的专业角色、引用资料与输出物，而不是启动真实多个模型。宿主 Agent 按路由加载少量必要资料。

## 章节创作与人类批准

```bash
python3 .agents/skills/novel-director/scripts/novel.py run-start /path/to/project V01-C01
# 打开输出的 .novel_runs/<run_id>/contract.json，按契约撰写/通过宿主模型生成候选稿
python3 .agents/skills/novel-director/scripts/novel.py run-submit /path/to/project <run_id> /path/to/draft.md
# 编写带 evidence 解释及 citations 原文定位的 JSON 审稿意见，详见 evidence-review.md
python3 .agents/skills/novel-director/scripts/novel.py run-review /path/to/project <run_id> /path/to/review.json
python3 .agents/skills/novel-director/scripts/novel.py run-quality /path/to/project <run_id>
# 只有作者明确批准才能走下一步（CLI 的 --by 不是身份认证）
python3 .agents/skills/novel-director/scripts/novel.py run-approve /path/to/project <run_id> --by 作者
python3 .agents/skills/novel-director/scripts/novel.py run-publish /path/to/project <run_id>
```

- 不可发布未审批正文；提交新 candidate 会丢弃旧版审稿与批准。阻断问题必须修改并再次审稿。
- 修改 `project/characters/chapters/canon` 等源设定后，已有审批失效；需要重新创建工作流程。
- 已有正文默认拒绝覆盖；显式 `--replace` 且原文摘要未被其它人改动时，写备份到 `manuscript/.history/`。
- `.novel_runs` 可以审计工作版本，但不替代版本控制；本地用户有文件读写权限，不提供密码学签名或多用户权限系统。
- 发布正式正文**不自动把所有正文推断升级为 Canon**；创作档案需由作者另行批准更新。

## 剧本结构骨架

```bash
python3 .agents/skills/novel-director/scripts/novel.py screen-adapt /path/to/project --volume 1
```

输出 `adaptations/volume-1-skeleton.fountain`，取自 scene cards，场景行使用 Fountain 语法，角色名用 `@` 强制标为对白角色。它是**结构骨架**，不是直接可拍的最终剧本。不得直接把人物复杂心理和小说旁白当作动作指示。

## 写作专项训练

```bash
python3 .agents/skills/novel-director/scripts/novel.py practice-plan /path/to/project --focus emotion --chapter V01-C04 --save
python3 .agents/skills/novel-director/scripts/novel.py practice-record /path/to/project <exercise_id> /path/to/feedback.json
```

专项包括 `worldbuilding / plot / character / emotion / mystery / dialogue / screenplay`；对一个很小、很明确的技术进行独立练习、反馈和重写，再用不同情境复练。反馈不会自动训练模型或修改 Canon。

## 媒介改编注意

世界观、人物动机与关键事件可跨媒介复用，但小说的限知心理描写在剧本中须转为演员可表演的选择、动作、场景物证和有效对白。Fountain 源文件可以继续输送到下游分镜 Skill，但自动导出并不意味着角色资产/视频已经创建。


## V0.6增量
已绑定定向修订的Run，批准与发布会额外调用revision-check。必须完成前后验收；详见[directed-revision](directed-revision.md)。基础Run契约保持V0.5兼容，project schema无需迁移。
