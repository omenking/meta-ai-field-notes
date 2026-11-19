#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""One-shot benchmark harness for Muse.

Runs every prompt of a source under ``prompts/<source>/`` (except
README.md) as an isolated, headless Muse session and records
tokens, duration, status and errors per prompt.

Driver note: the plan in plans/One-Shot.md names the Muse SDK
(@muse-code/sdk, TypeScript over the MSP wire protocol). This script
instead drives the same Muse engine through its supported
headless CLI, ``muse exec --json``, and harvests token usage from the
per-session log the CLI writes (~/.local/share/muse/sessions/...).
The observable results are the same (the SDK host is the same `muse`
binary speaking MSP), but the harness stays a single inspectable
Python file. Port to the TS SDK later if you prefer that surface.

Layout, per source (<source> is a prompts/ subdirectory name):

    prompts/<source>/<prompt>.md   prompt files (+ README.md index)
    manifests/<source>.yml         prompt list, settings, live statuses
    output/<source>/benchmark.log harness log (errors included)
    output/<source>/<prompt-name>/
        prompt.md                 exact prompt text that was sent
        events.jsonl              raw `muse exec --json` event stream
        stderr.log                child process stderr
        report.yml                status, duration, tokens, errors
        index.html ...            whatever the agent generated

output/ is generated: each (re)run of a prompt clears its folder first.
Scoping every artifact by source keeps prompt names unique per source,
so the same slug in two sources never collides.

Usage:

    uv run run_benchmark.py --init                 # (re)build all manifests
    uv run run_benchmark.py --source oneshotlm.com # run one source
    uv run run_benchmark.py --all-sources          # run every source
    uv run run_benchmark.py --source oneshotlm.com --only matrix-rain
    uv run run_benchmark.py --list                 # statuses, all sources
    uv run run_benchmark.py --dry-run              # preview, all sources
    uv run run_benchmark.py --source oneshotlm.com --force --only tetris
    uv run run_benchmark.py --source x.com --subscription --model muse-wonder-full-1.0

Billing: BILLING_MODE in .env selects `subscription` (stored `muse login`,
META_API_KEY withheld from children) or `api` (META_API_KEY, the default
when unset). --subscription forces subscription for one run.

A real run requires --source (or --all-sources / --manifest), so the
full collection never runs by accident; --init/--list/--dry-run
default to all sources.

Requires: `muse` on PATH, Node not needed. Run with uv (fetches
PyYAML), or with plain python3 if PyYAML is already installed.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # plain `python3 run_benchmark.py` without uv
    sys.exit("PyYAML is required. Run via `uv run run_benchmark.py` "
             "or `pip install pyyaml`.")

ROOT = Path(__file__).resolve().parent
VALID_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
HARNESS_FILES = {"prompt.md", "events.jsonl", "stderr.log", "report.yml"}
MANIFEST_HEADER = (
    "# One-shot benchmark manifest (one per source: manifests/<source>.yml\n"
    "# for prompts/<source>/, reporting into output/<source>/).\n"
    "# - Set `skip: true` on a prompt to skip it. Runs start in list order,\n"
    "#   up to settings.concurrency at a time.\n"
    "# - `status` is updated live by run_benchmark.py; edit it only to reset\n"
    "#   a prompt back to `pending`.\n"
    "# - output/<source>/ is generated and cleared per (re)run; keep no\n"
    "#   hand work there.\n"
    "# - Duration cap: settings.timeout_seconds applies per prompt; an\n"
    "#   entry may override it with its own `timeout_seconds`. An explicit\n"
    "#   --timeout flag overrides both. Reports record timeout_seconds\n"
    "#   (cap applied) and hit_cap; capped runs get status: timeout and\n"
    "#   hit_cap: true here and in report.yml.\n"
    "# - Optional pricing (USD per 1M tokens) enables cost_usd in reports:\n"
    "#     pricing: {input_per_mtok: 1.0, output_per_mtok: 5.0}\n"
    "# - `reference_url` is the source page for each prompt (backfilled\n"
    "#   from the prompt file's frontmatter when missing). `external`,\n"
    "#   when present, holds duration/cost/token figures published by\n"
    "#   that source for planning limits and skips; sync never writes\n"
    "#   it, so refresh it deliberately.\n"
)

