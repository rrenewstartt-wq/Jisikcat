"""Exercise reference review and release through the same CLI the desks use."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


STUDIO = Path(__file__).resolve().parents[1] / "tools" / "studio.py"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", *args],
                   capture_output=True, text=True, check=True)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
class ReleaseReviewTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.episode = self.root / "trial"
        self.cli("init", "trial", "--topic", "검수 테스트")
        for handoff in self.episode.glob("*/handoff.json"):
            questions = json.loads(handoff.read_text(encoding="utf-8"))
            write_json(handoff, {q: "테스트 회차의 인계 내역" for q in questions})
        for name in ("analysis/observations", "planning/brief", "script/script", "script/facts",
                     "marketing/metadata", "qa/review", "release/delivery"):
            (self.episode / (name + ".md")).write_text(name + " 검토용", encoding="utf-8")
        write_json(self.episode / "assets/sources.json", [
            dict(asset="테스트 영상", source="FFmpeg", license="자체 제작",
                 evidence="테스트 코드의 생성 명령", credit="테스트")])
        self.evidence = self.episode / "evidence"
        self.reference = dict(channel_id="UCi9Sl8GnFdYoqEVXnojBPJw", video_id="fixture0001",
                              selection_reason="합성 비교용 영상", origin_note="로컬 FFmpeg 생성")
        write_json(self.evidence / "reference.json", self.reference)
        ffmpeg("-f", "lavfi", "-i", "color=blue:s=320x180:r=10", "-f", "lavfi",
               "-i", "sine=frequency=440:sample_rate=48000", "-t", "3", "-c:v", "mpeg4",
               "-c:a", "aac", str(self.evidence / "reference.mp4"))
        ffmpeg("-i", str(self.evidence / "reference.mp4"), "-vn",
               str(self.episode / "audio/narration.wav"))
        ffmpeg("-i", str(self.evidence / "reference.mp4"), "-frames:v", "1",
               str(self.evidence / "reference.jpg"))
        self.thumbnail = self.episode / "thumbnail/thumbnail.jpg"
        ffmpeg("-f", "lavfi", "-i", "color=white:s=320x180", "-frames:v", "1", str(self.thumbnail))
        (self.evidence / "reference.srt").write_text(
            "1\n00:00:00,000 --> 00:00:02,000\n테스트 자막\n", encoding="utf-8")
        shutil.copyfile(self.evidence / "reference.mp4", self.episode / "edit/master.mp4")
        shutil.copyfile(self.evidence / "reference.srt", self.episode / "edit/captions.srt")

    def cli(self, *args, error=None):
        result = subprocess.run([sys.executable, str(STUDIO), "--root", str(self.root), *args],
                                capture_output=True, text=True)
        if error is None:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, args)
            self.assertIn(error, result.stderr)
        return result.stdout

    def submit(self, stage, author="producer", error=None):
        return self.cli("submit", "trial", stage, "--by", author, error=error)

    def reviewed_inputs(self):
        brief = self.cli("brief", "trial", "comparison")
        return json.JSONDecoder().raw_decode(brief.split("reviewed_inputs ", 1)[1])[0]

    def test_quality_gates_and_invalidation(self):
        self.submit("analysis")
        write_json(self.evidence / "reference.json", dict(self.reference, channel_id="wrong"))
        self.submit("evidence", error="채널")
        write_json(self.evidence / "reference.json", self.reference)
        for stage in ("evidence", "planning", "script", "assets", "thumbnail",
                      "audio", "edit", "marketing"):
            self.submit(stage)

        score_path = self.episode / "comparison/scorecard.json"
        dimensions = json.loads(score_path.read_text(encoding="utf-8"))
        score = {key: dict(reference_at="00:00:01", candidate_at="00:00:01",
                           finding="합성 장면을 같은 시각에서 비교함", verdict="pass")
                 for key in dimensions if key != "reviewed_inputs"}
        score["reviewed_inputs"] = self.reviewed_inputs()
        score_path.unlink()
        self.submit("comparison", "reviewer", error="필수 파일")
        write_json(score_path, score)
        self.submit("comparison", "PRODUCER", error="별도 검수자")
        self.submit("comparison", "reviewer", error="thumbnail_mean_gray")
        self.submit("release", "operator", error="선행")

        shutil.copyfile(self.evidence / "reference.jpg", self.thumbnail)
        self.submit("thumbnail")
        self.submit("marketing")
        self.submit("comparison", "reviewer", error="버전 불일치")
        score["reviewed_inputs"] = self.reviewed_inputs()
        write_json(score_path, score)
        self.submit("comparison", "reviewer")
        self.submit("qa", "Reviewer", error="별도 검수자")
        self.submit("qa", "independent-qa")
        self.submit("release", "operator")
        self.assertRegex(self.cli("status", "trial"), r"release\s+접수 #")

        (self.episode / "edit/captions.srt").write_text(
            "1\n00:00:00,000 --> 00:00:02,000\n변경된 자막\n", encoding="utf-8")
        self.assertRegex(self.cli("status", "trial"), r"release\s+재제출 필요")
        self.submit("release", "operator", error="선행")


if __name__ == "__main__":
    unittest.main()
