"""Explicit project style calibration. No inference of author approval or secrets."""
from pathlib import Path
import json
from copy import deepcopy
from evidence_audit import read_utf8
import creative_workflow as flow

GENRES = {
    'realism': ['制度、职业与生活细节是否有来源或明确架空？', '行动后果是否符合人物处境？'],
    'romance': ['关系变化是否有触发、误读、回应和余波？', '双方是否各有目标和拒绝空间？'],
    'mystery': ['读者何时看到必要证据？', '揭示是否重释已在场的线索，而非凭空补证？'],
    'fantasy': ['能力条件、代价与例外是否一致？', '力量如何改变人物的责任与选择？'],
    'science_fiction': ['技术假设怎样改变可采取的行动及人的关系？', '解释是否遮住冲突与人物处境？'],
    'historical': ['史实、推测和架空是否区分？', '人物选择是否受时代条件约束？'],
}


def validate(value):
    required = {'schema_version', 'status', 'reader_safe', 'narration', 'genres', 'rules', 'examples'}
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - {'confirmation', 'calibration', 'narration_origin'}:
        raise ValueError('文风配置缺少字段或含未知字段；不要混入全书设定')
    if value['schema_version'] != '1' or value['status'] not in ('candidate', 'confirmed') or type(value['reader_safe']) is not bool:
        raise ValueError('文风配置版本/状态/reader_safe 不合法')
    if value['narration'] not in ('first_person', 'third_person_limited'):
        raise ValueError('当前角色引擎仅支持第一人称/第三人称限知；全知需单独设计')
    if value.get('narration_origin','legacy_unspecified') not in ('tool_default','author_confirmed','legacy_unspecified'):
        raise ValueError('叙述视角来源须为工具默认或作者确认')
    for field in ('genres', 'rules', 'examples'):
        if not isinstance(value[field], list) or len(value[field]) > 24:
            raise ValueError('文风数组至多24项')
    if len(set(value['genres'])) != len(value['genres']) or not set(value['genres']) <= GENRES.keys():
        raise ValueError('题材未注册或重复')
    if any(not isinstance(x, str) or not x.strip() or len(x) > 1000 for x in value['rules']):
        raise ValueError('文风规则须为非空短文本')
    for sample in value['examples']:
        if not isinstance(sample, dict) or sample.keys() != {'prefer', 'avoid', 'reason'} or any(not isinstance(x, str) or len(x) > 1000 for x in sample.values()):
            raise ValueError('文风正反例只含prefer/avoid/reason短文本')
    if len(json.dumps(value, ensure_ascii=False)) > 16000:
        raise ValueError('文风配置过大，请提炼当前任务需要的规则')
    if value['status'] == 'confirmed':
        if not value['reader_safe'] or not isinstance(value.get('confirmation'), str) or not value['confirmation'].strip():
            raise ValueError('确认文风须记录本次作者原话范围，并明确无剧情秘密')
    return value


def projection(project: Path):
    path = project / 'writing_profile.json'
    if not path.exists():
        return None
    text, sha = read_utf8(path)
    value = validate(json.loads(text))
    if value['status'] != 'confirmed':
        return None
    # Deliberately omit approval text, raw calibration sources and author-only notes.
    return {**{key: deepcopy(value[key]) for key in ('narration', 'genres', 'rules', 'examples')},
            'narration_origin':value.get('narration_origin','legacy_unspecified'),
            'genre_focus': [question for genre in value['genres'] for question in GENRES[genre]],
            'source_sha256': sha, 'authority': 'style_only_not_story_facts'}


def template(project: Path):
    value = {'schema_version': '1', 'status': 'candidate', 'reader_safe': False,
             'confirmation': '', 'narration': 'third_person_limited', 'narration_origin':'tool_default', 'genres': [], 'rules': [], 'examples': [],
             'calibration': {'source_refs': [], 'scope': '', 'limits': '只保存作者授权样本；推测尚未确认。'}}
    flow.atomic_write(project / 'writing_profile.json', flow._pretty(value))
    return {'created': 'writing_profile.json', 'status': 'candidate', 'projected_to_writer': False}
