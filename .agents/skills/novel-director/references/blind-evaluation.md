# V0.5 · 匿名对照与顺序偏差检查

## 用途

回答“同一评审者调换两段正文顺序后是否仍偏好同一份稿”。这不是自动客观文学评分器，也不是证明模型优于作者的工具。

准备同一任务、相同已确认设定、相近篇幅与写作资源下的两份候选稿。固定评价维度和用户意图，记录真实生成模型、版本和设置。若要做无Skill/仅记忆/完整Skill消融实验，需要分别生成候选，再两两比较；本版不自动生成这些实验稿。

```bash
python3 scripts/novel.py eval-create A.md B.md ./comparison --brief "两位20岁主角第一次合作，保持有限信任；不要提前揭开时间谜底。"
```

输出两轮独立材料，A/B位置交换。只给评审 `evaluator_packets/`，不要给 `private_manifest.json`；后者记录来源身份映射。每轮使用不同会话，避免第二轮看见前一轮答案。人为选择样本或文风差异仍会影响匿名性，不能把匿名标签当完全盲化。

## 结果格式

每条 judgment 绑定 requests.json 提供的 trial_id 和 packet_sha256。

```json
{
  "judgments": [
    {
      "reviewer_id": "editor-01",
      "reviewer_type": "human",
      "trial_id": "使用实际轮次ID",
      "packet_sha256": "使用实际包SHA256",
      "winner": "A",
      "rationale": "解释偏好，并说明仍存疑的问题。",
      "citations": [
        {"label": "A", "quote": "A稿实际存在的原文"},
        {"label": "B", "quote": "B稿实际存在的原文"}
      ]
    }
  ]
}
```

reviewer_type 为 human / model / synthetic_test。模型判断必须填写 model_id。winner 为 A/B/tie/abstain。除弃权外，必须引用两个样本；弃权仍须理由。同一评审者每轮只能一条记录。身份字符串是本地登记，不是认证。

```bash
python3 scripts/novel.py eval-report ./comparison results.json
```

## 解释输出

- `consistent_preference`：两个顺序都选同一候选身份。
- `position_inconsistent`：换序后选择改变，不能直接认定原来的胜者更好。
- `consistent_tie`：两轮都认为平局。
- `incomplete_pair` / `inconclusive`：缺轮次或弃权，不合并不同评审者凑成一对。

没有结果时明确返回 awaiting_external_judgments；不能捏造分数。synthetic_test 不计入真实效果，测试里的human字符串只测试分类分支，并不表示真正招募了读者。汇总不自动发布小说，不自动写入作者偏好。跨评审分歧不以简单均分掩盖。本版的AB/BA仅诊断顺序敏感性，不消除自偏好、长度偏好、措辞说服与来源识别等偏差。
