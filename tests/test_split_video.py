import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "split_video.py"
SPEC = importlib.util.spec_from_file_location("split_video", MODULE_PATH)
assert SPEC and SPEC.loader
splitter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(splitter)


class SplitVideoTests(unittest.TestCase):
    def test_safe_stem_keeps_chinese_and_removes_path_characters(self):
        self.assertEqual(splitter.safe_stem(" 爆款视频一/汽车:用品.mp4 "), "爆款视频一-汽车-用品.mp4")

    def test_unique_output_dir_uses_expected_chinese_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(splitter.unique_output_dir(root, "爆款视频一"), root / "爆款视频一镜头分割")
            (root / "爆款视频一镜头分割").mkdir()
            self.assertEqual(splitter.unique_output_dir(root, "爆款视频一"), root / "爆款视频一镜头分割-2")

    def test_merge_short_segments_filters_adjacent_cuts(self):
        self.assertEqual(splitter.merge_short_segments([0.1, 0.6, 0.7, 1.4], 2.0, 0.35), [0.0, 0.6, 1.4, 2.0])


if __name__ == "__main__":
    unittest.main()
