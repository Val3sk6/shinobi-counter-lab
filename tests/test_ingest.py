import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ingest_evidence as ingest

class TestEvidenceIntake(unittest.TestCase):
    def test_pairing_and_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'proposals.json'
            ingest.preview(ROOT / 'examples/demo_evidence.json', out)
            rows = json.loads(out.read_text(encoding='utf-8'))['candidates']
            self.assertEqual(len(rows), 3)
            ready = [x for x in rows if x['readyForReview']]
            self.assertEqual(len(ready), 2)
            self.assertEqual([x for x in rows if not x['readyForReview']][0]['sourceRef']['replyIsVideoAuthor'], False)
            self.assertIn('10%', [x for x in ready if x['channel'] == 'description'][0]['case']['lim'])
            self.assertEqual([x for x in ready if x['channel'] == 'comment'][0]['case']['lim'], '未提供')

    def test_manual_approval_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'proposals.json'
            ingest.preview(ROOT / 'examples/demo_evidence.json', out)
            cid = json.loads(out.read_text(encoding='utf-8'))['candidates'][0]['candidateId']
            with self.assertRaises(ValueError):
                ingest.approve(out, cid, '2026-10')
            with self.assertRaises(ValueError):
                ingest.approve(out, cid, 'unknown', confirmed=True)

    def test_team_requires_three_distinct_known_ninjas(self):
        names = ingest.names_index(ingest.read_json(ingest.HERO_FILE))
        self.assertIsNone(ingest.extract_team('对面只有百虎', names))
        self.assertIsNone(ingest.extract_team('百蛇百蛇百虎', names))
        self.assertEqual(len(ingest.extract_team('百蛇 普佩 百虎', names)), 3)

if __name__ == '__main__':
    unittest.main()
