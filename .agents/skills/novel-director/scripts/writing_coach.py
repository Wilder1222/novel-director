"""V0.4 explicit writing-practice plans and feedback, no model self-training."""
from __future__ import annotations
from pathlib import Path
from uuid import uuid4
import json
import re
from creative_workflow import atomic_write, timestamp

EXERCISES={
    'worldbuilding':{
        'name':'规则经由行动显现',
        'task':'写一段600~900字的具体场景，让人物在不解释世界设定的情况下，因为某条世界规则而被迫做选择。',
        'constraints':['不能直接使用“按照世界规则”式旁白','必须有一个可观察的限制和一个明确代价'],
        'check':['规则如何限制可采取的行动？','读者能否从后果反推规则？']},
    'plot':{
        'name':'因此/但是的因果链',
        'task':'设计连续5个情节节拍，每个节拍由上一个行动引发，同时引发新的障碍，再扩写为600字。',
        'constraints':['不能有仅以“然后”连接的无因果节拍','第三节拍必须让原计划失效'],
        'check':['每段与上段有明确因果吗？','中点是否改变目标或策略？']},
    'character':{
        'name':'角色在压力下显露矛盾',
        'task':'写当前项目两名角色面对同一道德困境的不同选择，每个角色至少暴露一个自身矛盾。',
        'constraints':['避免用性格标签替代行动','角色选择必须付出代价'],
        'check':['每个人的目标和害怕失去什么是否清楚？','行为是否来自此前塑造的信念？']},
    'emotion':{
        'name':'不说喜欢的信任变化',
        'task':'描写当前项目两名角色在共同处境中发生关系变化的一场对话与行动，不直接写“我喜欢你”“我信任你”。',
        'constraints':['至少一次微小互助和一次意图误读','必须有场景中可以观察的行为后果'],
        'check':['如果删掉心理总结，关系是否仍有变化？','关系变化是否由行动付出代价换来？']},
    'mystery':{
        'name':'公平误导和重释证据',
        'task':'围绕一件当前项目允许使用的物证设计真实线索、合理误读、一次新证据核验以及最终重释。',
        'constraints':['不凭空增加已不存在的新超能力','揭示后前面每条证据仍应真实'],
        'check':['读者能否提前看到必需证据？','反转解释旧事实，而非简单增加新事实吗？']},
    'dialogue':{
        'name':'可复述的独特人物声线',
        'task':'写一场700字的分歧对话，依据当前两名人物已登记的不同目标和说话策略组织。删除说话人标签后，人物仍需可区分。',
        'constraints':['不能用角色互相介绍已知设定来偷运说明','至少一次话语的表层内容与实际意图不同'],
        'check':['每个说话者说话策略不同吗？','删掉一句对白是否会改变局势？']},
    'screenplay':{
        'name':'小说场景的可拍性翻译',
        'task':'选一个包含内心感受的小说场景，把心理推理改为可拍的行为、道具、画面与对白，输出 Fountain 场景。',
        'constraints':['不能用旁白直接说明所有隐藏信息','每个动作必须在真实场地能呈现'],
        'check':['观众不用读心理活动也能理解主要矛盾吗？','场景行动前后有变化吗？']},
}


def create(project:Path,focus:str,chapter:str|None=None,save=False):
    if focus not in EXERCISES:raise ValueError('不支持的专项训练：'+focus)
    if chapter:
        chapters={x['id'] for x in json.loads((project/'chapters.json').read_text(encoding='utf8'))['chapters']}
        if chapter not in chapters:raise ValueError('练习引用了不存在的章节')
    card=EXERCISES[focus]
    eid='exercise-'+uuid4().hex[:12]
    plan={'id':eid,'created_at':timestamp(),'project':json.loads((project/'project.json').read_text(encoding='utf8')).get('title'),
          'focus':focus,'chapter':chapter,'name':card['name'],'task':card['task'],'constraints':card['constraints'],
          'self_check':card['check'],'method':['独立完成初稿','对照检查问题评价','获取具体反馈并修改','隔1/3/7天复练新场景'],
          'revisit_after_days':[1,3,7],
          'note':'练习设计借鉴一般写作训练研究，不等于已证明提升小说质量，也不构成模型自动学习。'}
    if save:
        path=project/'learning'/'plans'/f'{eid}.json'
        atomic_write(path,json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        plan['stored_file']=str(path)
    return plan


def record(project:Path,exercise_id:str,feedback_file:Path):
    if not re.fullmatch(r'exercise-[0-9a-f]{12}',exercise_id):
        raise ValueError('练习 ID 非法')
    plan_path=project/'learning'/'plans'/f'{exercise_id}.json'
    if not plan_path.is_file():raise FileNotFoundError('必须先保存练习计划')
    feedback=json.loads(feedback_file.read_text(encoding='utf8'))
    if not feedback.get('observation') or not feedback.get('revision_action'):
        raise ValueError('反馈必须有具体观察和下一次修改动作')
    score=feedback.get('self_score')
    if not isinstance(score,(int,float)) or not 0<=score<=5:raise ValueError('自评分需要 0~5')
    report={'exercise_id':exercise_id,'recorded_at':timestamp(),'plan_file':str(plan_path.relative_to(project)),
            'focus':json.loads(plan_path.read_text(encoding='utf8'))['focus'],
            'feedback':feedback,'canon_updated':False,
            'note':'仅记录作者的训练意见，不能自动成为作品情节或世界设定。'}
    dest=project/'learning'/'sessions'/f'{exercise_id}.json'
    atomic_write(dest,json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return {'saved':str(dest),'focus':report['focus'],'canon_updated':False}
