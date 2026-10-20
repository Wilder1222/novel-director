"""V0.3 local, rebuildable SQLite retrieval for Chinese long fiction.

Security is enforced BEFORE ranking. No network, embedding service, or LLM.
The author-only view is an explicit review command, never writer context.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import math
import os
import re
import sqlite3
import tempfile

DATABASE='.novel_memory.sqlite3'
INPUTS=('project.json','canon.json','characters.json','chapters.json','clues.json','events.json','knowledge.json','versions.json','memory_docs.json','artifacts.json','world_rules.json','story_units.json','relationships.json','scenes.json')


def _read(path, default):
    if not path.is_file(): return default
    return json.loads(path.read_text(encoding='utf-8'))


def _sha(path: Path):
    return sha256(path.read_bytes()).hexdigest() if path.exists() else '-'


def signatures(project: Path):
    out={file:_sha(project/file) for file in INPUTS}
    chapter_dir=project/'manuscript'
    if chapter_dir.is_dir() and not chapter_dir.is_symlink():
        for p in sorted(chapter_dir.glob('V*-C*.md')):
            if p.is_file() and not p.is_symlink():
                out[str(p.relative_to(project))]=_sha(p)
    return out


def _order(ch):
    if not isinstance(ch,str): return None
    m=re.fullmatch(r'V(\d{1,3})-C(\d{1,4})',ch)
    return int(m.group(1))*10000+int(m.group(2)) if m else None


def _tokens(text: str):
    out=[]
    for block in re.findall(r'[\u3400-\u9fff]+|[A-Za-z][A-Za-z\d_]*|\d+',str(text)):
        if '\u3400' <= block[0] <= '\u9fff':
            if len(block)==1: out.append(block)
            for span in (2,3):
                out += [block[k:k+span] for k in range(max(0,len(block)-span+1))]
        else: out.append(block.lower())
    return out


def _make(id, text, source_type, **kw):
    return dict(id=id, text=str(text),source_type=source_type,
                source_path=kw.get('source_path',''),chapter_id=kw.get('chapter_id'),
                reveal_chapter=kw.get('reveal_chapter'),history_id=kw.get('history_id','global'),
                visibility=kw.get('visibility','author_only'),status=kw.get('status','planned'),
                allowed_povs=kw.get('allowed_povs',[]),characters=kw.get('characters',[]),
                importance=kw.get('importance',1.0))


def collect(project: Path):
    docs=[]
    author_docs=_read(project/'memory_docs.json', {'memories':[]}).get('memories',[])
    if not isinstance(author_docs,list): raise ValueError('memory_docs.json: memories 应为数组')
    for i,item in enumerate(author_docs):
        if not isinstance(item,dict) or not item.get('id') or not item.get('text'):
            raise ValueError(f'memory_docs.json: memories[{i}] 需要 id/text')
        docs.append(_make('note:'+item['id'],item['text'],'authored_note',source_path='memory_docs.json',
                          chapter_id=item.get('chapter_id'),reveal_chapter=item.get('reveal_chapter'),
                          history_id=item.get('history_id','global'),visibility=item.get('visibility','author_only'),
                          status=item.get('status','planned'),allowed_povs=item.get('allowed_povs',[]),
                          characters=item.get('characters',[]),importance=item.get('importance',1)))
    for fact in _read(project/'canon.json',{'facts':[]}).get('facts',[]):
        if not isinstance(fact,dict) or not fact.get('id'): continue
        status=fact.get('status','hypothesis')
        vis=('author_only' if fact.get('secret') else 'reader' if fact.get('reveal_chapter') else 'writer_canon' if status=='confirmed' else 'author_only')
        docs.append(_make('fact:'+fact['id'],f"{fact.get('subject','')} {fact.get('predicate','')}: {fact.get('value','')}",
                          'canon_fact',source_path='canon.json',history_id=fact.get('history_id','global'),
                          reveal_chapter=fact.get('reveal_chapter'),visibility=vis,status=status,importance=3.0))
    for ch in _read(project/'chapters.json',{'chapters':[]}).get('chapters',[]):
        if not isinstance(ch,dict) or not ch.get('id'): continue
        status='approved' if 'approved' in ch.get('status','').lower() else 'planned'
        docs.append(_make('chapter:'+ch['id'],f"{ch.get('title','')}：{ch.get('summary','')}",'chapter_summary',
                          source_path='chapters.json',chapter_id=ch['id'],reveal_chapter=ch['id'],
                          history_id=ch.get('history_id','global'),visibility='reader',status=status,
                          characters=[ch.get('pov')] if ch.get('pov') else [],importance=1.5))
    for clue in _read(project/'clues.json',{'clues':[]}).get('clues',[]):
        if not isinstance(clue,dict) or not clue.get('id'): continue
        docs.append(_make('clue:'+clue['id'],f"线索：{clue.get('question','')}；可见证据：{clue.get('observable_evidence','')}",
                          'clue_evidence',source_path='clues.json',reveal_chapter=clue.get('setup_chapter'),
                          visibility='reader',status=clue.get('status','planned'),importance=2.5))
        # Even after payoff, the writer should receive the answer only from an explicit chapter plan, not casual search.
        if clue.get('truth'):
            docs.append(_make('clue-secret:'+clue['id'],f"作者私有谜底：{clue['truth']}",'hidden_solution',
                              source_path='clues.json',reveal_chapter=clue.get('payoff_chapter'),
                              visibility='author_only',status=clue.get('status','planned'),importance=2.0))
    for event in _read(project/'events.json',{'events':[]}).get('events',[]):
        if not isinstance(event,dict) or not event.get('id'): continue
        docs.append(_make('event:'+event['id'],f"{event.get('at','')}：{event.get('description','')}",'event',
                          source_path='events.json',history_id=event.get('history_id','global'),
                          reveal_chapter=event.get('revealed_chapter'),visibility='reader' if event.get('revealed_chapter') else 'author_only',
                          status=event.get('status','planned'),characters=event.get('actor_ids',[]),importance=1.8))
    for person in _read(project/'characters.json',{'characters':[]}).get('characters',[]):
        if not isinstance(person,dict) or not person.get('id'): continue
        docs.append(_make('character:'+person['id'],f"{person.get('name','')}：{person.get('role','')}。{person.get('voice','')}",
                          'character_profile',source_path='characters.json',visibility='writer_canon',
                          history_id='global',status='planned',characters=[person['id']],importance=1.2))
    for obj in _read(project/'artifacts.json',{'artifacts':[]}).get('artifacts',[]):
        if not isinstance(obj,dict) or not obj.get('id'): continue
        docs.append(_make('artifact:'+obj['id'],f"{obj.get('name','')}，创建时间：{obj.get('created_at','')}，来源：{obj.get('origin_history_id','')}。",
                          'artifact',source_path='artifacts.json',history_id=obj.get('origin_history_id','global'),
                          visibility='author_only',status=obj.get('status','planned'),importance=1.4))
    # Official manuscript is indexed as reader-revealed, approved TEXT, not a
    # synonym of the planned chapter summaries. Chunking retains retrieval utility.
    chapter_dir=project/'manuscript'
    if chapter_dir.is_dir() and not chapter_dir.is_symlink():
        ch_map={c['id']:c for c in _read(project/'chapters.json',{'chapters':[]}).get('chapters',[]) if isinstance(c,dict) and c.get('id')}
        for prose in sorted(chapter_dir.glob('V*-C*.md')):
            if not prose.is_file() or prose.is_symlink() or prose.stem not in ch_map:continue
            raw=prose.read_text(encoding='utf8')
            chapter=ch_map[prose.stem]
            for i,start in enumerate(range(0,len(raw),800)):
                excerpt=raw[max(0,start-80):start+800]
                docs.append(_make(f'prose:{prose.stem}:{i:03}',excerpt,'manuscript_chunk',
                      source_path=str(prose.relative_to(project)),chapter_id=prose.stem,
                      reveal_chapter=prose.stem,history_id=chapter.get('history_id','global'),
                      visibility='reader',status='approved',characters=[chapter.get('pov')],importance=2.7))
    # V0.4: world rules, emotional continuity, and outlined units join retrieval
    # with spoiler fences. Relationship changes become available AFTER their scene.
    chapters_by_id={c['id']:c for c in _read(project/'chapters.json',{'chapters':[]}).get('chapters',[]) if isinstance(c,dict) and c.get('id')}
    for rule in _read(project/'world_rules.json',{'rules':[]}).get('rules',[]):
        if not isinstance(rule,dict) or not rule.get('id'):continue
        intro=rule.get('introduced_chapter')
        visibility='author_only' if rule.get('secret') else ('reader' if intro else 'writer_canon')
        docs.append(_make('rule:'+rule['id'],f"世界规则：{rule.get('rule','')}；限制代价：{rule.get('cost','')}；戏剧功能：{rule.get('dramatic_function','')}",
                'world_rule',source_path='world_rules.json',reveal_chapter=intro,
                history_id=rule.get('history_id','global'),visibility=visibility,
                status=rule.get('status','planned'),importance=3.0))
    for moment in _read(project/'relationships.json',{'moments':[]}).get('moments',[]):
        if not isinstance(moment,dict) or not moment.get('id'):continue
        cc=chapters_by_id.get(moment.get('chapter_id'),{})
        docs.append(_make('relationship:'+moment['id'],
                f"关系演变：{','.join(moment.get('pair_ids',[]))} 从 {moment.get('from_state','')} 到 {moment.get('to_state','')}；"
                f"可见触发行为：{moment.get('trigger_action','')}；付出代价：{moment.get('cost','')}；后果：{moment.get('consequence','')}",
                'relationship',source_path='relationships.json',reveal_chapter=moment.get('chapter_id'),
                history_id=moment.get('history_id',cc.get('history_id','global')),
                visibility='reader',status=moment.get('status','planned'),
                characters=moment.get('pair_ids',[]),importance=2.6))
    for unit in _read(project/'story_units.json',{'units':[]}).get('units',[]):
        if not isinstance(unit,dict) or not unit.get('id'):continue
        docs.append(_make('unit-goal:'+unit['id'],f"故事单元目标：{unit.get('goal','')}；阻碍：{unit.get('opposition','')}",
                          'story_unit_goal',source_path='story_units.json',history_id='global',
                          visibility='writer_canon',status='planned',importance=1.7))
        docs.append(_make('unit-payoff:'+unit['id'],f"故事单元结局（作者私有）：{unit.get('answer','')}；代价：{unit.get('consequence','')}",
                          'story_unit_payoff',source_path='story_units.json',history_id='global',
                          reveal_chapter=unit.get('last_chapter'),visibility='author_only',status='planned',importance=2.0))
    for scene in _read(project/'scenes.json',{'scenes':[]}).get('scenes',[]):
        if not isinstance(scene,dict) or not scene.get('id'):continue
        docs.append(_make('scene:'+scene['id'],f"场景 {scene.get('slugline','')}：目标{scene.get('goal','')}，转折{scene.get('turn','')}",
                         'scene_card',source_path='scenes.json',chapter_id=scene.get('chapter_id'),
                         reveal_chapter=scene.get('chapter_id'),history_id=scene.get('history_id','global'),
                         visibility='reader',status=scene.get('status','planned'),importance=1.3))
    ids=set()
    for doc in docs:
        if doc['id'] in ids: raise ValueError(f'重复记忆 ID: {doc["id"]}')
        ids.add(doc['id'])
        if doc['visibility'] not in ('reader','writer_canon','pov_private','author_only'):
            raise ValueError(f'记忆可见性不合法: {doc["id"]}')
        for field in ('chapter_id','reveal_chapter'):
            if doc[field] is not None and _order(doc[field]) is None:
                raise ValueError(f'{doc["id"]}: {field} 格式错误')
        if not 0.1<=float(doc['importance'])<=5:
            raise ValueError(f'{doc["id"]}: importance 应在 0.1-5 之间')
    return docs


def build(project: Path, dbpath: Path|None=None):
    """Atomic index replace; source files are never altered."""
    project=project.resolve()
    dbpath=dbpath or project/DATABASE
    docs=collect(project)
    dbpath.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.novel-index-',suffix='.sqlite3',dir=dbpath.parent)
    os.close(fd)
    try:
        db=sqlite3.connect(tmp)
        db.execute('PRAGMA journal_mode=DELETE')
        db.executescript('''
            CREATE TABLE docs (id TEXT PRIMARY KEY, text TEXT NOT NULL, source_type TEXT, source_path TEXT,
                chapter_id TEXT,reveal_chapter TEXT,history_id TEXT,visibility TEXT,status TEXT,
                allowed_povs TEXT,characters TEXT, importance REAL, source_hash TEXT);
            CREATE TABLE postings(token TEXT NOT NULL,doc_id TEXT NOT NULL,tf INTEGER NOT NULL,
                PRIMARY KEY(token,doc_id));
            CREATE INDEX postings_token ON postings(token);
            CREATE TABLE metadata(k TEXT PRIMARY KEY,v TEXT);
        ''')
        for doc in docs:
            db.execute('INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(
                doc['id'],doc['text'],doc['source_type'],doc['source_path'],doc['chapter_id'],doc['reveal_chapter'],
                doc['history_id'],doc['visibility'],doc['status'],json.dumps(doc['allowed_povs'],ensure_ascii=False),
                json.dumps(doc['characters'],ensure_ascii=False),float(doc['importance']),
                _sha(project/doc['source_path']) if doc['source_path'] else '-'))
            counts=Counter(_tokens(doc['text']))
            db.executemany('INSERT INTO postings VALUES (?,?,?)',[(tok,doc['id'],tf) for tok,tf in counts.items()])
        db.execute('INSERT INTO metadata VALUES (?,?)',('source_signatures',json.dumps(signatures(project),sort_keys=True)))
        db.execute('INSERT INTO metadata VALUES (?,?)',('schema','0.3'))
        db.commit();db.close()
        os.replace(tmp,dbpath)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return {'documents':len(docs),'postings':sum(len(set(_tokens(d['text']))) for d in docs),'database':str(dbpath)}


def stale(project:Path,dbpath:Path|None=None):
    dbpath=dbpath or project/DATABASE
    if not dbpath.exists(): return True
    try:
        db=sqlite3.connect(f'file:{dbpath}?mode=ro',uri=True)
        record=db.execute('SELECT v FROM metadata WHERE k=?',('source_signatures',)).fetchone()
        db.close()
        return record is None or json.loads(record[0])!=signatures(project)
    except (sqlite3.Error,ValueError): return True


def _allowed(row, chapter, history, pov, mode, include_author):
    (id,text,source_type,source_path,chapter_id,reveal_chapter,hid,visibility,status,povs,chars,importance,source_hash)=row
    if visibility=='author_only': return mode=='editor' and include_author
    if mode=='writer' and visibility=='pov_private' and pov not in json.loads(povs): return False
    if hid not in ('global',history): return False
    limit=_order(chapter)
    if mode=='writer':
        if limit is None: return False
        revealed=_order(reveal_chapter)
        if visibility not in ('writer_canon',) and (revealed is None or revealed>limit): return False
        # Previous chapter summaries only, never inject current chapter outcome as external memory.
        if source_type in ('chapter_summary','scene_card','manuscript_chunk') and revealed>=limit: return False
        if status in ('hypothesis','inferred'): return False
    return True


def search(project:Path,query:str,chapter:str,history:str,pov:str,limit:int=8,mode:str='writer',include_author:bool=False,dbpath:Path|None=None):
    project=project.resolve()
    dbpath=dbpath or project/DATABASE
    if stale(project,dbpath): raise RuntimeError('记忆索引缺失或过期；先运行 memory-index')
    if mode not in ('writer','editor'): raise ValueError('mode 只允许 writer 或 editor')
    if include_author and mode!='editor': raise ValueError('作者私有信息仅可在显式 editor 模式读取')
    tokens=set(_tokens(query))
    if not tokens: return []
    con=sqlite3.connect(f'file:{dbpath}?mode=ro',uri=True)
    try:
        placeholders=','.join('?' for _ in tokens)
        rows=con.execute(f'SELECT p.token,p.doc_id,p.tf FROM postings p WHERE token IN ({placeholders})',list(tokens)).fetchall()
        if not rows:return []
        # Security filter BEFORE score calculation: hidden and future documents
        # do not influence writer results or inverse-document-frequency weights.
        candidates={}
        for tok,did,tf in rows:
            if did not in candidates:
                doc=con.execute('SELECT * FROM docs WHERE id=?',(did,)).fetchone()
                candidates[did]=(doc,_allowed(doc,chapter,history,pov,mode,include_author))
        visible=[(tok,did,tf) for tok,did,tf in rows if candidates[did][1]]
        if not visible: return []
        counts=Counter(r[1] for r in visible)
        global_df=Counter(r[0] for r in visible)
        total=sum(ok for _,ok in candidates.values())
        ranks={}
        for tok,did,tf in visible:
            ranks[did]=ranks.get(did,0)+(1+math.log(tf))*math.log((total+1)/(1+global_df[tok]))
        result=[]
        for did in ranks:
            doc=candidates[did][0]
            s=ranks[did]*float(doc[11])*(1+0.08*counts[did]/len(tokens))
            result.append({'id':did,'score':round(s,4),'text':doc[1],'source_type':doc[2],
                           'source_path':doc[3],'chapter_id':doc[4],'reveal_chapter':doc[5],
                           'history_id':doc[6],'visibility':doc[7],'status':doc[8],
                           'characters':json.loads(doc[10])})
        result.sort(key=lambda x:(-x['score'],x['id']))
        return result[:limit]
    finally: con.close()


def scoped_context(project,chapter,history,pov,query, budget=2000,limit=8):
    """Trim retrieved memory only; caller must reserve hard rules/current chapter separately."""
    if budget<0: raise ValueError('budget 不能是负数')
    hits=search(project,query,chapter,history,pov,limit=limit)
    used=0;selected=[]
    for hit in hits:
        cost=len(json.dumps(hit,ensure_ascii=False))
        if cost+used<=budget:
            used+=cost
            selected.append(hit)
    return {'used_chars':used,'budget_chars':budget,'retrieved':selected,
            'notice':'结构检索不是语义理解；提及历史版本/人物隐私需额外人工审校'}
