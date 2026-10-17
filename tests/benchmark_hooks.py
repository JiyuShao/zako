#!/usr/bin/env python3
"""Measure paired whole-command PTY latency, including all Zako Hook work."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import time
from terminal import ROOT, Terminal, versions


def stats(samples):
    ordered = sorted(samples)
    def quantile(value):
        return ordered[math.ceil(value * len(ordered)) - 1]
    return {"count": len(samples), "p50_ms": statistics.median(samples), "p95_ms": quantile(.95),
            "p99_ms": quantile(.99), "max_ms": max(samples), "min_ms": min(samples)}


def timed(shell, command):
    begin = time.perf_counter_ns()
    shell.command(command)
    return (time.perf_counter_ns() - begin) / 1_000_000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    sources = [*sorted((ROOT / "src").glob("*.rs")), ROOT / "integrations/zako.zsh"]
    digest = hashlib.sha256(b"".join(path.read_bytes() for path in sources)).hexdigest()
    report = {
        "status": "running", "environment": {**versions(), "platform": platform.platform(),
            "rustc": subprocess.check_output([str(Path.home() / '.cargo/bin/rustc'), "--version"], text=True).strip()},
        "source_sha256": digest, "binary_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
        "method": "Paired full PTY round trips (input to next prompt), alternating baseline/integration order. Delta = integrated[i] - baseline[i]; nearest-rank quantiles. Includes preexec, Core launch/pipe/read/validation, feedback, precmd and prompt consumption. No per-sample Shell startup, no sleeps, no outlier removal.",
        "warmup_per_group": 30, "samples_per_group": 500, "threshold_ms": 10, "groups": [],
    }
    failed = False
    started = time.monotonic()
    try:
        for profile in ["clean", "plugins"]:
            for case, command in [("success", "true"), ("failure", "false"), ("correction", "gti status"), ("off", "true")]:
                print(f"BENCH {profile}/{case}: 30 warmups + 500 paired samples", flush=True)
                with Terminal(binary, profile, integration=False) as base, Terminal(binary, profile) as integrated:
                    if case == "off":
                        integrated.command("zako off")
                    for _ in range(30):
                        base.command(command)
                        integrated.command(command)
                    before, after = [], []
                    for index in range(500):
                        if index % 2:
                            integrated_ms = timed(integrated, command)
                            base_ms = timed(base, command)
                        else:
                            base_ms = timed(base, command)
                            integrated_ms = timed(integrated, command)
                        before.append(base_ms)
                        after.append(integrated_ms)
                    delta = [with_zako - without for without, with_zako in zip(before, after)]
                    group = {"profile": profile, "case": case, "command": command,
                             "startup_ms": {"baseline": base.startup_ms, "integrated": integrated.startup_ms},
                             "baseline": stats(before), "integrated": stats(after), "added": stats(delta),
                             "raw_ms": {"baseline": before, "integrated": after, "added": delta}}
                    group["passed"] = group["added"]["p95_ms"] < 10
                    failed |= not group["passed"]
                    report["groups"].append(group)
                    # Also fail if measurement hid a Core failure or disabled session.
                    state = integrated.state()
                    if case != "off" and state["enabled"] != "1":
                        raise AssertionError(f"Core disabled during benchmark {profile}/{case}")
                    if "Zako 配置无效或 Core 不可用" in integrated.transcript:
                        raise AssertionError(f"Unexpected fail-open during benchmark {profile}/{case}")
                    print(f"{'PASS' if group['passed'] else 'FAIL'} added p95={group['added']['p95_ms']:.3f}ms; full p95={group['integrated']['p95_ms']:.3f}ms", flush=True)
                    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        report["status"] = "failed" if failed else "passed"
    except Exception as error:
        failed = True
        report["status"] = "failed"
        report["error"] = repr(error)
        print(f"FAIL benchmark: {error}", flush=True)
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
