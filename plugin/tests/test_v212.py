"""V2.12: the Claude-directory edition (lite/) and `kipcb settings --save`."""

import importlib.util
import json
import os
import tempfile
import unittest
from unittest import mock

from kipcb import learn

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "tools", "build_lite.py")


def _build_lite():
    spec = importlib.util.spec_from_file_location("build_lite", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LiteEditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _build_lite()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = cls.mod.build(os.path.join(cls.tmp.name, "lite"), version="9.9")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, rel):
        with open(os.path.join(self.out, rel), encoding="utf-8") as f:
            return f.read()

    def test_only_files_the_directory_accepts(self):
        self.assertEqual(self.mod.check(self.out), [])

    def test_no_hook_or_status_line_option(self):
        m = json.loads(self.read(".claude-plugin/plugin.json"))
        self.assertEqual(m["name"], "viaduct")
        self.assertEqual(m["version"], "9.9")
        self.assertNotIn("hooks", m)
        self.assertNotIn("progress_statusline", m["userConfig"])

    def test_every_skill_installs_the_matching_engine(self):
        for name in ("design", "fab", "inquiry", "review"):
            text = self.read("skills/%s/SKILL.md" % name)
            self.assertIn("## The kipcb engine", text, name)
            self.assertIn("archive/refs/tags/v9.9.tar.gz", text, name)
            self.assertIn("AskUserQuestion before downloading", text, name)
            self.assertNotIn("on PATH", text, name)
            self.assertNotIn("bin/kipcb`)", text, name)
        self.assertIn("${user_config.fab_house}", self.read("skills/design/SKILL.md"))
        self.assertNotIn("status bar", self.read("skills/design/SKILL.md"))
        self.assertIn(".viaduct/engine/9.9/plugin/bin/kipcb", self.read("agents/circuit-reviewer.md"))

    def test_check_catches_code(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".claude-plugin"))
            with open(os.path.join(d, ".claude-plugin", "plugin.json"), "w") as f:
                f.write('{"name": "x"}')
            with open(os.path.join(d, "run.md"), "w") as f:
                f.write("#!/bin/sh\n")
            with open(os.path.join(d, "tool.py"), "w") as f:
                f.write("print(1)\n")
            os.makedirs(os.path.join(d, "bin"))
            problems = " ".join(self.mod.check(d))
            for word in ("run.md", "tool.py", "bin/"):
                self.assertIn(word, problems)


class SaveSettingsTests(unittest.TestCase):
    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(learn, "data_dir", return_value=d):
            learn.save_settings("PCBWay", "Hand soldering", "4", "false")
            self.assertEqual(learn.settings(), {"fab_house": "PCBWay", "build_method": "Hand soldering",
                                                "layers": 4, "learning": False})
            learn.save_settings(layers="Auto", learning="true")
            s = learn.settings()
            self.assertEqual((s["fab_house"], s["layers"], s["learning"]), ("PCBWay", "auto", True))


if __name__ == "__main__":
    unittest.main()
