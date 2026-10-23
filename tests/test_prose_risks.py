"""Editorial risks are scoped evidence, never authorship detection."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from tests.support import project,put
from tests.test_writing_spec import configured
import creative_workflow as flow
import prose_risks as prose


def clear_report(p,text,cid='V01-C01'):
    scan=prose.scan(p,cid,text)
    cite={'quote':text,'start':0,'end':len(text)}
    return {'scan_id':scan['scan_id'],
        'categories':[{'id':key,'verdict':'clear','rationale':'协议夹具，不声称实际文风验收。','citations':[cite]} for key in prose.CATEGORIES],
        'findings':[{'id':f['id'],'disposition':'intentional','rationale':'仅测试已解释保留分支，非外部读者认可。',
                     'citations':[{'quote':f['quote'],'start':f['start'],'end':f['end']}]} for f in scan['findings']]}


class ProseRisks(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.p=project(Path(tmp.name))

    def test_corpus_original_context_and_controls(self):
        value=prose.corpus(self.p)
        self.assertGreaterEqual(len(value['entries']),32)
        self.assertEqual({x['category'] for x in value['entries']},set(prose.CATEGORIES))
        for row in value['entries']:
            self.assertEqual(row['source'],'original_editorial_example')
            self.assertTrue(all(row[k] for k in ('context','bad','revision','why','preserves','exceptions','valid_example')))

    def test_exact_scan_is_nonmutating_and_not_identity_score(self):
        text='他把辞退通知折进兜里，反复按着那道折痕，心中涌起一股无法言说的复杂情绪。'
        result=prose.scan(self.p,'V01-C01',text)
        self.assertTrue(result['findings']);self.assertFalse(result['literary_quality_proven'])
        self.assertNotIn('AI率',json.dumps(result,ensure_ascii=False))
        for row in result['findings']:self.assertEqual(text[row['start']:row['end']],row['quote'])
        self.assertEqual(result,prose.scan(self.p,'V01-C01',text))

    def test_zero_hits_still_requires_all_context_checks(self):
        text='他核对登记，约好明早再来。'
        self.assertEqual(prose.scan(self.p,'V01-C01',text)['findings'],[])
        result=clear_report(self.p,text);prose.verify_report(self.p,'V01-C01',text,result)
        result['categories'].pop()
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',text,result)

    def test_pending_and_missed_findings_do_not_pass(self):
        text='他心中涌起一股无法言说的复杂情绪。';result=clear_report(self.p,text)
        bad=copy.deepcopy(result);bad['findings'].pop()
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',text,bad)
        bad=copy.deepcopy(result);bad['findings'][0]['disposition']='uncertain'
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',text,bad)
        prose.verify_report(self.p,'V01-C01',text,bad,require_resolved=False)
        bad=copy.deepcopy(result);bad['findings'][0]['disposition']='needs_revision'
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',text,bad)
        bad=copy.deepcopy(result);bad['findings'][0]['citations']=[{'quote':'完全没有'}]
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',text,bad)

    def test_body_corpus_and_protection_changes_invalidate(self):
        text='他心中涌起一股无法言说的复杂情绪。';report=clear_report(self.p,text)
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',text+'天亮了。',report)
        put(self.p/'prose_risks.json',{'schema_version':'1','entries':[],'protections':[]})
        with self.assertRaises(ValueError):prose.verify_report(self.p,'V01-C01',text,report)

    def test_exact_protection_is_annotation_not_auto_pass(self):
        text='他心中涌起一股无法言说的复杂情绪。';f=prose.scan(self.p,'V01-C01',text)['findings'][0]
        value={'schema_version':'1','entries':[],'protections':[{'id':'keep1','chapter_id':'V01-C01','rule_id':f['rule_id'],
            'candidate_sha256':flow.digest(text.encode()),'quote':f['quote'],'start':f['start'],'end':f['end'],
            'reason':'作者讨论的有意复现','author_quote':'保留此处表达'}]}
        put(self.p/'prose_risks.json',value)
        result=prose.scan(self.p,'V01-C01',text);self.assertEqual(result['findings'][0]['protected_by'],['keep1'])
        self.assertTrue(result['requires_context_review'])
        changed=prose.scan(self.p,'V01-C01',text+'天亮了。');self.assertEqual(changed['findings'][0]['protected_by'],[])
        self.assertNotIn('保留此处表达',json.dumps(result,ensure_ascii=False))

    def test_repeat_and_capacity_no_silent_truncation(self):
        text='他照着登记簿逐个念出名字，然后等候对方答复。\n\n'*3
        result=prose.scan(self.p,'V01-C01',text)
        self.assertTrue(any(x['rule_id']=='repeat_paragraph' for x in result['findings']))
        with self.assertRaises(ValueError):prose.scan(self.p,'V01-C01','无法言说的复杂情绪。'*300)

    def test_private_corpus_cannot_execute_regex(self):
        put(self.p/'prose_risks.json',{'schema_version':'1','entries':[],'protections':[],'regex':'(a+)+$'})
        with self.assertRaises(ValueError):prose.corpus(self.p)

    def test_configured_contract_freezes_editor(self):
        configured(self.p,single=True)
        run=flow.start(self.p,'V01-C01')['run_id'];folder,m=flow._manifest(self.p,run)
        self.assertEqual(flow.getjson(folder/'contract.json')['prose_risks'],prose.metadata(self.p))
        put(self.p/'prose_risks.json',{'schema_version':'1','entries':[],'protections':[]})
        with self.assertRaises(ValueError):
            import writing_spec;writing_spec.assert_contract(self.p,'V01-C01',flow.getjson(folder/'contract.json'))

    def test_needs_revision_requires_issue_and_recheck(self):
        from tests.test_stages import craft_review
        import writing_spec
        configured(self.p,single=True,origin='tool_default')
        body='他把辞退通知折进兜里，反复按着那道折痕，心中涌起一股无法言说的复杂情绪。'
        path=self.p/'draft.md';path.write_text(body,encoding='utf-8')
        run=flow.start(self.p,'V01-C01')['run_id'];flow.submit(self.p,run,path)
        contextual=clear_report(self.p,body);contextual['findings'][0]['disposition']='needs_revision'
        report={'reviewer_type':'agent','issues':[],'summary_citations':[{'quote':body}],
                'writing_spec_review':craft_review(self.p,body),'prose_risks_review':contextual}
        dest=self.p/'report.json';put(dest,report)
        with self.assertRaises(ValueError):flow.review(self.p,run,dest)
        report['issues']=[{'code':'PROSE_REVIEW','severity':'MINOR','evidence':'协议夹具：须改后重审',
                          'citations':[{'quote':body}],'prose_targets':['finding:'+contextual['findings'][0]['id']]}]
        put(dest,report);flow.review(self.p,run,dest)
        with self.assertRaises(ValueError):writing_spec.assert_run(self.p,run,require_review=True)
        with self.assertRaises(ValueError):flow.approve(self.p,run,'fixture_author')

    def test_stage_finding_single_character_cannot_pass(self):
        import stage_gates as gates
        text='他有无法言说的复杂情绪。';sha=flow.digest(text.encode())
        target='prose:finding:F1';a=text.index('无法');b=a+len('无法言说的复杂情绪')
        packet={'mode':'synthetic_test','packet_sha256':'packet','work_sha256':sha,'work':text,'review_targets':[target],
                'items':[],'prose_scope_spans':{target:[[a,b]],'prose:category:emotion_restatement':[[0,len(text)]]}}
        receipt={'source':'synthetic_test','worker_id':'reviewer','invocation_id':'review','host_thread_id':None,'context_claim':'test_only'}
        report={'packet_sha256':'packet','read_sha256':sha,'checks':[{'target':target,'verdict':'pass','reason':'仅测试引文覆盖',
                    'citations':[{'quote':'无','start':a,'end':a+1}]}],'unresolved':[],'limitations':'合成测试，不是语义验收'}
        with self.assertRaises(ValueError):gates._validate_report(packet,report,receipt,{'worker_id':'writer','invocation_id':'write'})
        report['checks'][0]['citations']=[{'quote':text[a:b],'start':a,'end':b}]
        self.assertTrue(gates._validate_report(packet,report,receipt,{'worker_id':'writer','invocation_id':'write'}))
