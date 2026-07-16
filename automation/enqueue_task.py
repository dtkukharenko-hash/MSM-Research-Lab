#!/usr/bin/env python3
"""Explicit operator entry point for MSM feeder validation and enqueueing."""
from __future__ import annotations
import argparse
from pathlib import Path
from msm_task_feeder import FeedError, ingest

def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--enqueue", action="store_true")
    parser.add_argument("--repo", default="/home/nnv/MSM-Research-Lab")
    parser.add_argument("--state-dir", default="/home/nnv/.local/state/msm-orchestrator")
    parser.add_argument("--owner", default="nnv")
    parser.add_argument("--group", default="nnv")
    args = parser.parse_args()
    try:
        status, detail = ingest(Path(args.repo), Path(args.state_dir), dry_run=args.dry_run, owner=args.owner, group=args.group)
    except FeedError as exc:
        print("REJECTED: " + str(exc))
        return 1
    print(status + ": " + detail)
    return 0 if status in {"DRY_RUN", "ENQUEUED", "NOOP", "BLOCKED"} else 1

if __name__ == "__main__":
    raise SystemExit(main())
