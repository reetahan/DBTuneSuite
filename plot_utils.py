import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"


def paired_bars(rows, rec_key, alt_key, rec_name, alt_name, xlabel, out, title, rec_short):
    systems = list(dict.fromkeys(r["sys"] for r in rows))
    n = max(sum(r["sys"] == s for r in rows) for s in systems)
    fig, axes = plt.subplots(1, len(systems), figsize=(5.2 * len(systems), 0.75 * n + 1.6), squeeze=False)
    for ax, s in zip(axes[0], systems):
        rs = [r for r in rows if r["sys"] == s][::-1]
        y = range(len(rs))
        h = 0.36
        ax.barh([i + h / 2 + 0.02 for i in y], [r[rec_key] for r in rs], h, color=BLUE, label=rec_name)
        ax.barh([i - h / 2 - 0.02 for i in y], [r[alt_key] for r in rs], h, color=ORANGE, label=alt_name)
        xmax = max(max(r[rec_key], r[alt_key]) for r in rs)
        for i, r in zip(y, rs):
            ratio = r[alt_key] / r[rec_key]
            note = f"{rec_short} {ratio:.2f}× faster" if ratio >= 1 else f"{rec_short} {1 / ratio:.2f}× slower"
            ax.text(max(r[rec_key], r[alt_key]) + 0.02 * xmax, i, note,
                    va="center", fontsize=9, color=INK)
        ax.set_yticks(list(y), [r["label"] for r in rs], fontsize=9, color=INK)
        ax.set_xlim(0, xmax * 1.9)
        ax.set_xlabel("Time (s)", fontsize=9, color=MUTED)
        ax.set_title(s, fontsize=11, color=INK, loc="left")
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ["top", "right"]:
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(MUTED)
        ax.spines["bottom"].set_color(MUTED)
        ax.tick_params(colors=MUTED, labelsize=8)
    handles, labels = axes[0][0].get_legend_handles_labels()
    H = fig.get_figheight()
    top = 1 - 0.7 / H                                
    fig.suptitle(title, x=0.01, y=0.995, ha="left", va="top", fontsize=11, color=INK)
    fig.text(0.01, 1 - 0.26 / H, xlabel, ha="left", va="top", fontsize=9, color=MUTED)
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.005, 1 - 0.42 / H),
               frameon=False, fontsize=9, ncol=1)
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(out, dpi=200)
