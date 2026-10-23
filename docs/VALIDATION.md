# v0.8 验证记录

2026-10-21。本文件记录本轮实际执行，不沿用原归档的历史测试数量。

## 研究与方案

research/2026-10-21-v0.8.md、research/2026-10-21-v0.8-plan.md 在首次代码编辑前写入；覆盖两类小说案例、作者访谈、原论文、两个真实开源Skill的定义/许可/测试/维护状态。

## 已执行的检查

- 先建立29项测试：13项既有行为通过，2项行为失败、14项缺接口错误，之后全部29项通过。
- 独立只读实现复核与自然请求前向验证；发现问题均先补可复现反例再修复，包括场次清单、时间解析、中断恢复、候选漂移、跨书同名ID、安装缓存与Windows junction。
- 两项Skill通过skill-creator quick_validate；引擎skillcheck通过。它们是结构校验，不是文学判断或官方skills-ref认证。
- 全量标准库测试：68项全部通过（2026-10-21，39.816秒，exit 0）；覆盖故障注入、精确引文、源版本、防泄露投影、审批失效、包排除及安装目录验证。Windows junction专项实际执行，未跳过。
- 离线演示生成两场完整合成排练、一个整章候选、逐章原文及跨章引文审查结果；source均标synthetic_test，0模型调用，不批准、不发布。
- 构建后的源码清单、ZIP内容及实际安装副本另行核对，不把源码测试等同于安装成功。

## 兼容与恢复

保留project0.1–0.4、ensemble0.7、Run0.5；无新文风文件时源签名和默认角色包保持旧结构。
整章交接用固定Run身份；初始化通过完整临时目录原子改名，故障后重试不会留下阻塞的半成品正式Run目录。
中断可保留.initializing或attempt记录，未自动删除；不会自行批准或发布。

## 宿主与文学边界

真实只读研究/审查的任务名：/root/fiction_research、/root/skills_research、/root/extension_design、/root/chapter_review、/root/skill_forward_test。
工具未提供独立host_thread_id，未捏造。审查属于同宿主模型，不是外部读者验收。
当前可不继承父聊天，但未取得禁用子代理文件工具的权限证据；严格人物执行仍受门槛阻断。
没有作者原小说，未执行《昨日归档》的真实作品回归，也未证明文学质量、读者接受或文风复现。

## 复跑

```bash
python3 -m unittest discover -s tests -v
python3 .agents/skills/novel-director/scripts/novel.py skillcheck
python3 scripts/studio.py doctor
python3 scripts/release.py verify
python3 scripts/demo.py <不存在的全新演示目录>
```

正文与审批仍按原始字节核验。仅发布用文本源码清单以utf8-lf兼容平台换行。
