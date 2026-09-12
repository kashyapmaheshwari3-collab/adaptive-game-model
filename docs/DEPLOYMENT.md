# Deployment Guide — live web app in two platforms

The dashboard is a standard Streamlit multi-page app (`app/Home.py` + `app/pages/`).
It reads pre-computed artefacts from `data/processed/`, so a deployed app
renders instantly without running the training pipeline.

## Option A — Streamlit Community Cloud (recommended, zero config)

1. Push this repository to GitHub (`main` branch).
2. Go to https://streamlit.io/cloud and sign in with GitHub.
3. Click **New app** → select the repository → set:
   - Main file path: `app/Home.py`
   - Python version: `3.12`
4. Click **Deploy**. Streamlit reads `requirements.txt` and `.streamlit/config.toml`
   automatically. Deployment takes ~2-4 minutes.
5. Your app is live at `https://<app-name>.streamlit.app`.

Notes:
- `data/processed/*.parquet/json/csv` are committed so the app has instant data.
- If you want the app to *also* train models at boot, uncomment the "Run pipeline" flow
  in `app/Home.py` — not recommended for a shared free tier (memory limits).

## Option B — Hugging Face Spaces

1. Create an account at https://huggingface.co.
2. **New Space** → SDK: **Streamlit** → name it, public or private → create.
3. In the Space, upload the repository files (or push with git):
   ```
   git clone https://huggingface.co/spaces/<user>/<space>
   # copy the project files in
   git add . && git commit -m "Adaptive Game Model" && git push
   ```
4. HF Spaces auto-installs `requirements.txt` and runs `app/Home.py`
   (Spaces run `streamlit run app/Home.py` by default for Streamlit SDK spaces;
   if your Space uses a different entry file, set it in Settings).
5. Live at `https://huggingface.co/spaces/<user>/<space>`.

## Option C — Render / any Docker host

```bash
docker build -t adaptive-game-model .
docker run -p 8501:8501 adaptive-game-model
```

On Render: New Web Service → connect repo → `Dockerfile` is auto-detected.

## Keeping the demo honest on the free tier

- The heavy computation (XGBoost, 200-bootstrap CIs) runs once in CI / locally;
  the app only *reads* artefacts.
- `data/processed` total size is a few MB — well within free-tier limits.
- If you regenerate artefacts locally, commit them so the hosted app stays in sync.

## Checklist before publishing

- [ ] Replace `you@example.com` / `your-handle` / `Your Name` in README, `pyproject.toml`, docs.
- [ ] Verify `python -m src.pipeline.run_all` passes and `data/processed` is populated.
- [ ] Run `pytest` and `ruff check src app tests scripts`.
- [ ] Commit `visuals/demo.gif`, `visuals/architecture_diagram.png`, `reports/*.pdf`.
- [ ] Add the live URL to the README "Demo link" and your CV.
