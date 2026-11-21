"""Verify story instructions through the same entry points used by desks."""
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
import dispatch
import studio
import story_formulas


class TopFiveTeams(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / ".agents").symlink_to(PROJECT / ".agents", target_is_directory=True)
        self.episodes = self.root / "episodes"
        with redirect_stdout(io.StringIO()):
            studio.init(self.episodes, "trial", "주제")
        self.episode = self.episodes / "trial"
        self.path = self.episode / "analysis" / "handoff.json"

    def select(self, key):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data["story_formula"] = key
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_all_teams_on_brief_and_dispatch(self):
        self.assertEqual(studio.STAGES.keys(), story_formulas.DESKS.keys())
        # Supply accepted dependencies to exercise prompt generation for every desk.
        ready = {key: (i,) for i, key in enumerate(studio.STAGES, 1)}
        for formula, (label, question, cues) in story_formulas.CASES.items():
            self.select(formula)
            for stage, (action, check) in story_formulas.DESKS.items():
                with self.subTest(formula=formula, stage=stage):
                    out = io.StringIO()
                    with patch.object(sys, "argv", ["studio.py", "--root", str(self.episodes),
                                                    "brief", "trial", stage]), redirect_stdout(out):
                        studio.main()
                    with patch.object(studio, "ROOT", self.root), patch.object(studio, "accepted", return_value=(ready, {})):
                        _, prompt = dispatch.assignment("trial", stage)
                    for output in (out.getvalue(), prompt):
                        for expected in (label, question, cues, action, check, "benchmark/top5-stories.md"):
                            self.assertIn(expected, output)

    def test_existing_custom_and_unknown(self):
        original = self.path.read_bytes()
        text = story_formulas.brief(self.episode, "edit")
        for label, *_ in story_formulas.CASES.values():
            self.assertIn(label, text)
        self.assertEqual(original, self.path.read_bytes())
        self.select("custom")
        self.assertIn("선택: custom", story_formulas.brief(self.episode, "qa"))
        self.select("unknown")
        with self.assertRaisesRegex(ValueError, "story_formula"):
            studio.validate(self.episode / "analysis", "analysis")


if __name__ == "__main__":
    unittest.main()
