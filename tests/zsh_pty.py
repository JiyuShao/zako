#!/usr/bin/env python3
"""Real-terminal end-to-end checks for Zsh and the installed target plugins."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time
import unittest
from terminal import ROOT, Terminal, plain, versions

BINARY = None
PROFILE = "clean"
ORDER = "after"


class ZshAcceptance(unittest.TestCase):
    def setUp(self):
        self.shell = Terminal(BINARY, PROFILE, ORDER)
        self.addCleanup(self.shell.close)

    def test_command_status_and_hook_chain(self):
        for command, expected in [("true", 0), ("false", 1), ("(exit 2)", 2), ("__zako_missing_command__", 127), ("(exit 130)", 130), ("false | true", 0)]:
            with self.subTest(command=command):
                self.shell.command(command)
                state = self.shell.state()
                self.assertEqual(int(state["native"]), expected)
                self.assertEqual(int(state["before"]), expected)
                self.assertEqual(int(state["after"]), expected)
                self.assertEqual(state["before_count"], state["after_count"])
        self.shell.command("setopt pipefail")
        self.shell.command("false | true")
        self.assertEqual(self.shell.state()["native"], "1")
        self.assertIn("OUTPUT-sentinel", self.shell.command("print -r -- OUTPUT-sentinel"))

    def test_target_lifecycle_and_no_execution(self):
        subprocess.run(["git", "init", "-q", str(self.shell.work)], check=True, timeout=5)
        self.shell.command("gti status")
        self.assertIn("建议：git status", self.shell.command("zako fix"))
        self.assertEqual(self.shell.state()["count"], "1")
        self.shell.command("zako doctor")
        self.assertEqual(self.shell.state()["count"], "1")
        self.shell.command("true")
        self.assertEqual(self.shell.state()["count"], "0")

        self.shell.command("git comit")
        self.assertIn("建议：git commit", self.shell.command("zako fix"))
        self.assertFalse((self.shell.work / ".git/refs/heads/main").exists())
        self.shell.command("cd ..")
        self.assertEqual(self.shell.state()["count"], "0")
        self.assertIn(str(self.shell.root), self.shell.command("pwd"))
        self.shell.command("gti status")
        self.shell.command("zako status; true")
        self.assertEqual(self.shell.state()["count"], "0")

    def test_session_stats_and_reset(self):
        self.shell.command("true")
        self.shell.command("false")
        self.shell.command("gti status")
        output = self.shell.command("zako stats")
        self.assertIn("commands=3", output)
        self.assertIn("successes=1", output)
        self.assertIn("failures=2", output)
        self.assertIn("corrections=1", output)
        self.shell.command("gti status")
        self.shell.command("zako stats reset")
        output = self.shell.command("zako stats")
        self.assertIn("commands=0 successes=0 failures=0 corrections=0", output)

    def test_achievements_config_and_session_isolation(self):
        config = '[interaction]\ncooldown_seconds=0\nsuccess_probability=1.0\n[session]\nsuccess_streak_goal=2\nfailure_milestone=2\n'
        with Terminal(BINARY, PROFILE, ORDER, config=config) as other:
            other.command("true")
            self.assertIn("连胜小天才", other.command("true"))
            self.assertNotIn("成就解锁", other.command("true"))
            other.command("false")
            self.assertIn("不服输的杂鱼", other.command("false"))
            output = other.command("zako stats")
            self.assertIn("other:2", output)
            self.assertIn("best_streak=3", output)
            other.command("zako off")
            other.command("false")
            other.command("zako on")
            self.assertIn("commands=5", other.command("zako stats"))
            other.command("zako stats reset")
            other.command("true")
            self.assertIn("连胜小天才", other.command("true"))
            self.assertIn("commands=2", other.command("zako stats"))
            self.assertIn('"commands":2', other.command("zako stats --json"))
            other.command("gti status")
            self.assertIn("已保存", other.command("zako config set persona.intensity 5"))
            self.assertEqual(other.state()["count"], "1")
            self.assertIn("intensity = 5", other.command("zako config show"))
            self.assertEqual(other.state()["enabled"], "1")
        self.assertIn("commands=0", self.shell.command("zako stats"))
        with Terminal(BINARY, PROFILE, ORDER, config='[session]\nenabled=false\n[interaction]\nfailure_budget=false\n') as other:
            other.command("false")
            self.assertIn("已关闭", other.command("zako stats"))
            self.assertEqual(other.state()["native"], "0")

    def test_multiple_candidates_and_empty_fields(self):
        self.shell.command("dat fixture")
        self.assertGreaterEqual(int(self.shell.state()["count"]), 2)
        output = self.shell.command("zako fix")
        self.assertIn("建议：cat fixture", output)
        self.assertIn("建议：date fixture", output)
        self.shell.command("true")
        self.shell.command("true")
        self.assertIn(self.shell.state()["mood"], ["happy", "proud"])
        self.assertNotIn("配置无效", self.shell.transcript)

    def test_on_off_prompt_and_user_takeover(self):
        self.assertEqual(self.shell.state()["owned"], "1")
        self.shell.command("zako off")
        state = self.shell.state()
        self.assertEqual(state["prompt"], "")
        self.assertEqual(state["enabled"], "0")
        self.shell.command("false")
        self.assertEqual(self.shell.state()["native"], "1")
        self.shell.command("zako on")
        state = self.shell.state()
        self.assertEqual(state["enabled"], "1")
        self.assertEqual(state["owned"], "1")
        self.assertNotEqual(state["prompt"], "")
        self.shell.command("RPROMPT=user-owned")
        self.shell.command("zako off")
        self.shell.command("zako on")
        state = self.shell.state()
        self.assertEqual(state["prompt"], "user-owned")
        self.assertEqual(state["owned"], "0")
        self.assertIn("RPROMPT", self.shell.command("zako doctor"))

    def test_expected_nonzero_and_real_errors(self):
        (self.shell.work / "a").write_text("alpha\n")
        (self.shell.work / "b").write_text("beta\n")
        for command in ["grep missing a", "diff a b", "test -e missing", "[ -e missing ]"]:
            self.shell.command("false")
            self.shell.command(command)
            self.assertEqual(self.shell.state()["failures"], "0", command)
        self.shell.command("grep x no-such-file")
        self.assertEqual(self.shell.state()["failures"], "1")

    def test_third_failure_cooldown_and_recovery(self):
        self.shell.command("false")
        self.shell.command("false")
        output = self.shell.command("false")
        self.assertIn("连续失败 3", output)
        self.assertNotIn("连续失败", self.shell.command("false"))
        # Advance only the session timestamp, never change production defaults.
        self.assertIn("失败预算", self.shell.command("_ZAKO_LAST_INTERACTION_MS=1; false"))
        self.assertNotIn("杂鱼", self.shell.command("false"))
        self.shell.command("true")
        self.assertEqual(self.shell.state()["failures"], "0")

    def test_actual_ctrl_c(self):
        self.shell.command("false")
        self.shell.send("/bin/sh -c 'printf \"INTERRUPT_READY\\n\"; exec /bin/sleep 30'\n")
        self.shell.read_until(b"INTERRUPT_READY\r\n", timeout=3)
        self.shell.send(b"\x03")
        self.shell.read_prompt(timeout=3)
        state = self.shell.state()
        self.assertEqual(state["native"], "130")
        self.assertEqual(state["failures"], "0")
        self.assertEqual(state["mood"], "idle")
        self.assertIn("alive-after-interrupt", self.shell.command("echo alive-after-interrupt"))

    def test_repeat_source_eval_and_options(self):
        self.shell.command(f"source {shlex.quote(str(ROOT / 'integrations/zako.zsh'))}")
        self.shell.command('eval "$(command zako init zsh)"; print -r -- still-running')
        output = self.shell.command("print -r -- HOOKS:${(j:,:)precmd_functions}")
        actual = re.search(r"^HOOKS:([^\n]+)", output, re.M).group(1)
        self.assertEqual(actual.split(",").count("_zako_precmd"), 1)
        self.assertEqual(self.shell.transcript.count("♡ 嘿，杂鱼，今天也别把代码写坏了哦？"), 1)
        self.shell.command("setopt shwordsplit ksharrays")
        self.shell.command("false")
        self.assertNotIn("配置无效", self.shell.transcript)
        self.shell.command("unsetopt shwordsplit ksharrays")

    def test_session_configuration_snapshot(self):
        self.shell.config.write_text("broken = [")
        self.shell.command("false")
        self.assertEqual(self.shell.state()["enabled"], "1")
        self.assertIn("config: ok", self.shell.command("zako doctor"))
        self.assertNotIn("配置无效", self.shell.transcript)
        with Terminal(BINARY, PROFILE, ORDER, config="broken = [") as other:
            self.assertEqual(other.state()["enabled"], "0")
            self.assertEqual(other.transcript.count("Zako 配置无效或 Core 不可用"), 1)
            other.command("false")
            self.assertEqual(other.state()["native"], "1")

    def test_initially_disabled_and_prompt_off(self):
        with Terminal(BINARY, PROFILE, ORDER, config='[general]\nenabled=false\n') as other:
            self.assertEqual(other.state()["enabled"], "0")
            self.assertNotIn("♡ 嘿", other.startup)
            other.command("zako on")
            self.assertEqual(other.state()["enabled"], "1")
            other.command("false")
            self.assertEqual(other.state()["failures"], "1")
        with Terminal(BINARY, PROFILE, ORDER, config='[prompt]\nmode="off"\n') as other:
            other.command("zako off")
            other.command("zako on")
            self.assertEqual(other.state()["owned"], "0")
            self.assertEqual(other.state()["prompt"], "")

    def test_noninteractive_and_uninstalled(self):
        env = {**os.environ, "ZAKO_CONFIG_DIR": str(self.shell.config.parent)}
        code = f"source {shlex.quote(str(ROOT / 'integrations/zako.zsh'))}; print -r -- noninteractive-only"
        result = subprocess.run(["zsh", "-dfc", code], env=env, capture_output=True, text=True, timeout=3)
        self.assertEqual(result.stdout, "noninteractive-only\n")
        self.assertEqual(result.stderr, "")
        with Terminal(BINARY, PROFILE, ORDER, integration=False) as other:
            self.assertNotIn("♡ 嘿", other.startup)
            self.assertEqual(other.state()["enabled"], "0")
            self.assertNotIn("_zako_precmd", other.command("print -r -- HOOKS:${(j:,:)precmd_functions}"))

    def test_faults_partial_invalid_missing_and_hung(self):
        with tempfile.TemporaryDirectory(prefix="zako-faults-") as directory:
            root = Path(directory)
            good = subprocess.check_output([BINARY, "event", "--command", "false", "--exit-code", "1"], env={**os.environ, "ZAKO_CONFIG_DIR": directory}, text=True).strip()
            fields = good.split("\x1f")
            invalid_number = fields.copy(); invalid_number[2] = "$(touch SHOULD-NOT-EXECUTE)"
            invalid_marker = fields.copy(); invalid_marker[5] = "$(touch SHOULD-NOT-EXECUTE)"
            invalid_count = fields.copy(); invalid_count[6] = "3"
            invalid_stats = fields.copy(); invalid_stats[13] = "$(touch SHOULD-NOT-EXECUTE)"
            cases = {
                "partial-nonzero": f"printf '%s\\n' {shlex.quote(good)}; exit 7",
                "malformed": "printf '9\\037idle\\037bogus\\nS:0\\n'",
                "invalid-number": "printf '%s\\nS:0\\n' " + shlex.quote("\x1f".join(invalid_number)),
                "invalid-marker": "printf '%s\\nS:0\\n' " + shlex.quote("\x1f".join(invalid_marker)),
                "invalid-stats": "printf '%s\\nS:0\\n' " + shlex.quote("\x1f".join(invalid_stats)),
                "invalid-count": "printf '%s\\nS:0\\n' " + shlex.quote("\x1f".join(invalid_count)),
                "control": "printf '1\\037idle\\033[31m\\nS:0\\n'",
                "hung": f"printf '%s' $$ > {shlex.quote(str(root / 'pid'))}; exec /bin/sleep 30",
                "empty": "exit 0",
            }
            for name, action in cases.items():
                with self.subTest(fault=name):
                    stub = root / name
                    stub.write_text("#!/bin/sh\n[ \"$1\" != warmup ] || exit 0\n" + action + "\n")
                    stub.chmod(0o755)
                    # macOS first-exec inspection of a fresh script can exceed
                    # the Core's 250ms budget. Warm only the interpreter image;
                    # the fault action is still exercised by the actual hook.
                    subprocess.run([str(stub), "warmup"], check=True, timeout=5)
                    with Terminal(BINARY, PROFILE, ORDER, after=f"_ZAKO_BINARY={shlex.quote(str(stub))}") as other:
                        start = time.monotonic()
                        other.command("false")
                        self.assertLess(time.monotonic() - start, 1.0)
                        state = other.state()
                        self.assertEqual(state["native"], "1")
                        self.assertEqual(state["enabled"], "0")
                        self.assertEqual(state["prompt"], "")
                        self.assertEqual(state["count"], "0")
                        self.assertFalse((other.work / "SHOULD-NOT-EXECUTE").exists())
                        other.command("false")
                        self.assertEqual(other.transcript.count("Zako 配置无效或 Core 不可用"), 1)
                        if name == "hung":
                            pid = int((root / "pid").read_text())
                            deadline = time.monotonic() + 0.5
                            while time.monotonic() < deadline:
                                try:
                                    os.kill(pid, 0)
                                except ProcessLookupError:
                                    break
                                time.sleep(0.01)
                            else:
                                self.fail(f"Hung Core process {pid} was not reaped")
            with Terminal(BINARY, PROFILE, ORDER, after=f"_ZAKO_BINARY={shlex.quote(str(root / 'missing'))}") as other:
                other.command("false")
                self.assertEqual(other.state()["enabled"], "0")
                self.assertEqual(other.state()["after"], "0")

    def test_real_tab_completion(self):
        (self.shell.work / "unique-completion-fixture").write_text("COMPLETE-OUTPUT\n")
        # Use the native executable: real startup may alias cat to bat, whose
        # decorated output is unrelated to the completion behavior under test.
        self.shell.send("/bin/cat unique-completion-\t")
        self.shell.send(b"\x1b[24~")
        self.shell.send(b"\n")
        output = self.shell.read_prompt()
        self.assertRegex(output, r"(?m)^COMPLETE-OUTPUT$")
        self.assertIn("unique-completion-fixture", self.shell.state()["buffer"])

    def test_real_plugin_widgets_and_suggestions(self):
        def bindings(terminal):
            output = terminal.command("bindkey -M emacs")
            return [line for line in output.splitlines() if line.startswith('"')]
        with Terminal(BINARY, PROFILE, ORDER, integration=False) as baseline:
            self.assertEqual(bindings(self.shell), bindings(baseline))
        # Check the live ZLE state after the final plugin wrappers are installed.
        self.shell.command("print -s -- 'echo AUTO-SUGGESTION-OUTPUT'")
        self.shell.send("echo AUTO-SUGG")
        self.shell.read_until(b"ESTION-OUTPUT", timeout=3)
        self.shell.send(b"\x1b[24~")
        self.shell.send(b"\x1b[C\n")
        output = self.shell.read_prompt()
        self.assertRegex(output, r"(?m)^AUTO-SUGGESTION-OUTPUT$")
        state = self.shell.state()
        self.assertEqual(state["post"], "ESTION-OUTPUT")
        self.assertNotEqual(state["highlight"], "")
        # Trigger the actual fzf Ctrl-T widget against deterministic local data.
        (self.shell.work / "fzf-choice").write_text("FZF-OUTPUT\n")
        self.shell.command("export FZF_CTRL_T_COMMAND='printf fzf-choice'; export FZF_CTRL_T_OPTS='--select-1 --exit-0'; export FZF_DEFAULT_OPTS='--height=10 --no-tmux'")
        self.shell.send("/bin/cat \x14")
        self.shell.read_until(b"fzf-choice", timeout=5)
        self.shell.send(b"\n")
        output = self.shell.read_prompt(timeout=8)
        self.assertRegex(output, r"(?m)^FZF-OUTPUT$")
        self.assertIn("fzf-file-widget", self.shell.command("bindkey '^T'"))
        self.assertIn("_zsh_autosuggest", self.shell.command("print -r -- $widgets[forward-char]"))


class RecordedResult(unittest.TextTestResult):
    records = []
    def startTest(self, test):
        self.started = time.monotonic()
        super().startTest(test)
    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"name": str(test), "order": ORDER, "status": "passed", "seconds": round(time.monotonic() - self.started, 3)})
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"name": str(test), "order": ORDER, "status": "failed"})
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            self.records.append({"name": str(subtest), "order": ORDER, "status": "failed", "reason": str(err[1])})
    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"name": str(test), "order": ORDER, "status": "error"})


def main():
    global BINARY, PROFILE, ORDER
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--profile", choices=["clean", "plugins", "real"], default="clean",
                        help="real loads the installed initialization from ~/.zshrc (run after installation)")
    parser.add_argument("--report", required=True)
    parser.add_argument("--case", action="append", help="run selected cases during diagnosis")
    args = parser.parse_args()
    BINARY, PROFILE = str(Path(args.binary).resolve()), args.profile
    # Build suites after setting PROFILE; plugin-only selection is explicit.
    failed = False
    for order in (["before", "after"] if PROFILE == "plugins" else ["after"]):
        ORDER = order
        names = unittest.defaultTestLoader.getTestCaseNames(ZshAcceptance)
        if PROFILE == "clean":
            names.remove("test_real_plugin_widgets_and_suggestions")
        if PROFILE == "real":
            names = [name for name in names if name in {
                "test_actual_ctrl_c", "test_command_status_and_hook_chain",
                "test_expected_nonzero_and_real_errors", "test_multiple_candidates_and_empty_fields",
                "test_on_off_prompt_and_user_takeover", "test_real_plugin_widgets_and_suggestions",
                "test_real_tab_completion", "test_target_lifecycle_and_no_execution",
                "test_session_stats_and_reset", "test_achievements_config_and_session_isolation",
                "test_third_failure_cooldown_and_recovery"}]
        if args.case:
            unknown = set(args.case) - set(names)
            if unknown:
                parser.error(f"unknown/unavailable cases: {unknown}")
            names = [name for name in names if name in args.case]
        suite = unittest.TestSuite(ZshAcceptance(name) for name in names)
        result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
        failed |= not result.wasSuccessful()
    report = {"profile": PROFILE, "status": "failed" if failed else "passed", "environment": versions(),
              "selection": args.case or "all", "cases": RecordedResult.records, "plugin_orders": ["before", "after"] if PROFILE == "plugins" else []}
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
