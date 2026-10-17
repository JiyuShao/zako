#!/usr/bin/env python3
"""Run the current baseline or the complete M1 acceptance gate."""

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone


def run_step(name, command, timeout, root, output_dir):
    log = output_dir / f"{name}.log"
    print(f"RUN {name} (timeout {timeout}s)", flush=True)
    started = time.monotonic()
    timed_out = False
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            command,
            cwd=root,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            code = 124 if timed_out else 130
    result = {
        "name": name,
        "command": command,
        "exit_code": code,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "log": str(log),
    }
    print(f"{'PASS' if code == 0 else 'FAIL'} {name}: {log}", flush=True)
    if code:
        # Show bounded diagnostic output; the full output remains in the log.
        print(log.read_text(encoding="utf-8", errors="replace")[-8000:])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--baseline", action="store_true", help="run existing checks only")
    modes.add_argument("--full", action="store_true", help="require all M1 checks (default)")
    args = parser.parse_args()
    mode = "baseline" if args.baseline else "full"
    root = Path(__file__).resolve().parents[1]
    report_root = root / "target" / "m1-validation"
    report_root.mkdir(parents=True, exist_ok=True)
    output_dir = Path(tempfile.mkdtemp(prefix=f"{mode}-", dir=report_root))
    summary = {
        "mode": mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "steps": [],
        "missing": [],
    }
    result_code = 1
    try:
        cargo = shutil.which("cargo")
        if cargo is None:
            fallback = Path.home() / ".cargo" / "bin" / "cargo"
            if fallback.is_file():
                cargo = str(fallback)
        if cargo is None:
            raise RuntimeError("cargo unavailable; install Rust or source ~/.cargo/env")
        binary = str(root / "target" / "release" / "zako")
        steps = [
            ("format", [cargo, "fmt", "--check"], 120),
            ("rust-tests", [cargo, "test", "--offline", "--locked"], 1200),
            (
                "clippy",
                [cargo, "clippy", "--offline", "--locked", "--all-targets", "--all-features", "--", "-D", "warnings"],
                1200,
            ),
            ("release", [cargo, "build", "--offline", "--locked", "--release"], 1200),
            ("zsh-syntax", ["zsh", "-n", "integrations/zako.zsh"], 30),
            ("bash-syntax", ["bash", "-n", "tests/zsh_integration.sh"], 30),
            ("smoke", ["bash", "tests/zsh_integration.sh", binary], 180),
            ("diff-whitespace", ["git", "diff", "--check"], 30),
        ]
        if mode == "full":
            required = [
                "tests/core_acceptance.py",
                "tests/zsh_pty.py",
                "tests/benchmark_hooks.py",
                "tests/install_acceptance.py",
            ]
            summary["missing"] = [path for path in required if not (root / path).is_file()]
            if summary["missing"]:
                raise RuntimeError(
                    "Full M1 gate incomplete. Implement tasks 02–06 first. Missing: "
                    + ", ".join(summary["missing"])
                )
            steps.extend([
                ("core", [sys.executable, "tests/core_acceptance.py", "--binary", binary], 300),
                (
                    "pty-clean",
                    [sys.executable, "tests/zsh_pty.py", "--binary", binary, "--profile", "clean", "--report", str(output_dir / "pty-clean.json")],
                    900,
                ),
                (
                    "pty-plugins",
                    [sys.executable, "tests/zsh_pty.py", "--binary", binary, "--profile", "plugins", "--report", str(output_dir / "pty-plugins.json")],
                    1800,
                ),
                (
                    "performance",
                    [sys.executable, "tests/benchmark_hooks.py", "--binary", binary, "--report", str(output_dir / "performance.json")],
                    3600,
                ),
                (
                    "installation",
                    [sys.executable, "tests/install_acceptance.py", "--binary", binary, "--report", str(output_dir / "installation.json")],
                    1800,
                ),
            ])
        for name, command, timeout in steps:
            result = run_step(name, command, timeout, root, output_dir)
            summary["steps"].append(result)
            if result["exit_code"]:
                summary["status"] = "failed"
                result_code = 130 if result["exit_code"] == 130 else 1
                break
        else:
            summary["status"] = "passed"
            result_code = 0
    except KeyboardInterrupt:
        summary["status"] = "interrupted"
        result_code = 130
    except (OSError, RuntimeError) as error:
        summary["status"] = "incomplete" if summary["missing"] else "failed"
        summary["error"] = str(error)
        print(f"FAIL: {error}", file=sys.stderr, flush=True)
        result_code = 2 if summary["missing"] else 1
    finally:
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        report = output_dir / "summary.json"
        report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{mode.upper()}: {summary['status']}; report: {report}", flush=True)
        if mode == "baseline" and result_code == 0:
            print("Baseline passed; complete M1 acceptance is still pending.", flush=True)
    return result_code


if __name__ == "__main__":
    sys.exit(main())
