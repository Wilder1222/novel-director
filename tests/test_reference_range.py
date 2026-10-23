import copy
import hashlib
import json
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path
from tests.support import project
import reference_library as refs


def sample(count=20):
    source=Path(__file__).resolve().parents[1]/'research/samples/2026-10-22-reference-samples.json'
    work=copy.deepcopy(json.loads(source.read_text(encoding='utf-8'))['works'][0])
    work['expected_numbers']=list(range(1,count+1))
    work['chapters']=work['chapters'][:count]
    if count>50:
        extra=copy.deepcopy(work['chapters'][-1]);extra.update(number=51,url='https://example.org/chapter/51',body_sha256=hashlib.sha256(b'different chapter').hexdigest())
        work['chapters'].append(extra)
    return {'schema_version':'2','minimum_per_work':20,'maximum_per_work':50,'works':[work]}


class ReferenceRange(unittest.TestCase):
    def test_twenty_and_fifty_are_valid_current_samples(self):
        for count in (20,50):
            with self.subTest(count=count):self.assertEqual(refs.validate_samples(sample(count))['ready_ids'],['jianlai'])

    def test_nineteen_and_fifty_one_are_rejected(self):
        for count in (19,51):
            with self.subTest(count=count),self.assertRaises(ValueError):refs.validate_samples(sample(count))

    def test_nineteen_cannot_borrow_from_another_work(self):
        value=sample(20);first=value['works'][0];first['chapters'].pop()
        second=copy.deepcopy(sample(21)['works'][0]);second.update(id='other',title='另一部作品',author='另一位作者')
        value['works'].append(second)
        with self.assertRaises(ValueError):refs.validate_samples(value)

    def test_same_title_author_two_editions_cannot_count_as_two_adopted_books(self):
        value=sample(20);second=copy.deepcopy(value['works'][0]);second.update(id='jianlai-another',edition='another official edition')
        value['works'].append(second)
        with self.assertRaises(ValueError):refs.validate_samples(value,['jianlai','jianlai-another'])

    def test_wrong_policy_cannot_lower_twenty(self):
        value=sample(20);value['minimum_per_work']=19
        with self.assertRaises(ValueError):refs.validate_samples(value)

    def test_study_contract_cannot_count_internal_whitespace_alias_as_another_book(self):
        value=sample(20);first=value['works'][0]
        for c in first['chapters']:c['semantic_status']='fully_semantically_reviewed'
        first['claim_scope']['semantic_numbers']=list(range(1,21))
        second=copy.deepcopy(first);second.update(id='same-book-alias',title='剑 来')
        value['works'].append(second)
        value['study_contract']={'work_ids':[first['id'],second['id']],'minimum_works':2,'minimum_read_per_work':20}
        with self.assertRaises(ValueError):refs.validate_samples(value)

    def test_portable_full_read_claim_requires_actual_study_in_all_read_paths(self):
        import reference_study
        value=sample(20);work=value['works'][0]
        for c in work['chapters']:c['semantic_status']='fully_semantically_reviewed'
        work['claim_scope']['semantic_numbers']=list(range(1,21))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=json.dumps(work,ensure_ascii=False).encode('utf-8')
            (root/'jianlai.json').write_bytes(raw)
            catalog={'schema_version':'1','sample_policy':{k:v for k,v in value.items() if k!='works'},'works':[{'id':work['id'],'file':'jianlai.json','sha256':hashlib.sha256(raw).hexdigest()}]}
            (root/'catalog.json').write_text(json.dumps(catalog),encoding='utf-8')
            with patch.object(refs,'LIBRARY',root):
                with self.assertRaises(ValueError):refs.load()
                with self.assertRaises(ValueError):refs.show('jianlai')
            with self.assertRaises(ValueError):reference_study.search(root,book='jianlai')

    def test_legacy_invalid_semantic_state_rejects_without_attribute_error(self):
        source=Path(__file__).resolve().parents[1]/'research/samples/2026-10-22-reference-samples.json'
        work=json.loads(source.read_text(encoding='utf-8'))['works'][0]
        raw=json.loads((source.parent/work['source_record']).read_text(encoding='utf-8'))
        raw['chapters'][0]['semantic_status']=None
        with self.assertRaises(ValueError):refs.source_projection(raw)
