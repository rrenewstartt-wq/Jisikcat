"""Exercise temporal checks on decoded video, audio and caption fixtures."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import media, parity_metrics


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-nostdin", "-loglevel", "error", *args],
                   check=True, capture_output=True)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
class TemporalTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.episode = Path(temp.name)
        for name in ("evidence", "edit", "thumbnail"):
            (self.episode / name).mkdir()
        self.reference = self.episode / "evidence/reference.mp4"
        self.master = self.episode / "edit/master.mp4"
        self.caption = self.episode / "edit/captions.srt"
        self.ref_caption = self.episode / "evidence/reference.srt"
        self.ref_caption.write_text("1\n00:00:01,000 --> 00:00:02,000\n검수 자막\n")
        shutil.copyfile(self.ref_caption, self.caption)
        ffmpeg("-f", "lavfi", "-i", "testsrc2=size=96x64:rate=10:duration=12",
               "-f", "lavfi", "-i", "sine=frequency=440:duration=12",
               "-c:v", "mpeg4", "-c:a", "aac", self.reference)
        shutil.copyfile(self.reference, self.master)
        thumb = self.episode / "evidence/reference.jpg"
        ffmpeg("-i", self.reference, "-frames:v", "1", thumb)
        shutil.copyfile(thumb, self.episode / "thumbnail/thumbnail.jpg")

    def test_shifted_cue_preserves_all_old_caption_metrics(self):
        self.caption.write_text("1\n00:00:13,000 --> 00:00:14,000\n검수 자막\n")
        self.assertEqual(media.caption_metrics(self.caption), media.caption_metrics(self.ref_caption))
        with self.assertRaisesRegex(ValueError, "자막 시각 범위"):
            parity_metrics.compare(self.episode)

    def test_silent_tail_with_normal_integrated_loudness(self):
        ffmpeg("-i", self.reference, "-c:v", "copy", "-af", "atrim=duration=7",
               "-c:a", "aac", self.master)
        self.assertLess(abs(parity_metrics.integrated_lufs(self.reference)
                            - parity_metrics.integrated_lufs(self.master)), 2)
        with self.assertRaisesRegex(ValueError, "silence_longest_s"):
            parity_metrics.compare(self.episode)

    def test_black_frozen_tail_and_static_reference(self):
        ffmpeg("-i", self.reference, "-vf", "drawbox=color=black:t=fill:enable='gte(t,4)'",
               "-c:v", "mpeg4", "-c:a", "copy", self.master)
        with self.assertRaises(ValueError) as error:
            parity_metrics.compare(self.episode)
        self.assertIn("black_longest_s", str(error.exception))
        self.assertIn("freeze_longest_s", str(error.exception))
        # A deliberate long still in the reference may also occur in the candidate.
        shutil.copyfile(self.master, self.reference)
        pairs = parity_metrics.compare(self.episode)
        self.assertGreater(pairs["freeze_longest_s"]["reference"], 7.5)
        self.assertGreater(pairs["black_total_s"]["candidate"], 7.5)

    def test_short_pause_and_overlapping_captions(self):
        ffmpeg("-i", self.reference, "-c:v", "copy",
               "-af", "volume=enable='between(t,3,4)':volume=0", "-c:a", "aac", self.master)
        for path in (self.caption, self.ref_caption):
            path.write_text("1\n00:00:00,000 --> 00:00:02,000\n첫 화자\n\n"
                            "2\n00:00:01,900 --> 00:00:03,000\n두 번째 화자\n")
        self.assertEqual(parity_metrics.compare(self.episode)["silence_longest_s"]["candidate"], 0)


if __name__ == "__main__":
    unittest.main()
