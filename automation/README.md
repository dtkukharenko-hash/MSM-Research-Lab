# MSM Codex runner

The installed service runs `/usr/local/lib/msm-runner/msm_runner.sh`; its audit and correction helpers are installed beside it. Editing repository sources never changes a live runner until a deliberate reinstall.

The shell takes a non-blocking lock, permits only the known Pine modification, pulls before parsing any task data, and owns all Git and result metadata. Codex is invoked in Bubblewrap sandbox modes: implementation R0 once, audit R0, at most one correction R1 then audit R1, at most one correction R2 then audit R2. Runtime JSONL, stderr, finals, state, and audit records are only under `/home/nnv/.local/state/msm-runner/`.

Infrastructure tasks are parsed only after pull and return `MANUAL_BOOTSTRAP_REQUIRED`; normal tasks require an explicit allowlist and cannot alter runner infrastructure. Codex never writes `.codex/RESULT.md`; after a technically valid permitted audit, the shell writes it and makes the existing two commits. Explicit-path staging is used throughout.

Validate and install:

```bash
bash automation/install.sh --dry-run
sudo bash automation/install.sh --enable-now
systemctl status msm-codex-runner.timer
```

The committed timer remains one minute. `automation/msm_runner.sh --dry-run` performs only preflight and makes no pull, task parse, process, result, or Git change.