log = logging.getLogger("oneshot")
manifest_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- .env ---

def load_dotenv(path: Path) -> dict[str, str]:
    """Parse a .env file leniently (quotes, `export`, trailing junk).

    A quoted value wins over anything after the closing quote, so a line
    like KEY="value" extra still yields `value` (with a warning).
    """
    values: dict[str, str] = {}
    if not path.exists():
        log.warning("No .env file at %s", path)
        return values
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        m = re.match(r'^"([^"]*)"(.*)$', val) or re.match(r"^'([^']*)'(.*)$", val)
        if m:
            if m.group(2).strip():
                log.warning(".env line %d (%s): ignoring trailing text after "
                            "quoted value: %r", lineno, key, m.group(2).strip())
            val = m.group(1)
        elif " " in val or "\t" in val:
            head = val.split()[0]
            log.warning(".env line %d (%s): unquoted value contains spaces; "
                        "using first token only", lineno, key)
            val = head
        values[key] = val.strip()
    return values


# ------------------------------------------------------------- prompts ---

def parse_prompt_file(path: Path) -> tuple[dict, str]:
    """Split optional YAML frontmatter from the prompt body."""
    text = path.read_text()
    if text.startswith("---\n") or text.startswith("---\r\n"):
        end = text.find("\n---", 3)
        if end != -1:
            meta = yaml.safe_load(text[3:end]) or {}
            body = text[end + 4:].lstrip("\n")
            return (meta if isinstance(meta, dict) else {}), body.strip() + "\n"
    return {}, text.strip() + "\n"


def discover_prompts(prompts_dir: Path) -> list[Path]:
    return sorted(p for p in prompts_dir.glob("*.md")
                  if p.name.lower() != "readme.md")


def discover_sources(root: Path) -> list[str]:
    """Source names: prompts/ subdirectories holding at least one prompt."""
    base = root / "prompts"
    if not base.is_dir():
        return []
    return sorted(d.name for d in base.iterdir()
                  if d.is_dir() and discover_prompts(d))


def manifest_path_for(source: str, root: Path) -> Path:
    return root / "manifests" / f"{source}.yml"


def source_for_manifest(path: Path) -> str | None:
    """Derive the source name from a manifests/<source>.yml path."""
    if path.parent.name == "manifests":
        return path.stem
    return None


# ------------------------------------------------------------ manifest ---

def default_settings(source: str | None = None) -> dict:
    return {
        "concurrency": 5,          # max prompts running at once
        "timeout_seconds": 1800,   # per-prompt wall-clock cap
        "prompts_dir": f"prompts/{source}" if source else "prompts",
        "output_dir": f"output/{source}" if source else "output",
        "model": None,             # null -> MODEL from .env
        "effort": None,            # null -> EFFORT from .env
        "pricing": None,           # e.g. {input_per_mtok: 1.0, output_per_mtok: 5.0}
    }


