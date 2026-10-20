"""V0.4 literary planning diagnostics: scene turns, thematic rules, relational evidence.

Reports missing or suspicious structural evidence, NOT a numerical literary grade.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json

REQUIRED={'world_rules.json':'rules','story_units.json':'units','relationships.json':'moments','scenes.json':'scenes'}
STAGES={'strangers':0,'wary':1,'provisional_cooperation':2,'tentative_trust':3,'deep_trust':4,'committed':5}


def _load(project:Path,file,key,required,issues):
    path=project/file
    if not path.exists():
        if required:issues.append(('ERROR','NARRATIVE_LEDGER_MISSING',file,'缺少章节/世界观/关系台账'))
        return []
    try:
        data=json.loads(path.read_text(encoding='utf8'))
        x=data.get(key)
        if not isinstance(x,list):raise ValueError(f'{key} should be list')
        return x
    except (OSError,ValueError,AttributeError) as ex:
        issues.append(('ERROR','NARRATIVE_LEDGER_INVALID',file,str(ex)))
        return []


def validate(project:Path,data:dict):
    issues=[]
    required=data.get('project',{}).get('schema_version')=='0.4'
    d={name:_load(project,name,key,required,issues) for name,key in REQUIRED.items()}
    chars={x['id'] for x in data.get('characters',{}).get('characters',[]) if isinstance(x,dict) and x.get('id')}
    chapters={x['id']:x for x in data.get('chapters',{}).get('chapters',[]) if isinstance(x,dict) and x.get('id')}
    for rule in d['world_rules.json']:
        rid=rule.get('id','?')
        if not rule.get('rule') or not rule.get('dramatic_function'):
            issues.append(('WARN','WORLD_RULE_NOT_DRAMATIC',rid,'世界观规则需说明它如何影响人物行动或代价'))
        key=rule.get('constraint_key')
        if key and key in data.get('project',{}).get('time_rules',{}):
            if rule.get('value')!=data['project']['time_rules'][key]:
                issues.append(('ERROR','WORLD_RULE_CONTRADICTION',rid,f'{key} 与项目硬规则冲突'))
        if rule.get('status')=='confirmed' and not rule.get('source'):
            issues.append(('ERROR','WORLD_RULE_SOURCE_MISSING',rid,'确认设定必须提供授权来源'))
    seen_units=set()
    for unit in d['story_units.json']:
        uid=unit.get('id')
        if not uid or uid in seen_units:
            issues.append(('ERROR','STORY_UNIT_ID',str(uid),'单元编号缺失或重复'))
        seen_units.add(uid)
        first=chapters.get(unit.get('first_chapter'))
        last=chapters.get(unit.get('last_chapter'))
        if not first or not last:
            issues.append(('ERROR','STORY_UNIT_RANGE_UNKNOWN',str(uid),'开始/结束章必须登记'))
        elif (first['volume'],first['number'])>(last['volume'],last['number']):
            issues.append(('ERROR','STORY_UNIT_REVERSED',str(uid),'故事单元区间逆序'))
        if not unit.get('goal') or not unit.get('opposition'):
            issues.append(('WARN','STORY_UNIT_GOAL_MISSING',str(uid),'缺少单元目标/阻碍'))
        if not unit.get('answer') or not unit.get('consequence'):
            issues.append(('WARN','STORY_UNIT_PAYOFF_MISSING',str(uid),'单元缺少可兑现答案及后果，可能只有悬念'))
    seen_scenes=set()
    for scene in d['scenes.json']:
        sid=scene.get('id','?')
        if sid in seen_scenes:
            issues.append(('ERROR','SCENE_ID_DUPLICATE',str(sid),'场景 ID 重复'))
        seen_scenes.add(sid)
        chapter=chapters.get(scene.get('chapter_id'))
        if not chapter:
            issues.append(('ERROR','SCENE_CHAPTER_UNKNOWN',str(sid),'场景引用不存在的章节'))
            continue
        if scene.get('history_id') not in (None,chapter.get('history_id')) and not scene.get('explicit_time_shift'):
            issues.append(('ERROR','SCENE_HISTORY_DRIFT',str(sid),'章节内历史版本变化没有显式转场说明'))
        if not scene.get('goal') or not scene.get('conflict') or not scene.get('turn'):
            issues.append(('WARN','SCENE_TURN_MISSING',str(sid),'场景目标/冲突/变化不完整'))
        before,after=scene.get('value_before'),scene.get('value_after')
        if before and after and before==after and not scene.get('intentional_stasis'):
            issues.append(('WARN','SCENE_NO_VALUE_TURN',str(sid),'场景价值状态未变化；若刻意留白请标识 intentional_stasis'))
    seen_moments=set()
    last_by_pair=defaultdict(list)
    for moment in d['relationships.json']:
        mid=moment.get('id','?')
        if mid in seen_moments:
            issues.append(('ERROR','EMOTION_MOMENT_DUPLICATE',str(mid),'关系节点 ID 重复'))
        seen_moments.add(mid)
        if moment.get('chapter_id') not in chapters:
            issues.append(('ERROR','EMOTION_CHAPTER_UNKNOWN',str(mid),'关系节点需指向已经登记的章节'))
        pair=moment.get('pair_ids',[])
        if not isinstance(pair,list) or len(set(pair))!=2 or any(person not in chars for person in pair):
            issues.append(('ERROR','EMOTION_PAIR_INVALID',str(mid),'关系节点需要两个有效人物'))
            continue
        key=tuple(sorted(pair))
        if not moment.get('trigger_action') or not moment.get('consequence'):
            issues.append(('WARN','EMOTION_UNEARNED',str(mid),'关系变化缺少可观察行为与后果'))
        frm,to=moment.get('from_state'),moment.get('to_state')
        if frm in STAGES and to in STAGES and STAGES[to]-STAGES[frm]>2 and not moment.get('deliberate_jump'):
            issues.append(('WARN','EMOTION_SUDDEN_INTIMACY',str(mid),'跳级太快，建议补足冲突、互助、代价和共同经历'))
        c=chapters.get(moment.get('chapter_id'))
        if c:last_by_pair[key].append((c['volume'],c['number'],mid,frm,to))
    for pair,moments in last_by_pair.items():
        moments.sort()
        for prev,nxt in zip(moments,moments[1:]):
            if nxt[3] != prev[4] and not (nxt[3]=='strained_trust' or nxt[4]=='strained_trust'):
                issues.append(('WARN','EMOTION_STATE_GAP',nxt[2],f'{prev[2]} 的关系结尾 {prev[4]} 与本次开始 {nxt[3]} 不一致'))
    return issues
