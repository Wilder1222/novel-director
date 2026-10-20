# 项目 JSON 状态文件说明（v0.1）

`novel.py` 是本项目的轻量确定性检查器，不是完整数据库或自动作者。

| 文件 | 根对象 | 核心字段 |
|---|---|---|
| project.json | object | schema_version, title, age_anchor_date, expected_ages, time_rules |
| characters.json | characters[] | id, name, birth_date, role, voice, motive |
| versions.json | versions[] | id, parent, status, description |
| trips.json | trips[] | id, history_id, traveler_id, depart_at, arrive_at, destination_exit_at, return_at, stay_hours |
| chapters.json | chapters[] | id, volume, number, pov, history_id, in_world_at, goal, conflict, change, summary, requires_prior_knowledge[] |
| clues.json | clues[] | id, setup_chapter, payoff_chapter, observable_evidence, plausible_misreading, truth |
| knowledge.json | knowledge[] | id, character_id, fact_id, learned_chapter, history_id |
| canon.json | facts[] | id, subject, predicate, value, status, history_id, source |
| events.json | events[] | id, history_id, at, actor_ids[], caused_by[], description |

时间表示为虚构中国城市当地时间，不带时区的 ISO `YYYY-MM-DDTHH:MM:SS`，不会默认为 UTC。日期采用 `YYYY-MM-DD`。`volume, number` 使用整数，按卷、章编号排序。历史版本 `H0`、`H1` 通过 `parent` 关联。

状态：confirmed = 作者已确认；planned = 尚未发布的工作方案；hypothesis = 角色或编辑推测。**绝不可根据模型自身输出擅自将 planned/hypothesis 改成 confirmed。**

## 使用命令

```bash
python3 scripts/novel.py init ./novel --title "小说名"
python3 scripts/novel.py validate ./novel
python3 scripts/novel.py context ./novel V01-C01
python3 scripts/novel.py status ./novel
```

`validate` 返回值：0 = 无结构错误（可有警告），1 = 发现结构错误，2 = 找不到请求章节/不允许覆盖等错误。`context` 给起草代理提供当前章、近期先前摘要、当前章可用线索和全球已确认事实；未主动加载未来全局真相。它无法自动阻止作者把未来剧透写在章节卡里。

### 数据迁移与回滚

建议版本控制所有 JSON/Markdown 文件。每次大幅修改先保存快照，生成变更提案并由作者审批。v0.1 尚未实现数据库事务、跨历史版本全链条自动重算、专业编辑软件集成或模型自动调用。
