"""Official NESO collection, UTC interval normalization, and as-of views."""

import gzip
import json
import time
import random
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .artifacts import atomic_bytes, digest, log, write_json
from .domain import SLOT, grid_time, utc

SOURCE = "https://api.carbonintensity.org.uk"


def retry_seconds(header, attempt):
    try:
        seconds = float(header)
    except (TypeError, ValueError):
        try:
            seconds = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            seconds = min(16, 2 ** attempt) + random.uniform(0, .5)
    return max(0., seconds)


def normalize(records, start, end):
    start, end = grid_time(start), grid_time(end)
    if end <= start:
        raise ValueError("Invalid requested range")
    rows = []
    for record in records:
        left, right = grid_time(record["from"]), grid_time(record["to"])
        if right - left != SLOT:
            raise ValueError("Source interval is not 30 minutes")
        if left < start or right > end:
            continue
        intensity = record["intensity"]
        values = []
        for key in ("actual", "forecast"):
            value = intensity.get(key)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not np.isfinite(value) or value < 0
            ):
                raise ValueError(f"Invalid source {key} value at {left}")
            values.append(np.nan if value is None else float(value))
        rows.append((left, *values, intensity.get("index")))
    frame = pd.DataFrame(rows, columns=["interval_start_utc", "actual", "provider_forecast", "provider_index"])
    if frame.empty:
        return pd.DataFrame(index=pd.date_range(start, end, freq="30min", inclusive="left"),
                            columns=["actual", "provider_forecast", "provider_index"]).rename_axis("interval_start_utc")
    for _, group in frame.groupby("interval_start_utc"):
        if len(group.drop_duplicates()) > 1:
            raise ValueError("Conflicting duplicate source intervals")
    frame = frame.drop_duplicates("interval_start_utc").set_index("interval_start_utc").sort_index()
    return frame.reindex(pd.date_range(start, end, freq="30min", inclusive="left")).rename_axis("interval_start_utc")


