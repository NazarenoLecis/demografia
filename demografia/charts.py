from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter

from demografia.indicators import build_pyramid, cohort_heatmap


def plot_population_pyramid(
    population: pd.DataFrame,
    iso3: str,
    year: int,
    output: Path,
    scenario: str | None = None,
    shares: bool = True,
) -> Path:
    pyramid = build_pyramid(population, iso3, year, scenario=scenario)
    male = -pyramid["male_share" if shares else "M"]
    female = pyramid["female_share" if shares else "F"]

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.barh(pyramid["age_label"], male, label="Uomini")
    ax.barh(pyramid["age_label"], female, label="Donne")
    ax.axvline(0, linewidth=0.8)
    ax.set_title(f"Piramide demografica {iso3} - {year}")
    ax.set_xlabel("Quota della popolazione (%)" if shares else "Popolazione")
    ax.set_ylabel("Età")
    ticks = ax.get_xticks()
    ax.set_xticklabels([f"{abs(tick):g}" for tick in ticks])
    ax.legend()
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_pyramid_comparison(
    population: pd.DataFrame,
    iso3: str,
    years: Iterable[int],
    output: Path,
) -> Path:
    years = list(years)
    fig, ax = plt.subplots(figsize=(10, 9))
    for year in years:
        pyramid = build_pyramid(population, iso3, year)
        total = pyramid[["M", "F"]].to_numpy().sum()
        shares = 100 * (pyramid["M"] + pyramid["F"]) / total
        ax.plot(shares, pyramid["age_label"], label=str(year))
    ax.set_title(f"Evoluzione della distribuzione per età - {iso3}")
    ax.set_xlabel("Quota della popolazione (%)")
    ax.set_ylabel("Età")
    ax.legend()
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_cohort_heatmap(population: pd.DataFrame, iso3: str, output: Path) -> Path:
    table = cohort_heatmap(population, iso3)
    fig, ax = plt.subplots(figsize=(14, 8))
    image = ax.imshow(np.log1p(table.to_numpy()), aspect="auto", origin="lower")
    ax.set_title(f"Evoluzione delle coorti - {iso3}")
    ax.set_xlabel("Anno")
    ax.set_ylabel("Età")
    year_positions = np.linspace(0, max(len(table.columns) - 1, 0), min(10, len(table.columns))).astype(int)
    ax.set_xticks(year_positions)
    ax.set_xticklabels([table.columns[position] for position in year_positions])
    fig.colorbar(image, ax=ax, label="log(1 + popolazione)")
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def plot_indicator_comparison(
    panel: pd.DataFrame,
    indicator: str,
    countries: Iterable[str],
    output: Path,
) -> Path:
    subset = panel[panel["indicator"].eq(indicator) & panel["iso3"].isin(countries)]
    fig, ax = plt.subplots(figsize=(11, 7))
    for iso3, group in subset.groupby("iso3"):
        ax.plot(group["year"], group["value"], label=iso3)
    ax.set_title(indicator.replace("_", " ").title())
    ax.set_xlabel("Anno")
    ax.set_ylabel("Valore")
    ax.legend(ncol=2)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def animate_population_pyramid(
    population: pd.DataFrame,
    iso3: str,
    years: Iterable[int],
    output: Path,
    fps: int = 4,
) -> Path:
    years = list(years)
    pyramids = {year: build_pyramid(population, iso3, year) for year in years}
    max_share = max(
        max(frame["male_share"].max(), frame["female_share"].max())
        for frame in pyramids.values()
    )
    first = pyramids[years[0]]
    fig, ax = plt.subplots(figsize=(9, 9))

    def update(year: int):
        ax.clear()
        frame = pyramids[year]
        ax.barh(frame["age_label"], -frame["male_share"], label="Uomini")
        ax.barh(frame["age_label"], frame["female_share"], label="Donne")
        ax.set_xlim(-max_share * 1.1, max_share * 1.1)
        ax.axvline(0, linewidth=0.8)
        ax.set_title(f"Piramide demografica {iso3} - {year}")
        ax.set_xlabel("Quota della popolazione (%)")
        ax.set_ylabel("Età")
        ax.legend()
        return ax.patches

    animation = FuncAnimation(fig, update, frames=years, interval=1000 / fps, blit=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    animation.save(output, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return output
