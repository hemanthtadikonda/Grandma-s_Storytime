# Scene images (priority order)

1. **Auto search** — from prompt keywords (`IMAGE_PROVIDER` in `.env`; temp files, deleted after job).
2. **These files** — if present, used instead of search for that scene:
   - `scene_00.png` … `scene_04.png` (or `.jpg`)
   - `s1.png`, `s2.png`, …
3. **Generated art** — if search fails and no file here.

Vertical **1080×1920** (or larger) works best.
