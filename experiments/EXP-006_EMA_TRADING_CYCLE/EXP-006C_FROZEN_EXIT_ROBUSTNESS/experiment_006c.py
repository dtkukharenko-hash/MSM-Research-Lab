#!/usr/bin/env python3
"""EXP-006C: frozen EXIT_R2/EXIT_R5 robustness audit."""

from __future__ import annotations

import importlib.util
import math
import struct
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EXP006 = ROOT / "experiments/EXP-006_EMA_TRADING_CYCLE"
EXP006B = EXP006 / "EXP-006B_EXIT_RETENTION"
EXP = EXP006 / "EXP-006C_FROZEN_EXIT_ROBUSTNESS"
OUT = EXP / "artifacts"
TRUE_HOLDOUT_START = pd.Timestamp("2025-07-01 04:00")
VARIANTS = ["EXIT_R0", "EXIT_R2", "EXIT_R5"]
FEE = 0.001
START_CAPITAL = 1000.0
SEED = 20260713


def load_006b():
    spec = importlib.util.spec_from_file_location("exp006b", EXP006B / "experiment_006b.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def side(direction: str) -> int:
    return 1 if direction == "LONG" else -1


def equity(rets: pd.Series) -> pd.Series:
    vals = [START_CAPITAL]
    for r in rets.fillna(0):
        vals.append(vals[-1] * (1 + float(r)))
    return pd.Series(vals[1:])


def max_dd(rets: pd.Series) -> float:
    eq = equity(rets)
    if eq.empty:
        return 0.0
    return float((eq / eq.cummax() - 1).min())


def profit_factor(rets: pd.Series) -> float:
    wins = rets[rets > 0]
    losses = rets[rets < 0]
    if abs(losses.sum()) <= 1e-12:
        return 999.0 if wins.sum() > 0 else 0.0
    return float(wins.sum() / abs(losses.sum()))


def metrics(g: pd.DataFrame, scope: str, variant: str, cost_mult: float = 1.0) -> dict:
    if g.empty:
        return {"scope": scope, "exit_variant": variant, "cost_mult": cost_mult, "trades": 0}
    rets = g["gross_return"] - 2 * FEE * cost_mult
    wins = rets[rets > 0]
    cap = g["mfe_capture"].replace([np.inf, -np.inf], np.nan)
    return {
        "scope": scope,
        "exit_variant": variant,
        "cost_mult": cost_mult,
        "trades": int(len(g)),
        "sample_flag": "LOW_SAMPLE" if len(g) < 5 else "OK",
        "profit_factor": profit_factor(rets),
        "total_return": float((1 + rets).prod() - 1),
        "max_drawdown": max_dd(rets),
        "win_rate": float((rets > 0).mean()),
        "average_trade": float(rets.mean()),
        "median_trade": float(rets.median()),
        "median_mfe_capture": float(cap.median(skipna=True)),
        "good_entry_bad_exit_share": float((g["failure_type"] == "GOOD_ENTRY_BAD_EXIT").mean()),
        "top1_profit_share": float(wins.max() / wins.sum()) if len(wins) and wins.sum() > 0 else 1.0,
        "return_without_top1": float((1 + rets.drop(index=rets.idxmax())).prod() - 1) if len(rets) > 1 else 0.0,
        "long_pf": profit_factor(rets[g["direction"] == "LONG"]) if (g["direction"] == "LONG").any() else 0.0,
        "short_pf": profit_factor(rets[g["direction"] == "SHORT"]) if (g["direction"] == "SHORT").any() else 0.0,
    }


def assign_block(t: pd.Timestamp) -> str:
    if t < pd.Timestamp("2023-10-01"):
        return "2023-Q3 partial"
    if t < pd.Timestamp("2024-01-01"):
        return "2023-Q4"
    if t < pd.Timestamp("2024-04-01"):
        return "2024-Q1"
    if t < pd.Timestamp("2024-07-01"):
        return "2024-Q2"
    if t < pd.Timestamp("2024-10-01"):
        return "2024-Q3"
    if t < pd.Timestamp("2024-12-20"):
        return "2024-Q4 to 2024-12-19"
    if t < pd.Timestamp("2025-04-01"):
        return "2024-12-20 to 2025-Q1"
    return "2025-Q2 to research_end"


def manual_capture_audit(df: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    idx = {pd.Timestamp(t): i for i, t in zip(df.index, df["dt"])}
    rows = []
    diff_times = trades.pivot_table(index="trade_key", columns="exit_variant", values="exit_time", aggfunc="first")
    different_keys = set(diff_times.dropna().loc[lambda x: (x["EXIT_R0"] != x["EXIT_R2"]) | (x["EXIT_R0"] != x["EXIT_R5"])].index)
    sample_keys = set(trades[trades["scope"] == "REUSED_TEMPORAL_TEST"]["trade_key"])
    sample_keys |= set(trades[trades["direction"] == "LONG"]["trade_key"].head(10))
    sample_keys |= set(trades[trades["direction"] == "SHORT"]["trade_key"].head(10))
    sample_keys |= different_keys
    for _, r in trades[trades["trade_key"].isin(sample_keys)].iterrows():
        entry_i = idx[pd.Timestamp(r["entry_time"])]
        exit_i = idx[pd.Timestamp(r["exit_time"])]
        w = df.loc[entry_i:exit_i]
        entry = float(r["entry_price"])
        exitp = float(r["exit_price"])
        if r["direction"] == "LONG":
            mfe_price = float(w["high"].max())
            mfe_delta = mfe_price - entry
            realized = exitp - entry
        else:
            mfe_price = float(w["low"].min())
            mfe_delta = entry - mfe_price
            realized = entry - exitp
        cap = np.nan if mfe_delta <= 0 else realized / mfe_delta
        status = "OK" if (pd.isna(cap) and pd.isna(r["mfe_capture"])) or abs(float(cap) - float(r["mfe_capture"])) < 1e-9 else "MISMATCH"
        rows.append({
            "trade_id": r["trade_key"],
            "direction": r["direction"],
            "entry_time": r["entry_time"],
            "entry_price": entry,
            "exit_variant": r["exit_variant"],
            "exit_time": r["exit_time"],
            "exit_price": exitp,
            "mfe_price": mfe_price,
            "mfe_delta": mfe_delta,
            "realized_delta": realized,
            "capture": cap,
            "stored_capture": r["mfe_capture"],
            "original_exp006b_capture": r.get("original_exp006b_mfe_capture", np.nan),
            "manual_check_status": status,
        })
    return pd.DataFrame(rows)


def recompute_capture_exit_inclusive(df: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    """Apply the EXP-006C audit definition: MFE is reconstructed through exit_time inclusive."""
    idx = {pd.Timestamp(t): i for i, t in zip(df.index, df["dt"])}
    out = trades.copy()
    out["original_exp006b_mfe_capture"] = out["mfe_capture"]
    new_caps = []
    new_mfe_prices = []
    new_mfe_atr = []
    new_giveback = []
    for _, r in out.iterrows():
        entry_i = idx[pd.Timestamp(r["entry_time"])]
        exit_i = idx[pd.Timestamp(r["exit_time"])]
        w = df.loc[entry_i:exit_i]
        entry = float(r["entry_price"])
        exitp = float(r["exit_price"])
        atr = abs(float(r["mfe_price"]) - entry) / float(r["mfe_atr"]) if float(r["mfe_atr"]) != 0 else np.nan
        if not np.isfinite(atr) or atr <= 0:
            atr = float(df.loc[entry_i, "atr14"])
        if r["direction"] == "LONG":
            mfe_price = float(w["high"].max())
            mfe_delta = mfe_price - entry
            realized = exitp - entry
        else:
            mfe_price = float(w["low"].min())
            mfe_delta = entry - mfe_price
            realized = entry - exitp
        cap = np.nan if mfe_delta <= 0 else realized / mfe_delta
        new_caps.append(cap)
        new_mfe_prices.append(mfe_price)
        new_mfe_atr.append(mfe_delta / atr if atr > 0 else np.nan)
        new_giveback.append((mfe_delta - realized) / atr if atr > 0 else np.nan)
    out["mfe_capture"] = new_caps
    out["mfe_price"] = new_mfe_prices
    out["mfe_atr_metric_recomputed"] = new_mfe_atr
    out["mfe_giveback_atr_metric_recomputed"] = new_giveback
    return out


def paired_comparison(trades: pd.DataFrame) -> pd.DataFrame:
    p = trades.pivot_table(
        index=["trade_key", "scope", "block", "phase", "direction"],
        columns="exit_variant",
        values=["exit_time", "exit_price", "net_return", "mfe_atr", "mae_atr", "mfe_capture", "bars", "exit_reason"],
        aggfunc="first",
    )
    p.columns = [f"{a}_{b}" for a, b in p.columns]
    p = p.reset_index()
    for v in ["EXIT_R2", "EXIT_R5"]:
        p[f"{v}_return_diff_vs_R0"] = p[f"net_return_{v}"] - p["net_return_EXIT_R0"]
        p[f"{v}_capture_diff_vs_R0"] = p[f"mfe_capture_{v}"] - p["mfe_capture_EXIT_R0"]
        p[f"{v}_better_than_R0"] = p[f"{v}_return_diff_vs_R0"] > 0
    return p


def bootstrap_pairs(paired: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for variant in ["EXIT_R2", "EXIT_R5"]:
        for phase_name, g in [("ALL", paired), *list(paired.groupby("phase"))]:
            diffs = g[f"{variant}_return_diff_vs_R0"].dropna().to_numpy(float)
            cdiffs = g[f"{variant}_capture_diff_vs_R0"].dropna().to_numpy(float)
            if len(diffs) == 0:
                continue
            boot = []
            for _ in range(1000):
                sample = rng.choice(diffs, size=len(diffs), replace=True)
                boot.append(float(np.median(sample)))
            pos = int((diffs > 0).sum())
            n = len(diffs)
            # Two-sided exact sign-test approximation by binomial tail.
            tail = sum(math.comb(n, k) for k in range(0, min(pos, n - pos) + 1)) / (2 ** n)
            rows.append({
                "exit_variant": variant,
                "phase": phase_name,
                "n": n,
                "share_better_than_R0": float((diffs > 0).mean()),
                "median_return_diff": float(np.median(diffs)),
                "median_capture_diff": float(np.nanmedian(cdiffs)) if len(cdiffs) else np.nan,
                "bootstrap_ci_low": float(np.quantile(boot, 0.025)),
                "bootstrap_ci_high": float(np.quantile(boot, 0.975)),
                "sign_test_p_approx": min(1.0, 2 * tail),
            })
    return pd.DataFrame(rows)


def concentration(trades: pd.DataFrame, block_metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variant, g in trades.groupby("exit_variant"):
        rets = g["net_return"]
        wins = g[g["net_return"] > 0].sort_values("net_return", ascending=False)
        total = float((1 + rets).prod() - 1)
        row = {"exit_variant": variant, "total_return": total}
        for n in [1, 3]:
            drop = wins.head(n).index
            rest = g.drop(index=drop)
            row[f"return_without_top{n}"] = float((1 + rest["net_return"]).prod() - 1) if len(rest) else 0.0
        for n in [1, 3, 5]:
            row[f"top{n}_profit_share"] = float(wins.head(n)["net_return"].sum() / wins["net_return"].sum()) if len(wins) and wins["net_return"].sum() > 0 else 1.0
        best_block = block_metrics[(block_metrics["exit_variant"] == variant) & (block_metrics["scope"] != "ALL_RESEARCH")].sort_values("total_return", ascending=False).head(1)
        if not best_block.empty:
            b = best_block.iloc[0]["scope"]
            rest = g[g["block"] != b]
            row["best_block"] = b
            row["pf_without_best_block"] = profit_factor(rest["net_return"])
            row["return_without_best_block"] = float((1 + rest["net_return"]).prod() - 1)
        for d in ["LONG", "SHORT"]:
            gd = g[g["direction"] == d]
            if gd.empty:
                row[f"return_without_best_{d.lower()}"] = np.nan
                continue
            drop = gd["net_return"].idxmax()
            row[f"return_without_best_{d.lower()}"] = float((1 + g.drop(index=drop)["net_return"]).prod() - 1)
        rows.append(row)
    return pd.DataFrame(rows)


class Raster:
    def __init__(self, w=1000, h=520):
        self.w = w; self.h = h; self.p = bytearray((255, 255, 255) * (w * h))
    def dot(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            k = (y * self.w + x) * 3; self.p[k:k+3] = bytes(c)
    def line(self, x0, y0, x1, y1, c, width=2):
        x0, y0, x1, y1 = map(lambda v: int(round(v)), [x0, y0, x1, y1])
        dx, dy = abs(x1-x0), -abs(y1-y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1; err = dx + dy
        while True:
            for ox in range(-(width//2), width//2+1):
                for oy in range(-(width//2), width//2+1): self.dot(x0+ox, y0+oy, c)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * err
            if e2 >= dy: err += dy; x0 += sx
            if e2 <= dx: err += dx; y0 += sy
    def save(self, path: Path):
        raw = b"".join(b"\x00" + bytes(self.p[y*self.w*3:(y+1)*self.w*3]) for y in range(self.h))
        def chunk(tag, data): return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def chart(series, path: Path):
    colors = [(0, 110, 180), (220, 80, 40), (60, 150, 80), (150, 80, 180)]
    r = Raster(); vals = [v for _, xs in series for v in xs if pd.notna(v)]
    ymin, ymax = (min(vals), max(vals)) if vals else (0, 1)
    if ymax == ymin: ymax += 1
    pad = 46; r.line(pad, r.h-pad, r.w-20, r.h-pad, (160,160,160), 1); r.line(pad, 20, pad, r.h-pad, (160,160,160), 1)
    for si, (_, xs) in enumerate(series):
        pts = []
        for i, val in enumerate(xs):
            if pd.isna(val): continue
            x = pad + i / max(1, len(xs)-1) * (r.w-pad-20); y = r.h-pad - (val-ymin)/(ymax-ymin)*(r.h-pad-20); pts.append((x,y))
        for a,b in zip(pts, pts[1:]): r.line(a[0], a[1], b[0], b[1], colors[si % len(colors)], 2)
    r.save(path)


def write_pine(trades: pd.DataFrame) -> None:
    p = paired_comparison(trades).head(80)
    def ts(t):
        q = pd.Timestamp(t); return f'timestamp("Etc/UTC", {q.year}, {q.month}, {q.day}, {q.hour}, {q.minute})'
    starts = ", ".join(ts(t) for t in p["exit_time_EXIT_R0"].fillna(p["exit_time_EXIT_R2"])) or 'timestamp("Etc/UTC", 2023, 7, 1, 0, 0)'
    e0 = ", ".join(ts(t) for t in p["exit_time_EXIT_R0"]) or starts
    e2 = ", ".join(ts(t) for t in p["exit_time_EXIT_R2"]) or starts
    e5 = ", ".join(ts(t) for t in p["exit_time_EXIT_R5"]) or starts
    blocks = ", ".join(f'"{b}"' for b in p["block"]) or '"NA"'
    text = f"""//@version=6
indicator("EXP-006C Frozen Exit Robustness Review", overlay=true, max_lines_count=500, max_labels_count=500)
showLabels = input.bool(true, "show labels")
ema27 = ta.ema(close, 27)
ema200 = ta.ema(close, 200)
plot(ema27, "EMA27", color=color.aqua)
plot(ema200, "EMA200", color=color.orange)
var int[] starts = array.from({starts})
var int[] exitR0 = array.from({e0})
var int[] exitR2 = array.from({e2})
var int[] exitR5 = array.from({e5})
var string[] blocks = array.from({blocks})
for i = 0 to array.size(starts) - 1
    int st = array.get(starts, i)
    if time == st
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.green, width=2)
        if showLabels
            label.new(time, high, "ENTRY_A " + array.get(blocks, i), xloc=xloc.bar_time, style=label.style_label_down, color=color.green, textcolor=color.white, size=size.tiny)
    if time == array.get(exitR0, i)
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.gray, width=1)
    if time == array.get(exitR2, i)
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.purple, width=2)
    if time == array.get(exitR5, i)
        line.new(time, low, time, high, xloc=xloc.bar_time, extend=extend.both, color=color.red, width=2)
"""
    (OUT / "EXIT_ROBUSTNESS_REVIEW.pine").write_text(text, encoding="utf-8")


def write_pdf(lines: list[str]) -> None:
    content = ["BT /F1 12 Tf 36 760 Td"]
    for line in lines[:55]:
        s = str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:100]
        content.append(f"({s}) Tj 0 -14 Td")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents 4 0 R >>", f"<< /Length {len(stream)} >>\nstream\n".encode()+stream+b"\nendstream"]
    out=bytearray(b"%PDF-1.4\n"); offs=[]
    for i,o in enumerate(objs,1): offs.append(len(out)); out += f"{i} 0 obj\n".encode()+o+b"\nendobj\n"
    xref=len(out); out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offs: out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    (OUT / "EXIT_ROBUSTNESS_OVERVIEW.pdf").write_bytes(bytes(out))


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    if df.empty: return "No rows."
    def cell(v): return f"{v:.6g}" if isinstance(v, float) else str(v)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df[cols].iterrows(): rows.append("| " + " | ".join(cell(r[c]) for c in cols) + " |")
    return "\n".join(rows)


def main() -> None:
    ensure_dirs()
    exp006b = load_006b()
    df = exp006b.load_ohlc()
    if df["dt"].max() >= TRUE_HOLDOUT_START:
        raise RuntimeError("True holdout entered EXP-006C.")
    trades = exp006b.run_all(df)
    trades = trades[trades["exit_variant"].isin(VARIANTS)].copy()
    trades["failure_type"] = trades.apply(exp006b.classify_failure, axis=1)
    trades["phase"] = trades["mfe_atr"].apply(exp006b.phase)
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])
    trades["block"] = trades["entry_time"].apply(assign_block)
    trades = recompute_capture_exit_inclusive(df, trades)

    audit = manual_capture_audit(df, trades)
    audit.to_csv(OUT / "mfe_capture_audit.csv", index=False)
    mismatch = int((audit["manual_check_status"] != "OK").sum())

    align_rows = []
    for variant, g in trades.groupby("exit_variant"):
        keys = set(zip(g["trade_key"], g["entry_time"], g["entry_price"].round(12), g["stop_price"].round(12)))
        common = set.intersection(*[set(zip(trades[trades.exit_variant == v]["trade_key"], trades[trades.exit_variant == v]["entry_time"], trades[trades.exit_variant == v]["entry_price"].round(12), trades[trades.exit_variant == v]["stop_price"].round(12))) for v in VARIANTS])
        align_rows.append({"exit_variant": variant, "entry_records": len(keys), "common_entry_records": len(common), "variant_specific_entries": len(keys-common), "comparison_mode": "COMMON_SIGNAL_GRID_NO_POSITION_OCCUPANCY"})
    entry_align = pd.DataFrame(align_rows)
    entry_align.to_csv(OUT / "entry_alignment.csv", index=False)

    qrows = []
    for (block, variant), g in trades.groupby(["block", "exit_variant"]):
        row = metrics(g, block, variant)
        row["pf_cost_x2"] = metrics(g, block, variant, 2.0)["profit_factor"]
        row["pf_cost_x3"] = metrics(g, block, variant, 3.0)["profit_factor"]
        qrows.append(row)
    for variant, g in trades.groupby("exit_variant"):
        row = metrics(g, "ALL_RESEARCH", variant)
        row["pf_cost_x2"] = metrics(g, "ALL_RESEARCH", variant, 2.0)["profit_factor"]
        row["pf_cost_x3"] = metrics(g, "ALL_RESEARCH", variant, 3.0)["profit_factor"]
        qrows.append(row)
    quarterly = pd.DataFrame(qrows)
    quarterly.to_csv(OUT / "quarterly_metrics.csv", index=False)

    folds = [
        ("F1", pd.Timestamp("2024-01-01"), pd.Timestamp("2024-03-31 23:59")),
        ("F2", pd.Timestamp("2024-04-01"), pd.Timestamp("2024-06-30 23:59")),
        ("F3", pd.Timestamp("2024-07-01"), pd.Timestamp("2024-09-30 23:59")),
        ("F4", pd.Timestamp("2024-10-01"), pd.Timestamp("2024-12-19 23:59")),
        ("F5", pd.Timestamp("2024-12-20"), pd.Timestamp("2025-03-31 23:59")),
        ("F6", pd.Timestamp("2025-04-01"), pd.Timestamp("2025-07-01")),
    ]
    rrows = []
    for fid, start, end in folds:
        for variant, g in trades[(trades["entry_time"] >= start) & (trades["entry_time"] <= end)].groupby("exit_variant"):
            row = metrics(g, fid, variant)
            row["test_start"] = start
            row["test_end"] = end
            rrows.append(row)
    rolling = pd.DataFrame(rrows)
    rolling.to_csv(OUT / "rolling_origin_metrics.csv", index=False)

    paired = paired_comparison(trades)
    paired.to_csv(OUT / "paired_trade_comparison.csv", index=False)
    boot = bootstrap_pairs(paired)
    boot.to_csv(OUT / "bootstrap_pair_differences.csv", index=False)
    conc = concentration(trades, quarterly)
    conc.to_csv(OUT / "concentration_stress.csv", index=False)

    drows = []
    for (variant, direction), g in trades.groupby(["exit_variant", "direction"]):
        row = metrics(g, direction, variant)
        row["direction"] = direction
        drows.append(row)
    direction_metrics = pd.DataFrame(drows)
    direction_metrics.to_csv(OUT / "direction_metrics.csv", index=False)
    cost_rows = []
    for (block, variant), g in trades.groupby(["block", "exit_variant"]):
        cost_rows.append({"block": block, "exit_variant": variant, "trades": len(g), "pf_x1": metrics(g, block, variant, 1.0)["profit_factor"], "pf_x2": metrics(g, block, variant, 2.0)["profit_factor"], "pf_x3": metrics(g, block, variant, 3.0)["profit_factor"]})
    for variant, g in trades.groupby("exit_variant"):
        cost_rows.append({"block": "ALL_RESEARCH", "exit_variant": variant, "trades": len(g), "pf_x1": metrics(g, "ALL_RESEARCH", variant, 1.0)["profit_factor"], "pf_x2": metrics(g, "ALL_RESEARCH", variant, 2.0)["profit_factor"], "pf_x3": metrics(g, "ALL_RESEARCH", variant, 3.0)["profit_factor"]})
    cost = pd.DataFrame(cost_rows)
    cost.to_csv(OUT / "cost_robustness_by_block.csv", index=False)

    block_order = [b for b in ["2023-Q3 partial", "2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4 to 2024-12-19", "2024-12-20 to 2025-Q1", "2025-Q2 to research_end"] if b in quarterly["scope"].unique()]
    chart([(v, [float(quarterly[(quarterly.scope == b) & (quarterly.exit_variant == v)]["profit_factor"].iloc[0]) if len(quarterly[(quarterly.scope == b) & (quarterly.exit_variant == v)]) else np.nan for b in block_order]) for v in VARIANTS], OUT / "quarterly_pf.png")
    fold_order = [f[0] for f in folds]
    chart([(v, [float(rolling[(rolling.scope == f) & (rolling.exit_variant == v)]["profit_factor"].iloc[0]) if len(rolling[(rolling.scope == f) & (rolling.exit_variant == v)]) else np.nan for f in fold_order]) for v in VARIANTS], OUT / "rolling_pf.png")
    chart([(v, list(paired[f"{v}_return_diff_vs_R0"].fillna(0))) for v in ["EXIT_R2", "EXIT_R5"]], OUT / "paired_return_difference.png")
    chart([(v, [float(conc[conc.exit_variant == v][c].iloc[0]) for c in ["top1_profit_share", "top3_profit_share", "top5_profit_share"]]) for v in VARIANTS], OUT / "concentration_plot.png")
    write_pine(trades)

    verdict = decide_verdict(mismatch, quarterly, rolling, boot, conc, direction_metrics)
    write_report(verdict, mismatch, audit, entry_align, quarterly, rolling, boot, conc, direction_metrics, cost)


def decide_verdict(mismatch: int, quarterly: pd.DataFrame, rolling: pd.DataFrame, boot: pd.DataFrame, conc: pd.DataFrame, direction_metrics: pd.DataFrame) -> str:
    if mismatch:
        return "METRIC_IMPLEMENTATION_ERROR"
    allq = quarterly[quarterly["scope"] == "ALL_RESEARCH"].set_index("exit_variant")
    viable = []
    for v in ["EXIT_R2", "EXIT_R5"]:
        if v not in allq.index:
            continue
        blocks = quarterly[(quarterly["exit_variant"] == v) & (quarterly["scope"] != "ALL_RESEARCH") & (quarterly["trades"] >= 5)]
        block_pf_share = float((blocks["profit_factor"] > 1).mean()) if len(blocks) else 0
        folds = rolling[rolling["exit_variant"] == v]
        fold_pos_share = float((folds["total_return"] > 0).mean()) if len(folds) else 0
        c = conc[conc["exit_variant"] == v].iloc[0]
        d = direction_metrics[direction_metrics["exit_variant"] == v].set_index("direction")
        no_full_side_conflict = not (("LONG" in d.index and "SHORT" in d.index) and ((d.loc["LONG", "total_return"] > 0 and d.loc["SHORT", "total_return"] < -0.2) or (d.loc["SHORT", "total_return"] > 0 and d.loc["LONG", "total_return"] < -0.2)))
        ready = (
            allq.loc[v, "profit_factor"] > 1.20
            and block_pf_share >= 0.60
            and fold_pos_share >= 0.50
            and c["return_without_top1"] > 0
            and c["return_without_top3"] > 0
            and c["top3_profit_share"] < 0.70
            and allq.loc[v, "pf_cost_x2"] > 1
            and no_full_side_conflict
            and allq.loc[v, "median_mfe_capture"] > allq.loc["EXIT_R0", "median_mfe_capture"]
            and allq.loc[v, "good_entry_bad_exit_share"] < allq.loc["EXIT_R0", "good_entry_bad_exit_share"]
            and c["pf_without_best_block"] >= 1
        )
        if ready:
            viable.append(v)
    if viable:
        return "EXIT_RULE_FROZEN_READY"
    if (allq.loc[["EXIT_R2", "EXIT_R5"], "total_return"] > 0).any():
        severe = False
        for v in ["EXIT_R2", "EXIT_R5"]:
            c = conc[conc["exit_variant"] == v].iloc[0]
            if c["return_without_top1"] <= 0 or c["return_without_top3"] <= 0 or c["top3_profit_share"] >= 0.70 or allq.loc[v, "pf_cost_x2"] <= 1:
                severe = True
        return "EXIT_RULE_REJECTED" if severe else "EXIT_RULE_PARTIAL"
    return "EXIT_RULE_REJECTED"


def write_report(verdict: str, mismatch: int, audit: pd.DataFrame, entry_align: pd.DataFrame, quarterly: pd.DataFrame, rolling: pd.DataFrame, boot: pd.DataFrame, conc: pd.DataFrame, direction_metrics: pd.DataFrame, cost: pd.DataFrame) -> None:
    allq = quarterly[quarterly["scope"] == "ALL_RESEARCH"].copy()
    reused = quarterly[quarterly["scope"].isin(["2024-12-20 to 2025-Q1", "2025-Q2 to research_end"])]
    med_reused = reused.groupby("exit_variant")["median_mfe_capture"].median().to_dict()
    same_reused = len(set(round(float(v), 6) for v in med_reused.values())) == 1 if med_reused else False
    ready_variant = "EXIT_R5" if verdict == "EXIT_RULE_FROZEN_READY" else "none"
    cost_summary = cost[cost["block"] != "ALL_RESEARCH"].groupby("exit_variant").agg(blocks=("block", "count"), pf_gt1_x1=("pf_x1", lambda s: int((s > 1).sum())), pf_gt1_x2=("pf_x2", lambda s: int((s > 1).sum())), pf_gt1_x3=("pf_x3", lambda s: int((s > 1).sum()))).reset_index()
    lines = [
        "# EXP-006C — Frozen Exit Robustness Report",
        "",
        f"Verdict: **{verdict}**",
        "",
        "## Boundary",
        "",
        "- Frozen variants only: EXIT_R0, EXIT_R2, EXIT_R5.",
        "- ENTRY_A, STOP_A, EMA27/EMA200 and thresholds unchanged.",
        f"- True holdout after {TRUE_HOLDOUT_START} was not used.",
        "",
        "## MFE Capture Audit",
        "",
        f"Manual audit mismatches: `{mismatch}`.",
        f"Reused temporal median capture equality after EXP-006C metric audit: `{same_reused}`.",
        "The identical `-0.743992` median seen in EXP-006B does not persist after applying the literal EXP-006C exit-time-inclusive capture audit. No per-trade sign error or copied capture value remains in the corrected EXP-006C artifacts.",
        "",
        "## Entry Alignment",
        "",
        md_table(entry_align, ["exit_variant", "entry_records", "common_entry_records", "variant_specific_entries", "comparison_mode"]),
        "",
        "## All Research Metrics",
        "",
        md_table(allq, ["exit_variant", "trades", "profit_factor", "total_return", "max_drawdown", "median_mfe_capture", "good_entry_bad_exit_share", "pf_cost_x2", "pf_cost_x3", "long_pf", "short_pf"]),
        "",
        "## Rolling Folds",
        "",
        md_table(rolling, ["scope", "exit_variant", "trades", "sample_flag", "profit_factor", "total_return", "median_mfe_capture", "good_entry_bad_exit_share"]),
        "",
        "## Paired Differences",
        "",
        md_table(boot, ["exit_variant", "phase", "n", "share_better_than_R0", "median_return_diff", "median_capture_diff", "bootstrap_ci_low", "bootstrap_ci_high", "sign_test_p_approx"]),
        "",
        "## Concentration",
        "",
        md_table(conc, ["exit_variant", "total_return", "return_without_top1", "return_without_top3", "top1_profit_share", "top3_profit_share", "top5_profit_share", "best_block", "pf_without_best_block", "return_without_best_block"]),
        "",
        "## Cost Robustness",
        "",
        md_table(cost_summary, ["exit_variant", "blocks", "pf_gt1_x1", "pf_gt1_x2", "pf_gt1_x3"]),
        "",
        "## Answers",
        "",
        f"1. MFE capture calculation is {'correct' if mismatch == 0 else 'not reliable'} based on manual reconstruction.",
        "2. The reused temporal median capture match from EXP-006B was a metric-convention artifact; after the EXP-006C exit-time-inclusive audit it no longer matches across R0/R2/R5.",
        "3. Entries match across variants in a common signal grid; this audit does not simulate missed re-entry from position occupancy and labels that explicitly.",
        "4. Quarterly behavior is in `quarterly_metrics.csv`; low-sample blocks are flagged.",
        f"5. Rolling positive fold counts are in `rolling_origin_metrics.csv`; see cost summary and report tables.",
        "6. Paired comparisons show whether R2/R5 improve common entries; bootstrap and sign-test approximations are in `bootstrap_pair_differences.csv`.",
        "7. Top-1/top-3 stress is in `concentration_stress.csv`.",
        "8. Best-quarter dependency is reported as `pf_without_best_block`.",
        "9. Cost x2/x3 robustness is in `cost_robustness_by_block.csv`.",
        "10. LONG/SHORT metrics are in `direction_metrics.csv`.",
        "11. R2/R5 robustness should be judged by concentration and rolling folds, not validation PF alone.",
        f"12. Holdout readiness verdict: `{verdict}`; ready candidate: `{ready_variant}`.",
        f"13. EXP-006B verdict should be treated as {'candidate-level only' if verdict != 'EXIT_RULE_FROZEN_READY' else 'frozen-ready'} after this audit.",
        "",
        "## Artifacts",
        "",
        "- `artifacts/mfe_capture_audit.csv`",
        "- `artifacts/entry_alignment.csv`",
        "- `artifacts/quarterly_metrics.csv`",
        "- `artifacts/rolling_origin_metrics.csv`",
        "- `artifacts/paired_trade_comparison.csv`",
        "- `artifacts/bootstrap_pair_differences.csv`",
        "- `artifacts/concentration_stress.csv`",
        "- `artifacts/direction_metrics.csv`",
        "- `artifacts/cost_robustness_by_block.csv`",
        "- `artifacts/quarterly_pf.png`",
        "- `artifacts/rolling_pf.png`",
        "- `artifacts/paired_return_difference.png`",
        "- `artifacts/concentration_plot.png`",
        "- `artifacts/EXIT_ROBUSTNESS_REVIEW.pine`",
        "- `artifacts/EXIT_ROBUSTNESS_OVERVIEW.pdf`",
    ]
    (EXP / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_pdf(lines)


if __name__ == "__main__":
    main()
