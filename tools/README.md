# TOI Ranking Chart Generator

Generates one interactive Plotly HTML chart per year for the TOI
(Taiwan Olympiad in Informatics) preliminary-round rankings stored in
this repository (`2024/ranking`, `2025/ranking`, `2026/ranking`).

Each chart shows **every contestant's cumulative global-best score**
over elapsed contest time.  Every submission / history record is plotted
as a point; connected points form a fold-line per contestant.

---

## Requirements

Python 3.8+ and the `plotly` package:

```bash
pip install plotly
```

or use the provided requirements file:

```bash
pip install -r tools/requirements.txt
```

---

## Usage

```bash
python3 tools/generate_plots.py [--top-n N] [--out-dir DIR]
```

| Argument | Default | Description |
|---|---|---|
| `--top-n N` | `100` | Highlight the top-N finishers with vivid colours and legend entries. All other contestants are drawn as faint grey lines (still visible, no legend clutter). |
| `--out-dir DIR` | `plots/` | Directory where output files are written. Created automatically if it does not exist. |

### Examples

```bash
# Default: top 100, output to plots/
python3 tools/generate_plots.py

# Top 50 only
python3 tools/generate_plots.py --top-n 50

# Custom output directory
python3 tools/generate_plots.py --out-dir docs/plots

# Both options together
python3 tools/generate_plots.py --top-n 200 --out-dir /tmp/charts
```

---

## Output

After a successful run you will find:

```
plots/
  plotly.min.js          # Plotly bundle (~4.8 MB), shared by all HTML files
  2024-TOI2024.html      # Interactive chart for TOI2024初選
  2025-TOI2025.html      # Interactive chart for TOI2025初選
  2026-TOI2026.html      # Interactive chart for TOI2026初選
```

Open any HTML file in a browser (all three HTML files must stay in the
same folder as `plotly.min.js`).

### Chart interactions

| Action | How |
|---|---|
| Zoom in | Drag a rectangle, or scroll wheel |
| Pan | Click and drag |
| Reset view | Double-click the chart area |
| Hover detail | Move the cursor over any point to see contestant ID, school, elapsed time, and global score |
| Toggle a contestant | Click their name in the legend |
| Hide/show all non-top lines | They are always drawn; zoom in for individual inspection |
| Save as PNG | Camera icon in the mode bar (top-right) |

---

## Chart definition

**X axis** — seconds elapsed since contest start (ticks labelled as `HH:MM:SS`).

**Y axis** — *global score*: for each contestant, at each submission moment,
sum the **per-task best score** across all tasks submitted so far.
The result is monotonically non-decreasing.

**Lines** — top-N contestants (by final global score) are drawn in distinct
colours with legend entries.  All remaining contestants are drawn in
semi-transparent grey without legend entries.

---

## Data sources

| File | Purpose |
|---|---|
| `<year>/ranking/contests/index.json` | Contest key, start/end timestamps, score precision |
| `<year>/ranking/history` | Submission time-series: `[user, task, unix_timestamp, score]` |
| `<year>/ranking/users/index.json` | Optional display names / school affiliations |

---

## GitHub Pages auto-publish

The workflow at `.github/workflows/deploy.yml` runs automatically on every
push to `main`:

1. Checks out the repository
2. Installs `plotly` from `tools/requirements.txt`
3. Runs `python3 tools/generate_plots.py` to produce the HTML charts
4. Deploys the entire repository (including the generated `plots/` directory)
   to GitHub Pages via `actions/deploy-pages`

After the workflow completes the charts are accessible at:

```
https://<owner>.github.io/<repo>/plots/
https://<owner>.github.io/<repo>/plots/2024-TOI2024.html
https://<owner>.github.io/<repo>/plots/2025-TOI2025.html
https://<owner>.github.io/<repo>/plots/2026-TOI2026.html
```

To trigger a re-deploy manually, go to **Actions → Generate Plots & Deploy
to GitHub Pages → Run workflow**.

> **First-time setup:** In the repository **Settings → Pages**, set the
> source to **"GitHub Actions"** (not a branch).  This is required for the
> `actions/deploy-pages` step to work.