def load_or_init_manifest(path: Path,
                          source: str | None = None) -> dict:
    """Load a manifest, creating/syncing it from its prompts dir as needed.

    Existing entries keep their order, skip flags and statuses; newly
    discovered prompt files are appended as `pending`. Stored file and
    report paths that no longer exist are repaired to the locations
    implied by the manifest's own settings (for example after a prompt
    tree is reorganized into per-source folders); run history fields
    are never touched by the repair.
    """
    source = source or source_for_manifest(path)
    manifest: dict = {}
    if path.exists():
        manifest = yaml.safe_load(path.read_text()) or {}
    settings = {**default_settings(source),
                **(manifest.get("settings") or {})}
    manifest["settings"] = settings
    entries = manifest.get("prompts") or []
    known = {e.get("name") for e in entries if isinstance(e, dict)}
    prompts_dir = ROOT / settings["prompts_dir"]
    for pf in discover_prompts(prompts_dir):
        if pf.stem not in known:
            entries.append({
                "name": pf.stem,
                "file": f"{settings['prompts_dir']}/{pf.name}",
                "skip": False,
                "status": "pending",
            })
            log.info("Manifest: added prompt %s", pf.stem)
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        expected_file = f"{settings['prompts_dir']}/{entry['name']}.md"
        if (entry.get("file") != expected_file
                and not (ROOT / (entry.get("file") or "")).exists()
                and (ROOT / expected_file).exists()):
            log.info("Manifest: repaired file path for %s", entry["name"])
            entry["file"] = expected_file
        if entry.get("report"):
            expected_report = (f"{settings['output_dir']}/"
                               f"{entry['name']}/report.yml")
            if (entry["report"] != expected_report
                    and not (ROOT / entry["report"]).exists()):
                entry["report"] = expected_report
        if not entry.get("reference_url"):
            prompt_file = ROOT / (entry.get("file") or "")
            if prompt_file.exists():
                try:
                    meta, _ = parse_prompt_file(prompt_file)
                except Exception:
                    meta = {}
                if meta.get("source"):
                    entry["reference_url"] = meta["source"]
    pricing = resolve_pricing(settings)
    if pricing:
        settings["pricing"] = pricing
        for entry in entries:
            report_path = ROOT / (entry.get("report") or
                f"{settings['output_dir']}/{entry['name']}/report.yml")
            if not report_path.is_file():
                continue
            report = yaml.safe_load(report_path.read_text()) or {}
            cost = estimate_cost(report.get("tokens"), pricing)
            if cost is not None:
                entry["cost_usd"] = cost
                report_text = report_path.read_text()
                if re.search(r"^cost_usd:.*$", report_text, re.M):
                    report_text = re.sub(r"^cost_usd:.*$", f"cost_usd: {cost}", report_text, flags=re.M)
                else:
                    report_text += f"\ncost_usd: {cost}\n"
                report_path.write_text(report_text)
        manifest.setdefault("summary", {})["total_cost_usd"] = round(
            sum(e.get("cost_usd") or 0 for e in entries), 4)
    manifest["prompts"] = entries
    save_manifest(path, manifest)
    return manifest


