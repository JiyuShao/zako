#!/usr/bin/env python3
"""Install into an isolated prefix and verify packaged initialization/removal."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from terminal import ROOT, Terminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    report = {"status": "running", "cases": []}
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo")
        with tempfile.TemporaryDirectory(prefix="zako-install-") as directory:
            result = subprocess.run([cargo, "install", "--offline", "--locked", "--path", str(ROOT), "--root", directory],
                env={**os.environ, "CARGO_TARGET_DIR": str(ROOT / "target")}, text=True, capture_output=True, timeout=1200)
            if result.returncode:
                raise AssertionError(result.stderr)
            installed = Path(directory) / "bin/zako"
            assert installed.is_file()
            assert subprocess.check_output([str(installed), "--version"]) == subprocess.check_output([str(Path(args.binary).resolve()), "--version"])
            assert subprocess.check_output([str(installed), "init", "zsh"]) == subprocess.check_output([str(Path(args.binary).resolve()), "init", "zsh"])
            report["cases"].append({"name": "offline-source-install-and-bundled-integration", "status": "passed"})
            with Terminal(installed, "plugins", init='eval "$(zako init zsh)"') as shell:
                assert shell.state()["enabled"] == "1"
                shell.command("gti status")
                assert "建议：git status" in shell.command("zako fix")
                shell.command("zako off")
                assert shell.state()["prompt"] == ""
                shell.command("zako on")
                assert shell.state()["owned"] == "1"
            report["cases"].append({"name": "installed-binary-new-shell-and-on-off", "status": "passed"})
            with Terminal(installed, "plugins", init="") as shell:
                assert "♡ 哼" not in shell.startup
                assert "_zako_precmd" not in shell.command("print -r -- HOOKS:${(j:,:)precmd_functions}")
                output_text = shell.command("print -r -- initialized=${_ZAKO_INITIALIZED-no}")
                assert "\ninitialized=no\n" in output_text
            report["cases"].append({"name": "initialization-removed-in-new-shell", "status": "passed"})
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = repr(error)
        print(f"FAIL install acceptance: {error}", flush=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
