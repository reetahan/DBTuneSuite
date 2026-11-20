"""Summarize the small-table UPDATE runs into a LaTeX table and a bar chart."""
import argparse
import csv
import statistics
from pathlib import Path

from plot_utils import paired_bars

RESULTS = Path("results")
WORKLOADS = {"2process": r"$10^3$-row table, 2 clients", "10process": r"$10^4$-row table, 10 clients"}
SYSTEMS = {"mysql": "MySQL", "postgres": "PostgreSQL"}


def median_time(path, label):
    vals = [float(r["response_time"]) for r in csv.DictReader(open(path)) if r["label"] == label]
    return statistics.median(vals) if vals else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setting", nargs="+", required=True, metavar="TAG=NAME")
    a = ap.parse_args()
    settings = [(t, n.replace("\\n", "\n")) for t, n in (s.split("=", 1) for s in a.setting)]

    rows = []
    for dbms, sys_name in SYSTEMS.items():
        for wl, wl_name in WORKLOADS.items():
            path = RESULTS / f"{dbms}_index_small_update_{wl}.csv"
            if not path.exists():
                continue
            for tag, name in settings:
                c = median_time(path, f"{tag}clustered")
                n = median_time(path, f"{tag}scan")
                if c is None or n is None:
                    continue
                rows.append(dict(sys=sys_name, wl=wl_name, name=name, c=c, n=n))
                print(f"{sys_name:10s} {wl:9s} {name:16s} clustered {c:7.3f} s  no index {n:7.3f} s  "
                      f"speedup {n / c:5.2f}x")

    lines = [r"\begin{tabular}{lllrrr}", r"\toprule",
             r"System & Workload & Setting & Clustered (s) & No index (s) & Speedup \\", r"\midrule"]
    prev = None
    for r in rows:
        if prev and prev != r["sys"]:
            lines.append(r"\addlinespace")
        prev = r["sys"]
        lines.append(f"{r['sys']} & {r['wl']} & {r['name']} & {r['c']:.3f} & {r['n']:.3f} & "
                     f"{r['n'] / r['c']:.2f}$\\times$ \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    Path("small_table_update.tex").write_text("\n".join(lines) + "\n")

    for r in rows:
        r["label"] = f"{r['wl']}\n{r['name']}"
    paired_bars(rows, "c", "n", "Clustered index (primary key) on the filtered column",
                "No index on the filtered column (each update scans the table)",
                "Time to finish all updates (s), median of 10 runs; each client runs 100 single-row UPDATEs",
                "small_table_update.png",
                "Concurrent single-row UPDATEs on a small table: clustered index vs. no index", "index")
    print("wrote small_table_update.tex and small_table_update.png")


if __name__ == "__main__":
    main()