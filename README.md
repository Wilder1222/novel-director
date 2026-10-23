# Novel Director

中文长篇小说创作工具：Director **0.11.0**，Studio **0.4.1**。作者以自然语言构思、规划、写候选、审稿和修改；主会话维护文件，唯一 narrator 与人物执行者通过有限信息包协作。

所有新任务采用[阶段作品与核验](.agents/skills/novel-director/references/staged-workflow.md)：按意图逐阶段交付真实作品、逐项证据和版本绑定核验，未通过或过期不能推进；作者批准独立保留。升级依据见[研究](research/2026-10-22-v0.9.md)与[方案](research/2026-10-22-v0.9-plan.md)。

[本版变化](docs/V0.11-CHANGELOG.md) · [实际验证与边界](docs/V0.11-VALIDATION.md)。离线阶段演示：`python scripts/stage_demo.py <不存在的新目录>`，结果明确标记为合成协议夹具。

[章/剧情硬范围与细节铺垫](.agents/skills/novel-director/references/writing-spec.md) · [36条原创反AI味案例与检查](.agents/skills/novel-director/references/prose-risks.md) · [当前作品细读与技巧索引](.agents/skills/novel-director/references/reference-library.md)。当前已达标作品及实际数量见索引；每部20–50章、至少20章完整模型细读并实际复核。新增五部的已完成与缺口见[指定参考进度](research/REQUESTED-REFERENCES.md)。模型复核不是外部读者验收。

当前每章硬范围按作者要求为 **3000–6000 LN**（标点空白不计），剧情默认500–2500；新章先规划具体章卡，再计数核验。

[开场与分卷结构](.agents/skills/novel-director/references/opening-volume-structure.md)：重大冲突开篇、随行动补因果，每卷目标与高潮兑现；称谓默认全名/已设昵称，情境对白在演员端执行并逐字按顺序保留采纳台词。

## 本版完成

- LF/CRLF兼容的源码校验与独立当前发布清单；保留历史来源。
- 公开标准库合成回归测试；默认项目不预设人物、年龄、年代或穿越上限。
- 按书注册核心人物、保存任务checkpoint并核对恢复状态。
- 经作者确认的文风/题材投影、多场景整章候选、3–5连续章的引文审查。
- 有证据、日期和本地配置指纹的宿主能力记录；不把read-only或提示词当硬隔离。
- 独立Skill、完整workspace与本地Codex插件包；安装代码与作者作品目录分离。

## 发布边界

本仓库只发布工具、空白模板及明确标识的合成工程演示，不发布作者作品。books/、.studio/、本地local_角色、凭据、数据库和构建目录均不进入发布包。
原始来源仍见ENGINE-PROVENANCE.json与PUBLIC-SOURCE-MANIFEST.json；它们是来源记录，本版不再宣称所有源码与原归档相同。软件交付遵循[只保留最新版本](docs/RELEASE-POLICY.md)规则，不创建旧版发布或安装备份。
当前内容见RELEASE-MANIFEST.json：文本源码以utf8-lf摘要，research/samples冻结采集记录保留原字节（utf8-lf+reference-bytes-v1），防止换行转换破坏来源链；小说原文、引文和审批仍按精确原始字节核验。
没有擅自添加开源许可证；公开可见不等于任意再许可。

## 初始化与使用

Python **3.11+**，无第三方运行依赖。Windows可将python3替换为`python -X utf8`。以下命令从仓库根执行：

```bash
python3 scripts/studio.py workspace-init
python3 scripts/studio.py doctor
python3 .agents/skills/novel-director/scripts/novel.py skillcheck
python3 -m unittest discover -s tests -v
```

workspace-init保留任何已有.studio，不覆盖作者书；没有本地工作区时创建books/new-novel和空白状态。
在支持该配置的Codex中读AGENTS.md与$novel-studio。人物按本书characters.json登记，再role-register；样例两位人物不是新书默认。
严格多角色写作还需按[宿主说明](docs/CODEX-HOST.md)验证实际清洁输入和权限。

独立Director Skill安装后，用实际Skill绝对路径调用其scripts/novel.py，项目参数指向作者书。
完整插件安装后，用工具根scripts/studio.py的绝对路径加`--workspace <作者目录>`；工具拒绝把安装目录或其子目录用作作者工作区。
Studio需要随完整workspace/插件提供的接线与模板，单独一个SKILL.md不能运行全流程。

## 参考入口

- [研究](research/2026-10-21-v0.8.md)与[先行实施方案](research/2026-10-21-v0.8-plan.md)
- [任务恢复与人物注册](docs/STUDIO-WORKFLOWS.md)
- [文风、整章与跨章契约](.agents/skills/novel-director/references/long-form-execution.md)
- [本版变化](docs/V0.11-CHANGELOG.md)与[验证结果](docs/V0.11-VALIDATION.md)
- [原公开版检查（历史）](docs/PUBLICATION-CHECK.md)

## 构建

```bash
python3 scripts/release.py refresh
python3 scripts/release.py verify
python3 scripts/release.py package
python3 scripts/release.py plugin
```

refresh只在审查有意变更后显式运行，不作为doctor遇错时自动修复。
package输出Director Skill和完整workspace ZIP；plugin输出含portable与Codex兼容manifest的本地插件目录/ZIP。
默认拒绝覆盖已有包。包内容来自源码白名单；额外的skills/从权威.agents/skills派生，构建时纳入当前清单，不手改投影。

## 能力限制

脚本不调用模型、不生成文学判断、不自动批准或发布。同宿主模型审查不是外部读者验收；测试数量不能证明小说优秀。
角色引擎当前支持第一人称/第三人称限知，不把全知叙述伪称已支持。多场景组装检查场序与对白，情绪、行动与转场仍需整章审稿。
宿主探针只是有来源的本地记录，不创建权限沙箱；缺乏真正禁工具条件时暂停严格人物委派。
本版不包含网站服务、后台自动连载执行器，也未对作者原小说进行真实作品验收。
