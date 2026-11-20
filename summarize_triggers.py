"""Summarize the aggregate-maintenance (trigger) runs into a LaTeX table and a bar chart."""
import argparse
import csv
import statistics
from pathlib import Path

from plot_utils import paired_bars

N_INSERTS = 1000          # rows in triggers_input.csv
RESULTS = Path("results")


def medians(path, label):
    vals = [float(r["response_time"]) for r in csv.DictReader(open(path)) if r["label"] == label]
    if not vals:
        raise SystemExit(f"no rows labelled {label} in {path}")
    return statistics.median(vals)


def measure(dbms, tag):
    ins = RESULTS / f"{dbms}_aggregate_triggers_insert.csv"
    qry = RESULTS / f"{dbms}_aggregate_triggers_queries_{tag}.csv"
    if not qry.exists():
        return None
    i_w = medians(ins, f"{tag}with_trigger_insert") / N_INSERTS
    i_o = medians(ins, f"{tag}without_trigger_insert") / N_INSERTS
    q_w = medians(qry, f"{tag}with_trigger_vendor")
    q_o = medians(qry, f"{tag}without_trigger_vendor")
    return i_w, i_o, q_w, q_o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", type=float, default=100, help="inserts per vendor query")
    ap.add_argument("--setting", nargs=2, action="append", required=True,
                    metavar=("STRONG_TAG=NAME", "WEAK_TAG=NAME"))
    a = ap.parse_args()
    n_q = N_INSERTS / a.ratio

    rows = []
    for pair in a.setting:
        for role, item in zip(["strong", "weak"], pair):
            tag, name = item.split("=", 1)
            name = name.replace("\\n", "\n")
            for dbms in ["mysql", "postgres"]:
                m = measure(dbms, tag)
                if m is None:
                    continue
                i_w, i_o, q_w, q_o = m
                w_with = N_INSERTS * i_w + n_q * q_w
                w_without = N_INSERTS * i_o + n_q * q_o
                n_s = (q_o - q_w) / (i_w - i_o) if i_w > i_o else float("inf")
                rows.append(dict(dbms=dbms, name=name, role=role, i_w=i_w, i_o=i_o, q_w=q_w,
                                 q_o=q_o, w_with=w_with, w_without=w_without, n_s=n_s))

    for r in rows:
        print(f"{r['dbms']:8s} {r['name']:18s} insert/row {r['i_w']*1e3:8.3f} vs {r['i_o']*1e3:7.3f} ms | "
              f"query {r['q_w']*1e3:8.3f} vs {r['q_o']*1e3:8.3f} ms | workload {r['w_with']:7.3f} vs "
              f"{r['w_without']:7.3f} s | N_s {r['n_s']:9.1f}")

    lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
             r"System & Setting & With trigger (s) & Without trigger (s) & Speedup & $N_s$ \\",
             r"\midrule"]
    prev = None
    for r in rows:
        if prev and prev != r["dbms"]:
            lines.append(r"\addlinespace")
        prev = r["dbms"]
        sys_name = {"mysql": "MySQL", "postgres": "PostgreSQL"}[r["dbms"]]
        lines.append(f"{sys_name} & {r['name']} ({r['role']}) & {r['w_with']:.3f} & {r['w_without']:.3f} & "
                     f"{r['w_without'] / r['w_with']:.2f}$\\times$ & {r['n_s']:.0f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    Path("triggers_table.tex").write_text("\n".join(lines) + "\n")

    for r in rows:
        r["sys"] = {"mysql": "MySQL", "postgres": "PostgreSQL"}[r["dbms"]]
        r["label"] = r["name"]
    paired_bars(rows, "w_with", "w_without",
                "Trigger keeps per-vendor totals in a summary table (query reads one row)",
                "No trigger (query recomputes the total with a join over orders)",
                f"Time for {N_INSERTS} single-row order inserts + {n_q:g} vendor-total queries (s)",
                "triggers_workload.png",
                "Maintaining vendor totals with a trigger vs. computing them at query time", "trigger")
    print("wrote triggers_table.tex and triggers_workload.png")


if __name__ == "__main__":
    main()