def save_manifest(path: Path, manifest: dict) -> None:
    """Atomically rewrite the manifest (header comment re-emitted)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True,
                          width=120)
    tmp = path.with_suffix(".yml.tmp")
    tmp.write_text(MANIFEST_HEADER + body)
    os.replace(tmp, path)


def update_entry(manifest_path: Path, manifest: dict, name: str, **fields) -> None:
    with manifest_lock:
        for entry in manifest["prompts"]:
            if entry.get("name") == name:
                entry.update(fields)
                break
        save_manifest(manifest_path, manifest)


# ------------------------------------------------------- usage harvest ---

TOKEN_FIELDS = ("input_tokens", "output_tokens", "reasoning_tokens",
                "cached_tokens", "cache_read_tokens", "cache_write_tokens")


def find_session_log(session_id: str) -> Path | None:
    base = Path(os.environ.get("XDG_DATA_HOME",
                               Path.home() / ".local" / "share"))
    patterns = [str(base / "muse" / "sessions" / "*" / "*" / "*" /
                    session_id / "session.jsonl"),
                str(base / "muse" / "sessions" / "**" /
                    session_id / "session.jsonl")]
    for pat in patterns:
        hits = glob.glob(pat, recursive=True)
        if hits:
            return Path(hits[0])
    return None


def harvest_usage(session_id: str, retries: int = 10) -> dict | None:
    """Sum per-step `model_completed` usage from the session log.

    The `muse exec --json` stream carries lifecycle events only, so
    token usage is read from the durable session log. The log can lag
    process exit slightly, hence the short retry.
    """
    log_path = None
    for _ in range(retries):
        log_path = find_session_log(session_id)
        if log_path:
            break
        time.sleep(0.5)
    if not log_path:
        return None
    totals = {k: 0 for k in TOKEN_FIELDS}
    steps = 0
    for line in log_path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = ((rec.get("payload") or {}).get("event") or {})
        if event.get("kind") == "model_completed":
            steps += 1
            usage = event.get("usage") or {}
            for k in TOKEN_FIELDS:
                totals[k] += int(usage.get(k) or 0)
    return {
        "input": totals["input_tokens"],
        "output": totals["output_tokens"],
        "reasoning": totals["reasoning_tokens"],
        "cached": totals["cached_tokens"],
        "cache_read": totals["cache_read_tokens"],
        "cache_write": totals["cache_write_tokens"],
        "total": totals["input_tokens"] + totals["output_tokens"],
        "model_steps": steps,
    }


def summarize_events(events_path: Path) -> dict:
    """Extract terminal state and final text from the exec event stream."""
    info = {"terminal": None, "reason": None, "text": None,
            "task_failures": []}
    if not events_path.exists():
        return info
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ptype = rec.get("payload_type", "")
        payload = rec.get("payload") or {}
        if ptype.startswith("run.terminal"):
            info["terminal"] = payload.get("terminal")
            info["reason"] = payload.get("reason")
            info["text"] = payload.get("text")
        elif ptype == "task.lifecycle.failed":
            reason = (payload.get("event") or {}).get("reason")
            if reason:
                info["task_failures"].append(reason)
    return info


# ----------------------------------------------------------------- run ---

def clear_outdir(outdir: Path) -> None:
    """Start each one-shot from an empty workspace."""
    if outdir.exists():
        contents = sorted(p.name for p in outdir.iterdir())
        if contents:
            log.warning("[%s] clearing previous output: %s",
                        outdir.name, ", ".join(contents))
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)


def write_report(outdir: Path, report: dict) -> None:
    (outdir / "report.yml").write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=True,
                       width=120))


def entry_timeout(entry: dict, cfg: dict) -> int:
    """Effective duration cap for one prompt, in seconds.

    Precedence: an explicit --timeout for this invocation wins, then a
    per-prompt `timeout_seconds` in the manifest entry, then the
    manifest-wide settings value (cfg["timeout"]). Invalid entry values
    fall back to the manifest-wide value with a warning.
    """
    if cfg.get("timeout_explicit"):
        return int(cfg["timeout"])
    raw = entry.get("timeout_seconds")
    if raw is not None:
        try:
            value = int(raw)
            if value > 0:
                return value
            raise ValueError
        except (TypeError, ValueError):
            log.warning("[%s] invalid timeout_seconds %r in manifest; "
                        "using manifest setting %ss",
                        entry.get("name"), raw, cfg["timeout"])
    return int(cfg["timeout"])


def parse_cost_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    rates = {}
    for label, key in (("Input", "input_per_mtok"), ("Output", "output_per_mtok")):
        match = re.search(rf"^{label}\s+\$([0-9]+(?:\.[0-9]+)?)", path.read_text(), re.M)
        if not match:
            return None
        rates[key] = float(match.group(1))
    return rates


def resolve_pricing(settings: dict) -> dict | None:
    return settings.get("pricing") or parse_cost_file(ROOT / "cost.txt")


def estimate_cost(tokens: dict | None, pricing: dict | None) -> float | None:
    if not tokens or not pricing:
        return None
    try:
        return round(tokens["input"] / 1e6 * float(pricing["input_per_mtok"])
                     + tokens["output"] / 1e6 * float(pricing["output_per_mtok"]), 4)
    except (KeyError, TypeError, ValueError):
        return None


def run_one(entry: dict, cfg: dict) -> dict:
    """Run a single prompt to completion; always writes report.yml."""
    name = entry["name"]
    rlog = logging.LoggerAdapter(log, {"prompt": name})
    outdir = cfg["output_root"] / name
    prompt_path = ROOT / entry["file"]
    timeout = entry_timeout(entry, cfg)
    started_wall, started_mono = now_iso(), time.monotonic()
    report: dict = {
        "name": name,
        "source": cfg.get("source"),
        "prompt_file": entry["file"],
        "model": cfg["model"],
        "effort": cfg["effort"],
        "provider": "meta",
        "billing_mode": cfg.get("billing_mode", "api"),
        "status": "error",
        "started_at": started_wall,
        "finished_at": None,
        "duration_seconds": None,
        "timeout_seconds": timeout,
        "hit_cap": False,
        "exit_code": None,
        "session_id": None,
        "tokens": None,
        "cost_usd": None,
        "error": None,
        "warnings": [],
        "terminal_text": None,
        "output_files": [],
        "files": {"prompt": "prompt.md", "events": "events.jsonl",
                  "stderr": "stderr.log", "report": "report.yml"},
        "command": None,
    }
    try:
        meta, body = parse_prompt_file(prompt_path)
        for key in ("title", "category", "slug"):
            if meta.get(key):
                report[key] = meta[key]
        clear_outdir(outdir)
        (outdir / "prompt.md").write_text(body)

        session_id = str(uuid.uuid4())
        report["session_id"] = session_id
        cmd = ["muse", "exec", "--json", "--provider", "meta",
               "--model", cfg["model"], "--effort", cfg["effort"],
               "--prompt-file", str(outdir / "prompt.md"),
               "--workspace", str(outdir),
               "--session-id", session_id,
               "--disable-approval", "--disable-sandbox",
               "--disable-reminders", "--no-foreign-personal-context"]
        if not cfg["allow_web"]:
            cmd.append("--disable-web-tools")
        report["command"] = " ".join(cmd)

        rlog.info("starting (model=%s effort=%s timeout=%ss)",
                  cfg["model"], cfg["effort"], timeout)
        timed_out = False
        with open(outdir / "events.jsonl", "w") as ev_fh, \
                open(outdir / "stderr.log", "w") as err_fh:
            proc = subprocess.Popen(cmd, cwd=outdir, env=cfg["child_env"],
                                    stdout=ev_fh, stderr=err_fh,
                                    start_new_session=True)
            try:
                report["exit_code"] = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                rlog.error("hit %ss cap; terminating", timeout)
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    report["exit_code"] = proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    report["exit_code"] = proc.wait()

        report["duration_seconds"] = round(time.monotonic() - started_mono, 2)
        report["finished_at"] = now_iso()

        events = summarize_events(outdir / "events.jsonl")
        if events["text"]:
            report["terminal_text"] = events["text"][:4000]
        report["warnings"] += [f"task failed: {r}"
                               for r in events["task_failures"]]

        report["tokens"] = harvest_usage(session_id)
        if report["tokens"] is None:
            report["warnings"].append(
                "token usage unavailable: session log not found")
        report["cost_usd"] = estimate_cost(report["tokens"], cfg["pricing"])

        report["output_files"] = sorted(
            str(p.relative_to(outdir)) for p in outdir.rglob("*")
            if p.is_file() and p.name not in HARNESS_FILES)

        stderr_tail = (outdir / "stderr.log").read_text(
            errors="replace")[-1500:].strip()
        report["hit_cap"] = timed_out
        if timed_out:
            report["status"] = "timeout"
            report["error"] = f"killed after {timeout}s timeout"
        elif report["exit_code"] != 0:
            report["status"] = "failed"
            report["error"] = (events["reason"] or stderr_tail
                               or f"muse exec exited {report['exit_code']}")
        elif events["terminal"] not in (None, "completed"):
            report["status"] = "failed"
            report["error"] = (events["reason"]
                               or f"run terminal: {events['terminal']}")
        else:
            report["status"] = "completed"
            if not report["output_files"]:
                report["warnings"].append("no files were generated")
            elif "index.html" not in report["output_files"]:
                report["warnings"].append("index.html was not produced")
    except Exception:  # one bad prompt must never sink the whole run
        log.exception("[%s] harness error", name)
        report["status"] = "error"
        report["error"] = traceback.format_exc(limit=5)
        report["duration_seconds"] = round(time.monotonic() - started_mono, 2)
        report["finished_at"] = now_iso()
        outdir.mkdir(parents=True, exist_ok=True)

    write_report(outdir, report)
    tok = (report["tokens"] or {}).get("total")
    rlog.info("finished status=%s duration=%ss tokens=%s files=%s",
              report["status"], report["duration_seconds"], tok,
              ",".join(report["output_files"]) or "-")
    if report["error"]:
        rlog.error("error: %s", str(report["error"])[:500])
    return report


def write_skipped_report(entry: dict, cfg: dict) -> dict:
    outdir = cfg["output_root"] / entry["name"]
    outdir.mkdir(parents=True, exist_ok=True)
    report = {"name": entry["name"], "source": cfg.get("source"),
              "prompt_file": entry["file"],
              "model": cfg["model"], "effort": cfg["effort"],
              "billing_mode": cfg.get("billing_mode", "api"),
              "status": "skipped", "started_at": now_iso(),
              "finished_at": now_iso(), "duration_seconds": 0.0,
              "timeout_seconds": None, "hit_cap": False,
              "exit_code": None, "session_id": None, "tokens": None,
              "cost_usd": None, "error": None, "warnings": [],
              "terminal_text": None, "output_files": [],
              "note": "skip: true in the source manifest"}
    write_report(outdir, report)
    return report


# ---------------------------------------------------------------- main ---

class _PromptFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "prompt"):
            record.prompt = "-"
        return True


def setup_logging(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s [%(prompt)s] %(message)s",
        datefmt="%H:%M:%S")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    for handler in (logging.StreamHandler(sys.stdout),
                    logging.FileHandler(output_root / "benchmark.log")):
        handler.setFormatter(fmt)
        handler.addFilter(_PromptFilter())
        log.addHandler(handler)
    log.propagate = False


def select_entries(manifest: dict, only: list[str] | None,
                   force: bool) -> tuple[list[dict], list[dict]]:
    """Split manifest entries into (to_run, skipped), in manifest order.

    Rules: `skip: true` always skips (unless --force); already-completed
    prompts are skipped unless --force or named explicitly via --only.
    """
    to_run, skipped = [], []
    for entry in manifest["prompts"]:
        if only and entry["name"] not in only:
            continue
        if entry.get("skip") and not force:
            skipped.append(entry)
        elif (entry.get("status") == "completed" and not force
              and not only):
            log.info("[%s] already completed; skipping (use --force to rerun)",
                     entry["name"])
        else:
            to_run.append(entry)
    if only:
        known = {e["name"] for e in manifest["prompts"]}
        for name in only:
            if name not in known:
                log.error("--only: no prompt named %r in manifest", name)
    return to_run, skipped


VALID_BILLING_MODES = {"subscription", "api"}


def resolve_billing_mode(args, dotenv: dict) -> str:
    """Billing path for child `muse exec` processes.

    Precedence: --subscription flag, then BILLING_MODE from .env, then
    BILLING_MODE from the process environment, then the default `api`.
    """
    if getattr(args, "subscription", False):
        return "subscription"
    raw = (dotenv.get("BILLING_MODE") or os.environ.get("BILLING_MODE")
           or "api")
    mode = str(raw).strip().lower()
    if mode not in VALID_BILLING_MODES:
        sys.exit(f"Invalid BILLING_MODE {raw!r}; expected one of "
                 f"{sorted(VALID_BILLING_MODES)}.")
    return mode


def build_config(args, manifest: dict, dotenv: dict,
                 source: str | None = None) -> dict:
    s = manifest["settings"]
    model = args.model or s.get("model") or dotenv.get("MODEL")
    effort = (args.effort or s.get("effort") or dotenv.get("EFFORT")
              or "high").lower()
    if not model:
        sys.exit("No model configured: set MODEL in .env, settings.model "
                 "in the manifest, or pass --model.")
    if effort not in VALID_EFFORTS:
        sys.exit(f"Invalid effort {effort!r}; expected one of "
                 f"{sorted(VALID_EFFORTS)}.")
    billing_mode = resolve_billing_mode(args, dotenv)
    child_env = dict(os.environ)
    child_env.update({k: v for k, v in dotenv.items() if v})
    if billing_mode == "subscription":
        # META_API_KEY always takes priority over the stored subscription
        # login in Muse, so it must not reach the child at all.
        child_env.pop("META_API_KEY", None)
        log.info("Billing: subscription (META_API_KEY withheld from "
                 "children; using stored `muse login` credentials)")
    elif not dotenv.get("META_API_KEY") and not os.environ.get("META_API_KEY"):
        log.warning("META_API_KEY not found in .env or environment; "
                    "relying on stored `muse auth` credentials.")
    return {
        "source": source,
        "model": model,
        "effort": effort,
        "billing_mode": billing_mode,
        "concurrency": args.concurrency or int(s["concurrency"]),
        "timeout": args.timeout or int(s["timeout_seconds"]),
        "timeout_explicit": bool(args.timeout),
        "output_root": ROOT / s["output_dir"],
        "pricing": resolve_pricing(s),
        "allow_web": args.allow_web,
        "child_env": child_env,
    }


def resolve_targets(args, root: Path) -> list[tuple[str | None, Path]]:
    """Resolve CLI selection to (source, manifest_path) targets.

    Precedence: explicit --manifest, then --source, then all sources.
    Reading/preview modes (--init/--list/--dry-run) and --all-sources
    select every discovered source; a real run with no selection is
    refused so the whole collection never runs by accident.
    """
    if getattr(args, "manifest", None):
        path = root / args.manifest
        return [(source_for_manifest(path), path)]
    sources = discover_sources(root)
    available = ", ".join(sources) or "(none under prompts/)"
    if getattr(args, "source", None):
        if args.source not in sources:
            sys.exit(f"Unknown source {args.source!r}. "
                     f"Available sources: {available}")
        return [(args.source, manifest_path_for(args.source, root))]
    if (getattr(args, "all_sources", False) or args.init or args.list
            or args.dry_run):
        if not sources:
            sys.exit("No prompt sources found under prompts/<source>/.")
        return [(s, manifest_path_for(s, root)) for s in sources]
    sys.exit("Specify --source <name> (or --all-sources) to run. "
             f"Available sources: {available}")


def process_source(source: str | None, manifest_path: Path, args,
                   dotenv: dict) -> int:
    """Run one source's manifest end to end; return 0/1 exit status."""
    label = source or manifest_path.name
    manifest = load_or_init_manifest(manifest_path, source=source)
    cfg = build_config(args, manifest, dotenv, source=source)
    setup_logging(cfg["output_root"])
    log.info("=== source: %s | manifest: %s ===", label, manifest_path)

    if args.init:
        log.info("Manifest ready: %s (%d prompts)",
                 manifest_path, len(manifest["prompts"]))
        return 0
    if args.list:
        print(f"== {label} ({len(manifest['prompts'])} prompts) ==")
        for e in manifest["prompts"]:
            print(f"{e['name']:<48} status={e.get('status', 'pending'):<10} "
                  f"skip={bool(e.get('skip'))}")
        return 0

    only = None
    if args.only:
        only = [n for chunk in args.only for n in chunk.split(",") if n]
    to_run, skipped = select_entries(manifest, only, args.force)

    log.info("[%s] Model=%s effort=%s billing=%s concurrency=%d "
             "timeout=%ds | %d to run, %d skipped (skip:true)",
             label, cfg["model"], cfg["effort"],
             cfg.get("billing_mode", "api"), cfg["concurrency"],
             cfg["timeout"], len(to_run), len(skipped))
    if args.dry_run:
        for e in to_run:
            print(f"  would run: {label}/{e['name']}  ({e['file']})")
        for e in skipped:
            print(f"  skipped:   {label}/{e['name']}")
        return 0

    for entry in skipped:
        write_skipped_report(entry, cfg)
        update_entry(manifest_path, manifest, entry["name"],
                     status="skipped", finished_at=now_iso())
        log.info("[%s] skipped via manifest", entry["name"])

    results: list[dict] = []
    run_started = time.monotonic()
    if to_run:
        with ThreadPoolExecutor(
                max_workers=max(1, cfg["concurrency"])) as pool:
            futures = {}
            for entry in to_run:  # submit in manifest order
                update_entry(manifest_path, manifest, entry["name"],
                             status="running", started_at=now_iso())
                futures[pool.submit(run_one, entry, cfg)] = entry
            for fut in as_completed(futures):
                entry = futures[fut]
                try:
                    report = fut.result()
                except Exception:
                    log.exception("[%s] worker crashed", entry["name"])
                    update_entry(manifest_path, manifest, entry["name"],
                                 status="error", finished_at=now_iso())
                    continue
                results.append(report)
                fields = {"status": report["status"],
                          "finished_at": report["finished_at"],
                          "duration_seconds": report["duration_seconds"],
                          "hit_cap": report["hit_cap"],
                          "report": str((cfg["output_root"] / entry["name"]
                                         / "report.yml").relative_to(ROOT))}
                fields["cost_usd"] = report.get("cost_usd")
                if report["tokens"]:
                    fields["tokens_total"] = report["tokens"]["total"]
                update_entry(manifest_path, manifest, entry["name"],
                             **fields)

    done = [r for r in results if r["status"] == "completed"]
    bad = [r for r in results if r["status"] != "completed"]
    total_tokens = sum((r["tokens"] or {}).get("total", 0) for r in results)
    with manifest_lock:
        manifest["summary"] = {
            "source": source,
            "last_run_finished_at": now_iso(),
            "last_run_wall_seconds": round(time.monotonic() - run_started, 2),
            "completed": len(done), "failed": len(bad),
            "hit_cap": sum(1 for r in results if r.get("hit_cap")),
            "skipped": len(skipped), "total_tokens": total_tokens,
            "model": cfg["model"], "effort": cfg["effort"],
            "billing_mode": cfg.get("billing_mode", "api"),
            "total_cost_usd": round(sum(e.get("cost_usd") or 0
                                        for e in manifest["prompts"]), 4),
        }
        save_manifest(manifest_path, manifest)

    log.info("=== [%s] summary: %d completed, %d not completed, "
             "%d skipped | %s tokens | reports in %s ===",
             label, len(done), len(bad), len(skipped), f"{total_tokens:,}",
             cfg["output_root"])
    for r in sorted(results, key=lambda r: r["name"]):
        tok = (r["tokens"] or {}).get("total")
        log.info("  %-48s %-10s %8ss  tokens=%s",
                 r["name"], r["status"], r["duration_seconds"],
                 f"{tok:,}" if tok else "-")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Run one-shot prompts through Muse in parallel, "
                    "one manifest per prompt source.")
    ap.add_argument("--source", metavar="NAME",
                    help="prompt source to run: a prompts/<name>/ directory "
                         "(manifest manifests/<name>.yml, output "
                         "output/<name>/)")
    ap.add_argument("--all-sources", action="store_true",
                    help="run every source under prompts/, sequentially")
    ap.add_argument("--manifest", default=None,
                    help="explicit manifest path (overrides --source)")
    ap.add_argument("--env", default=".env")
    ap.add_argument("--only", nargs="+", metavar="NAME",
                    help="run only these prompt names (reruns even if "
                         "completed; still honours skip unless --force)")
    ap.add_argument("--concurrency", type=int,
                    help="max parallel runs (default: manifest setting)")
    ap.add_argument("--timeout", type=int,
                    help="hard duration cap per prompt for this run; overrides "
                         "per-entry timeout_seconds and the manifest setting "
                         "(default: entry value, else manifest setting)")
    ap.add_argument("--model", help="override model id")
    ap.add_argument("--effort", help="override reasoning effort")
    ap.add_argument("--subscription", action="store_true",
                    help="force subscription billing: withhold META_API_KEY "
                         "from muse exec children so the stored `muse "
                         "login` credentials are used; overrides BILLING_MODE "
                         "in .env (subscription|api, default: api)")
    ap.add_argument("--force", action="store_true",
                    help="rerun completed prompts and run skip:true ones")
    ap.add_argument("--allow-web", action="store_true",
                    help="do not pass --disable-web-tools to muse exec")
    ap.add_argument("--init", action="store_true",
                    help="(re)build manifests/<source>.yml files and exit "
                         "(all sources unless --source is given)")
    ap.add_argument("--list", action="store_true",
                    help="print manifest statuses and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would run, then exit")
    args = ap.parse_args(argv)

    if not shutil.which("muse"):
        sys.exit("`muse` binary not found on PATH.")

    dotenv = load_dotenv(ROOT / args.env)
    exit_code = 0
    for source, manifest_path in resolve_targets(args, ROOT):
        exit_code |= process_source(source, manifest_path, args, dotenv)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
