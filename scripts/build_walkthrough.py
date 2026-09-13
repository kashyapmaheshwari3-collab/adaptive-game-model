"""Generate a self-contained project walkthrough with source listings."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "WALKTHROUGH.md"
EXCLUDED = {".git", ".venv", ".pytest_cache", "__pycache__"}
INCLUDED_SUFFIXES = {".py", ".toml", ".yml", ".yaml", ".md", ".txt", ".json", ".dockerfile"}


def files() -> list[Path]:
    result = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED for part in path.parts):
            continue
        if "data" in path.parts or "reports" in path.parts or "visuals" in path.parts:
            continue
        if path.name == "WALKTHROUGH.md":
            continue
        if path.suffix.lower() in INCLUDED_SUFFIXES or path.name == "Dockerfile":
            result.append(path)
    return sorted(result)


def language(path: Path) -> str:
    return {
        ".py": "python",
        ".json": "json",
        ".toml": "toml",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".md": "markdown",
        ".dockerfile": "dockerfile",
    }.get(path.suffix.lower(), "")


def main() -> None:
    lines = [
        "# Adaptive Game Model — Complete Walkthrough",
        "",
        "This document explains the project from first setup to deployment and includes the "
        "text source of every maintained code/configuration/document file.",
        "",
        "## 1. Start from zero",
        "",
        "1. Install Python 3.10–3.12 and Git.",
        "2. Unzip or clone this repository and open a terminal at its root.",
        "3. Create an environment: `python -m venv .venv`.",
        "4. Activate it (`.venv\\Scripts\\activate` on Windows, `source .venv/bin/activate` elsewhere).",
        "5. Install dependencies: `pip install -r requirements.txt`.",
        "6. Optionally download StatsBomb Open Data with `python scripts/download_data.py`.",
        "7. Run the reproducible offline pipeline: `python -m src.pipeline.run_all --synthetic`.",
        "8. Launch the dashboard: `streamlit run app/Home.py`.",
        "9. Generate reports and visuals with the scripts in `scripts/`.",
        "10. Run `pytest` and `ruff check src app tests scripts` before sharing.",
        "",
        "## 2. What happens in the pipeline",
        "",
        "Raw StatsBomb events (or the deterministic fallback) are loaded, standardised, validated, "
        "aggregated into possessions, enriched with Elo and tactical proxies, scored with calibrated "
        "possession-value models, grouped into named tactical states, and passed to doubly-robust "
        "adjustment estimation. Recommendations retain confidence intervals, sample sizes, risks, "
        "and execution requirements. Streamlit and PDF reports consume the persisted artefacts.",
        "",
        "## 3. How to read the outputs",
        "",
        "- `data/processed/evaluation_report.json`: temporal performance and calibration.",
        "- `data/processed/adjustments.csv`: state-by-adjustment estimates and uncertainty.",
        "- `data/processed/recommendations.csv`: coach-facing ranked recommendations.",
        "- `data/processed/validation_report.json`: data-quality gate.",
        "- `reports/`: technical, coach, recruitment, and opponent PDFs.",
        "- `visuals/`: architecture, calibration, pitch plots, carousel, and demo GIF.",
        "",
        "## 4. Deployment",
        "",
        "The included Dockerfile listens on the injected `PORT` (default 8080) and the "
        "`.verdentc.json` manifest declares the fullstack deployment contract. For Streamlit "
        "Community Cloud, select `app/Home.py`; for Hugging Face Spaces, select the Streamlit "
        "SDK and use `requirements.txt`. Keep private credentials out of source and provide them "
        "through the hosting platform's secrets settings.",
        "",
        "## 5. Complete source listing",
        "",
    ]
    for path in files():
        rel = path.relative_to(ROOT).as_posix()
        lines.extend([f"### `{rel}`", "", f"```{language(path)}"])
        try:
            lines.append(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            lines.append("[binary or non-UTF-8 file omitted]")
        lines.extend(["```", ""])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} with {len(files())} source listings")


if __name__ == "__main__":
    main()
