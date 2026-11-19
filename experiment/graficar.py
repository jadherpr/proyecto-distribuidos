import argparse
import csv
import statistics
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_series(path: str) -> dict:
    by_outage = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            value = row["recuperacion_s"]
            if value in ("", "ERROR"):
                continue
            by_outage[float(row["caida_s"])].append(float(value))
    return by_outage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grafica los resultados del tiempo de recuperacion para el poster"
    )
    parser.add_argument("csv", nargs="+", help="archivos resultados.csv")
    parser.add_argument("--out", default="experiment/datos/grafica_poster.png")
    args = parser.parse_args()

    groups: dict[str, tuple[list[float], list[float]]] = {}
    for path in args.csv:
        for outage, values in read_series(path).items():
            durations, means = groups.get(outage, ([], []))
            durations.extend(values)
            means.append(statistics.mean(values))
            groups[outage] = (durations, means)

    labels = []
    medias = []
    errores = []
    for outage in sorted(groups):
        durations, _ = groups[outage]
        labels.append(f"caida\n{outage:g} s")
        medias.append(statistics.mean(durations))
        errores.append(statistics.stdev(durations) if len(durations) > 1 else 0.0)

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, medias, yerr=errores, capsize=8, color="#2a9d8f", edgecolor="black")
    for bar, media in zip(bars, medias):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            f"{media:.2f} s",
            ha="center",
            fontweight="bold",
        )
    ax.set_ylabel("Tiempo de recuperación (s)")
    ax.set_xlabel("Duración de la caída del servidor")
    ax.set_title(
        f"Tiempo de recuperación tras reinicio (n={sum(len(v[0]) for v in groups.values())} mediciones)"
    )
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.out, dpi=200)
    print(f"figura guardada en {args.out}")

    for path in args.csv:
        for outage, values in sorted(read_series(path).items()):
            print(
                f"{path} caida={outage:g}s n={len(values)} "
                f"media={statistics.mean(values):.2f}s "
                + (f"desv={statistics.stdev(values):.2f}s" if len(values) > 1 else "")
            )


if __name__ == "__main__":
    main()
