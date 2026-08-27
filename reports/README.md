# Analysis Reports Directory

This directory contains all analysis outputs from AI Analyst.

## Directory Structure

After running analyses, you'll find:

```
reports/
├── analyses/           # Analysis narratives and summaries
├── charts/            # Generated visualizations (PNG files)
├── decks/             # Slide presentations (Marp/PDF)
├── sql/               # SQL queries used in analyses
└── data/              # Exported data tables (CSV)
```

## File Naming Convention

Files are automatically timestamped for version control:
- `analysis_YYYYMMDD_HHMMSS.md` - Analysis writeups
- `chart_YYYYMMDD_HHMMSS.png` - Chart images
- `deck_YYYYMMDD_HHMMSS.pdf` - Presentation decks
- `query_YYYYMMDD_HHMMSS.sql` - SQL queries

## Git Handling

By default, this directory is included in git. If you want to exclude reports from version control, add to `.gitignore`:

```
reports/analyses/
reports/charts/
reports/decks/
reports/sql/
reports/data/
```

Keep `reports/README.md` tracked to preserve directory documentation.
