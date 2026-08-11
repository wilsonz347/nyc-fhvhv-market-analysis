# NYC FHVHV Demand Analysis & Forecasting

Analyzes NYC High-Volume For-Hire Vehicle (Uber/Lyft) trip data to understand ride demand patterns and forecast hourly demand for a high-traffic pickup zone (Times Square).

## What this project does

1. **Audits** raw TLC trip data for quality issues (missing values, invalid timestamps, outliers)
2. **Cleans** the data into an analysis-ready table
3. **Explores** demand patterns across time and location
4. **Forecasts** hourly demand using SARIMA, benchmarked against a naive baseline

## Project structure

```
nyc-fhvhv-analysis/
├── data/
│   ├── raw/                          # Downloaded TLC parquet files
│   ├── reference/                    # Taxi zone lookup table
├── notebooks/
│   ├── 01_data_understanding.ipynb   # Data quality audit
│   ├── 02_data_preprocessing.ipynb   # Cleaning pipeline
│   ├── 03_exploratory_data_analysis.ipynb  # Demand pattern analysis
│   └── 04_modeling.ipynb             # Forecasting model + evaluation
├── scripts/
│   └── download_fhvhv_data.py        # Incremental data downloader
├── src/nyc_fhvhv/
│   └── cleaning.py                   # Shared cleaning logic (clean_fhvhv)
├── .gitignore
├── LICENSE
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Data

**Source:** [NYC TLC HVFHV trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) (monthly Parquet files) + TLC taxi zone lookup table.

**Coverage:** December 2025 – May 2026

**Getting the data:**
```bash
python scripts/download_fhvhv_data.py --start 2025-12 --end 2026-05
```
Downloads are incremental — already-downloaded, valid files are skipped automatically.

## Pipeline

### 1. Data quality audit (`01_data_understanding.ipynb`)
Profiles the raw dataset before any cleaning. Checks duplicates, missing values, invalid timestamp ordering, out-of-range location IDs, and outliers in trip distance/duration/fare. Findings from this notebook justify every filter applied in step 2.

### 2. Cleaning (`02_data_preprocessing.ipynb` / `src/nyc_fhvhv/cleaning.py`)
A single shared function, `clean_fhvhv()`, applies the filters identified in the audit:
- Valid trip distance, fare, and driver pay (> 0)
- Valid timestamp ordering (`request → on_scene → pickup → dropoff`)
- Joins pickup/dropoff location IDs to zone names via the TLC zone lookup table

This function is reused across notebooks so every month of data is cleaned identically.

### 3. Exploratory analysis (`03_exploratory_data_analysis.ipynb`)
Answers demand-pattern questions that inform the modeling approach: when and where demand peaks, whether zones behave differently, whether demand is autocorrelated, and whether there are anomalous days. 

### 4. Modeling (`04_modeling.ipynb`)
Builds an hourly demand forecast for Times Square:
- **Baseline:** same-hour-last-week naive forecast
- **Model:** SARIMA, tuned using ACF/PACF diagnostics
- **Evaluation:** rolling 24-hour-ahead forecast on a May 2026 holdout, compared to baseline via MAE

## Key result

| Model | MAE |
|---|---:|
| Same-hour-last-week baseline | 56.87 |
| SARIMA | 72.77 |

The naive baseline outperformed SARIMA. SARIMA tended to underestimate demand during peak periods, especially on high-demand days, which could lead to insufficient capacity during the busiest times.

## Setup

```bash
pip install -e .
```

## Requirements

- Python 3.10+
- DuckDB