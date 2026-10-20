# 结构化创作交付契约

所有 JSON 与 `manuscript` 正文分开保存。没有得到作者批准的草稿/猜测不更新 `confirmed`。

## 世界观规则（`world_rules.json.rules[]`）

- `id, rule, constraint_key?, value?, cost, dramatic_function, status, source?`。
- 规则应该能回答：“这项规则妨碍了谁、迫使他付出什么、如何被读者观察到？”
- `constraint_key` 与 `project.time_rules` 对齐时，冲突必须报错。
- 科幻与玄幻的特殊规则不能成为万能解题钥匙；现实题材的法律、制度等事实须有现实研究证据。

## 故事单元（`story_units.json.units[]`）

- `id, volume, first_chapter, last_chapter, goal, opposition, answer, consequence, new_question, status`。
- 每个单元必须有具体的阶段性答案和实际后果。不能只问“神秘人是谁”，到单元末仍仅问“更神秘的人是谁”。
- 场景之间优先用“因此/但是”而不是“然后”连接。

## 场景卡（`scenes.json.scenes[]`）

- `id, chapter_id, order, slugline, in_world_at, history_id, goal, conflict, turn, action, dialogue?`。
- 内部诊断可补 `value_before, value_after, intentional_stasis`；绝非要求每场必须正负翻转，安静场景同样可以合法存在。
- 剧本导出时 `slugline` 使用 Fountain `INT./EXT.` 格式。小说风格/内心思考不能直接冒充可拍动作。

## 情感关系节点（`relationships.json.moments[]`）

- `id, chapter_id, pair_ids[2], from_state, to_state, trigger_action, cost, consequence, status`。
- 情绪链强调“可观察行动”与“人物解读”。极端状态跳跃产生提醒，不机械禁止灵感和戏剧性加速。
- 陈叙与许知微：初见防备 → 有限合作 → 风险共担 → 初步互信 → 被隐瞒的信息伤害 → 修复或决裂。关系与案件同步互相改变。

## 章节写作契约（`.novel_runs/<run>/contract.json`）

- 最少包含章节 ID、POV、历史、事件时点、目标、冲突、选择、变化、允许本章出现的线索 ID。
- `chapter-writer` 只能写候选稿；`continuity-auditor` 先核对确定性事实，`development-editor` 在写作评分卡中举证问题。
- 初稿被审稿时应保留文体、信息节奏与中国生活的具体细节，不只调整生硬字数。

## 审稿报告（V0.5 JSON）

必须分别提供 evidence（解释）和 citations（真实原文）。完整格式、字符范围与SHA绑定见 [evidence-review.md](evidence-review.md)。以下quote只是格式示意，实际提交必须取自当前候选稿：

```json
{
  "reviewer_type": "agent",
  "issues": [],
  "scores": {
    "characters": {
      "score": 3,
      "evidence": "主角通过暂缓行动体现谨慎；解释仍需人工判断。",
      "citations": [{"source": "candidate", "quote": "她没有答应。"}]
    }
  }
}
```

分数0~5。确定性结构错误可标BLOCKING并阻止发布；其他分数供作者参考。引用存在并不自动证明评价正确。无问题也需提供summary_citations，不能用空报告通过审批。
