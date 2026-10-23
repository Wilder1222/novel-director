# V0.5 · 剧情改动影响分析

执行：`python3 .agents/skills/novel-director/scripts/novel.py impact PROJECT --changed events:E-OLD-FIRE`。

节点使用 `文件类别:记录ID`，例如 `characters:chen-xu`、`world_rules:WR-01`、`chapters:V01-C04`。先检查真实ID，不自行猜测。可重复 `--changed` 指定多个变化来源。

系统读取各资料中已登记的类型化引用、causal_edges，以及可选的 dependency_links.json。可显式登记：

```json
{
  "links": [
    {
      "id": "DEP-01",
      "from": "events:E-OLD-FIRE",
      "to": "clues:CL-DATES",
      "reason": "仅示例：火灾日期一旦调整，日期物证需复核。采用前由作者确认。",
      "status": "planned"
    }
  ]
}
```

该例是写法演示，不能无授权添加到小说既定真相中。也可在记录中添加 `depends_on`，值为带类型ID数组。

报告区分 `declared_causal`（登记的因果关系）、`reference_dependency`（资料引用）、`declared_dependency`（显式维护依赖）。引用了角色的章节可能要重审，但并不必然重写；工具不会把关联关系当成物理因果。输出保留节点和路径中的 planned/hypothesis，不会自动提升为 confirmed。

未知改动节点报错。尚未登记的被引用对象进入 diagnostics，提醒作者补充或清理。`global` 是全局事实范围，不是缺失历史版本。图可含时间循环，遍历会终止，但终止不等于证明时间逻辑成立。

报告仅供主编/作者：可能含后续章与结局，不可直接作为当前章写作上下文。不做自然语言推断、最小修复搜索或完整平行世界模拟。每个目标显示一条最短路径示例，reachable_edges 保留范围内其余边。所有操作只读，无 canon 写入。
