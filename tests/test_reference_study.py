import copy
import hashlib
import json
import unittest
from tests.support import project
import reference_study as study


def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fixture():
    """Explicit synthetic protocol fixture, never actual model/human reading evidence."""
    rows=[];notes=[]
    for n in range(1,21):
        paras=[f'村门在第{n}天的晨光里被打开，来客正在等待回答。',f'守门者把钥匙握在掌心，决定先确认来客的身份。']
        body='\n\n'.join(paras);sha=digest(body);anchors=[]
        for p,text in enumerate(paras,1):anchors.append({'id':f'c{n}-p{p}','paragraph':p,'quote':text[:8],'start':0,'end':8,'paragraph_sha256':digest(text),'body_sha256':sha})
        rows.append({'number':n,'title':f'合成测试章{n}','url':f'https://example.org/test/{n}','body_sha256':sha,'paragraphs':2,'paragraph_records':[{'number':p,'sha256':digest(text),'codepoints':len(text)} for p,text in enumerate(paras,1)],'reading_evidence':anchors})
        notes.append({'number':n,'body_sha256':sha,**{f:f'合成协议夹具第{n}项候选分析，不是实际作品细读。' for f in study.FIELDS},'evidence':[e['id'] for e in anchors]})
    work={'id':'synthetic-work','chapters':rows,'claim_scope':{'semantic_numbers':list(range(1,21))}}
    report={'schema_version':'1','work_id':work['id'],'producer':{'worker_id':'synthetic-producer','invocation_id':'synthetic-invocation','source':'synthetic_test'},'read_numbers':list(range(1,21)),'chapter_notes':notes,'nonstory_paragraphs':[],'cross_chapter':['合成测试链甲','合成测试链乙','合成测试链丙'],'techniques':[{'id':'synthetic-'+dim,'dimension':dim,'method':'合成测试方法','preconditions':'合成测试前提','limits':'合成测试局限','original_exercise':'原创合成测试练习','evidence':['paragraph:1:1']} for dim in study.DIMENSIONS],'limitations':'合成协议测试，不是小说质量或真正阅读验收。'}
    targets=[f'chapter:{n}' for n in report['read_numbers']]+[f'technique:{c["id"]}' for c in report['techniques']]+['scope']
    report['source_context_sha256']=study.source_context_sha(work)
    report['peer_review']={'reviewed_payload_sha256':study.payload_sha(report),'reviewer_id':'synthetic-reviewer','source':'synthetic_test','checks':[{'target':t,'verdict':'pass','reason':'合成协议测试回执，不是真实语义审查。'} for t in targets],'unresolved':[],'limitations':'合成审查夹具，不是实际宿主或外部读者。'}
    return work,report


class ReferenceStudy(unittest.TestCase):
    def test_synthetic_protocol_is_never_accepted_as_formal_reading(self):
        work,report=fixture();self.assertEqual(study.validate(work,report,require_host=False)['model_read_chapters'],20)
        with self.assertRaises(ValueError):study.validate(work,report)

    def test_missing_chapter_cannot_be_masked_by_collection_count(self):
        work,report=fixture();report['chapter_notes'].pop()
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_nineteen_read_chapters_is_not_twenty(self):
        work,report=fixture();report['read_numbers'].pop();report['chapter_notes'].pop()
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_other_body_or_wrong_paragraph_fails(self):
        work,report=fixture();report['chapter_notes'][0]['body_sha256']=digest('other draft')
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)
        work,report=fixture();work['chapters'][0]['reading_evidence'][0]['paragraph']=3
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_one_character_or_same_paragraph_is_not_coverage(self):
        work,report=fixture();e=work['chapters'][0]['reading_evidence'][0];e.update(quote='村',end=1)
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_changed_analysis_stales_review(self):
        work,report=fixture();report['chapter_notes'][0]['event']='修改后的候选分析，旧审查必须失效。'
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_copied_chapter_summary_is_not_close_reading(self):
        work,report=fixture()
        for field in ('event','character','bridge'):report['chapter_notes'][1][field]=report['chapter_notes'][0][field]
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_missing_dimension_or_self_review_cannot_pass(self):
        work,report=fixture();report['techniques'].pop()
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)
        work,report=fixture();report['peer_review']['reviewer_id']=report['producer']['worker_id']
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_author_note_excluded_but_narrator_aside_can_have_literary_function(self):
        work,report=fixture();report['nonstory_paragraphs']=[{'chapter':1,'paragraphs':[1],'kind':'author_note'}]
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)
        work,report=fixture();report['nonstory_paragraphs']=[{'chapter':1,'paragraphs':[1],'kind':'narrator_aside'}]
        report['peer_review']['reviewed_payload_sha256']=study.payload_sha(report)
        study.validate(work,report,require_host=False)

    def test_anchor_ids_cannot_alias_another_chapter_or_paragraph_reference(self):
        work,report=fixture()
        old=work['chapters'][1]['reading_evidence'][0]['id']
        work['chapters'][1]['reading_evidence'][0]['id']='c1-p1'
        report['chapter_notes'][1]['evidence'][0]='c1-p1'
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)
        work,report=fixture();work['chapters'][0]['reading_evidence'][0]['id']='paragraph:20:1'
        report['chapter_notes'][0]['evidence'][0]='paragraph:20:1'
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_malformed_report_containers_fail_with_validation_error(self):
        for field,value in [('producer',[]),('peer_review',[]),('nonstory_paragraphs',{} )]:
            work,report=fixture();report[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_changed_anchor_or_url_invalidates_actual_review_payload(self):
        for field,value in [('quote','另一个合法长度的测试短句'),('url','https://example.org/changed')]:
            work,report=fixture()
            if field=='quote':work['chapters'][0]['reading_evidence'][0][field]=value[:8]
            else:work['chapters'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):study.validate(work,report,require_host=False)
            report['source_context_sha256']=study.source_context_sha(work)
            with self.subTest(updated_context=field),self.assertRaises(ValueError):study.validate(work,report,require_host=False)

    def test_duplicate_chapter_cannot_validate_one_row_and_resolve_another(self):
        work,report=fixture();bad=copy.deepcopy(work['chapters'][0]);bad['body_sha256']='0'*64
        work['chapters'].insert(0,bad)
        with self.assertRaises(ValueError):study.validate(work,report,require_host=False)
        with self.assertRaises(ValueError):study.evidence(work,'c1-p1')
