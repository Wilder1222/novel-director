#!/usr/bin/env python3
"""Novel Director: offline project scaffolding, deterministic audits and spoiler-safe context.

Standard-library only. Does not call an LLM, alter drafts, or approve canon.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from timeline_engine import audit_timeline
from story_memory import build as build_memory, search as search_memory, scoped_context, stale as memory_stale, DATABASE as MEMORY_DATABASE
import creative_workflow as flow
from screenplay_handoff import export as export_screenplay
from narrative_audit import validate as narrative_audit
from writing_coach import create as create_exercise, record as record_exercise
from agent_router import route as route_agent
from evidence_audit import verify_review, read_utf8
from revision_impact import analyze as analyze_impact
from blind_evaluation import create as create_evaluation, summarize as summarize_evaluation

FILES = ("project", "characters", "versions", "trips", "chapters", "clues", "knowledge", "canon", "events")


def read_data(path: Path, issues: list):
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            issues.append(("ERROR", "ROOT_TYPE", path.name, "文件根节点必须为 JSON object"))
            return {}
        return result
    except FileNotFoundError:
        issues.append(("ERROR", "FILE_MISSING", path.name, "缺少项目数据文件"))
    except (ValueError, UnicodeError) as exc:
        issues.append(("ERROR", "JSON_INVALID", path.name, str(exc)))
    return {}


def index(items, key, location, issues):
    result = {}
    if not isinstance(items, list):
        issues.append(("ERROR", "COLLECTION_TYPE", location, "字段必须是数组"))
        return result
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(("ERROR", "ITEM_TYPE", f"{location}[{i}]", "数组成员必须是对象"))
            continue
        value = item.get(key)
        if not isinstance(value, str) or not value:
            issues.append(("ERROR", "ID_MISSING", f"{location}[{i}]", f"缺少 {key}"))
        elif value in result:
            issues.append(("ERROR", "ID_DUPLICATE", f"{location}[{i}]", value))
        else:
            result[value] = item
    return result


def parse_date(value, where, issues):
    try:
        return dt.date.fromisoformat(value)
    except (ValueError, TypeError):
        issues.append(("ERROR", "DATE_INVALID", where, str(value)))
        return None


def parse_time(value, where, issues):
    try:
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("时间必须包含 ISO 日期与 T 分隔的钟点")
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            raise ValueError("本项目采用虚构城市当地时间，不接受含时区的时间戳")
        return parsed
    except (ValueError, TypeError) as exc:
        issues.append(("ERROR", "TIME_INVALID", where, f"{value}: {exc}"))
        return None


def age_at(birth: dt.date, at: dt.date) -> int:
    return at.year - birth.year - ((at.month, at.day) < (birth.month, birth.day))


def load_project(path: Path, issues: list):
    return {key: read_data(path / f"{key}.json", issues) for key in FILES}


def audit(path: Path):
    issues = []
    data = load_project(path, issues)
    p = data["project"]
    if p.get("schema_version") not in ("0.1", "0.2", "0.3", "0.4"):
        issues.append(("ERROR", "SCHEMA_VERSION", "project.json", "支持的 schema_version 为 0.1~0.4"))
    characters = index(data["characters"].get("characters", []), "id", "characters", issues)
    versions = index(data["versions"].get("versions", []), "id", "versions", issues)
    trips = index(data["trips"].get("trips", []), "id", "trips", issues)
    chapters = index(data["chapters"].get("chapters", []), "id", "chapters", issues)
    clues = index(data["clues"].get("clues", []), "id", "clues", issues)
    facts = index(data["canon"].get("facts", []), "id", "facts", issues)
    events = index(data["events"].get("events", []), "id", "events", issues)
    knowledge = index(data["knowledge"].get("knowledge", []), "id", "knowledge", issues)
    chapter_order = {}
    anchor = parse_date(p.get("age_anchor_date", "2032-10-20"), "project.age_anchor_date", issues)
    for cid, ch in characters.items():
        bd = parse_date(ch.get("birth_date"), f"characters.{cid}.birth_date", issues)
        expected = p.get("expected_ages", {}).get(cid)
        if expected is not None and bd and anchor and age_at(bd, anchor) != expected:
            issues.append(("ERROR", "AGE_MISMATCH", cid, f"锚点年龄应为 {expected}，实际 {age_at(bd, anchor)}"))
    for vid, v in versions.items():
        parent = v.get("parent")
        if parent is not None and parent not in versions:
            issues.append(("ERROR", "VERSION_PARENT_UNKNOWN", vid, str(parent)))
    for vid in versions:
        ancestors = set()
        cursor = vid
        while cursor is not None and cursor in versions:
            if cursor in ancestors:
                issues.append(("ERROR", "VERSION_CYCLE", vid, "历史版本父节点构成循环"))
                break
            ancestors.add(cursor)
            cursor = versions[cursor].get("parent")
    max_stay = p.get("time_rules", {}).get("max_stay_hours", 72)
    if not isinstance(max_stay, (int, float)) or isinstance(max_stay, bool) or max_stay <= 0:
        issues.append(("ERROR", "STAY_CONFIG_INVALID", "project.time_rules", "max_stay_hours 必须是正数"))
        max_stay = 72
    for tid, trip in trips.items():
        if trip.get("traveler_id") not in characters:
            issues.append(("ERROR", "TRAVELER_UNKNOWN", tid, str(trip.get("traveler_id"))))
        if trip.get("history_id") not in versions:
            issues.append(("ERROR", "TRIP_HISTORY_UNKNOWN", tid, str(trip.get("history_id"))))
        a = parse_time(trip.get("depart_at"), f"trips.{tid}.depart_at", issues)
        b = parse_time(trip.get("arrive_at"), f"trips.{tid}.arrive_at", issues)
        c = parse_time(trip.get("return_at"), f"trips.{tid}.return_at", issues)
        hours = trip.get("stay_hours")
        if not isinstance(hours, (float, int)) or isinstance(hours, bool) or hours <= 0:
            issues.append(("ERROR", "STAY_INVALID", tid, "stay_hours 必须为正数"))
            continue
        if hours > max_stay:
            issues.append(("ERROR", "STAY_LIMIT", tid, f"{hours}h 超过 {max_stay}h 的上限"))
        if a and c and abs((c - a).total_seconds() / 3600 - hours) > 1 / 60:
            issues.append(("ERROR", "RETURN_CLOCK", tid, "出发与回归的原时间线流逝时间不等于主观停留时长"))
        if b and trip.get("destination_exit_at"):
            d = parse_time(trip["destination_exit_at"], f"trips.{tid}.destination_exit_at", issues)
            if d and abs((d - b).total_seconds() / 3600 - hours) > 1 / 60:
                issues.append(("ERROR", "DESTINATION_CLOCK", tid, "目的时间线停留时长不一致"))
    seen_positions = {}
    for chid, chapter in chapters.items():
        key = (chapter.get("volume"), chapter.get("number"))
        if key in seen_positions:
            issues.append(("ERROR", "CHAPTER_DUPLICATE_POSITION", chid, f"与 {seen_positions[key]} 冲突"))
        seen_positions[key] = chid
        if not isinstance(key[0], int) or not isinstance(key[1], int):
            issues.append(("ERROR", "CHAPTER_POSITION", chid, "volume/number 必须为整数"))
        else:
            chapter_order[chid] = key
        if chapter.get("pov") not in characters:
            issues.append(("ERROR", "POV_UNKNOWN", chid, str(chapter.get("pov"))))
        if chapter.get("history_id") not in versions:
            issues.append(("ERROR", "CHAPTER_HISTORY_UNKNOWN", chid, str(chapter.get("history_id"))))
        when = parse_time(chapter.get("in_world_at"), f"chapters.{chid}.in_world_at", issues)
        # Do not mark a time traveler's pre-birth presence as impossible.
        if when and chapter.get("pov") in characters:
            born = parse_date(characters[chapter["pov"]].get("birth_date"), f"characters.{chapter['pov']}.birth_date", issues)
            if born and when.date() < born:
                allowed = False
                for t in trips.values():
                    if t.get("traveler_id") != chapter["pov"] or t.get("history_id") != chapter.get("history_id"):
                        continue
                    try:
                        arrival = dt.datetime.fromisoformat(t["arrive_at"])
                        end = dt.datetime.fromisoformat(t["destination_exit_at"])
                        if arrival <= when <= end:
                            allowed = True
                            break
                    except (ValueError, TypeError, KeyError):
                        continue
                if not allowed:
                    issues.append(("ERROR", "PREBIRTH_WITHOUT_TRIP", chid, "人物出生之前的场景未找到覆盖该时间的穿越记录"))
        if not chapter.get("goal") or not chapter.get("conflict") or not chapter.get("change"):
            issues.append(("WARN", "CHAPTER_CARD_INCOMPLETE", chid, "建议填写目标、冲突、变化"))
    for eid, event in events.items():
        if event.get("history_id") not in versions:
            issues.append(("ERROR", "EVENT_HISTORY_UNKNOWN", eid, str(event.get("history_id"))))
        parse_time(event.get("at"), f"events.{eid}.at", issues)
        for actor in event.get("actor_ids", []):
            if actor not in characters:
                issues.append(("ERROR", "EVENT_ACTOR_UNKNOWN", eid, actor))
        for cause in event.get("caused_by", []):
            if cause not in events:
                issues.append(("ERROR", "EVENT_CAUSE_UNKNOWN", eid, cause))
            else:
                previous = parse_time(events[cause].get("at"), f"events.{cause}.at", issues)
                current = parse_time(event.get("at"), f"events.{eid}.at", issues)
                if previous and current and previous > current:
                    if event.get("causality") != "cross_time" or event.get("via_trip") not in trips:
                        issues.append(("ERROR", "CAUSAL_TIME_ORDER", eid, f"原因事件 {cause} 晚于后果；若为跨时因果必须标注 causality=cross_time 与有效 via_trip"))
    for fid, fact in facts.items():
        if fact.get("status") not in ("confirmed", "planned", "hypothesis"):
            issues.append(("ERROR", "CANON_STATUS_INVALID", fid, "应为 confirmed/planned/hypothesis"))
        if fact.get("history_id") not in versions and fact.get("history_id") != "global":
            issues.append(("ERROR", "CANON_HISTORY_UNKNOWN", fid, str(fact.get("history_id"))))
        if fact.get("status") == "confirmed" and not fact.get("source"):
            issues.append(("ERROR", "CANON_SOURCE_MISSING", fid, "确认事实必须有来源"))
    for clue_id, clue in clues.items():
        setup = clue.get("setup_chapter")
        payoff = clue.get("payoff_chapter")
        if setup not in chapters:
            issues.append(("ERROR", "CLUE_SETUP_UNKNOWN", clue_id, str(setup)))
        if payoff and payoff not in chapters:
            issues.append(("ERROR", "CLUE_PAYOFF_UNKNOWN", clue_id, str(payoff)))
        if setup in chapter_order and payoff in chapter_order and chapter_order[payoff] < chapter_order[setup]:
            issues.append(("ERROR", "CLUE_EARLY_PAYOFF", clue_id, "伏笔先回收，后埋设"))
        if payoff is None:
            issues.append(("WARN", "CLUE_OPEN", clue_id, "伏笔尚无计划回收章节"))
    knowledge_by_person_fact = {}
    for kid, entry in knowledge.items():
        c, f, from_ch = entry.get("character_id"), entry.get("fact_id"), entry.get("learned_chapter")
        if c not in characters:
            issues.append(("ERROR", "KNOWLEDGE_CHARACTER_UNKNOWN", kid, str(c)))
        if f not in facts:
            issues.append(("ERROR", "KNOWLEDGE_FACT_UNKNOWN", kid, str(f)))
        if from_ch not in chapters:
            issues.append(("ERROR", "KNOWLEDGE_CHAPTER_UNKNOWN", kid, str(from_ch)))
        if c and f and from_ch in chapter_order:
            knowledge_by_person_fact.setdefault((c, f), []).append((chapter_order[from_ch], entry.get("history_id"), entry.get("retained_across_histories", False)))
        if entry.get("history_id") not in versions:
            issues.append(("ERROR", "KNOWLEDGE_HISTORY_UNKNOWN", kid, str(entry.get("history_id"))))
    for chid, chapter in chapters.items():
        for fid in chapter.get("requires_prior_knowledge", []):
            known = knowledge_by_person_fact.get((chapter.get("pov"), fid), [])
            if chid in chapter_order and not any(order < chapter_order[chid] and (history == chapter.get("history_id") or retained) for order, history, retained in known):
                issues.append(("ERROR", "KNOWLEDGE_LEAK", chid, f"{chapter.get('pov')} 此章开场不应提前知道或跨版本获知 {fid}"))
    issues.extend(audit_timeline(path, data))
    issues.extend(narrative_audit(path, data))
    return issues, data


def cmd_validate(args):
    path = Path(args.project).expanduser().resolve()
    issues, data = audit(path)
    errors = [x for x in issues if x[0] == "ERROR"]
    warnings = [x for x in issues if x[0] == "WARN"]
    print(f"Novel Director 项目审校 | {path}")
    print(f"章节 {len(data['chapters'].get('chapters', []))} | 时间旅行 {len(data['trips'].get('trips', []))} | 伏笔 {len(data['clues'].get('clues', []))}")
    for sev, code, source, note in issues:
        print(f"{sev:<5} {code:<28} {source}: {note}")
    print(f"结果：{len(errors)} 个错误，{len(warnings)} 个警告。结构检查不等于文学质量评审。")
    return 1 if errors else 0


def cmd_migrate(args):
    """Non-destructive copy migration: never overwrites the source project."""
    source=Path(args.source).expanduser().resolve()
    target=Path(args.target).expanduser().resolve()
    if not source.is_dir():
        print('源项目不存在',file=sys.stderr);return 2
    if target.exists():
        print('迁移目标已经存在，拒绝覆盖',file=sys.stderr);return 2
    if source==target or source in target.parents:
        print('迁移目标不能位于原项目内部',file=sys.stderr);return 2
    try:
        src_ver=read_data(source/'project.json',[]).get('schema_version','unknown')
        if src_ver not in ('0.1','0.2','0.3','0.4'):
            raise ValueError('不支持的旧数据结构版本：'+str(src_ver))
        shutil.copytree(source,target,ignore=shutil.ignore_patterns('.novel_memory.sqlite3','.novel_runs','__pycache__'))
        additions={'presences':'presences','artifacts':'artifacts','rewrites':'rewrites',
                   'causal_edges':'edges','memory_docs':'memories','scenes':'scenes',
                   'world_rules':'rules','story_units':'units','relationships':'moments'}
        for fname,key in additions.items():
            p=target/f'{fname}.json'
            if not p.exists():p.write_text(json.dumps({key:[]},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        p=target/'project.json';project=json.loads(p.read_text(encoding='utf8'))
        project['schema_version']='0.4'
        p.write_text(json.dumps(project,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        receipt={'source_schema':src_ver,'target_schema':'0.4','source':str(source),
                 'note':'迁移只复制并补充结构，不推断新Canon；旧源项目没有被修改。'}
        (target/'migration-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        errors,_=audit(target)
        print(json.dumps({'target':str(target),'old_schema':src_ver,'new_schema':'0.4',
                          'errors':[x[1] for x in errors if x[0]=='ERROR'],
                          'warnings':[x[1] for x in errors if x[0]=='WARN']},ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError) as e:
        print(f'迁移失败：{e}',file=sys.stderr)
        return 2


def cmd_init(args):
    base = Path(__file__).resolve().parents[1] / "assets" / "project-template"
    dest = Path(args.project).expanduser().resolve()
    if dest.exists():
        print(f"拒绝覆盖已有路径：{dest}", file=sys.stderr)
        return 2
    shutil.copytree(base, dest)
    p = json.loads((dest / "project.json").read_text(encoding="utf-8"))
    p["title"] = args.title
    (dest / "project.json").write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"新项目已创建：{dest}（未生成小说正文）")
    return 0


def cmd_context(args):
    path = Path(args.project).expanduser().resolve()
    issues, data = audit(path)
    if any(x[0] == "ERROR" for x in issues):
        print("项目存在结构错误；请先运行 validate 修复。", file=sys.stderr)
        return 1
    chapters = {ch["id"]: ch for ch in data["chapters"].get("chapters", [])}
    ch = chapters.get(args.chapter)
    if not ch:
        print(f"找不到章节 {args.chapter}", file=sys.stderr)
        return 2
    number = (ch["volume"], ch["number"])
    prev = sorted([x for x in chapters.values() if (x["volume"], x["number"]) < number], key=lambda x: (x["volume"], x["number"]))[-3:]
    person = next(x for x in data["characters"].get("characters", []) if x["id"] == ch["pov"])
    revealed = []
    for clue in data["clues"].get("clues", []):
        if clue.get("setup_chapter") == args.chapter:
            revealed.append({"id": clue["id"], "function": "plant", "observable_evidence": clue.get("observable_evidence")})
        if clue.get("payoff_chapter") == args.chapter:
            revealed.append({"id": clue["id"], "function": "payoff", "truth": clue.get("truth")})
    output = {
        "notice": "Drafter context. Do not access future chapters or author-only truth files without task justification.",
        "title": data["project"].get("title"),
        "style_file": "style.md",
        "fixed_rules": data["project"].get("time_rules", {}),
        "current_chapter": ch,
        "viewpoint_character": person,
        "recent_prior_chapter_summaries": [{"id":x["id"], "summary":x.get("summary", "")} for x in prev],
        "current_chapter_clues": revealed,
        "confirmed_global_facts": [x for x in data["canon"].get("facts", []) if x.get("status") == "confirmed" and x.get("history_id") == "global"],
    }
    # Preserve mandatory data before optional, query-retrieved memory. If the caller's
    # context budget is too small for hard rules, fail rather than silently omitting them.
    minimum=len(json.dumps(output,ensure_ascii=False))
    budget=getattr(args,"budget",8000)
    if budget < minimum:
        print(f"上下文预算 {budget} 小于硬约束和本章计划 {minimum} 字符，拒绝裁掉关键事实。",file=sys.stderr)
        return 3
    if (path/MEMORY_DATABASE).exists():
        if memory_stale(path):
            output["memory_warning"]="本地记忆索引过期，请运行 memory-index；本次未使用过期检索"
        else:
            scoped=scoped_context(path,args.chapter,ch['history_id'],ch['pov'],
                                  ' '.join(str(ch.get(x,'')) for x in ('title','goal','conflict','summary')),
                                  budget=budget-minimum,limit=8)
            output['related_memory']=scoped
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def cmd_memory_index(args):
    path=Path(args.project).expanduser().resolve()
    try:
        print(json.dumps(build_memory(path),ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError) as e:
        print(f'索引失败：{e}',file=sys.stderr)
        return 1


def cmd_memory_search(args):
    path=Path(args.project).expanduser().resolve()
    try:
        result=search_memory(path,args.query,args.chapter,args.history,args.pov,
                             limit=args.limit,mode=args.mode,include_author=args.include_author_only)
        print(json.dumps({'hits':result,'count':len(result)},ensure_ascii=False,indent=2))
        return 0
    except (ValueError,RuntimeError,FileNotFoundError) as e:
        print(f'检索失败：{e}',file=sys.stderr)
        return 2


def cmd_workflow(args):
    project=Path(args.project).expanduser().resolve()
    try:
        if args.command=='run-start':result=flow.start(project,args.chapter)
        elif args.command=='run-submit':result=flow.submit(project,args.run_id,Path(args.draft))
        elif args.command=='run-review':result=flow.review(project,args.run_id,Path(args.review))
        elif args.command=='run-approve':result=flow.approve(project,args.run_id,args.by)
        elif args.command=='run-publish':result=flow.publish(project,args.run_id,replace=args.replace)
        elif args.command=='run-status':result=flow.status(project,args.run_id)
        elif args.command=='run-quality':result=flow.quality_report(project,args.run_id)
        elif args.command=='screen-adapt':result=export_screenplay(project,args.volume,Path(args.out) if args.out else None)
        elif args.command=='practice-plan':result=create_exercise(project,args.focus,args.chapter,save=args.save)
        elif args.command=='practice-record':result=record_exercise(project,args.exercise_id,Path(args.feedback))
        elif args.command=='route':result=route_agent(args.task)
        else:raise ValueError('unknown workflow command')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,KeyError,FileExistsError,FileNotFoundError,PermissionError,UnicodeError,OSError) as e:
        print(f'操作被拒绝：{e}',file=sys.stderr)
        return 2


def cmd_status(args):
    path = Path(args.project).expanduser().resolve()
    issues, data = audit(path)
    for key, field in (("chapters", "chapters"), ("characters", "characters"), ("versions", "versions"), ("trips", "trips"), ("clues", "clues"), ("events", "events")):
        print(f"{key}: {len(data[key].get(field, []))}")
    print(f"review: {sum(x[0]=='ERROR' for x in issues)} errors, {sum(x[0]=='WARN' for x in issues)} warnings")
    return 0


def cmd_skillcheck(args):
    root = Path(__file__).resolve().parents[1]
    path = root / "SKILL.md"
    source = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", source, re.S)
    if not match:
        print("ERROR: YAML frontmatter missing")
        return 1
    block = match.group(1)
    name = re.search(r"^name:\s*(.+)$", block, re.M)
    desc = re.search(r"^description:\s*(.+)$", block, re.M)
    if not name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name.group(1).strip()) or name.group(1).strip() != root.name:
        print("ERROR: invalid skill name")
        return 1
    if not desc or not (1 <= len(desc.group(1).strip()) <= 1024):
        print("ERROR: missing or invalid description")
        return 1
    for relative in ("references/craft.md", "references/learning.md", "references/time-travel.md", "references/development-research-protocol.md", "references/story-memory.md", "references/temporal-ledger.md", "references/workflow.md", "references/output-contracts.md", "agents/routes.json", "agents/roles.json", "assets/project-template/project.json", "references/evidence-review.md", "references/revision-impact.md", "references/blind-evaluation.md", "references/craft-lab.md", "scripts/evidence_audit.py", "scripts/revision_impact.py", "scripts/blind_evaluation.py", "scripts/directed_revision.py", "references/directed-revision.md", "references/revision-learning.md", "assets/revision-spec-example.json", "scripts/ensemble_runtime.py", "references/ensemble-writing.md", "references/ensemble-host.md", "agents/narrator.md", "agents/core-character-template.md", "agents/ordinary-cast.md"):
        if not (root / relative).is_file():
            print(f"ERROR: missing {relative}")
            return 1
    print(f"Skill metadata and required resources: PASS ({root.name}); not an official skills-ref validation")
    return 0


def cmd_v05(args):
    try:
        if args.command == 'review-check':
            report = json.loads(read_utf8(Path(args.review))[0])
            flow._validate_review(report)
            checked, audit = verify_review(Path(args.project).resolve(), Path(args.draft), report)
            result = {'audit': audit, 'normalized_review': checked}
        elif args.command == 'impact':
            result = analyze_impact(Path(args.project).resolve(), args.changed)
        elif args.command == 'eval-create':
            result = create_evaluation(Path(args.draft_a), Path(args.draft_b), Path(args.output), args.brief)
        elif args.command == 'eval-report':
            result = summarize_evaluation(Path(args.experiment), Path(args.results))
        else:
            raise ValueError('未知 V0.5 命令')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print(f'操作被拒绝：{exc}', file=sys.stderr)
        return 2


def cmd_v06(args):
    try:
        import directed_revision as revision
        project = Path(args.project)
        if args.command == 'revision-plan':
            result = revision.plan(project, args.run_id, Path(args.spec))
        elif args.command == 'revision-apply':
            result = revision.apply(project, args.run_id, args.revision_id, Path(args.patch))
        else:
            result = revision.check(project, args.run_id, Path(args.assessment) if args.assessment else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print(f'操作被拒绝：{exc}', file=sys.stderr)
        return 2


def cmd_ensemble(args):
    try:
        import ensemble_runtime as ensemble
        project = Path(args.project)
        if args.command == 'ensemble-start':
            config = json.loads(read_utf8(Path(args.config))[0])
            scene = json.loads(read_utf8(Path(args.scene))[0])
            memories = [json.loads(read_utf8(Path(x))[0]) for x in args.memory]
            result = ensemble.start(project, config, scene, memories)
        elif args.command == 'ensemble-packet':
            result = ensemble.packet(project, args.ensemble_id)
        elif args.command == 'ensemble-respond':
            result = ensemble.respond(project, args.ensemble_id,
                json.loads(read_utf8(Path(args.response))[0]), source=args.source)
        elif args.command == 'ensemble-memory':
            result = ensemble.export_memory(project, args.ensemble_id)
        elif args.command == 'ensemble-handoff':
            result = ensemble.handoff(project, args.ensemble_id)
        else:
            result = ensemble.status(project, args.ensemble_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print(f'操作被拒绝：{exc}', file=sys.stderr)
        return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="Novel Director 0.7.0")
    sub = parser.add_subparsers(dest="command", required=True)
    sp = sub.add_parser("init", help="复制空白项目模板，拒绝覆盖")
    sp.add_argument("project")
    sp.add_argument("--title", required=True)
    sp.set_defaults(func=cmd_init)
    sp=sub.add_parser('migrate',help='将旧小说项目复制升级到V0.4，不修改原路径')
    sp.add_argument('source');sp.add_argument('target');sp.set_defaults(func=cmd_migrate)
    for name, fn in (("validate", cmd_validate), ("status", cmd_status)):
        sp = sub.add_parser(name)
        sp.add_argument("project")
        sp.set_defaults(func=fn)
    sp = sub.add_parser("context", help="构建当前章节上下文，尽量隔离未来剧透")
    sp.add_argument("project")
    sp.add_argument("chapter")
    sp.add_argument("--budget",type=int,default=8000,help="上下文最大字符预算；不能剪裁硬规则")
    sp.set_defaults(func=cmd_context)
    sp = sub.add_parser("memory-index", help="构建可重建、可验证来源签名的 SQLite 中文记忆索引")
    sp.add_argument("project")
    sp.set_defaults(func=cmd_memory_index)
    sp = sub.add_parser("memory-search", help="中文小说记忆检索；严格按章节/历史版本过滤")
    sp.add_argument("project")
    sp.add_argument("query")
    sp.add_argument("--chapter",required=True)
    sp.add_argument("--history",required=True)
    sp.add_argument("--pov",required=True)
    sp.add_argument("--limit",type=int,default=8)
    sp.add_argument("--mode",choices=("writer","editor"),default="writer")
    sp.add_argument("--include-author-only",action="store_true")
    sp.set_defaults(func=cmd_memory_search)
    sp=sub.add_parser('run-start',help='创建一次不可覆盖的章节创作契约')
    sp.add_argument('project');sp.add_argument('chapter');sp.set_defaults(func=cmd_workflow)
    sp=sub.add_parser('run-submit',help='提交候选稿版本，不修改正式正文')
    sp.add_argument('project');sp.add_argument('run_id');sp.add_argument('draft');sp.set_defaults(func=cmd_workflow)
    sp=sub.add_parser('run-review',help='提交独立审稿 JSON；不自动批准')
    sp.add_argument('project');sp.add_argument('run_id');sp.add_argument('review');sp.set_defaults(func=cmd_workflow)
    sp=sub.add_parser('run-approve',help='作者显式批准已经审校的确切候选版本')
    sp.add_argument('project');sp.add_argument('run_id');sp.add_argument('--by',required=True);sp.set_defaults(func=cmd_workflow)
    sp=sub.add_parser('run-publish',help='校验审批后安全发布章节')
    sp.add_argument('project');sp.add_argument('run_id');sp.add_argument('--replace',action='store_true');sp.set_defaults(func=cmd_workflow)
    for command in ('run-status','run-quality'):
        sp=sub.add_parser(command)
        sp.add_argument('project');sp.add_argument('run_id');sp.set_defaults(func=cmd_workflow)
    sp=sub.add_parser('screen-adapt',help='导出基于场景卡的 Fountain 剧本骨架')
    sp.add_argument('project');sp.add_argument('--volume',type=int,required=True);sp.add_argument('--out')
    sp.set_defaults(func=cmd_workflow)
    sp=sub.add_parser('practice-plan',help='按世界观、剧情、人物、情感等维度生成独立写作练习')
    sp.add_argument('project');sp.add_argument('--focus',choices=('worldbuilding','plot','character','emotion','mystery','dialogue','screenplay'),required=True)
    sp.add_argument('--chapter');sp.add_argument('--save',action='store_true');sp.set_defaults(func=cmd_workflow)
    sp=sub.add_parser('practice-record',help='保存作者提供的训练反馈，不更新小说设定')
    sp.add_argument('project');sp.add_argument('exercise_id');sp.add_argument('feedback');sp.set_defaults(func=cmd_workflow)
    sp=sub.add_parser('route',help='查询各创作任务应加载的角色和输出契约；不调用模型')
    sp.add_argument('project');sp.add_argument('--task',choices=('research','worldbuilding','outline','chapter','revision','screenplay','learning','audit','impact','compare','ensemble'),required=True)
    sp.set_defaults(func=cmd_workflow)
    sp = sub.add_parser("skillcheck", help="轻量检查本技能文件结构")
    sp.set_defaults(func=cmd_skillcheck)
    sp = sub.add_parser('review-check', help='核验引文、字符位置、来源摘要，不作文学判断')
    sp.add_argument('project');sp.add_argument('draft');sp.add_argument('review')
    sp.set_defaults(func=cmd_v05)
    sp = sub.add_parser('impact', help='只读输出已登记依赖的改动影响路径，可能含剧透')
    sp.add_argument('project');sp.add_argument('--changed', action='append', required=True)
    sp.set_defaults(func=cmd_v05)
    sp = sub.add_parser('eval-create', help='创建匿名AB/BA包，不调用评审模型')
    sp.add_argument('draft_a');sp.add_argument('draft_b');sp.add_argument('output')
    sp.add_argument('--brief', required=True);sp.set_defaults(func=cmd_v05)
    sp = sub.add_parser('eval-report', help='导入外部评审，诊断顺序一致性而不是宣称文学优劣')
    sp.add_argument('experiment');sp.add_argument('results');sp.set_defaults(func=cmd_v05)
    sp = sub.add_parser('revision-plan', help='将已核验问题转为限定范围的修订计划，不改正文')
    sp.add_argument('project'); sp.add_argument('run_id'); sp.add_argument('spec'); sp.set_defaults(func=cmd_v06)
    sp = sub.add_parser('revision-apply', help='应用精确补丁为新候选稿，保留原稿，不发布')
    sp.add_argument('project'); sp.add_argument('run_id'); sp.add_argument('revision_id'); sp.add_argument('patch'); sp.set_defaults(func=cmd_v06)
    sp = sub.add_parser('revision-check', help='核验改稿前后证据及语义验收声明，不自动批准')
    sp.add_argument('project'); sp.add_argument('run_id'); sp.add_argument('--assessment'); sp.set_defaults(func=cmd_v06)
    sp = sub.add_parser('ensemble-start', help='冻结主线/核心角色/普通角色池配置，新建场景排练')
    sp.add_argument('project'); sp.add_argument('--config', required=True); sp.add_argument('--scene', required=True)
    sp.add_argument('--memory', action='append', default=[]); sp.set_defaults(func=cmd_ensemble)
    for command in ('ensemble-packet', 'ensemble-status', 'ensemble-memory', 'ensemble-handoff'):
        sp = sub.add_parser(command, help='按角色隔离调用材料/查询状态/导出候选记忆/交接待审稿')
        sp.add_argument('project'); sp.add_argument('ensemble_id'); sp.set_defaults(func=cmd_ensemble)
    sp = sub.add_parser('ensemble-respond', help='导入宿主实际返回的角色/主线响应，不自动调用模型')
    sp.add_argument('project'); sp.add_argument('ensemble_id'); sp.add_argument('response')
    sp.add_argument('--source', choices=('manual','host_supplied','synthetic_test'), default='manual')
    sp.set_defaults(func=cmd_ensemble)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
