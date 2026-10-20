"""V0.4 novel-to-screenplay scene-card conversion (Fountain skeleton, not a screenplay)."""
from __future__ import annotations
from pathlib import Path
import json
import re
from creative_workflow import atomic_write


def build(project:Path,volume:int):
    data=json.loads((project/'scenes.json').read_text(encoding='utf8'))
    rows=data.get('scenes')
    if not isinstance(rows,list): raise ValueError('scenes.json: scenes 应为数组')
    chapters={ch['id']:ch for ch in json.loads((project/'chapters.json').read_text(encoding='utf8'))['chapters']}
    people={ch['id']:ch['name'] for ch in json.loads((project/'characters.json').read_text(encoding='utf8'))['characters']}
    output=['Title: '+json.loads((project/'project.json').read_text(encoding='utf8')).get('title','未命名')+'：剧本结构骨架',
            'Credit: 开发用结构稿，非最终剧本','Draft date: 2026-10-20','','# 卷'+str(volume)+'·由场景卡生成',
            '[[此文件仅把小说已规划的可拍场景转为 Fountain 结构，不保证对白及动作的正式剧本质量。]]','']
    valid=[];seen=set()
    for s in rows:
        if not isinstance(s,dict):raise ValueError('scene 记录必须为对象')
        ch=chapters.get(s.get('chapter_id'))
        if ch is None:raise ValueError('场景引用未知章节 '+str(s.get('chapter_id')))
        if ch['volume']!=volume:continue
        sid=s.get('id')
        if not sid or sid in seen:raise ValueError('重复或缺失场景 ID')
        seen.add(sid)
        slug=s.get('slugline','')
        if not isinstance(slug,str) or '\n' in slug or not re.match(r'^(INT\.|EXT\.|INT/EXT\.|I/E\.)\s*\S',slug,re.I):
            raise ValueError(f'{sid}: 场景行必须以 INT./EXT. 等开头')
        for req in ('goal','conflict','turn','action'):
            if not s.get(req): raise ValueError(f'{sid}: 缺少 {req}')
        valid.append((ch['number'],int(s.get('order',1)),s))
    valid.sort(key=lambda x:(x[0],x[1]))
    for number,order,sc in valid:
        output+= [f'## 第{number}章 · 场景 {order}', '',f'{sc["slugline"]} #{sc["id"]}#','',
                   f'[[事件时间：{sc.get("in_world_at", "未定")}；历史版本：{sc.get("history_id", "未定")}]]',
                   f'[[目标：{sc["goal"]}；阻碍：{sc["conflict"]}；转折：{sc["turn"]}]]','',
                   sc['action'].strip(),'']
        for line in sc.get('dialogue',[]):
            if line.get('character_id') not in people:raise ValueError('未知对白角色')
            name=people[line['character_id']]
            output.extend(['@'+name, line['text'].strip(), ''])
        output+= ['[[待后续编剧根据故事圣经、人物心理和镜头表达补写可拍对白。]]','']
    if not valid:raise ValueError(f'没有第 {volume} 卷可导出的场景')
    return '\n'.join(output).rstrip()+'\n',len(valid)


def export(project:Path,volume:int,outfile:Path|None=None):
    project=project.resolve()
    text,n=build(project,volume)
    if outfile is None:outfile=project/'adaptations'/f'volume-{volume}-skeleton.fountain'
    else:
        # Only inside adaptations; prevent output traversal and silent overwrite.
        proposed=outfile.expanduser().resolve()
        allowed=(project/'adaptations').resolve()
        if proposed.parent!=allowed or proposed.suffix!='.fountain':
            raise ValueError('Fountain 输出只能位于项目 adaptations/ 目录且扩展名为 .fountain')
        outfile=proposed
    atomic_write(outfile,text)
    return {'volume':volume,'scenes':n,'file':str(outfile),'kind':'Fountain scene skeleton, not complete screenplay'}
