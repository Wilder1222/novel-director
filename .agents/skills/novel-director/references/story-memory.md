# V0.3 中文长篇记忆引擎说明

## 命令

```bash
python3 .agents/skills/novel-director/scripts/novel.py memory-index /path/to/project
python3 .agents/skills/novel-director/scripts/novel.py memory-search /path/to/project "婚礼照片" --chapter V01-C45 --history H0 --pov xu-zhiwei
python3 .agents/skills/novel-director/scripts/novel.py context /path/to/project V01-C07 --budget 8000
# 只有明确以编辑/作者身份审稿，才可以显式查作者私有资料：
python3 .agents/skills/novel-director/scripts/novel.py memory-search /path/to/project "终局" --chapter V01-C01 --history H0 --pov chen-xu --mode editor --include-author-only
```

## 存储与上下文
- 已发布的 `manuscript/Vxx-Cxx.md` 将以约800字符分块进入索引，标记为 `approved`，只有其后的章节可以检索。它不会被误称为仍然只有章卡的规划事实。
- `memory_docs.json.memories[]` 可手工维护 `id`, `text`, `history_id`, `reveal_chapter`, `visibility`, `status`, `characters`, `allowed_povs`, `importance`。
- `visibility` 有 `reader`（读者已获知）、`writer_canon`（创作硬约束）、`pov_private`（仅特定视角）、`author_only`（幕后真相）。默认自建记忆为 `author_only`。
- 当 `status` 为 `hypothesis/inferred` 时，**writer 不会检索它**，即便章节已到。`planned` 允许作为标记为规划的上下文，不能当成已写事实。
- `clues.json` 的 `observable_evidence` 与 `truth` 记为不同条目。真相绝不因关键词命中而自动泄露；若要在当前章节正式回收，由章卡明确指示。
- 过滤顺序：作者私有 → 历史匹配 → POV → `reveal_chapter` → 章节限制 → 结果评分。权限不是根据语义模型预测，而是显式元数据控制。
- `.novel_memory.sqlite3` 为本地可重建缓存，不是作品的主 Canon 源。任何相关源文件变更导致签名失效，检索拒绝使用旧索引。
- 使用 stdlib SQLite 保存倒排索引；中文以双字与三字 n-gram 处理，不等同于专业中文分词/语义检索。后续可选 embedding，但也必须先做元数据强过滤。

## 情感铺垫的记忆设计
不要把“好感度 80”当人物情感。记忆记录应包括：当时看见了什么行为、人物如何理解、关系从什么状态变为怎样、下一章哪项冲突检验这份信任、证据来自哪个正式章节。主角不应突然知道未来自己婚礼的感受。

## 失败方式
- 若强规则和当前章卡已经超出上下文预算，`context` 拒绝删除核心规则并报错。
- 若索引过期，应重新运行 `memory-index`；不允许悄悄读取旧召回。
- 不能用检索得分代表文学质量或事实可信度；所有结果保留路径、版本、状态，以便审查。
