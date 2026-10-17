#!/usr/bin/env python3
"""Behavior tests against the real Core CLI, using isolated configuration/PATH."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

BINARY = None


class CoreAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zako-core-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.config.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = {**os.environ, "ZAKO_CONFIG_DIR": str(self.config), "PATH": str(self.bin)}

    def executable(self, name, mode=0o755):
        path = self.bin / name
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(mode)

    def configure(self, text):
        (self.config / "config.toml").write_text(text)

    def call(self, *args, ok=True):
        result = subprocess.run([BINARY, *args], env=self.env, capture_output=True, text=True, timeout=3)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def event(self, command="false", code=1, failures=0, now=100_000, last=0, sample="0"):
        return json.loads(self.call("event", "--command", command, "--exit-code", str(code),
            "--failures", str(failures), "--now-ms", str(now), "--last-interaction-ms", str(last),
            "--sample", sample, "--json").stdout)

    def suggestions(self, command):
        return json.loads(self.call("suggest", "--command", command).stdout)

    def test_nonzero_classification(self):
        for cmd in ["grep missing fixture", "rg missing fixture", "diff a b", "test -e missing", "[ -e missing ]"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.event(cmd, 1, 2)["failure_class"], "neutral")
                response = self.event(cmd, 2, 2)
                self.assertEqual(response["failure_class"], "unknown")
                self.assertEqual(response["consecutive_failures"], 3)
        for cmd in ["grep missing file | cat", "if false; then true; fi", "grep 'x' file"]:
            self.assertEqual(self.event(cmd, 1)["failure_class"], "unknown")

    def test_interrupt_and_success_reset(self):
        for code, klass in [(0, "success"), (130, "interrupted"), (148, "interrupted")]:
            result = self.event("false", code, 9)
            self.assertEqual(result["failure_class"], klass)
            self.assertEqual(result["consecutive_failures"], 0)

    def test_cooldown_and_third_failure(self):
        self.assertTrue(self.event(last=99_000)["message"] == "")
        third = self.event(failures=2, last=99_000)
        self.assertIn("连续失败 3", third["message"])
        self.assertEqual(self.event(failures=3, last=99_000)["message"], "")
        self.assertTrue(self.event(failures=4, now=121_000, last=100_000)["message"])
        self.assertEqual(self.event(failures=5, now=121_001, last=121_000)["message"], "")

    def test_probability_profiles_and_styles(self):
        self.assertTrue(self.event("true", 0, sample="0.349")["message"])
        self.assertEqual(self.event("true", 0, sample="0.35")["message"], "")
        self.assertEqual(self.event("true", 0, last=99_000)["message"], "")
        self.configure('[interaction]\nprofile="quiet"\n')
        self.assertEqual(self.event(failures=2)["message"], "")
        self.configure('[interaction]\nprofile="chatty"\n')
        self.assertTrue(self.event("true", 0, sample="0.99")["message"])
        self.assertEqual(self.event("true", 0, last=99_000)["message"], "")
        messages = set()
        for style in ["gentle", "normal", "spicy"]:
            self.configure(f'[persona]\nstyle="{style}"\n')
            messages.add(self.event("true", 0)["message"])
        self.assertEqual(len(messages), 3)

    def test_known_corrections(self):
        self.executable("git")
        self.assertEqual(self.suggestions("gti status")[0]["command"], "git status")
        self.assertEqual(self.suggestions("git comit")[0]["command"], "git commit")
        self.assertEqual(self.event("git comit", 1)["failure_class"], "correctable")
        # Existing command failures are not assumed to be spelling mistakes.
        self.assertEqual(self.event("gti status", 2)["suggestions"], [])
        self.executable("gti")
        self.assertEqual(self.suggestions("gti status"), [])

    def test_safe_candidates_and_limits(self):
        for command in ["cat", "date", "cut", "rm", "sudo"]:
            self.executable(command)
        values = self.suggestions("dat fixture")
        self.assertEqual({v["command"] for v in values}, {"cat fixture", "date fixture"})
        self.configure('[correction]\nmax_suggestions=1\n')
        self.assertEqual(len(self.suggestions("dat fixture")), 1)
        self.assertEqual(self.suggestions("rmm fixture"), [])
        self.assertEqual(self.suggestions("sud fixture"), [])
        self.executable("git", mode=0o644)
        self.assertEqual(self.suggestions("gti status"), [])
        (self.bin / "git").unlink()
        (self.bin / "git").mkdir()
        self.assertEqual(self.suggestions("gti status"), [])

    def test_reject_unsafe_syntax_and_actions(self):
        self.executable("git")
        for text in ["gti status | cat", "gti status > x", "gti $(id)", "gti `id`", "gti *", "gti [abc]", "gti ~", "gti {a,b}",
                     "gti 'status'", 'gti "status"', "gti status\ntrue", "gti\tstatus", "gti status\r", "gti status\x1b",
                     "sudo gti status", "gti push --force", "gti push -uf", "gti reset --hard", "gti clean -fd", "gti branch -D x"]:
            with self.subTest(text=text):
                self.assertEqual(self.suggestions(text), [])
        self.assertFalse((self.root / "x").exists())

    def test_disabled_and_config_errors(self):
        self.executable("git")
        for source in ['[general]\nenabled=false\n', '[correction]\nenabled=false\n']:
            self.configure(source)
            self.assertEqual(self.suggestions("gti status"), [])
            self.assertEqual(self.event("gti status", 127)["suggestions"], [])
        for source in ['broken = [', '[interaction]\nsuccess_probability=2.0', '[general]\nlanguage="en"',
                       '[privacy]\ntelemetry=true', '[correction]\nmax_suggestions=0', '[persona]\nnickname="bad\\u001b"',
                       '[general]\nenabld=false']:
            self.configure(source)
            self.call("doctor", ok=False)

    def test_argument_protocol_boundaries(self):
        for args in [("--protocol-version", "9"), ("--event", "bogus"), ("--sample", "NaN"),
                     ("--sample", "1.1"), ("--unknown", "0"), ("--exit-code", "x"), ("--command",),
                     ("--json", "--json")]:
            self.call("event", *args, ok=False)
        # A value equal to a flag must remain data, not become a second option.
        response = self.call("event", "--command", "--json", "--exit-code", "1").stdout
        self.assertFalse(response.startswith("{"))
        value = json.loads(self.call("event", "--command", "--exit-code", "--exit-code", "127", "--json").stdout)
        self.assertEqual(value["failure_class"], "unknown")

    def test_snapshot_and_json(self):
        session = json.loads(self.call("session", "--json").stdout)
        snapshot = session["config_json"]
        self.configure("not valid [")
        result = self.call("event", "--config-json", snapshot, "--command", "true", "--exit-code", "0", "--json")
        self.assertEqual(json.loads(result.stdout)["failure_class"], "success")

    def test_transport_completion(self):
        for command, count in [("session", 6), ("event", 13)]:
            result = self.call("--shell-transport", command).stdout.splitlines()
            self.assertEqual(result[-1], "S:0")
            self.assertEqual(len(result[0].split("\x1f")), count)
        for args in [("event", "--protocol-version", "9"), ("doctor",)]:
            result = self.call("--shell-transport", *args, ok=False)
            self.assertNotIn("S:0", result.stdout)
        self.configure("broken = [")
        self.assertNotIn("S:0", self.call("--shell-transport", "session", ok=False).stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    args = parser.parse_args()
    BINARY = str(Path(args.binary).resolve())
    unittest.main(argv=[__file__], verbosity=2)
