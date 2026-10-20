# V0.2 角色在场、时空因果与物证台账

程序入口：`python3 scripts/novel.py validate <project>`。此模块由 `scripts/timeline_engine.py` 实现，是**明确登记数据的一致性编译器**，并非对小说进行自动真相推断。

## 角色与时间
- `characters.json.characters[]` 定义稳定的人物身份 `id`；同名不同历史版本或不同年龄仍然使用这一 `id`，不能把旅者和自然长大的自己合并成一个年龄记录。
- `presences.json.presences[]` 定义一段**在场实例**。`mode=native` 是该历史下自然生长的角色；`mode=traveler` 必须通过 `trip_id` 指向相匹配的穿越记录。
- `from_at` 与 `to_at` 均为虚构城市的当地 ISO 日期时刻，不带 `Z` 和 `+08:00`。
- `age_at_start` 对 native 根据该历史角色出生日期计算，对 traveler 根据 `trip.depart_at` 算出发时的肉身年龄。
- 示例：2041年自然成长的许知微为29岁；2032年出发并进入2041年的许知微仍为20岁。两者能在同一日期同场存在，必须通过不同在场实例标注。

## 历史与归档
- `versions.json` 是历史分支的父子树。`rewrites.json` 一条记录标识从父历史到子历史的明确改写，其中 `cause_event_id` 必须来源于父历史。
- `artifacts.json` 维护物件 origin + appearances + transfers。普通物件只能顺时间、同版本传递；物件跟随旅行使用 `traveler_carry`，受保护的归档媒介使用 `archival`；跨历史可见必须有对应的保护/运输机制。
- 物证为 `hypothesis/planned` 时依然需要自洽，但不等同于作者确认事实。

## 因果边
- `causal_edges.json.edges[]` 以事件 ID 而非纯文字建立因果关系。
- `ordinary` 因果在同一历史分支里按时间顺序推进；`time_travel` 需要 `via_trip`，并满足来源事件发生不晚于出发、目标事件发生不早于抵达；`bootstrap` 还要有 `loop_id`。
- 明确声明自举环仅生成 WARN，不能自动认为逻辑成立；未经说明的因果环为 ERROR。

## 限制
- 目前不模拟世界线整体重算，不预测某人是否会出生，也不能推导哲学悖论是否满足物理学。
- 物件跨版本显示路径检查的是明示边，不能判定复杂的多步连通；多步可达性列入下一版的深化任务。
- 只有作者明确要求才把 planned/hypothesis 提升为 confirmed。脚本绝不自动批准 Canon。
