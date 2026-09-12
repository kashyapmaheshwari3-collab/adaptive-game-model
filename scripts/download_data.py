"""Download the StatsBomb Open Data subset used by the project.

Usage::

    python scripts/download_data.py --competition 11 --season 27 \\
        --only-teams "Barcelona,Real Madrid,Atlético Madrid" --max-matches 40

The dataset is La Liga 2015/16 (competition 11, season 27) - the Messi-era
Barcelona / Real Madrid / Atlético Madrid fixtures - which demonstrates the
system on genuine elite-club event data. StatsBomb Open Data is CC BY-NC-SA 4.0.
"""

from __future__ import annotations

import argparse

from src.ingestion.download import download


def main() -> None:
    parser = argparse.ArgumentParser(description="Download StatsBomb Open Data subset")
    parser.add_argument("--competition", type=int, default=11)
    parser.add_argument("--season", type=int, default=27)
    parser.add_argument("--max-matches", type=int, default=40)
    parser.add_argument("--only-teams", type=str, default="Barcelona,Real Madrid,Atlético Madrid")
    args = parser.parse_args()
    teams = [t.strip() for t in args.only_teams.split(",") if t.strip()]
    download(args.competition, args.season, args.max_matches, teams)


if __name__ == "__main__":
    main()
