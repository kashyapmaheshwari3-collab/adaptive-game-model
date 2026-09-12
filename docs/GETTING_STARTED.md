# Getting Started — Adaptive Game Model

This guide is written for a football analyst, coach, or sporting director who has
received this repository or its live link and wants to evaluate it without a
computer-science background. Choose the path that matches you.

---

## Option 1 — Use the hosted app (zero installation, recommended for evaluation)

1. Open the live dashboard in any browser (Chrome, Edge, Safari, Firefox) on a
   laptop or tablet with an internet connection.
2. The app already contains **real StatsBomb La Liga 2015/16 data** (40 matches,
   148,071 events) and renders instantly — no training, no waiting.
3. Use it as a coach would:
   - **Home** — executive summary and key findings.
   - **Match Explorer** — pick a match, watch possessions and tactical states.
   - **Recommendations** — the decision engine output: which adjustment, expected
     benefit, confidence, sample size, and risk.
   - **Sequences** — example event sequences behind each recommendation.
   - **Validation & Model Card** — data quality gate, calibration, error analysis.
   - **Human-in-the-Loop** — add analyst comments, scout overrides, coach feedback.
4. No account, no downloads, nothing to install.

> If you were sent only this repository and not a live link, use Option 2, or
> deploy it yourself in ~10 minutes with `docs/DEPLOYMENT.md`.

---

## Option 2 — Run it locally (full evaluation, ~15 minutes)

### What you need first

| Requirement | Why | Where to get it |
|---|---|---|
| A laptop/desktop (Windows, macOS, or Linux) | The app and pipeline run on all three | — |
| **Python 3.10–3.12** | The project is pinned to these versions | https://www.python.org/downloads/ (Windows/macOS) or your package manager (Linux) |
| ~1.5 GB free disk space | Environment + dependencies + data | — |
| Internet connection | First-time package download | — |
| *(Optional)* Git | Required only for the "clone from GitHub" path | https://git-scm.com/downloads |

### Step 1 — Get the project files

Either:

- **Download the ZIP** and extract it to a folder you can find (e.g. `Documents/adaptive-game-model`), **or**
- **Clone from GitHub** (if you have Git installed):
  ```bash
  git clone https://github.com/<your-username>/adaptive-game-model
  cd adaptive-game-model
  ```

### Step 2 — Create the Python environment

Open a terminal in the project folder and run:

```bash
python -m venv .venv
```

Then activate it:

- **Windows:** `.venv\Scripts\activate`
- **macOS / Linux:** `source .venv/bin/activate`

You should now see a `(.venv)` prefix at the start of your terminal line.

### Step 3 — Install the requirements

```bash
pip install -r requirements.txt
```

This installs pandas, scikit-learn, xgboost, streamlit, mplsoccer, and the other
dependencies. It takes 2–5 minutes the first time.

### Step 4 — Get the data and run the pipeline

The project can run in two ways:

- **Real StatsBomb data** (downloads ~40 La Liga matches):
  ```bash
  python scripts/download_data.py
  python -m src.pipeline.run_all --competition 11 --season 27
  ```
- **Built-in synthetic data** (identical schema, no internet needed, ~90 seconds):
  ```bash
  python -m src.pipeline.run_all --synthetic
  ```

You will see progress lines and a final summary — `status: PASS` means everything
worked. Full run takes 4–6 minutes; `--synthetic --quick` takes under a minute.

### Step 5 — Launch the dashboard

```bash
streamlit run app/Home.py
```

Your browser opens automatically at `http://localhost:8501`. You are now looking
at the same app that is hosted live, running on your machine.

### Step 6 — (Optional) Regenerate reports and visuals

```bash
python scripts/generate_reports.py      # technical / coach / recruitment / opponent PDFs
python scripts/generate_visuals.py      # architecture, pitch plots, calibration, carousel
```

Outputs land in `reports/` and `visuals/`.

### Step 7 — When you are done

Type `Ctrl+C` in the terminal to stop the app. Close the window. Nothing is
installed globally — the `.venv` folder contains everything.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognized | Python is not on your PATH — reinstall Python and tick **"Add Python to PATH"**, or restart your terminal after installing |
| `pip install` fails on a package | Try `python -m pip install --upgrade pip`, then re-run the install |
| Port 8501 already in use | `streamlit run app/Home.py --server.port 8502` |
| Pipeline reports `PASS (0 errors, N warnings)` | Warnings are informational by design (e.g. outlier passes >90 m) — not failures |
| App loads but a chart is empty | Ensure the pipeline completed first (Step 4) before launching the app |

---

## Data & licensing notes

- **StatsBomb Open Data** — used under **CC BY-NC-SA 4.0** (non-commercial, share-alike, attribution). See `data/raw/statsbomb/LICENSE.txt` and https://github.com/statsbomb/open-data.
- **Code** — MIT License (`LICENSE`), free to reuse with attribution.
- The synthetic generator produces data with the identical schema so every feature
  works offline; results from synthetic data are marked `synthetic` in the outputs.

## Where the numbers come from (30-second orientation)

1. Events are aggregated into **possessions** (one attacking phase).
2. A **possession value model** (XGBoost + calibration) scores every possession
   from 0–5 using the outcome ladder in `docs/data_dictionary.md`.
3. Possessions are clustered into **named tactical states** (low block, high press,
   wide overload, ...) using football prototypes, never bare cluster numbers.
4. For each state × adjustment pair, a **doubly-robust causal estimate** (IPW +
   outcome model) yields an expected benefit with a 95% confidence interval.
5. Validation is **temporal and match-level** — never random splits — with a
   leakage check, ablation, and sensitivity analysis in the Model Card page.
