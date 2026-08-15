import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "local_api_server.py"
SPEC = importlib.util.spec_from_file_location("local_api_server", MODULE_PATH)
assert SPEC and SPEC.loader
local_api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(local_api)


class LocalApiTests(unittest.TestCase):
    def test_safe_label_keeps_readable_chinese_and_removes_path_characters(self):
        self.assertEqual(local_api.safe_label(" 今天的爆款/车载:收纳.mp4 "), "车载-收纳")

    def test_unique_work_dir_never_reuses_an_existing_task(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "work" / "2026-08-15-今日爆款").mkdir(parents=True)
            label, work_dir = local_api.unique_work_dir(root, "今日爆款", "2026-08-15")
            self.assertEqual(label, "今日爆款-2")
            self.assertEqual(work_dir, (root / "work" / "2026-08-15-今日爆款-2").resolve())

    def test_task_config_uses_one_whole_script_voice_request(self):
        config = local_api.task_config(1080, 1920)
        self.assertEqual(config["canvas"]["orientation"], "portrait")
        self.assertEqual(config["voice"]["mode"], "whole_script_single_request")
        self.assertEqual(config["voice"]["max_tts_requests"], 1)
        self.assertEqual(config["draft"]["target"], "none")


if __name__ == "__main__":
    unittest.main()
