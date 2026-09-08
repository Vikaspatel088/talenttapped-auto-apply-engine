import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from engine.core import engine
from engine.core.models import ApplyResult, ApplyStatus, Profile
class EngineContractTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self): self.original_runs_dir=engine.RUNS_DIR;self.original_runner=engine._run_adapter;self.temp_dir=tempfile.TemporaryDirectory();engine.RUNS_DIR=Path(self.temp_dir.name)
 def tearDown(self): engine.RUNS_DIR=self.original_runs_dir;engine._run_adapter=self.original_runner;self.temp_dir.cleanup()
 async def test_detects_supported_hosts(self):
  self.assertEqual(engine.detect_ats('https://jobs.lever.co/acme/1').value,'lever');self.assertEqual(engine.detect_ats('https://job-boards.greenhouse.io/acme/jobs/1').value,'greenhouse');self.assertEqual(engine.detect_ats('https://jobs.ashbyhq.com/acme/1/application').value,'ashby');self.assertEqual(engine.detect_ats('https://apply.workable.com/acme/j/1/apply/').value,'workable');self.assertEqual(engine.detect_ats('https://example.com/jobs/1').value,'unknown')
 async def test_profile_round_trips_canonical_fields(self):
  p=Profile.from_dict({'personalInfo':{'fullName':'Jordan Lee','profiles':[{'label':'Portfolio','url':'https://example.com'}]},'preferences':{'work_mode':'remote'}});self.assertEqual(p.portfolio_url,'https://example.com');self.assertEqual(p.preferences['work_mode'],'remote')
 async def test_resume_pdf_extracts_candidate_profile_from_resume_text(self):
  with mock.patch('engine.core.models.extract_resume_text',return_value='Jane Doe\njane.doe@email.com\n+1 (415) 555-1212\ngithub.com/janedoe\nlinkedin.com/in/janedoe'):
   p=Profile.from_resume_pdf(b'%PDF-1.4');self.assertEqual(p.full_name,'Jane Doe');self.assertEqual(p.email,'jane.doe@email.com');self.assertEqual(p.github_url,'https://github.com/janedoe');self.assertEqual(p.linkedin_url,'https://linkedin.com/in/janedoe')
if __name__=='__main__':unittest.main()
