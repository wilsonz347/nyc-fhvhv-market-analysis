"""
Incremental downloader for NYC TLC HVFHV trip data (Parquet files).

Downloads:
- Monthly HVFHV trip data (Parquet)
- NYC Taxi Zone Lookup table (CSV)

Features:
- Skips files that already exist locally (incremental)
- Validates existing files aren't partial/corrupt (via HTTP Content-Length check)
- Retries transient failures with exponential backoff
- Downloads to a temp file first, then renames — avoids leaving corrupt
  partial files if the script is interrupted mid-download
- Clear per-file logging: skipped / downloaded / failed

Usage:
    python download_fhvhv_data.py --start 2026-01 --end 2026-05
    python download_fhvhv_data.py --months 2026-01 2026-03 2026-05
"""

import argparse
import sys
import time
from pathlib import Path

import requests

TRIP_DATA_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
REFERENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5
CHUNK_SIZE = 1024 * 1024  # 1 MB

def download_lookup_table(summary, force=False):
    """Download the NYC TLC taxi zone lookup table."""
    filename = "taxi_zone_lookup.csv"
    dest = REFERENCE_DIR / filename

    print(f"\n{filename}")

    if not force and file_is_valid(dest, LOOKUP_URL):
        print("  Already exists and looks valid — skipping.")
        summary["skipped"].append(filename)
        return

    if dest.exists():
        print("  Existing file missing/incomplete/forced — re-downloading.")

    print(f"  Downloading from {LOOKUP_URL} ...")

    success = download_with_retries(LOOKUP_URL, dest)

    if success:
        size_kb = dest.stat().st_size / 1024
        print(f"  Done ({size_kb:.1f} KB)")
        summary["downloaded"].append(filename)
    else:
        print("  Failed after retries.")
        summary["failed"].append(filename)

def month_range(start: str, end: str) -> list[str]:
    """Generate a list of YYYY-MM strings from start to end, inclusive."""
    start_year, start_month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))

    months = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def remote_file_size(url: str) -> int | None:
    """Return the remote file's Content-Length via a HEAD request, or None if unavailable."""
    try:
        resp = requests.head(url, allow_redirects=True, timeout=30)
        if resp.status_code == 200:
            size = resp.headers.get("Content-Length")
            return int(size) if size is not None else None
        return None
    except requests.RequestException:
        return None


def file_is_valid(local_path: Path, url: str) -> bool:
    """Check if an already-downloaded file matches the remote file's expected size."""
    if not local_path.exists():
        return False
    expected_size = remote_file_size(url)
    if expected_size is None:
        # Can't verify remotely, but at least check that the local file isn't empty
        return local_path.stat().st_size > 0
    return local_path.stat().st_size == expected_size


def download_with_retries(url: str, dest: Path) -> bool:
    """Download a URL to dest, retrying on failure. Returns True on success."""
    tmp_path = dest.with_suffix(dest.suffix + ".part")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, stream=True, timeout=60) as resp:
                if resp.status_code == 404:
                    print(f"  Not found (404) — likely not published yet: {url}")
                    return False
                resp.raise_for_status()

                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                        f.write(chunk)

            tmp_path.rename(dest)  # Rename temp file to final destination
            return True

        except requests.RequestException as e:
            print(f"  Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if tmp_path.exists():
                tmp_path.unlink()
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * attempt
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)

    return False


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Download NYC TLC HVFHV trip data and reference datasets.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--start", help="Start month, e.g. 2026-01 (use with --end)")
    group.add_argument("--months", nargs="+", help="Explicit list of months, e.g. 2026-01 2026-03")
    parser.add_argument("--end", help="End month, e.g. 2026-05 (required with --start)")
    parser.add_argument("--force", action="store_true", help="Re-download even if a valid local file exists")
    args = parser.parse_args()

    if args.start and not args.end:
        parser.error("--start requires --end")

    months = month_range(args.start, args.end) if args.start else args.months

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "skipped": [],
        "downloaded": [],
        "failed": []
    }

    download_lookup_table(summary, force=args.force)

    for month in months:
        filename = f"fhvhv_tripdata_{month}.parquet"
        url = f"{TRIP_DATA_URL}/{filename}"
        dest = RAW_DIR / filename

        print(f"\n{filename}")

        if not args.force and file_is_valid(dest, url):
            print("  Already exists and looks valid — skipping.")
            summary["skipped"].append(filename)
            continue

        if dest.exists():
            print("  Existing file missing/incomplete/forced — re-downloading.")

        print(f"  Downloading from {url} ...")
        success = download_with_retries(url, dest)

        if success:
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"  Done ({size_mb:.1f} MB)")
            summary["downloaded"].append(filename)
        else:
            print("  Failed after retries.")
            summary["failed"].append(filename)

    print("\n" + "=" * 50)
    print(f"Skipped (already present):  {len(summary['skipped'])}")
    print(f"Downloaded:                 {len(summary['downloaded'])}")
    print(f"Failed:                     {len(summary['failed'])}")
    if summary["failed"]:
        print("\nFailed files (may not be published yet, or check connection):")
        for f in summary["failed"]:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()