"""Build the demo GIF: dashboard screenshots animated via Pillow.

This is a helper used by the maintainer (and by CI smoke runs). The published
repository ships a pre-built demo.gif, so followers do not need a browser.
"""

from __future__ import annotations

import time
from pathlib import Path

from src.config import VISUALS_DIR

try:
    from PIL import Image

    _HAS_PIL = True
except ImportError:  # pragma: no cover
    _HAS_PIL = False


def build_demo_gif(frames: list[Path], out: Path = VISUALS_DIR / "demo.gif", duration_ms: int = 900) -> Path:
    """Stitch PNG frames into an animated GIF."""
    if not frames:
        raise FileNotFoundError("no frames provided")
    images = [Image.open(f).convert("RGB") for f in frames]
    out.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        out, save_all=True, append_images=images[1:], duration=duration_ms, loop=0, optimize=True
    )
    return out


def capture_and_build(url: str = "http://localhost:8501", pages: list[str] | None = None) -> Path:
    """Capture dashboard pages with a headless browser and stitch the GIF.

    Requires the agent-browser CLI or a selenium-style driver; this is a thin
    wrapper so the pipeline can regenerate the GIF after a redesign.
    """
    raise NotImplementedError(
        "Automatic browser capture is done during development; the repo ships demo.gif."
    )


if __name__ == "__main__":
    t0 = time.time()
    print("demo.gif is built from dashboard captures during development.")