def collect(root, start="2022-01-01T00:00Z", end="2026-01-01T00:00Z", chunk_days=7):
    root = Path(root)
    start, end = grid_time(start), grid_time(end)
    if not 1 <= chunk_days <= 14:
        raise ValueError("API requests cannot exceed 14 days")
    frames, chunks = [], []
    session = requests.Session()
    session.headers["User-Agent"] = "GridShift-academic-research/1.0"
    for left in pd.date_range(start, end, freq=f"{chunk_days}D", inclusive="left"):
        right = min(end, left + pd.Timedelta(days=chunk_days))
        stem = f"{left:%Y-%m-%d}_{right:%Y-%m-%d}"
        path = root / "data/raw" / (stem + ".json.gz")
        metadata_path = path.with_suffix(".meta.json")
        url = f"{SOURCE}/intensity/{left:%Y-%m-%dT%H:%MZ}/{right:%Y-%m-%dT%H:%MZ}"
        if path.exists() and metadata_path.exists():
            payload = gzip.decompress(path.read_bytes())
            metadata = json.loads(metadata_path.read_text())
            if digest(payload) != metadata["raw_hash"]:
                raise ValueError("Cached raw response hash mismatch")
        else:
            for attempt in range(5):
                try:
                    response = session.get(url, timeout=(10, 40))
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt == 4:
                            response.raise_for_status()
                        retry = response.headers.get("Retry-After", "")
                        time.sleep(retry_seconds(retry, attempt))
                        continue
                    response.raise_for_status()
                    payload = response.content
                    content = json.loads(payload)
                    if not isinstance(content.get("data"), list):
                        raise ValueError("NESO response does not contain a data array")
                    break
                except (requests.Timeout, requests.ConnectionError):
                    if attempt == 4:
                        raise
                    time.sleep(min(16, 2 ** attempt))
            metadata = {
                "url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": response.status_code, "raw_hash": digest(payload),
                "headers": {key: response.headers.get(key) for key in ("Content-Type", "Date", "ETag", "Last-Modified")},
            }
            atomic_bytes(path, gzip.compress(payload, mtime=0))
            write_json(metadata_path, metadata)
            time.sleep(0.15)
        records = json.loads(payload)["data"]
        frame = normalize(records, left, right)
        frame["raw_hash"] = metadata["raw_hash"]
        frame["retrieved_at_utc"] = metadata["retrieved_at_utc"]
        frames.append(frame)
        chunks.append({"path": path.relative_to(root).as_posix(), **metadata, "normalized_slots": len(frame)})
        print(f"COLLECT {stem} {len(frame)} slots actual_missing={frame.actual.isna().sum()}", flush=True)
    result = pd.concat(frames).sort_index()
    if result.index.has_duplicates:
        raise ValueError("Normalized chunks overlap")
    result["actual_observed"] = result.actual.notna()
    result["quality_flag"] = np.where(result.actual_observed, "observed", "missing_actual")
    result["interval_end_utc"] = result.index + SLOT
    result["available_at_utc"] = result.index + 2 * SLOT
    result["availability_basis"] = "assumed interval end plus 30 minutes; not vintage verified"
    target = root / "data/normalized/carbon.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp.parquet")
    result.to_parquet(temporary)
    temporary.replace(target)
    manifest = {
        "schema_version": 1, "start_utc": str(start), "end_utc": str(end),
        "source": SOURCE, "licence": "CC BY 4.0 and official API terms",
        "units": "gCO2/kWh", "target": "NESO estimated actual",
        "forecast_vintage_verified": False, "expected_slots": int((end-start)/SLOT),
        "observed_slots": int(result.actual_observed.sum()), "normalized_slots": len(result),
        "normalized_hash": digest(target.read_bytes()), "chunks": chunks,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(root / "data/manifest.json", manifest)
    audit(root, result)
    log(root, "data", "Collect official half-hour interval responses",
        "Explicit UTC bounds avoid civil-day and preceding-slot traps", root / "data/manifest.json", "COLLECTED")
    return result


def load(root):
    root = Path(root)
    path = root / "data/normalized/carbon.parquet"
    manifest = json.loads((root / "data/manifest.json").read_text())
    if digest(path.read_bytes()) != manifest["normalized_hash"]:
        raise ValueError("Normalized dataset hash mismatch")
    frame = pd.read_parquet(path)
    frame.index = pd.DatetimeIndex(frame.index).tz_convert("UTC")
    frame.attrs["gridshift_source"] = "NESO"
    frame.attrs["dataset_hash"] = manifest["normalized_hash"]
    return frame.asfreq("30min")


def as_of(series, origin, delay_slots=1):
    origin = grid_time(origin)
    if delay_slots < 0:
        raise ValueError("Publication delay cannot be negative")
    if not isinstance(series.index, pd.DatetimeIndex) or series.index.tz is None or series.index.has_duplicates:
        raise ValueError("History must have unique timezone-aware timestamps")
    return series.loc[series.index + SLOT * (1 + delay_slots) <= origin].copy()


def verify_raw(root):
    root = Path(root)
    manifest = json.loads((root / "data/manifest.json").read_text())
    normalized = load(root)
    frames = []
    missingness = []
    for chunk in manifest["chunks"]:
        payload = gzip.decompress((root / chunk["path"]).read_bytes())
        if digest(payload) != chunk["raw_hash"]:
            raise ValueError("Raw response hash mismatch")
        boundaries = chunk["url"].split("/intensity/")[1].split("/")
        records = json.loads(payload)["data"]
        chunk_frame = normalize(records, *boundaries)
        frames.append(chunk_frame)
        present = {utc(record["from"]) for record in records}
        for timestamp in chunk_frame.index[chunk_frame.actual.isna()]:
            missingness.append({"interval_start_utc": timestamp,
                                "reason": "explicit_null_actual" if timestamp in present else "absent_interval"})
    rebuilt = pd.concat(frames).sort_index()
    pd.testing.assert_frame_equal(
        rebuilt[["actual", "provider_forecast", "provider_index"]],
        normalized[["actual", "provider_forecast", "provider_index"]],
        check_freq=False,
    )
    result = {"raw_chunks": len(frames), "reconstructed_slots": len(rebuilt), "values_match": True, "raw_hashes_match": True}
    missing_table = pd.DataFrame(missingness, columns=["interval_start_utc", "reason"])
    missing_table.to_csv(root / "artifacts/data/source_missingness.csv", index=False)
    result["missing_reason_counts"] = missing_table.reason.value_counts().to_dict()
    write_json(root / "artifacts/data/reconstruction.json", result)
    return result


def audit(root, frame=None):
    root = Path(root)
    frame = load(root) if frame is None else frame
    coverage = frame.actual.notna().groupby(frame.index.strftime("%Y-%m")).agg(["sum", "count", "mean"])
    coverage.columns = ["observed_slots", "expected_slots", "coverage"]
    out = root / "artifacts/data"
    out.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(out / "monthly_coverage.csv")
    test_coverage = coverage.loc[coverage.index.str.startswith("2025-"), "coverage"]
    missing = frame.actual.isna().to_numpy()
    edges = np.diff(np.r_[False, missing, False].astype(int))
    begins, finishes = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    gaps = pd.DataFrame([
        {"start": frame.index[a], "end": frame.index[b-1]+SLOT, "slots": int(b-a)}
        for a, b in zip(begins, finishes)
    ], columns=["start", "end", "slots"])
    gaps.to_csv(out / "gaps.csv", index=False)
    quality = {
        "slots": len(frame), "observed": int((~missing).sum()), "missing": int(missing.sum()),
        "zeros": int((frame.actual == 0).sum()),
        "overall_coverage": float((~missing).mean()), "minimum_monthly_coverage": float(coverage.coverage.min()),
        "minimum_test_monthly_coverage": float(test_coverage.min()) if len(test_coverage) else None,
        "unique_utc_intervals": not frame.index.has_duplicates,
        "regular_grid": bool(np.all(np.diff(frame.index.asi8) == SLOT.value)),
        "data_gate_pass": bool((~missing).mean() >= .99 and len(test_coverage) == 12 and test_coverage.min() >= .95),
        "availability_is_assumed": True,
    }
    write_json(out / "quality.json", quality)
    return quality
