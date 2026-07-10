# NYC FHV Market Analysis

Repository scaffold for data ingestion, transformation, analysis, and reporting.

## Structure

- `data/raw/`: source pulls (gitignored)
- `data/interim/`: cleaned intermediate datasets
- `data/processed/`: aggregated analysis-ready outputs
- `sql/`: standalone DuckDB SQL transformations
- `src/data/`: data acquisition scripts
- `src/analysis/`: analytical workflows
- `src/utils/`: shared utilities
- `notebooks/`: thin notebooks that call into `src/`
- `reports/`: written deliverables
- `figures/`: generated visual assets
