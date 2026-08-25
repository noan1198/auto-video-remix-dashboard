import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "split_video.py"
SPEC = importlib.util.spec_from_file_location("split_video_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
splitter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(splitter)


class SplitVideoRuntimeTests(unittest.TestCase):
    def test_runtime_python_path_is_distinct_even_when_venv_binary_is_a_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / ".splitter-runtime"
            expected = runtime / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            self.assertEqual(splitter.runtime_python(runtime), expected)
            self.assertNotEqual(Path(sys.executable).absolute(), expected.absolute())


if __name__ == "__main__":
    unittest.main()
