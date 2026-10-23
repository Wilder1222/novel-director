"""Author selection policy survives acquisition and portable read projections."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_reference_range import sample
import reference_library as refs
import reference_study as study
import build_reference_library as builder


class ReferencePolicy(unittest.TestCase):
    def test_legacy_without_policy_and_allowed_author_remain_valid(self):
        value=sample(50);value.update(schema_version='1',minimum_per_work=50);value.pop('maximum_per_work')
        refs.validate_samples(value)
        value['excluded_authors']=['天蚕土豆'];refs.validate_samples(value)

    def test_policy_shape_and_normalized_duplicate_rejected(self):
        for policy in ('天蚕土豆',{},[''],[None],['天蚕土豆','天 蚕 土 豆']):
            value=sample();value['excluded_authors']=policy
            with self.subTest(policy=policy),self.assertRaises(ValueError):refs.validate_samples(value)

    def test_work_id_cannot_evade_author_or_source_author_policy(self):
        for field in ('author','source_identity'):
            value=sample();value['excluded_authors']=['天蚕土豆'];work=value['works'][0];work['id']='unrelated-id'
            if field=='author':work[field]='天 蚕 土 豆'
            else:work[field]['author']='天蚕土豆'
            with self.subTest(field=field),self.assertRaises(ValueError):refs.validate_samples(value)
        value=sample();value['excluded_authors']=['天蚕土豆'];value['works'][0].pop('author')
        with self.assertRaises(ValueError):refs.validate_samples(value)

    def test_every_portable_read_path_checks_top_level_policy(self):
        value=sample();work=value['works'][0];work['author']='天蚕土豆'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=json.dumps(work,ensure_ascii=False).encode('utf-8');(root/'jianlai.json').write_bytes(raw)
            row={**work,'file':'jianlai.json','sha256':hashlib.sha256(raw).hexdigest(),'collected_chapters':20}
            catalog={'schema_version':'1','sample_policy':{k:v for k,v in value.items() if k!='works'},'excluded_authors':['天蚕土豆'],'works':[row]}
            (root/'catalog.json').write_text(json.dumps(catalog),encoding='utf-8')
            with patch.object(refs,'LIBRARY',root):
                for call in (refs.load,refs.search,lambda:refs.show('jianlai'),lambda:study.search(root),lambda:study.read(root,'jianlai')):
                    with self.subTest(call=call),self.assertRaisesRegex(ValueError,'排除'):call()
                # A forged allowed summary must not bless a banned hashed file.
                catalog['works'][0]['author']='允许作者'
                catalog['works'][0]['source_identity']={**work['source_identity'],'author':'允许作者'}
                (root/'catalog.json').write_text(json.dumps(catalog),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'排除'):refs.search()

    def test_builder_carries_policy_without_changing_per_work_context(self):
        value=sample();value['excluded_authors']=['天蚕土豆'];value['author_policy']={'quote':'不要天蚕土豆的书'}
        work=value['works'][0];before=study.source_context_sha(work)
        # Isolate projection from the separately tested exact source-file adapter.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'library';source=root/'research/samples';source.mkdir(parents=True)
            (source/'2026-10-22-reference-study-samples.json').write_text(json.dumps(value),encoding='utf-8')
            with patch.object(builder,'ROOT',root),patch.object(refs,'LIBRARY',out),patch.object(refs,'validate_file') as valid:
                builder.build();valid.assert_called_once()
            catalog=json.loads((out/'catalog.json').read_text(encoding='utf-8'))
            self.assertEqual(catalog['excluded_authors'],value['excluded_authors']);self.assertEqual(catalog['author_policy'],value['author_policy'])
            self.assertEqual(study.source_context_sha(json.loads((out/'jianlai.json').read_text(encoding='utf-8'))),before)
