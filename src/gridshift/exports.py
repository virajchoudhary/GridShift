"""Generate evidence-bound GridShift academic exports."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata as package_metadata
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


RESULT_KEYS = (
    "study_id",
    "forecast_champion",
    "strongest_simple",
    "deployment_model",
    "validation_metrics",
    "test_metrics",
    "validation_common_metrics",
    "test_common_metrics",
    "primary_summary",
    "primary_bootstrap",
    "versus_simple_bootstrap",
    "forecast_loss_bootstrap",
    "queue_summary",
    "primary_savings_pct",
    "primary_ci95_pct",
    "primary_jobs",
    "headline",
    "limitations",
)
RESULT_TABLE_KEYS = (
    "validation_metrics",
    "test_metrics",
    "validation_common_metrics",
    "test_common_metrics",
    "primary_summary",
    "primary_bootstrap",
    "versus_simple_bootstrap",
    "forecast_loss_bootstrap",
    "queue_summary",
)
SENSITIVITY_MONTHS = (1, 4, 7, 10)
SENSITIVITY_VARIANTS = (
    "default",
    "delay_0min",
    "delay_60min",
    "window_90days",
    "window_365days",
    "native_missing",
)
SAFE_STUDY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SOURCE_REFERENCES = (
    ("S1", "Official GB Carbon Intensity API", "https://api.carbonintensity.org.uk/"),
    ("S2", "Official API definitions", "https://carbon-intensity.github.io/api-definitions/"),
    ("S3", "NESO national carbon-intensity dataset", "https://www.neso.energy/data-portal/national-carbon-intensity-forecast"),
    ("S4", "NESO national resource dictionary", "https://www.neso.energy/data-portal/national-carbon-intensity-forecast/national_carbon_intensity_forecast"),
    ("S5", "NESO national carbon-intensity methodology", "https://api.neso.energy/dataset/f406810a-1a36-48d2-b542-1dfb1348096e/resource/36638178-e993-4d34-afdc-4ada83993585/download/neso-ci-national-methodology_v2.pdf"),
    ("S6", "Carbon Intensity API terms", "https://github.com/carbon-intensity/terms"),
    ("S7", "NESO Open Data Licence", "https://www.neso.energy/data-portal/neso-open-licence"),
    ("S8", "NESO historic generation mix and carbon intensity", "https://www.neso.energy/data-portal/historic-generation-mix"),
    ("S9", "Forecasting: Principles and Practice, forecasting toolbox", "https://otexts.com/fpp3/toolbox.html"),
    ("S10", "Forecasting: Principles and Practice, ARIMA", "https://otexts.com/fpp3/arima.html"),
    ("S11", "statsmodels augmented Dickey-Fuller test", "https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html"),
    ("S12", "statsmodels SARIMAX", "https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html"),
    ("S13", "statsmodels SARIMAX missing-data example", "https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_internet.html"),
)


class ExportInputError(ValueError):
    """Raised when the verified artifact set cannot support honest exports."""


@dataclass(frozen=True)
class Evidence:
    root: Path
    study_id: str
    config: Mapping[str, Any]
    results: Mapping[str, Any]
    quality: Mapping[str, Any]
    diagnostics: Mapping[str, Any]
    manifest: Mapping[str, Any]
    protocol: Mapping[str, Any]
    source_tables: Mapping[str, list[dict[str, Any]]]
    table_paths: Mapping[str, Path]
    figures: Mapping[str, Path]
    diagnostic_tables: Mapping[str, list[dict[str, Any]]]
    missing_diagnostic_tables: tuple[str, ...]
    missing_diagnostic_figures: tuple[str, ...]
    source_stages: Mapping[str, str]
    reconstruction: Mapping[str, Any] = field(default_factory=dict)
    sensitivity_completion: Mapping[str, Any] = field(default_factory=dict)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise ExportInputError(f"Cannot read {label} as valid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ExportInputError(f"{label} must contain a JSON object: {path}")
    return value


def _safe_artifact_path(base: Path, relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ExportInputError(f"{label} must be a non-empty relative path")
    candidate = Path(relative)
    if candidate.is_absolute() or any(part in {"..", ""} for part in candidate.parts):
        raise ExportInputError(f"{label} escapes its artifact directory: {relative!r}")
    resolved_base = base.resolve()
    resolved = (resolved_base / candidate).resolve()
    if resolved != resolved_base and resolved_base not in resolved.parents:
        raise ExportInputError(f"{label} escapes its artifact directory: {relative!r}")
    return resolved


def _csv_records(path: Path, label: str) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ExportInputError(f"{label} has no CSV header: {path}")
            columns = [str(value) for value in reader.fieldnames]
            records = [
                {key: _clean_cell(value) for key, value in row.items() if key is not None}
                for row in reader
            ]
    except FileNotFoundError:
        raise
    except (OSError, csv.Error) as exc:
        raise ExportInputError(f"Cannot parse {label}: {path}") from exc
    return columns, records


def _clean_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return None if text in {"", "NaN", "nan", "NA", "N/A", "null", "None"} else text
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _records(value: Any, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        if not value:
            return []
        if any(not isinstance(row, dict) for row in value):
            raise ExportInputError(f"{label} must be an array of table records")
        return [{str(key): _clean_cell(cell) for key, cell in row.items()} for row in value]
    if isinstance(value, dict):
        for key in ("records", "rows", "data"):
            if key in value:
                return _records(value[key], label)
        if value and all(isinstance(row, dict) for row in value.values()):
            rows = []
            for key, row in value.items():
                record = {str(name): _clean_cell(cell) for name, cell in row.items()}
                record.setdefault("model_id", str(key))
                rows.append(record)
            return rows
        return [{str(key): _clean_cell(cell) for key, cell in value.items()}]
    raise ExportInputError(f"{label} must be an array or object of records")


def _canonical_cell(value: Any) -> tuple[str, Any]:
    value = _clean_cell(value)
    number = _number(value)
    if number is not None:
        return ("number", number)
    if value is None:
        return ("null", None)
    return ("text", str(value))


def _canonical_records(records: Sequence[Mapping[str, Any]]) -> Counter:
    return Counter(
        tuple((key, _canonical_cell(row.get(key))) for key in sorted(row))
        for row in records
    )


def _tables_match(json_rows, csv_rows):
    if len(json_rows) != len(csv_rows):
        return False
    for left, right in zip(json_rows, csv_rows, strict=True):
        if set(left) != set(right):
            return False
        for key in left:
            a, b = _canonical_cell(left[key]), _canonical_cell(right[key])
            if a[0] == b[0] == "number":
                if not math.isclose(a[1], b[1], rel_tol=1e-9, abs_tol=1e-9):
                    return False
            elif a != b:
                return False
    return True


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        default=str,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_study_id(value: Any) -> str:
    if not isinstance(value, str) or not SAFE_STUDY_ID.fullmatch(value):
        raise ExportInputError("results.json study_id must be a safe artifact-directory name")
    return value


def _find_run_tables(run_root: Path, folder: str, filenames: Sequence[str]) -> tuple[Path, str]:
    candidates = (
        (run_root / "test" / folder, "test"),
        (run_root / folder, "stage-unspecified"),
        (run_root / "validation" / folder, "validation"),
    )
    for directory, stage in candidates:
        if all((directory / name).is_file() for name in filenames):
            return directory, stage
    searched = ", ".join(str(directory) for directory, _ in candidates)
    raise FileNotFoundError(
        f"Required {folder} evidence is incomplete for study {run_root.name}. "
        f"Expected {', '.join(filenames)} under one of: {searched}"
    )


def _verify_protocol(root: Path, results: Mapping[str, Any]) -> dict[str, Any]:
    path = root / "artifacts/protocol_freeze.json"
    if not path.is_file():
        raise FileNotFoundError(f"Required frozen protocol is missing: {path}")
    protocol_doc = _read_json(path, "protocol freeze")
    protocol = protocol_doc.get("protocol", {})
    if not isinstance(protocol, dict):
        raise ExportInputError("protocol_freeze.json protocol must be an object")
    digest = protocol_doc.get("protocol_hash")
    if not isinstance(digest, str) or not digest:
        raise ExportInputError("protocol_freeze.json must contain protocol_hash")
    actual = hashlib.sha256(_json_bytes(protocol)).hexdigest()
    if actual != digest:
        raise ExportInputError("protocol_freeze.json protocol_hash does not match its contents")
    result_protocol_hash = results.get("protocol_hash")
    if result_protocol_hash != digest:
        raise ExportInputError("results.json protocol_hash differs from protocol_freeze.json")
    frozen_study_id = protocol.get("study_id")
    if frozen_study_id != results.get("study_id"):
        raise ExportInputError("results.json study_id differs from the frozen protocol")
    software_hash = results.get("software_hash")
    if not isinstance(software_hash, str) or not software_hash:
        raise ExportInputError("results.json must contain the frozen software_hash")
    if protocol.get("software_hash") != software_hash:
        raise ExportInputError("results.json software_hash differs from the frozen protocol")
    return protocol_doc


def _validate_source_missingness(
    quality: Mapping[str, Any],
    reconstruction: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> None:
    if reconstruction.get("raw_hashes_match") is not True or reconstruction.get("values_match") is not True:
        raise ExportInputError("Source reconstruction hashes or normalized values do not match")
    reason_counts = reconstruction.get("missing_reason_counts")
    if not isinstance(reason_counts, dict):
        raise ExportInputError("reconstruction.json missing_reason_counts must be an object")

    expected: dict[str, int] = {}
    for reason, count in reason_counts.items():
        number = _number(count)
        if number is None or number < 0 or not number.is_integer():
            raise ExportInputError(f"Invalid reconstructed missingness count for {reason!r}")
        expected[str(reason)] = int(number)

    columns = set().union(*(row.keys() for row in records)) if records else set()
    if not {"interval_start_utc", "reason"}.issubset(columns):
        raise ExportInputError("source_missingness.csv must include interval_start_utc and reason")
    actual: Counter[str] = Counter()
    timestamps = []
    for row in records:
        reason = row.get("reason")
        timestamp = row.get("interval_start_utc")
        if not isinstance(reason, str) or not reason or timestamp is None:
            raise ExportInputError("source_missingness.csv contains an incomplete row")
        actual[reason] += 1
        timestamps.append(str(timestamp))
    if len(timestamps) != len(set(timestamps)):
        raise ExportInputError("source_missingness.csv contains duplicate interval timestamps")
    if dict(actual) != expected:
        raise ExportInputError("source_missingness.csv reason counts differ from reconstruction.json")

    slots = _number(quality.get("slots"))
    observed = _number(quality.get("observed"))
    missing = _number(quality.get("missing"))
    reconstructed_slots = _number(reconstruction.get("reconstructed_slots"))
    raw_chunks = _number(reconstruction.get("raw_chunks"))
    if slots is None or observed is None or missing is None or reconstructed_slots is None:
        raise ExportInputError("quality.json and reconstruction.json must contain slot counts")
    if raw_chunks is None or raw_chunks < 1 or not raw_chunks.is_integer():
        raise ExportInputError("reconstruction.json raw_chunks must be a positive integer")
    if reconstructed_slots != slots or sum(actual.values()) != missing or observed + missing != slots:
        raise ExportInputError("Quality, raw-source missingness, and reconstruction counts disagree")


def _validate_certified_summary(
    results: Mapping[str, Any],
    source_tables: Mapping[str, Sequence[Mapping[str, Any]]],
    config: Mapping[str, Any],
) -> None:
    point = _number(results.get("primary_savings_pct"))
    interval = results.get("primary_ci95_pct")
    jobs = results.get("primary_jobs")
    headline = results.get("headline")
    if point is None or not isinstance(interval, list) or len(interval) != 2:
        raise ExportInputError("results.json primary_savings_pct and two-value primary_ci95_pct are required")
    bounds = [_number(value) for value in interval]
    if any(value is None for value in bounds):
        raise ExportInputError("results.json primary_ci95_pct must contain two finite numbers")
    if isinstance(jobs, bool) or not isinstance(jobs, int) or jobs < 0:
        raise ExportInputError("results.json primary_jobs must be a non-negative integer")
    if not isinstance(headline, str) or not headline.strip():
        raise ExportInputError("results.json headline must be a non-empty string")

    bootstrap_rows = source_tables.get("primary_bootstrap", [])
    primary_rows = [
        row for row in bootstrap_rows
        if _number(row.get("block_days")) == 7
    ]
    if len(primary_rows) != 1:
        raise ExportInputError("primary_bootstrap.csv must contain exactly one seven-day primary row")
    primary = primary_rows[0]
    estimate_key = _field([primary], "estimate_savings_pct", "paired_savings_pct", "savings_pct")
    low_key = _field([primary], "ci95_savings_pct_low", "lower_95", "ci_low")
    high_key = _field([primary], "ci95_savings_pct_high", "upper_95", "ci_high")
    if not estimate_key or not low_key or not high_key:
        raise ExportInputError("The seven-day bootstrap row is missing its estimate or confidence bounds")
    source_values = [_number(primary.get(key)) for key in (estimate_key, low_key, high_key)]
    if any(value is None for value in source_values):
        raise ExportInputError("The seven-day bootstrap row contains a non-finite primary estimate")
    if not math.isclose(point, source_values[0], rel_tol=1e-10, abs_tol=1e-8) or any(
        not math.isclose(bound, source, rel_tol=1e-10, abs_tol=1e-8)
        for bound, source in zip(bounds, source_values[1:], strict=True)
    ):
        raise ExportInputError("results.json primary summary differs from primary_bootstrap.csv")

    if "h2_modeled_benefit_supported" in results:
        supported = results["h2_modeled_benefit_supported"]
        if not isinstance(supported, bool) or supported != (bounds[0] > 0):
            raise ExportInputError("results.json headline support flag differs from its primary interval")
        expected_headline = (
            "Modeled isolated-job benefit under declared assumptions"
            if supported else "Inconclusive or negative modeled isolated-job benefit"
        )
        if headline != expected_headline:
            raise ExportInputError("results.json headline differs from its primary support flag")

    scheduling = config.get("scheduling", {})
    if not isinstance(scheduling, Mapping):
        return
    duration = scheduling.get("default_duration_hours")
    slack = scheduling.get("default_slack_hours")
    deployment = results.get("deployment_model")
    matching_summary = []
    for row in source_tables.get("primary_summary", []):
        if row.get("result_type") not in {None, "scheduling"} or row.get("policy") != "forecast":
            continue
        if deployment is not None and str(row.get("model_id")) != str(deployment):
            continue
        if row.get("month_utc"):
            continue
        if duration is not None and _number(row.get("duration_hours")) is not None:
            if not math.isclose(_number(row.get("duration_hours")), float(duration), abs_tol=1e-9):
                continue
        if slack is not None and _number(row.get("slack_hours")) is not None:
            if not math.isclose(_number(row.get("slack_hours")), float(slack), abs_tol=1e-9):
                continue
        matching_summary.append(row)
    if len(matching_summary) != 1:
        raise ExportInputError("primary_summary.csv must contain one default-scenario row for the deployment model")
    scheduled = _number(matching_summary[0].get("n_scheduled"))
    if scheduled is None or scheduled != jobs:
        raise ExportInputError("results.json primary_jobs differs from the scheduled count in primary_summary.csv")


def _load_sensitivity_evidence(
    root: Path,
    table_paths: dict[str, Path],
    source_tables: dict[str, list[dict[str, Any]]],
    source_stages: dict[str, str],
) -> dict[str, Any]:
    directory = root / "artifacts/sensitivities"
    completion_path = directory / "completion.json"
    summary_path = directory / "sensitivity_summary.csv"
    if not completion_path.exists() and not summary_path.exists():
        return {}
    if not completion_path.is_file() or not summary_path.is_file():
        raise ExportInputError("Sensitivity completion and summary must both be present")

    completion = _read_json(completion_path, "sensitivity completion")
    expected_variants = set(SENSITIVITY_VARIANTS)
    if completion.get("completed") is not True:
        raise ExportInputError("Sensitivity completion does not mark the bounded study as completed")
    if completion.get("year") != 2024 or completion.get("months") != list(SENSITIVITY_MONTHS):
        raise ExportInputError("Sensitivity completion does not match the four planned 2024 quarters")
    if completion.get("episode_days") != 3:
        raise ExportInputError("Sensitivity completion does not use the prespecified three-day episodes")
    variants = completion.get("variants")
    if not isinstance(variants, dict) or set(variants) != expected_variants:
        raise ExportInputError("Sensitivity completion does not list the six prespecified variants")
    scope = completion.get("scope")
    if not isinstance(scope, str) or "No full-year robustness" not in scope:
        raise ExportInputError("Sensitivity completion must state its bounded episode-level scope")

    _, rows = _csv_records(summary_path, "sensitivity summary")
    observed = set()
    for row in rows:
        month = _number(row.get("month"))
        variant = row.get("variant")
        if month is None or not month.is_integer() or variant not in expected_variants:
            raise ExportInputError("Sensitivity summary contains an unknown month or variant")
        observed.add((int(month), str(variant)))
    expected = {(month, variant) for month in SENSITIVITY_MONTHS for variant in SENSITIVITY_VARIANTS}
    if len(rows) != len(expected) or observed != expected:
        raise ExportInputError("Sensitivity summary must contain each of the 24 month-variant cases exactly once")

    table_paths["sensitivity_summary"] = summary_path
    table_paths["sensitivity_completion"] = completion_path
    source_tables["sensitivity_summary"] = rows
    source_stages["sensitivity_summary"] = str(summary_path)
    return completion


def _load_evidence(root: str | Path, config: Mapping[str, Any]) -> Evidence:
    root_path = Path(root).resolve()
    results_path = root_path / "artifacts/results.json"
    if not results_path.is_file():
        raise FileNotFoundError(
            f"Academic export refused because verified results are absent: {results_path}"
        )
    if not isinstance(config, Mapping):
        raise ExportInputError("config must be a mapping")

    results = _read_json(results_path, "results.json")
    missing_keys = [key for key in RESULT_KEYS if key not in results]
    if missing_keys:
        raise ExportInputError(f"results.json is missing required keys: {', '.join(missing_keys)}")
    if results.get("schema_version") != 1:
        raise ExportInputError("results.json schema_version must be 1")
    if results.get("experimental_status") != "EXECUTED_FROZEN_2025":
        raise ExportInputError("results.json does not certify the frozen 2025 experiment")
    if results.get("external_deployment") != "NOT_PERFORMED":
        raise ExportInputError("Academic export expects the project record to state that external deployment was not performed")
    if results.get("verified") is False:
        raise ExportInputError("results.json explicitly marks this artifact set as unverified")
    if not isinstance(results["limitations"], list) or any(
        not isinstance(item, str) or not item.strip() for item in results["limitations"]
    ):
        raise ExportInputError("results.json limitations must be a non-empty-string array")

    study_id = _safe_study_id(results["study_id"])
    for key in RESULT_TABLE_KEYS:
        _records(results[key], f"results.json {key}")

    quality = _read_json(root_path / "artifacts/data/quality.json", "data quality")
    reconstruction_path = root_path / "artifacts/data/reconstruction.json"
    reconstruction = _read_json(reconstruction_path, "source reconstruction")
    missingness_path = root_path / "artifacts/data/source_missingness.csv"
    _, missingness_rows = _csv_records(missingness_path, "source missingness")
    _validate_source_missingness(quality, reconstruction, missingness_rows)
    diagnostics = _read_json(root_path / "artifacts/diagnostics/diagnostics.json", "diagnostics")
    manifest_path = root_path / "data/manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Required data provenance manifest is missing: {manifest_path}")
    manifest = _read_json(manifest_path, "data manifest")
    manifest_hash = manifest.get("normalized_hash")
    if not isinstance(manifest_hash, str) or not manifest_hash:
        raise ExportInputError("data/manifest.json must contain normalized_hash")
    result_data_hash = results.get("data_hash")
    if not isinstance(result_data_hash, str) or not result_data_hash:
        raise ExportInputError("results.json must contain data_hash")
    if result_data_hash != manifest_hash:
        raise ExportInputError("results.json data hash differs from data/manifest.json")
    expected_study_id = hashlib.sha256(
        _json_bytes({"data": manifest_hash, "config": dict(config)})
    ).hexdigest()[:16]
    if study_id != expected_study_id:
        raise ExportInputError(
            f"results.json study_id {study_id} does not match the data/config identity {expected_study_id}"
        )
    from .artifacts import require_freeze
    require_freeze(root_path, config)
    protocol = _verify_protocol(root_path, results)
    frozen_data_hash = protocol.get("data_hash")
    if frozen_data_hash != manifest_hash:
        raise ExportInputError("Frozen protocol data hash differs from data/manifest.json")
    if protocol.get("protocol", {}).get("config") != dict(config):
        raise ExportInputError("Exporter config differs from the configuration frozen before the test")

    diagnostic_dir = root_path / "artifacts/diagnostics"
    artifact_lists = diagnostics.get("artifacts", {})
    if not isinstance(artifact_lists, dict):
        raise ExportInputError("diagnostics.json artifacts must be an object")
    table_names = artifact_lists.get("tables", [])
    figure_names = artifact_lists.get("figures", [])
    if not isinstance(table_names, list) or not isinstance(figure_names, list):
        raise ExportInputError("diagnostics.json tables and figures must be arrays")

    diagnostic_tables: dict[str, list[dict[str, Any]]] = {}
    table_paths: dict[str, Path] = {
        "source_missingness": missingness_path,
        "reconstruction": reconstruction_path,
    }
    missing_tables = []
    for name in table_names:
        path = _safe_artifact_path(diagnostic_dir, name, "diagnostic table")
        if not path.is_file():
            missing_tables.append(str(name))
            continue
        _, diagnostic_tables[str(name)] = _csv_records(path, f"diagnostic table {name}")
        table_paths[f"diagnostics/{name}"] = path

    figures: dict[str, Path] = {}
    missing_figures = []
    for name in figure_names:
        path = _safe_artifact_path(diagnostic_dir / "figures", name, "diagnostic figure")
        if not path.is_file():
            missing_figures.append(str(name))
            continue
        if path.suffix.lower() != ".png" or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ExportInputError(f"Diagnostic figure is not a readable PNG: {path}")
        figures[str(name)] = path
        table_paths[f"diagnostics/figures/{name}"] = path
    if len(figures) < 3:
        raise ExportInputError(
            f"Academic exports require at least three verified diagnostic figures; found {len(figures)}"
        )

    run_root = root_path / "artifacts/runs" / study_id
    stage_tables: dict[str, list[dict[str, Any]]] = {
        "source_missingness": missingness_rows,
    }
    sources: dict[str, str] = {}
    for stage in ("validation", "test"):
        for metric_type in ("forecast_metrics", "forecast_common_metrics"):
            path = run_root / stage / f"{metric_type}.csv"
            if not path.is_file():
                raise FileNotFoundError(f"Required {stage} {metric_type} are missing: {path}")
            _, stage_tables[f"{stage}_{metric_type.removeprefix('forecast_')}"] = _csv_records(
                path,
                f"{stage} {metric_type}",
            )
            sources[f"{stage}_{metric_type.removeprefix('forecast_')}"] = str(path)
            table_paths[f"{stage}_{metric_type.removeprefix('forecast_')}"] = path
    selection_ledger = run_root / "selection/selection_ledger.csv"
    for stage in ("validation", "test"):
        path = run_root / stage / "forecast_path_metrics.csv"
        if path.is_file():
            _, stage_tables[f"{stage}_path_metrics"] = _csv_records(path, f"{stage} cumulative path metrics")
            table_paths[f"{stage}_path_metrics"] = path
    if selection_ledger.is_file():
        _, stage_tables["selection_ledger"] = _csv_records(selection_ledger, "selection ledger")
        table_paths["selection_ledger"] = selection_ledger
        sources["selection_ledger"] = str(selection_ledger)
    data_monthly_path = root_path / "artifacts/data/monthly_coverage.csv"
    if data_monthly_path.is_file():
        _, stage_tables["data_monthly_coverage"] = _csv_records(
            data_monthly_path,
            "monthly data-quality coverage",
        )
        table_paths["data_monthly_coverage"] = data_monthly_path

    single_dir, single_stage = _find_run_tables(
        run_root,
        "single_job",
        (
            "primary_summary.csv",
            "primary_bootstrap.csv",
            "primary_monthly.csv",
            "versus_simple_bootstrap.csv",
        ),
    )
    for filename, key in (
        ("primary_summary.csv", "primary_summary"),
        ("primary_bootstrap.csv", "primary_bootstrap"),
        ("primary_monthly.csv", "primary_monthly"),
        ("versus_simple_bootstrap.csv", "versus_simple_bootstrap"),
    ):
        path = single_dir / filename
        _, stage_tables[key] = _csv_records(path, key)
        sources[key] = str(path)
        table_paths[key] = path
    sources["primary_stage"] = single_stage

    forecast_loss_path = run_root / "test" / "forecast_loss_bootstrap.csv"
    if not forecast_loss_path.is_file():
        raise FileNotFoundError(f"Required test forecast-loss bootstrap is missing: {forecast_loss_path}")
    _, stage_tables["forecast_loss_bootstrap"] = _csv_records(
        forecast_loss_path,
        "forecast-loss bootstrap",
    )
    sources["forecast_loss_bootstrap"] = str(forecast_loss_path)
    table_paths["forecast_loss_bootstrap"] = forecast_loss_path

    queue_dir, queue_stage = _find_run_tables(run_root, "queue", ("queue_summary.csv",))
    queue_path = queue_dir / "queue_summary.csv"
    _, stage_tables["queue_summary"] = _csv_records(queue_path, "queue summary")
    sources["queue_summary"] = str(queue_path)
    sources["queue_stage"] = queue_stage
    table_paths["queue_summary"] = queue_path
    sensitivity_completion = _load_sensitivity_evidence(
        root_path,
        table_paths,
        stage_tables,
        sources,
    )
    residual_path = run_root / "validation/residuals/ljung_box.csv"
    if residual_path.is_file():
        _, stage_tables["validation_ljung_box"] = _csv_records(residual_path, "Validation Ljung-Box diagnostics")
        table_paths["validation_ljung_box"] = residual_path
    distribution_path = run_root / "validation/residuals/innovation_distribution.csv"
    if distribution_path.is_file():
        _, stage_tables["validation_innovation_distribution"] = _csv_records(distribution_path, "Validation innovation distribution")
        table_paths["validation_innovation_distribution"] = distribution_path

    for key in RESULT_TABLE_KEYS:
        json_rows = _records(results[key], f"results.json {key}")
        csv_rows = stage_tables[key]
        if json_rows and csv_rows:
            json_columns = set().union(*(row.keys() for row in json_rows))
            csv_columns = set().union(*(row.keys() for row in csv_rows))
            if json_columns != csv_columns or (
                len(json_rows) != len(csv_rows)
                or not _tables_match(json_rows, csv_rows)
            ):
                raise ExportInputError(f"results.json {key} does not match its source run CSV")
        elif json_rows or csv_rows:
            raise ExportInputError(f"results.json {key} is empty while its source run CSV is not, or vice versa")

    _validate_certified_summary(results, stage_tables, config)

    return Evidence(
        root=root_path,
        study_id=study_id,
        config=dict(config),
        results=results,
        quality=quality,
        diagnostics=diagnostics,
        manifest=manifest,
        protocol=protocol,
        source_tables=stage_tables,
        table_paths=table_paths,
        figures=figures,
        diagnostic_tables=diagnostic_tables,
        missing_diagnostic_tables=tuple(missing_tables),
        missing_diagnostic_figures=tuple(missing_figures),
        source_stages=sources,
        reconstruction=reconstruction,
        sensitivity_completion=sensitivity_completion,
    )


def _ascii(value: Any) -> str:
    text = str(value)
    replacements = {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00a0": " ",
        "\u2264": "<=",
        "\u2265": ">=",
        "\u2248": "about",
        "\u00d7": "x",
        "\u03c6": "phi",
        "\u03b8": "theta",
        "\u03b5": "epsilon",
        "\u03c3": "sigma",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _format(value: Any, *, digits: int = 5) -> str:
    value = _clean_cell(value)
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "true" if value else "false"
    number = _number(value)
    if number is not None:
        if number.is_integer():
            return str(int(number))
        return f"{number:.{digits}g}"
    return _ascii(value)


def _markdown_escape(value: Any) -> str:
    text = _ascii(_format(value))
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("\r", " ").replace("\n", " ")
    for marker in ("`", "*", "_", "[", "]", "<", ">"):
        text = text.replace(marker, "\\" + marker)
    return text


def _field(records: Sequence[Mapping[str, Any]], *names: str) -> str | None:
    if not records:
        return None
    available = set(records[0])
    for name in names:
        if name in available:
            return name
    lowered = {key.lower(): key for key in available}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _columns(records: Sequence[Mapping[str, Any]], preferred: Sequence[str] = ()) -> list[str]:
    if not records:
        return []
    existing = set().union(*(row.keys() for row in records))
    columns = [name for name in preferred if name in existing]
    columns.extend(
        name for name in records[0].keys() if name in existing and name not in columns
    )
    return columns


def _table(records: Sequence[Mapping[str, Any]], columns: Sequence[str] | None = None, limit: int | None = None) -> str:
    if not records:
        return "_Not evaluated. No scored rows are present in the verified artifact._"
    names = list(columns) if columns is not None else _columns(records)
    if not names:
        return "_No table columns are present._"
    rows = list(records[:limit] if limit is not None else records)
    clean = _markdown_escape
    lines = [
        "| " + " | ".join(clean(name) for name in names) + " |",
        "| " + " | ".join("---" for _ in names) + " |",
    ]
    lines.extend("| " + " | ".join(clean(row.get(name)) for name in names) + " |" for row in rows)
    if limit is not None and len(records) > limit:
        lines.append(f"\n_Table shows {limit} rows. The complete table remains in the referenced CSV artifact._")
    return "\n".join(lines)


def _select_records(
    records: Sequence[Mapping[str, Any]],
    *,
    equals: Mapping[str, Any] | None = None,
    in_values: Mapping[str, set[Any]] | None = None,
) -> list[dict[str, Any]]:
    result = []
    for record in records:
        matched = True
        for name, expected in (equals or {}).items():
            actual = record.get(name)
            if str(actual) != str(expected):
                matched = False
                break
        if not matched:
            continue
        for name, expected_values in (in_values or {}).items():
            actual = record.get(name)
            if actual not in expected_values:
                matched = False
                break
        if matched:
            result.append(dict(record))
    return result


def _metric_rows(evidence: Evidence, stage: str, models: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    records = evidence.source_tables.get(f"{stage}_metrics", [])
    selected = {str(value) for value in (models or ()) if value is not None}
    rows = []
    for row in records:
        group = str(row.get("group", row.get("group_type", ""))).lower()
        if group not in {"all", "overall", ""}:
            continue
        model = row.get("model_id", row.get("model"))
        if selected and str(model) not in selected:
            continue
        rows.append(dict(row))
    return rows


def _common_metric_rows(
    evidence: Evidence,
    stage: str,
    models: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    records = evidence.source_tables.get(f"{stage}_common_metrics", [])
    selected = {str(value) for value in (models or ()) if value is not None}
    rows = []
    for row in records:
        group = str(row.get("group", row.get("group_type", ""))).lower()
        if group not in {"all", "overall", ""}:
            continue
        model = row.get("model_id", row.get("model"))
        if selected and str(model) not in selected:
            continue
        rows.append(dict(row))
    return rows


def _shortlist_ic_rows(evidence: Evidence) -> list[dict[str, Any]]:
    records = evidence.source_tables.get("selection_ledger", [])
    anchors = [str(row["anchor"]) for row in records if row.get("anchor")]
    first = min(anchors) if anchors else None
    return [row for row in records if str(row.get("selected")).lower() == "true"
            and str(row.get("anchor")) == first]


def _stationarity_sentence(adf_rows, kpss_rows):
    levels = [row for row in adf_rows if str(row.get("variant", "")).startswith("levels_")]
    probabilities = [_number(row.get("p_value")) for row in levels]
    probabilities = [value for value in probabilities if value is not None]
    kpss = [row for row in kpss_rows if str(row.get("variant", "")).startswith("levels_")]
    if not probabilities:
        return "Level stationarity results are unavailable; no unit-root conclusion follows."
    return (
        f"Recorded level ADF p-values range from {_format(min(probabilities))} to "
        f"{_format(max(probabilities))}. "
        f"Level KPSS p-values are {', '.join(_format(row.get('p_value')) for row in kpss)}. "
        "KPSS values at 0.1 or 0.01 are lookup-table bounds, not exact tail probabilities. "
        "Read each against its specified regression, sample period, and lag cap. "
        "These tests do not establish stability across years or prove white noise."
    )


def _default_primary_rows(evidence: Evidence) -> list[dict[str, Any]]:
    records = evidence.source_tables.get("primary_summary", [])
    study = evidence.config.get("scheduling", {})
    if not isinstance(study, Mapping):
        return list(records)
    duration = study.get("default_duration_hours")
    slack = study.get("default_slack_hours")
    selected = []
    for row in records:
        if row.get("result_type") not in {None, "scheduling"}:
            continue
        if duration is not None and _number(row.get("duration_hours")) is not None:
            if not math.isclose(_number(row.get("duration_hours")), float(duration), abs_tol=1e-9):
                continue
        if slack is not None and _number(row.get("slack_hours")) is not None:
            if not math.isclose(_number(row.get("slack_hours")), float(slack), abs_tol=1e-9):
                continue
        if not row.get("month_utc"):
            selected.append(dict(row))
    return selected


def _bootstrap_rows(evidence: Evidence) -> list[dict[str, Any]]:
    rows = evidence.source_tables.get("primary_bootstrap", [])
    deployment_model = evidence.results.get("deployment_model")
    selected = []
    for row in rows:
        if deployment_model is not None and row.get("model_id") not in {None, deployment_model}:
            continue
        if row.get("block_days") is not None and _number(row.get("block_days")) is not None:
            selected.append(dict(row))
    return selected


def _monthly_default_rows(evidence: Evidence) -> list[dict[str, Any]]:
    rows = evidence.source_tables.get("primary_monthly", [])
    duration = evidence.config.get("scheduling", {}).get("default_duration_hours")
    slack = evidence.config.get("scheduling", {}).get("default_slack_hours")
    selected = []
    for row in rows:
        if duration is not None and _number(row.get("duration_hours")) is not None:
            if not math.isclose(_number(row.get("duration_hours")), float(duration), abs_tol=1e-9):
                continue
        if slack is not None and _number(row.get("slack_hours")) is not None:
            if not math.isclose(_number(row.get("slack_hours")), float(slack), abs_tol=1e-9):
                continue
        selected.append(dict(row))
    return selected


def _chosen_bootstrap_row(evidence: Evidence) -> Mapping[str, Any] | None:
    rows = _bootstrap_rows(evidence)
    primary = [row for row in rows if row.get("block_days") is not None and _number(row.get("block_days")) == 7]
    if primary:
        return primary[0]
    return rows[0] if rows else None


def _quality_rows(quality: Mapping[str, Any]) -> list[dict[str, Any]]:
    preferred = (
        "slots",
        "observed",
        "missing",
        "overall_coverage",
        "minimum_monthly_coverage",
        "minimum_test_monthly_coverage",
        "unique_utc_intervals",
        "regular_grid",
        "data_gate_pass",
        "availability_is_assumed",
    )
    return [{"measure": key, "value": quality[key]} for key in preferred if key in quality]


def _source_missingness_rows(evidence: Evidence) -> list[dict[str, Any]]:
    reasons = evidence.reconstruction.get("missing_reason_counts", {})
    if not isinstance(reasons, Mapping):
        return []
    labels = {
        "absent_interval": "No raw API interval record",
        "explicit_null_actual": "API interval with null actual",
    }
    return [
        {"reason": labels.get(str(reason), str(reason)), "interval_count": count}
        for reason, count in sorted(reasons.items())
    ]


def _quality_evidence_rows(evidence: Evidence) -> list[dict[str, Any]]:
    rows = _quality_rows(evidence.quality)
    for row in _source_missingness_rows(evidence):
        rows.append({
            "measure": f"missing: {row['reason']}",
            "value": row["interval_count"],
        })
    rows.extend(
        [
            {"measure": "raw source chunks verified", "value": evidence.reconstruction.get("raw_chunks")},
            {"measure": "raw hashes match", "value": evidence.reconstruction.get("raw_hashes_match")},
            {"measure": "normalized values match", "value": evidence.reconstruction.get("values_match")},
        ]
    )
    return rows


def _source_missingness_sentence(evidence: Evidence) -> str:
    reconstruction = evidence.reconstruction
    counts = reconstruction.get("missing_reason_counts", {})
    if not isinstance(counts, Mapping):
        return "The raw-source missingness reconstruction was not recorded."
    absent = counts.get("absent_interval", 0)
    explicit_null = counts.get("explicit_null_actual", 0)
    return (
        f"The raw reconstruction verified { _format(reconstruction.get('raw_chunks')) } source chunks "
        f"and { _format(reconstruction.get('reconstructed_slots')) } UTC half-hour slots. "
        f"It identifies {_format(absent)} intervals without a raw API record and "
        f"{_format(explicit_null)} records with an explicit null actual. "
        "These categories come from the raw interval audit; diagnostics.input_absent_intervals "
        "describes the development-series input and cannot establish raw API absence."
    )


def _adf_sample_rows(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in records:
        start = row.get("sample_start_utc")
        end = row.get("sample_end_exclusive_utc")
        sample = f"{start} to {end}" if start is not None and end is not None else None
        rows.append({
            "variant": row.get("variant"),
            "regression": row.get("regression"),
            "autolag": row.get("autolag"),
            "sample_n": row.get("sample_n"),
            "selected_lag": row.get("selected_lag"),
            "p_value": row.get("p_value"),
            "sample_range_utc": sample,
        })
    return rows


def _failed_search_rows(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []
    status_key = _field(records, "status", "fit_status", "outcome")
    converged_key = _field(records, "converged", "is_converged")
    failed = []
    for row in records:
        status = str(row.get(status_key, "")).strip().lower() if status_key else ""
        converged = row.get(converged_key) if converged_key else None
        failed_status = any(word in status for word in ("fail", "error", "exception", "nonconverged"))
        not_converged = converged is False or str(converged).strip().lower() in {"false", "0", "no"}
        if failed_status or not_converged:
            failed.append(dict(row))
    return failed


def _result_sentence(evidence: Evidence) -> str:
    chosen = evidence.results.get("deployment_model")
    headline = evidence.results.get("headline")
    certified_point = _number(evidence.results.get("primary_savings_pct"))
    certified_interval = evidence.results.get("primary_ci95_pct")
    certified_jobs = evidence.results.get("primary_jobs")
    if (
        isinstance(headline, str)
        and certified_point is not None
        and isinstance(certified_interval, list)
        and len(certified_interval) == 2
        and all(_number(value) is not None for value in certified_interval)
    ):
        low, high = (_number(value) for value in certified_interval)
        bootstrap = _chosen_bootstrap_row(evidence)
        paired_count_key = _field([bootstrap], "paired_job_count", "n", "paired_n") if bootstrap else None
        paired_count = (
            f"; the bootstrap paired {_format(bootstrap.get(paired_count_key))} jobs"
            if bootstrap is not None and paired_count_key is not None
            else ""
        )
        job_count = (
            f" across {_format(certified_jobs)} scheduled primary-policy jobs"
            if isinstance(certified_jobs, int) and not isinstance(certified_jobs, bool)
            else ""
        )
        return (
            f"{headline}. The certified seven-day paired block estimate is "
            f"{_format(certified_point)}% (95% interval {_format(low)} to {_format(high)}%)"
            f"{job_count}{paired_count}. This estimates modeled operational CO2 under the "
            "declared job, energy, and deadline assumptions."
        )

    bootstrap = _chosen_bootstrap_row(evidence)
    if bootstrap is None:
        return (
            f"The verified study record identifies {chosen or 'no deployment model'} as the "
            "validation-selected scheduling model. No paired bootstrap row is available."
        )
    point = _field([bootstrap], "estimate_savings_pct", "paired_savings_pct", "savings_pct")
    low = _field([bootstrap], "ci95_savings_pct_low", "lower_95", "ci_low")
    high = _field([bootstrap], "ci95_savings_pct_high", "upper_95", "ci_high")
    count = _field([bootstrap], "paired_job_count", "n", "paired_n")
    if not point or _number(bootstrap.get(point)) is None:
        return (
            f"The verified study record identifies {chosen or 'no deployment model'} as the "
            "validation-selected scheduling model. The primary interval has no numeric estimate."
        )
    interval = ""
    if low and high:
        interval = f" (95% interval {_format(bootstrap.get(low))} to {_format(bootstrap.get(high))})"
    n_text = f" across {_format(bootstrap.get(count))} paired jobs" if count else ""
    block = _format(bootstrap.get("block_days")) if bootstrap.get("block_days") is not None else "recorded"
    return (
        f"The recorded {block}-day paired block estimate is {_format(bootstrap.get(point))}%"
        f"{interval}{n_text}. This estimates modeled operational CO2 under the declared job, "
        "energy, and deadline assumptions."
    )


def _recorded_software_hash(evidence: Evidence) -> str:
    protocol = evidence.protocol.get("protocol", {})
    return str(
        evidence.results.get("software_hash")
        or (protocol.get("software_hash") if isinstance(protocol, Mapping) else None)
        or "Not recorded"
    )


def _markdown_report(evidence: Evidence) -> str:
    validation_models = (
        evidence.results.get("forecast_champion"),
        evidence.results.get("strongest_simple"),
    )
    validation_rows = _common_metric_rows(evidence, "validation")
    test_rows = _common_metric_rows(evidence, "test")
    primary = _default_primary_rows(evidence)
    bootstrap = _bootstrap_rows(evidence)
    monthly = _monthly_default_rows(evidence)
    quality = _quality_rows(evidence.quality)
    monthly_quality_rows = evidence.source_tables.get("data_monthly_coverage", [])
    package_versions = ", ".join(
        f"{name}={version}" for name, version in _package_versions().items()
    )
    diagnostic_figure_lines = []
    figure_captions = (
        ("series.png", "Observed development-period intensity"),
        ("representative_week.png", "Representative development week"),
        ("daily_slot_heatmap.png", "Intensity by local date and half-hour"),
        ("stl48.png", "Robust STL decomposition"),
    )
    for name, caption in figure_captions:
        if name in evidence.figures:
            diagnostic_figure_lines.extend(
                [
                    f"![{caption}](../artifacts/diagnostics/figures/{name})",
                    "",
                ]
            )
    lines = [
        "# GridShift: carbon-aware GPU workload scheduling",
        "",
        "## Abstract",
        "",
        (
            "This report evaluates a frozen classical time-series forecasting and workload-scheduling "
            f"study. The study identifier is `{evidence.study_id}`. "
            f"The validation-selected forecast champion is `{evidence.results.get('forecast_champion') or 'Not selected'}`. "
            f"The validation-selected scheduling model is `{evidence.results.get('deployment_model') or 'Not selected'}`. "
            + _result_sentence(evidence)
        ),
        "",
        "The target is NESO estimated GB carbon intensity in gCO2/kWh. Scheduling emissions are modeled from declared job energy and the estimated-actual series. They are not measured GPU energy or causal grid-emissions reductions.",
        "",
        "## Research question and scope",
        "",
        "Under declared duration, energy, deadline, and capacity assumptions, do forecasts of NESO estimated GB carbon intensity reduce modeled operational CO2 for completed GPU workloads compared with earliest-feasible execution and simple forecast baselines?",
        "",
        "The study compares half-hourly forecasts with persistence, daily and weekly seasonal-naive, and calendar-mean controls. It uses chronological validation and a locked test period. The isolated-job experiment estimates temporal placement value. The one-GPU queue simulation examines how a simple reservation policy behaves under synthetic arrivals.",
        "",
        "The carbon oracle uses realized future intensity and is an unattainable opportunity bound. It is never presented as a deployable forecast.",
        "",
        "## Data and provenance",
        "",
        f"- Study ID: `{evidence.study_id}`",
        f"- Data source: {evidence.config.get('data', {}).get('source', 'Not recorded in config')}",
        f"- Declared interval: `{evidence.config.get('data', {}).get('start', 'Not recorded')}` to `{evidence.config.get('data', {}).get('end', 'Not recorded')}`",
        f"- Normalized data hash: `{evidence.manifest.get('normalized_hash', evidence.results.get('data_hash', 'Not recorded'))}`",
        "- Target: NESO estimated actual carbon intensity. Provider forecasts remain separate and are not scored as as-issued historical forecasts without issue-time provenance. [S1-S5]",
        "",
        "## Data-quality results",
        "",
        _source_missingness_sentence(evidence),
        "",
        _table(quality, ("measure", "value")),
        "",
        "Monthly coverage rows are read from the data-quality artifact when present.",
        "",
        _table(
            monthly_quality_rows,
            ("interval_start_utc", "observed_slots", "expected_slots", "coverage"),
        ),
        "",
        "Coverage is reported from the stored audit. Missing or excluded intervals remain visible. The observed target is not replaced with a provider forecast. [S2, S4, S6]",
        "",
        "## Development diagnostics",
        "",
        f"Diagnostics used data through `{evidence.diagnostics.get('development_end_exclusive_utc', 'the recorded development boundary')}`. They support model design only. They do not establish test-year forecast skill.",
        "",
        *diagnostic_figure_lines,
        "Diagnostic table files remain at `../artifacts/diagnostics/`. The exporter includes every listed table and figure that exists. Missing listed files appear in the export manifest rather than being replaced with invented values.",
        "",
        "## Forecast methods",
        "",
        "The study uses AR, MA, ARMA, ARIMA, and daily-seasonal SARIMA structures with persistence, seasonal-naive, and calendar-mean baselines. It compares information criteria only within compatible groups, then selects across groups by validation loss. [S9-S13]",
        "",
        "### Order-search record",
        "",
        "AIC = -2 log L + 2k. BIC = -2 log L + k log(n_effective). AICc adds 2k(k+1)/(n_effective-k-1). Estimated variance and deterministic parameters count in k. The first-anchor shortlist below spans separate likelihood groups; cross-transformation IC comparisons are invalid.",
        "",
        _table(_shortlist_ic_rows(evidence), ("family", "transform", "order", "seasonal_order",
               "aic", "bic", "aicc", "converged_anchors")),
        "",
        (
            _table(
                evidence.source_tables.get("selection_ledger", []),
                limit=100,
            )
            if evidence.source_tables.get("selection_ledger")
            else "The selection ledger was not present in the verified export inputs."
        ),
        "",
        f"Search ledger source: `{evidence.source_stages.get('selection_ledger', 'not supplied')}`.",
        "",
        "Forecasts use a 48-slot path and report lead times from the configured horizon list. Comparisons use common eligible targets and retain counts by horizon. The 2025 test is evaluated after the validation protocol is frozen. The exporter does not change the validation-selected forecast champion after observing test metrics.",
        "",
        "### Validation-selected forecast results",
        "",
        "Common-origin results exclude origins where any competitor falls back. Full end-to-end tables retain those cases. These are different estimands.",
        "",
        f"Champion: `{evidence.results.get('forecast_champion') or 'Not selected'}`. Strongest simple baseline: `{evidence.results.get('strongest_simple') or 'Not selected'}`.",
        "",
        _table(
            validation_rows,
            ("model_id", "group", "horizon", "n", "mae", "rmse", "mean_error", "mase", "coverage80", "coverage95"),
        ),
        "",
        f"Full validation metrics: `../artifacts/runs/{evidence.study_id}/validation/forecast_metrics.csv`.",
        "",
        "### Locked-test forecast results",
        "",
        _table(
            test_rows,
            ("model_id", "group", "horizon", "n", "mae", "rmse", "mean_error", "mase", "coverage80", "coverage95"),
        ),
        "",
        f"Full test metrics: `../artifacts/runs/{evidence.study_id}/test/forecast_metrics.csv`.",
        "",
        "### Paired forecast-loss contrast",
        "",
        "The validation-selected classical model is compared with the validation-selected simple forecast using equal-weight endpoint MAE at common no-fallback origins. Positive loss reduction favors the classical model. The seven-day block is the declared primary block length; this forecast contrast is secondary and descriptive.",
        "",
        _table(evidence.source_tables.get("forecast_loss_bootstrap", []),
               ("block_days", "paired_origin_count", "estimate_loss_reduction_pct",
                "ci95_loss_reduction_pct_low", "ci95_loss_reduction_pct_high")),
        "",
        "### Cumulative forecast-path errors",
        "",
        "Path MAE and RMSE score all half-hours in each prefix. Prefix-mean MAE scores the time-average intensity over that prefix. Complete observed prefixes use a common target mask. These descriptive metrics do not alter endpoint-based model selection.",
        "",
        _table([row for row in evidence.source_tables.get("test_path_metrics", [])
                if row.get("comparison") == "common_no_fallback"
                and row.get("model_id") in {evidence.results.get("forecast_champion"), evidence.results.get("strongest_simple")}],
               ("model_id", "horizon", "n_complete_paths", "path_mae", "path_rmse", "prefix_mean_mae")),
        "",
        "Test scores describe the locked period. They do not authorize changing the frozen deployment candidate or claiming performance beyond the observed year. [S9, S10]",
        "",
        "## Scheduling methods",
        "",
        "### Residual adequacy",
        "",
        _table([row for row in evidence.source_tables.get("validation_ljung_box", [])
                if _number(row.get("lag")) == 48],
               ("model_id", "n_contiguous", "lb_stat", "lb_pvalue")),
        "",
        _table(evidence.source_tables.get("validation_innovation_distribution", []),
               ("model_id", "normality_p_value", "skew", "excess_kurtosis")),
        "",
        "Small Ljung-Box p-values indicate residual serial dependence. Small Jarque-Bera p-values challenge Gaussian innovation assumptions. Printed zero p-values are numerical underflow, not proof of an exactly zero probability. Forecast skill must be judged separately by chronological errors and empirical coverage.",
        "",
        "For each feasible start, the scheduler minimizes integrated predicted carbon cost over the full job duration. Deadlines and reservations are hard constraints. Exact ties use the earliest start. Isolated releases are counterfactual cases, not one simultaneous workload trace.",
        "",
        "The primary accounting uses modeled energy-intensity products. The default power and PUE values are declared scenarios, not telemetry. Queue arrivals are synthetic and one-GPU reservations are not globally optimal. [S5, S9]",
        "",
        "### Primary scheduling results",
        "",
        _result_sentence(evidence),
        "",
        "The deployment model is selected independently of the forecast-MAE champion. If the deployment choice is a simple baseline, its benefit establishes temporal-placement value under the assumptions, not added value from classical forecasting. Persistence can have low forecast MAE yet schedule at release because its point path is flat. The complete policy table is necessary to assess stronger timing baselines.",
        "",
        _table(
            primary,
            ("scenario_id", "policy", "model_id", "n_eligible_jobs", "n_scheduled", "fallback_rate", "mean_realized_grams", "paired_savings_grams", "paired_savings_pct", "oracle_regret_grams"),
        ),
        "",
        f"Source: `{evidence.source_stages.get('primary_summary')}`.",
        "",
        "### Paired block uncertainty",
        "",
        _table(
            bootstrap,
            ("block_days", "paired_job_count", "estimate_savings_pct", "ci95_savings_pct_low", "ci95_savings_pct_high", "is_primary_block"),
        ),
        "",
        f"Source: `{evidence.source_stages.get('primary_bootstrap')}`. Secondary block estimates are descriptive sensitivity checks. The primary block is the configured seven-day block when available.",
        "",
        "### Selected policy versus the strongest simple forecast",
        "",
        evidence.results.get("h3_interpretation", "No added-classical-value conclusion is recorded."),
        "",
        _table(evidence.source_tables.get("versus_simple_bootstrap", []),
               ("block_days", "paired_job_count", "estimate_savings_pct",
                "ci95_savings_pct_low", "ci95_savings_pct_high")),
        "",
        "### Complete declared scenario outcomes",
        "",
        "Every declared duration/slack scenario is included below. These are secondary descriptive comparisons. The full policy and metric table remains in the cited source CSV.",
        "",
        _table([row for row in evidence.source_tables.get("primary_summary", [])
                if row.get("result_type") == "scheduling"
                and row.get("policy") == "forecast"
                and row.get("model_id") == evidence.results.get("deployment_model")],
               ("scenario_id", "n_eligible_jobs", "n_scheduled", "fallback_rate",
                "mean_realized_grams", "paired_savings_pct", "oracle_regret_grams")),
        "",
        "### Monthly scheduling outcomes",
        "",
        _table(
            monthly,
            ("month_utc", "scenario_id", "policy", "model_id", "n_eligible_jobs", "n_scheduled", "mean_realized_grams", "paired_savings_pct", "fallback_rate"),
        ),
        "",
        f"Source: `{evidence.source_stages.get('primary_monthly')}`. Monthly results are shown for the default duration and slack when those fields are present.",
        "",
        "### Queue outcomes",
        "",
        _table(
            evidence.source_tables.get("queue_summary", []),
            ("offered_load", "seed", "slack_hours", "policy", "offered_jobs", "completed_jobs", "rejected_jobs", "deadline_misses", "matched_savings_pct", "unmatched_completed_jobs", "interpretation"),
        ),
        "",
        f"Queue source: `{evidence.source_stages.get('queue_summary')}`. Compare emissions with service outcomes. The completion intersection can be selective when policies accept different work.",
        "",
        "## Limitations and claim boundaries",
        "",
        "### Computing overhead",
        "",
        f"At an illustrative computing-supply intensity of 100 gCO2/kWh, the recorded gross benefit corresponds to {_format(evidence.results.get('overhead_break_even_kwh_per_isolated_case'))} kWh per isolated counterfactual case. Actual forecasting and scheduler energy is unmeasured. This is a break-even scenario, not a verified net-emissions result. Runtime is recorded in forecast metadata and the selection ledger.",
        "",
        "### Bounded validation sensitivities",
        "",
        "These six variants cover four three-day quarterly episodes in 2024. They are descriptive checks, not full-year robustness or test-driven model selection.",
        "",
        _table(evidence.source_tables.get("sensitivity_summary", []),
               ("month", "variant", "model_id", "n_scheduled", "paired_savings_pct", "fallback_rate")),
        "",
    ]
    for limitation in evidence.results["limitations"]:
        lines.append(f"- {_markdown_escape(limitation)}")
    lines.extend(
        [
            "- NESO `actual` is an estimated target for generation-related CO2, not a full lifecycle or all-GHG inventory. [S2, S5]",
            "- Historical publication delay and revision history are not fully established. The replay is pseudo-real-time under the declared availability assumption. [S2, S4]",
            "- GPU energy, PUE, job duration, and queue arrivals are modeled inputs unless a verified telemetry record states otherwise.",
            "- Savings are attributional estimates under the declared accounting boundary. They do not measure a causal change in grid emissions.",
            "- A lower queue total is not a saving when policies complete different work. Report workload and service outcomes alongside emissions.",
        ]
    )
    lines.extend(
        [
            "",
            "## Appendix: complete validation metrics",
            "",
            _table(evidence.source_tables.get("validation_metrics", [])),
            "",
            f"Source CSV: `../artifacts/runs/{evidence.study_id}/validation/forecast_metrics.csv`.",
            "",
            "## Appendix: complete locked-test metrics",
            "",
            _table(evidence.source_tables.get("test_metrics", [])),
            "",
            f"Source CSV: `../artifacts/runs/{evidence.study_id}/test/forecast_metrics.csv`.",
        ]
    )
    lines.extend(
        [
            "",
            "## Reproducibility and claim traceability",
            "",
            f"- Results manifest: `../artifacts/results.json` (SHA-256 `{_sha256(evidence.root / 'artifacts/results.json')}`).",
            f"- Data manifest hash: `{evidence.manifest.get('normalized_hash', evidence.results.get('data_hash', 'Not recorded'))}`.",
            f"- Configuration digest: `{hashlib.sha256(_json_bytes(evidence.config)).hexdigest()}`.",
            f"- Protocol hash: `{evidence.protocol.get('protocol_hash', evidence.results.get('protocol_hash', 'Not recorded'))}`.",
            f"- Software source hash: `{_recorded_software_hash(evidence)}`.",
            f"- Python runtime: `{platform.python_version()}`.",
            f"- Exporter package versions: `{_markdown_escape(package_versions)}`.",
            f"- Validation forecast metrics: `{evidence.source_stages.get('validation_metrics')}`.",
            f"- Test forecast metrics: `{evidence.source_stages.get('test_metrics')}`.",
            f"- Primary and queue summaries: `{evidence.source_stages.get('primary_summary')}`; `{evidence.source_stages.get('queue_summary')}`.",
            "- The notebook reads these files without collecting data or fitting models. The root workflow executes it with `nbconvert` after generation.",
            "",
            "## References",
            "",
        ]
    )
    lines.extend(f"- [{key}] [{title}]({url})" for key, title, url in SOURCE_REFERENCES)
    return "\n".join(lines).rstrip() + "\n"


def _pdf_table(records: Sequence[Mapping[str, Any]], columns: Sequence[str], *, max_rows: int | None = None):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Table, TableStyle

    if not records:
        records = [{"status": "Not evaluated"}]
        columns = ("status",)
    else:
        available = set().union(*(row.keys() for row in records))
        columns = tuple(name for name in columns if name in available)
        if not columns:
            columns = tuple(_columns(records)[:6])
        if not columns:
            columns = ("status",)
            records = [{"status": "Rows are present, but no display fields were recognized."}]
    selected = list(records[:max_rows] if max_rows is not None else records)
    if not selected:
        selected = [{"status": "Not evaluated"}]
        columns = ("status",)
    small = ParagraphStyle(
        "GridShiftTable",
        fontName="Helvetica",
        fontSize=7.2,
        leading=8.6,
        textColor=colors.HexColor("#1F2933"),
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    header = ParagraphStyle(
        "GridShiftTableHeader",
        parent=small,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    data = [[Paragraph(_escape_pdf(name), header) for name in columns]]
    for row in selected:
        data.append(
            [
                Paragraph(_escape_pdf(_format(row.get(name), digits=4)), small)
                for name in columns
            ]
        )
    widths = [6.8 * 72 / max(1, len(columns))] * len(columns)
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D5A54")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D2D0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F5F3")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _escape_pdf(value: str) -> str:
    from xml.sax.saxutils import escape

    return escape(_ascii(value)).replace("\n", "<br/>")


def _pdf_story(evidence: Evidence):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Flowable, Image, PageBreak, Paragraph, Spacer

    class MainBodyEndMarker(Flowable):
        _gridshift_main_body_end = True

        def wrap(self, available_width, available_height):
            return 0, 0

        def draw(self):
            pass

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "GridShiftTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=31,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#163A35"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            "GridShiftHeading",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#163A35"),
            spaceBefore=0,
            spaceAfter=9,
        )
    )
    styles.add(
        ParagraphStyle(
            "GridShiftSubheading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#A5523D"),
            spaceBefore=4,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "GridShiftBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#263238"),
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "GridShiftSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#455A64"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            "GridShiftCover",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=31,
            leading=37,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#163A35"),
            spaceAfter=13,
        )
    )
    story: list[Any] = []

    def p(text: Any, style: str = "GridShiftBody") -> None:
        story.append(Paragraph(_escape_pdf(str(text)), styles[style]))

    def page(
        title: str,
        paragraphs: Iterable[str] = (),
        table=None,
        image: str | None = None,
        caption: str | None = None,
        *,
        break_after: bool = True,
    ) -> None:
        p(title, "GridShiftHeading")
        for paragraph in paragraphs:
            p(paragraph)
        if table is not None:
            story.append(table)
            story.append(Spacer(1, 8))
        if image is not None:
            path = evidence.figures.get(image)
            if path:
                picture = Image(str(path), width=6.8 * inch, height=3.7 * inch, kind="proportional")
                picture._restrictSize(6.8 * inch, 3.7 * inch)
                story.append(picture)
                if caption:
                    p(caption, "GridShiftSmall")
        if break_after:
            story.append(PageBreak())

    story.append(Spacer(1, 1.2 * inch))
    p("GridShift", "GridShiftCover")
    p("Carbon-aware GPU workload scheduling with classical time-series forecasts")
    p("Research report generated from verified local artifacts")
    story.append(Spacer(1, 0.35 * inch))
    p(f"Study ID: {evidence.study_id}", "GridShiftSmall")
    p("Target: NESO estimated GB carbon intensity in gCO2/kWh", "GridShiftSmall")
    p("Scheduling emissions are modeled from declared energy assumptions.", "GridShiftSmall")
    if "series.png" in evidence.figures:
        image = Image(str(evidence.figures["series.png"]), width=6.8 * inch, height=3.7 * inch, kind="proportional")
        image._restrictSize(6.8 * inch, 3.7 * inch)
        story.append(Spacer(1, 0.25 * inch))
        story.append(image)
    story.append(PageBreak())

    page(
        "Abstract",
        (
            "This report evaluates a frozen classical forecasting and scheduling study. It separates validation selection from locked-test measurement.",
            _result_sentence(evidence),
            "The source series contains NESO estimated actual carbon intensity. The scheduling outcomes are modeled estimates under stated job and energy assumptions.",
        ),
    )
    page(
        "Research question and scope",
        (
            "The study asks whether half-hourly forecasts of NESO estimated GB carbon intensity can improve feasible GPU workload placement against earliest-feasible execution and simple seasonal controls.",
            "The primary experiment uses isolated counterfactual jobs. A secondary one-GPU queue replay tests a simple reservation policy under synthetic arrivals.",
            "The carbon oracle observes realized future intensity. It is an unattainable opportunity bound, not a candidate for deployment.",
        ),
        _pdf_table(
            [
                {"component": "Target", "definition": "NESO estimated actual, gCO2/kWh"},
                {"component": "Forecast path", "definition": "Half-hourly, configured horizons"},
                {"component": "Primary contrast", "definition": "Validation-selected schedule versus earliest feasible"},
                {"component": "Queue", "definition": "One GPU, synthetic arrivals, non-preemptive reservations"},
            ],
            ("component", "definition"),
        ),
    )
    page(
        "Data and provenance",
        (
            f"The data manifest records normalized hash `{evidence.manifest.get('normalized_hash', evidence.results.get('data_hash', 'not recorded'))}`.",
            f"The configured source is `{evidence.config.get('data', {}).get('source', 'not recorded')}`. The target spans `{evidence.config.get('data', {}).get('start', 'not recorded')}` through `{evidence.config.get('data', {}).get('end', 'not recorded')}`.",
            "The provider's historical forecast values do not have verified issue-time provenance in the inspected interfaces. They are not treated as fair as-issued competitors. [S1-S5]",
        ),
    )
    page(
        "Data-quality audit",
        (
            "The table reproduces the stored quality audit. It reports coverage and grid checks without converting the planned thresholds into measured facts.",
            _source_missingness_sentence(evidence),
        ),
        _pdf_table(_quality_rows(evidence.quality), ("measure", "value")),
        image="missingness.png",
        caption="Figure. Development-period missingness by month and local hour. Source: artifacts/diagnostics/figures/missingness.png.",
    )
    page(
        "Development series",
        (
            "This plot uses development observations only. It informs transformations and candidate construction. It is not a test-year result.",
            "The source target remains separate from provider forecasts. Missing target values are not filled from the forecast field. [S2, S4]",
        ),
        image="representative_week.png",
        caption="Figure. Representative development week from the stored diagnostics.",
    )
    page(
        "Seasonality and decomposition",
        (
            f"The diagnostic record reports daily ACF at lag 48 as `{_format(evidence.diagnostics.get('seasonal_acf', {}).get('48'))}` and weekly ACF at lag 336 as `{_format(evidence.diagnostics.get('seasonal_acf', {}).get('336'))}` when those values exist.",
            "Robust STL at period 48 is descriptive. Its centered endpoint behavior cannot support a real-time claim. Residual whiteness does not establish forecast accuracy. [S9-S13]",
        ),
        image="stl48.png",
        caption="Figure. Robust STL decomposition on the recorded development segment.",
    )
    adf_rows = evidence.diagnostic_tables.get("adf.csv", [])
    kpss_rows = evidence.diagnostic_tables.get("kpss.csv", [])
    page(
        "Stationarity diagnostics",
        (
            "ADF tests address a unit-root null under specified deterministic terms. KPSS uses a different null. Conflicting or inconclusive tests do not select a forecasting model by themselves. [S11]",
            f"The diagnostics record contains {len(adf_rows)} ADF rows and {len(kpss_rows)} KPSS rows. Missing rows remain absent rather than being filled with assumed p-values.",
            _stationarity_sentence(adf_rows, kpss_rows),
        ),
        _pdf_table(adf_rows, ("variant", "regression", "autolag", "status", "sample_n", "selected_lag", "test_statistic", "p_value", "critical_5pct"), max_rows=12),
    )
    page(
        "Forecast model catalogue",
        (
            "The study uses AR, MA, ARMA, ARIMA, and daily-seasonal SARIMA structures. Baselines include persistence, daily and weekly seasonal-naive, and past-only calendar mean.",
            "AR, MA, and ARMA can be nested ARIMA cases. Effective duplicates are counted once in comparisons. Unsuccessful fits remain part of the run ledger. [S9, S10, S12]",
            "AR uses past levels; MA uses past innovations rather than a rolling arithmetic average. ARMA combines those terms. ARIMA applies (1-B)^d before stationary ARMA dynamics. SARIMA adds seasonal polynomials and (1-B^48)^D.",
        ),
        _pdf_table(
            [
                {"family": "AR", "role": "Stationary autoregression"},
                {"family": "MA", "role": "Past innovation dependence"},
                {"family": "ARMA", "role": "Stationary mixed dynamics"},
                {"family": "ARIMA", "role": "Integrated level model"},
                {"family": "SARIMA", "role": "Daily seasonal state-space model"},
                {"family": "Simple baselines", "role": "Persistence, seasonal-naive, calendar mean"},
            ],
            ("family", "role"),
        ),
    )
    page(
        "Lag selection and information criteria",
        (
            "AIC = -2 log L + 2k; BIC = -2 log L + k log(n_effective). AICc adds 2k(k+1)/(n_effective-k-1). k includes variance and deterministic parameters.",
            "These representative first-anchor shortlist rows belong to separate family, transformation, and differencing groups. Their absolute IC values must not be pooled into a leaderboard.",
            "All attempted orders and failures remain in selection_ledger.csv. Aggregate within-anchor AICc and BIC ranks shortlist orders; chronological validation chooses representations.",
        ),
        _pdf_table(_shortlist_ic_rows(evidence),
                   ("family", "transform", "order", "aic", "bic", "aicc", "converged_anchors"), max_rows=10),
    )
    p("Representative validation residual diagnostics", "GridShiftHeading")
    p("Ljung-Box at lag 48 checks remaining serial dependence with model degrees of freedom. All lags, innovation normality, and ACF/PACF plots remain in validation/residuals/.")
    residual_rows = [row for row in evidence.source_tables.get("validation_ljung_box", [])
                     if _number(row.get("lag")) == 48]
    story.append(_pdf_table(residual_rows, ("model_id", "n_contiguous", "lb_stat", "lb_pvalue"), max_rows=5))
    p("Small p-values indicate remaining serial dependence. The innovation-distribution table accompanies the report. Printed zero p-values represent numerical underflow. These diagnostics and imperfect predictive coverage prevent a calibrated Gaussian-uncertainty claim.")
    story.append(PageBreak())
    study_cfg = evidence.config.get("study", {})
    page(
        "Chronological evaluation design",
        (
            "Forecasts use eligible history, persist before scoring, and are compared on common target masks. The test year remains outside validation selection.",
            "Report MAE, RMSE, mean error, daily-seasonal MASE, predictive interval coverage, interval width, and sample counts by lead time. Avoid MAPE when targets may be zero. [S9-S13]",
        ),
        _pdf_table(
            [
                {"setting": "Validation start", "value": study_cfg.get("validation_start", "not recorded")},
                {"setting": "Validation end", "value": study_cfg.get("validation_end", "not recorded")},
                {"setting": "Test start", "value": study_cfg.get("test_start", "not recorded")},
                {"setting": "Test end", "value": study_cfg.get("test_end", "not recorded")},
                {"setting": "Reported horizons", "value": study_cfg.get("reported_horizons", "not recorded")},
                {"setting": "Forecast path slots", "value": study_cfg.get("horizon_slots", "not recorded")},
            ],
            ("setting", "value"),
        ),
    )
    chosen_models = (evidence.results.get("forecast_champion"), evidence.results.get("strongest_simple"))
    val_rows = _common_metric_rows(evidence, "validation", chosen_models)
    page(
        "Validation forecast outcomes",
        (
            f"The validation-selected forecast champion is `{evidence.results.get('forecast_champion') or 'not selected'}`.",
            f"The strongest simple validation baseline is `{evidence.results.get('strongest_simple') or 'not selected'}`. These selections precede locked-test scoring.",
            "These are common-origin scores. End-to-end scores and all required families remain in the accompanying Markdown report and source tables.",
        ),
        _pdf_table(
            val_rows,
            ("model_id", "group", "horizon", "n", "mae", "rmse", "mean_error", "mase", "coverage80", "coverage95"),
            max_rows=15,
        ),
    )
    test_rows = _common_metric_rows(evidence, "test", chosen_models)
    page(
        "Locked-test forecast outcomes",
        (
            "These rows report the recorded locked-test results for the validation-selected champion and strongest simple baseline.",
            "The exporter does not choose a new winner from test outcomes. A post-test revision requires another untouched evaluation period.",
        ),
        _pdf_table(
            test_rows,
            ("model_id", "group", "horizon", "n", "mae", "rmse", "mean_error", "mase", "coverage80", "coverage95"),
            max_rows=15,
        ),
        break_after=False,
    )
    p("Paired forecast-loss comparison", "GridShiftHeading")
    p("Positive loss reduction favors the validation-selected classical model over the validation-selected simple forecast. The equal-horizon common-origin contrast is secondary and descriptive.")
    story.append(_pdf_table(
        [row for row in evidence.source_tables.get("forecast_loss_bootstrap", [])
         if _number(row.get("block_days")) == 7],
        ("block_days", "paired_origin_count", "estimate_loss_reduction_pct",
         "ci95_loss_reduction_pct_low", "ci95_loss_reduction_pct_high"),
    ))
    story.append(PageBreak())
    path_rows = [row for row in evidence.source_tables.get("test_path_metrics", [])
                 if row.get("comparison") == "common_no_fallback"
                 and row.get("model_id") in set(chosen_models)]
    page(
        "Cumulative forecast-path errors",
        (
            "Path MAE and RMSE score every half-hour in each prefix in gCO2/kWh. Prefix-mean MAE scores the error of the time-average intensity.",
            "Only complete observed prefixes are scored. Common-origin masks exclude any competitor fallback. These descriptive results do not change endpoint-based selection.",
        ),
        _pdf_table(path_rows, ("model_id", "horizon", "n_complete_paths", "path_mae", "path_rmse", "prefix_mean_mae"), max_rows=10),
    )
    sched = evidence.config.get("scheduling", {})
    page(
        "Scheduling formulation",
        (
            "For a candidate start, the scheduler sums forecast intensity times interval-overlap energy across the full job duration. It obeys hard deadlines and capacity. Exact cost ties favor the earliest start.",
            "Primary releases are independent counterfactual cases. They are not a simultaneous workload trace. The one-GPU queue simulation uses synthetic arrivals and immutable reservations. [S5]",
        ),
        _pdf_table(
            [
                {"assumption": "Default duration (hours)", "value": sched.get("default_duration_hours", "not recorded")},
                {"assumption": "Default slack (hours)", "value": sched.get("default_slack_hours", "not recorded")},
                {"assumption": "Declared power (kW)", "value": sched.get("power_kw", "not recorded")},
                {"assumption": "PUE", "value": sched.get("pue", "not recorded")},
                {"assumption": "Primary selected model", "value": evidence.results.get("deployment_model") or "not selected"},
            ],
            ("assumption", "value"),
        ),
    )
    primary_rows = _default_primary_rows(evidence)
    page(
        "Primary scheduling outcomes",
        (_result_sentence(evidence),
         "A simple-baseline deployment choice does not establish added scheduling value from classical forecasting. Persistence's flat path resolves to earliest execution. Read all policy rows before attributing the benefit to model complexity."),
        _pdf_table(
            primary_rows,
            ("policy", "model_id", "n_scheduled", "mean_realized_grams", "paired_savings_pct", "oracle_regret_grams"),
            max_rows=12,
        ),
    )
    bootstrap_rows = _bootstrap_rows(evidence)
    page(
        "Primary uncertainty",
        (
            "The paired moving-block bootstrap keeps neighboring cases together. The seven-day estimate is primary when present; three- and fourteen-day estimates are sensitivity checks.",
            "A non-positive interval or a null estimate remains a valid negative result. A positive estimate does not establish measured or causal grid emissions.",
        ),
        _pdf_table(
            bootstrap_rows,
            ("block_days", "paired_job_count", "estimate_savings_pct", "ci95_savings_pct_low", "ci95_savings_pct_high", "is_primary_block"),
        ),
        break_after=False,
    )
    p("Selected policy versus the strongest simple forecast", "GridShiftHeading")
    p(evidence.results.get("h3_interpretation", "No added-classical-value conclusion is recorded."))
    story.append(_pdf_table(
        [row for row in evidence.source_tables.get("versus_simple_bootstrap", [])
         if _number(row.get("block_days")) == 7],
        ("paired_job_count", "estimate_savings_pct",
         "ci95_savings_pct_low", "ci95_savings_pct_high"),
    ))
    p("All declared duration/slack scenarios are reproduced in the complete scenario table in gridshift_report.md and the primary_summary.csv source. They remain secondary descriptive comparisons.")
    story.append(PageBreak())
    monthly = _monthly_default_rows(evidence)
    page(
        "Monthly scheduling outcomes",
        (
            "Monthly figures show the default duration and slack where the source table records both. They describe temporal variation and do not replace the prespecified aggregate contrast.",
        ),
        _pdf_table(
            monthly,
            ("month_utc", "scenario_id", "policy", "model_id", "n_eligible_jobs", "n_scheduled", "mean_realized_grams", "paired_savings_pct", "fallback_rate"),
            max_rows=14,
        ),
    )
    queue_rows = evidence.source_tables.get("queue_summary", [])
    page(
        "Queue replay outcomes",
        (
            "Queue emissions must be read with offered jobs, completed jobs, rejections, deadline misses, and unmatched work. A lower total caused by rejected work is not a carbon saving.",
            f"The queue summary comes from the `{evidence.source_stages.get('queue_stage', 'unknown')}` artifact path.",
        ),
        _pdf_table(
            queue_rows,
            ("offered_load", "seed", "slack_hours", "policy", "offered_jobs", "completed_jobs", "rejected_jobs", "matched_savings_pct", "interpretation"),
            max_rows=12,
        ),
    )
    page(
        "Bounded sensitivity checks",
        (
            "Six forecasting variants use four three-day quarterly episodes in validation year 2024. These checks do not establish full-year robustness.",
            "Constant power and PUE scale absolute costs algebraically. They cannot establish robustness to measured energy variation.",
        ),
        _pdf_table(evidence.source_tables.get("sensitivity_summary", []),
                   ("month", "variant", "n_scheduled", "paired_savings_pct"), max_rows=12),
    )
    page(
        "Deployment and demonstration",
        (
            f"The study records `{evidence.results.get('deployment_model') or 'no deployment model'}` as the validation-selected scheduling model.",
            "This export does not claim a live GPU scheduler, Slurm integration, cloud workload execution, or public deployment. A local dashboard demo must use the saved versioned artifacts and preserve stale, missing, and infeasible states.",
            f"At an illustrative supply intensity of 100 gCO2/kWh, gross savings permit {_format(evidence.results.get('overhead_break_even_kwh_per_isolated_case'))} kWh of overhead per isolated counterfactual case. Computing energy is unmeasured, so no net-emissions claim follows.",
        ),
    )
    page(
        "Limitations",
        (
            "The NESO series is estimated generation-related CO2. It is not a complete lifecycle or all-GHG inventory. [S2, S5]",
            "Historical publication latency and revisions remain uncertain. Without verified vintages, retrospective replay is pseudo-real-time. [S2, S4]",
            "Power, PUE, duration, and synthetic arrival assumptions do not establish measured GPU behavior.",
        )
        + tuple(evidence.results["limitations"])
        + (_result_sentence(evidence),),
    )
    page(
        "Reproducibility and evidence map",
        (
            f"Results manifest SHA-256: {_sha256(evidence.root / 'artifacts/results.json')}.",
            f"Data hash: {evidence.manifest.get('normalized_hash', evidence.results.get('data_hash', 'not recorded'))}.",
            f"Configuration digest: {hashlib.sha256(_json_bytes(evidence.config)).hexdigest()}.",
            f"Protocol hash: {evidence.protocol.get('protocol_hash', evidence.results.get('protocol_hash', 'not recorded'))}.",
            f"Software source hash: {_recorded_software_hash(evidence)}.",
            f"Study ID: {evidence.study_id}.",
        ),
        _pdf_table(
            [
                {"claim": "Validation selection", "evidence": "results.json selections and the recorded order-search ledger when present"},
                {"claim": "Locked-test forecast result", "evidence": "test/forecast_metrics.csv"},
                {"claim": "Primary scheduling estimate", "evidence": evidence.source_stages.get("primary_summary", "missing")},
                {"claim": "Paired uncertainty", "evidence": evidence.source_stages.get("primary_bootstrap", "missing")},
                {"claim": "Queue service and emissions", "evidence": evidence.source_stages.get("queue_summary", "missing")},
            ],
            ("claim", "evidence"),
        ),
    )
    page(
        "References",
        tuple(f"[{key}] {title}. {url}" for key, title, url in SOURCE_REFERENCES),
        break_after=False,
    )
    story.append(MainBodyEndMarker())
    return story


def _build_pdf(path: Path, evidence: Evidence) -> tuple[int, int]:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
    from reportlab.pdfgen.canvas import Canvas

    class GridShiftCanvas(Canvas):
        page_count = 0

        def showPage(self):
            type(self).page_count += 1
            super().showPage()

    class GridShiftDoc(BaseDocTemplate):
        main_body_pages = 0

        def afterFlowable(self, flowable):
            if getattr(flowable, "_gridshift_main_body_end", False):
                self.main_body_pages = self.page

    page_width, page_height = letter
    doc = GridShiftDoc(
        str(path),
        pagesize=letter,
        leftMargin=0.78 * inch,
        rightMargin=0.78 * inch,
        topMargin=0.76 * inch,
        bottomMargin=0.7 * inch,
        title="GridShift research report",
        author="GridShift study",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        page_width - doc.leftMargin - doc.rightMargin,
        page_height - doc.topMargin - doc.bottomMargin,
        id="report-frame",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    def decorate(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#163A35"))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(document.leftMargin, page_height - 0.45 * inch, "GridShift research report")
        canvas.setStrokeColor(colors.HexColor("#C8D2D0"))
        canvas.setLineWidth(0.5)
        canvas.line(document.leftMargin, page_height - 0.52 * inch, page_width - document.rightMargin, page_height - 0.52 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#52636A"))
        canvas.drawString(document.leftMargin, 0.42 * inch, f"Study {evidence.study_id}")
        canvas.drawRightString(page_width - document.rightMargin, 0.42 * inch, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=decorate)])
    doc.build(_pdf_story(evidence), canvasmaker=GridShiftCanvas)
    total_pages = GridShiftCanvas.page_count
    body_pages = doc.main_body_pages
    if not 15 <= body_pages <= 25:
        raise ExportInputError(
            f"Report must have 15-25 pages; generated {body_pages} body pages"
        )
    if total_pages != body_pages or path.stat().st_size < 1000:
        raise ExportInputError("Report PDF failed its basic size or page-count check")
    return body_pages, total_pages


def _markdown_notebook(evidence: Evidence) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    artifact_paths = {
        key: path.relative_to(evidence.root).as_posix()
        for key, path in evidence.table_paths.items()
        if key in {
            "validation_metrics",
            "test_metrics",
            "primary_summary",
            "primary_bootstrap",
            "primary_monthly",
            "queue_summary",
        }
    }

    def markdown(source: str) -> None:
        cells.append(
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": source.splitlines(keepends=True),
            }
        )

    def code(source: str) -> None:
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            }
        )

    markdown(
        "# GridShift study\n\n"
        "This notebook reads the frozen local artifacts. It does not collect data, refit models, "
        "or alter the protocol. Run it offline from the project environment after the verified "
        "`artifacts/results.json` and tables are present."
    )
    code(
        "from pathlib import Path\n"
        "import json\n"
        "from importlib.metadata import PackageNotFoundError, version\n"
        "import pandas as pd\n"
        "import yaml\n"
        "from IPython.display import display, Image\n"
        "from gridshift.study import run_dir\n"
        "\n"
        "def find_root(start):\n"
        "    for candidate in (start, *start.parents):\n"
        "        if (candidate / 'artifacts/results.json').is_file() and (candidate / 'configs/study.yaml').is_file():\n"
        "            return candidate\n"
        "    raise FileNotFoundError('Run this notebook inside the GridShift project tree.')\n"
        "\n"
        "ROOT = find_root(Path.cwd().resolve())\n"
        "CONFIG = yaml.safe_load((ROOT / 'configs/study.yaml').read_text(encoding='utf-8'))\n"
        "RESULTS = json.loads((ROOT / 'artifacts/results.json').read_text(encoding='utf-8'))\n"
        "STUDY_ID = RESULTS['study_id']\n"
        "VALIDATION_RUN = run_dir(ROOT, CONFIG, 'validation')\n"
        "TEST_RUN = run_dir(ROOT, CONFIG, 'test')\n"
        "assert VALIDATION_RUN.parent.name == STUDY_ID == TEST_RUN.parent.name\n"
        "VALIDATION_RESIDUALS = VALIDATION_RUN / 'residuals'\n"
        "print('Study ID:', STUDY_ID)\n"
        "print('Validation run:', VALIDATION_RUN)\n"
        "print('Test run:', TEST_RUN)\n"
        "software = {}\n"
        "for package in ('gridshift', 'numpy', 'pandas', 'scipy', 'statsmodels'):\n"
        "    try:\n"
        "        software[package] = version(package)\n"
        "    except PackageNotFoundError:\n"
        "        software[package] = 'not installed'\n"
        "display(pd.Series(software, name='version').to_frame())"
    )
    markdown("## 1. Question, scope, units, sources, and frozen configuration")
    code(
        "display(pd.DataFrame([\n"
        "    {'item': 'question', 'value': 'Do eligible carbon forecasts improve feasible workload placement under declared assumptions?'},\n"
        "    {'item': 'target_unit', 'value': 'gCO2/kWh'},\n"
        "    {'item': 'forecast_champion', 'value': RESULTS.get('forecast_champion')},\n"
        "    {'item': 'strongest_simple', 'value': RESULTS.get('strongest_simple')},\n"
        "    {'item': 'deployment_model', 'value': RESULTS.get('deployment_model')},\n"
        "]))\n"
        "display(pd.json_normalize(CONFIG, sep='.').T.rename(columns={0: 'value'}))"
    )
    markdown("## 2. Collection audit, missingness, and training EDA")
    code(
        "quality = json.loads((ROOT / 'artifacts/data/quality.json').read_text(encoding='utf-8'))\n"
        "display(pd.Series(quality, name='value').to_frame())\n"
        "diagnostics = json.loads((ROOT / 'artifacts/diagnostics/diagnostics.json').read_text(encoding='utf-8'))\n"
        "display(pd.DataFrame([diagnostics.get('development_opportunity', {})]))\n"
        "for name in ('series.png', 'missingness.png', 'daily_slot_heatmap.png'):\n"
        "    path = ROOT / 'artifacts/diagnostics/figures' / name\n"
        "    if path.is_file():\n"
        "        display(Image(filename=str(path)))"
    )
    markdown("## 3. ADF, transformations, differencing, decomposition, and ACF/PACF")
    markdown(
        "ADF tests the unit-root null under the recorded deterministic regression; its "
        "augmentation lag is not an AR model order. KPSS tests a stationarity null. "
        "The recorded AIC and BIC autolag choices use a 48-slot cap on contiguous "
        "development segments. Neither test proves stable forecasts across years.\n\n"
        + _stationarity_sentence(
            evidence.diagnostic_tables.get("adf.csv", []),
            evidence.diagnostic_tables.get("kpss.csv", []),
        )
        + "\n\nIdentity and log1p representations compete on chronological validation loss, "
        "not incompatible absolute likelihoods. Inverting a Gaussian log1p forecast "
        "uses exp(mu + variance/2) - 1 for its conditional mean; exp(mu) - 1 is a "
        "median. Statsmodels state-space integration restores differenced level paths. "
        "First, seasonal, and combined differences are diagnostics even when omitted "
        "from the selected forecast. Box-Cox requires strictly positive inputs and "
        "is recorded as inappropriate where zero targets occur.\n\n"
        "STL with period 48 is a descriptive centered decomposition, not a real-time "
        "predictor. ACF/PACF guide a bounded catalogue, while held-out errors decide "
        "between representations. Zero-valued carbon remains observed data."
    )
    code(
        "for name in ('adf.csv', 'kpss.csv', 'distribution.csv', 'stl48_components.csv', 'acf_pacf.csv'):\n"
        "    path = ROOT / 'artifacts/diagnostics' / name\n"
        "    if path.is_file():\n"
        "        print(name)\n"
        "        display(pd.read_csv(path).head(20))\n"
        "for name in ('acf_pacf_levels.png', 'acf_pacf_differences.png', 'acf_pacf_daily.png', 'acf_pacf_weekly.png'):\n"
        "    path = ROOT / 'artifacts/diagnostics/figures' / name\n"
        "    if path.is_file():\n"
        "        display(Image(filename=str(path)))"
    )
    markdown("## 4. AR, MA, ARMA, ARIMA, and SARIMA")
    markdown(
        "The package owns the model definitions and fitting logic. This notebook reads the "
        "recorded forecasts and diagnostics. It does not fit a second copy of any model."
    )
    markdown(
        "### Model equations\n\n"
        "These schematic forms use B for the lag operator and epsilon[t] for an innovation:\n\n"
        "```text\n"
        "AR(p):       y[t] = c + phi_1*y[t-1] + ... + phi_p*y[t-p] + epsilon[t]\n"
        "MA(q):       y[t] = mu + epsilon[t] + theta_1*epsilon[t-1] + ... + theta_q*epsilon[t-q]\n"
        "ARMA(p,q):   combine AR(p) dependence in y with MA(q) dependence in epsilon\n"
        "ARIMA(p,d,q): phi(B)*(1-B)^d*y[t] = c + theta(B)*epsilon[t]\n"
        "SARIMA:      Phi(B^48)*phi(B)*(1-B)^d*(1-B^48)^D*y[t] = Theta(B^48)*theta(B)*epsilon[t]\n"
        "```\n\n"
        "AR, MA, and ARMA are the d=0 cases of ARIMA. The seasonal period is 48 half-hour slots. "
        "These equations describe the model families; fitted parameter values below come only "
        "from the stored validation residual-fit artifacts."
    )
    code(
        "parameter_files = sorted(VALIDATION_RESIDUALS.glob('model_*_parameters.json'))\n"
        "fitted_examples = []\n"
        "for path in parameter_files:\n"
        "    record = json.loads(path.read_text(encoding='utf-8'))\n"
        "    spec = record.get('spec', {})\n"
        "    names = record.get('parameter_names', [])\n"
        "    values = record.get('parameters', [])\n"
        "    fitted_examples.append({\n"
        "        'file': path.name,\n"
        "        'model': spec.get('name'),\n"
        "        'family': spec.get('family'),\n"
        "        'order': spec.get('order'),\n"
        "        'seasonal_order': spec.get('seasonal_order'),\n"
        "        'transform': spec.get('transform'),\n"
        "        'training_cutoff': record.get('training_cutoff'),\n"
        "        'parameters': dict(zip(names, values)) if len(names) == len(values) else values,\n"
        "    })\n"
        "if fitted_examples:\n"
        "    display(pd.DataFrame(fitted_examples))\n"
        "else:\n"
        "    print('No validation residual-fit parameter files were recorded.')\n"
        "print('Configured transforms:', CONFIG.get('forecast', {}).get('transforms'))\n"
        "print('Seasonal period:', 48, 'half-hour slots')"
    )
    markdown("## 5. Lag selection, information criteria, convergence, and residual checks")
    markdown(
        "Residual tests describe representative validation fits on contiguous observed innovation "
        "segments. They are diagnostics, not a substitute for chronological forecast scores."
    )
    code(
        "selection_path = ROOT / 'artifacts/runs' / STUDY_ID / 'selection' / 'selection_ledger.csv'\n"
        "if selection_path.is_file():\n"
        "    display(pd.read_csv(selection_path))\n"
        "else:\n"
        "    print('No selection ledger was recorded.')\n"
        "for name in ('adf.csv', 'kpss.csv'):\n"
        "    path = ROOT / 'artifacts/diagnostics' / name\n"
        "    if path.is_file():\n"
        "        display(pd.read_csv(path).head(30))\n"
        "ljung_path = VALIDATION_RESIDUALS / 'ljung_box.csv'\n"
        "if ljung_path.is_file():\n"
        "    display(pd.read_csv(ljung_path))\n"
        "else:\n"
        "    print('No validation Ljung-Box table was recorded.')\n"
        "for path in sorted(VALIDATION_RESIDUALS.glob('model_*_acf_pacf.csv')):\n"
        "    print(path.name)\n"
        "    display(pd.read_csv(path).head(20))\n"
        "for path in sorted(VALIDATION_RESIDUALS.glob('model_*_diagnostics.png')):\n"
        "    display(Image(filename=str(path)))"
    )
    markdown("## 6. Chronological forecast comparisons and uncertainty")
    markdown(
        "Each issue origin uses only observations whose interval end plus the assumed "
        "publication delay precedes that origin. Weekly parameter refits and causal "
        "filter updates forecast through the unobserved bridge onto a 48-slot UTC "
        "path. The test cannot change model or policy selections.\n\n"
        "The common comparison excludes an origin if any competitor falls back. "
        "End-to-end metrics retain fallback behavior. Marginal interval coverage is "
        "not joint job-cost coverage, and parameter-estimation uncertainty is excluded."
    )
    code(
        "validation_metrics = pd.read_csv(VALIDATION_RUN / 'forecast_metrics.csv')\n"
        "test_metrics = pd.read_csv(TEST_RUN / 'forecast_metrics.csv')\n"
        "display(validation_metrics)\n"
        "display(test_metrics)\n"
        "display(pd.read_csv(VALIDATION_RUN / 'forecast_common_metrics.csv'))\n"
        "display(pd.read_csv(TEST_RUN / 'forecast_common_metrics.csv'))"
        "\nfor run in (VALIDATION_RUN, TEST_RUN):\n"
        "    path = run / 'forecast_path_metrics.csv'\n"
        "    if path.is_file():\n"
        "        display(pd.read_csv(path))"
    )
    markdown("## 7. Primary and queue scheduling backtests")
    code(
        f"SOURCE_PATHS = {artifact_paths!r}\n"
        "for name, relative_path in SOURCE_PATHS.items():\n"
        "    path = ROOT / relative_path\n"
        "    print(name, path.relative_to(ROOT))\n"
        "    display(pd.read_csv(path))"
    )
    code(
        "display(pd.DataFrame([{\n"
        "    'primary_jobs': RESULTS['primary_jobs'],\n"
        "    'deadline_misses': RESULTS['primary_deadline_misses'],\n"
        "    'modeled_savings_pct': RESULTS['primary_savings_pct'],\n"
        "    'ci95_pct': RESULTS['primary_ci95_pct'],\n"
        "    'interpretation': RESULTS['h3_interpretation'],\n"
        "}]))\n"
        "display(pd.read_csv(TEST_RUN / 'forecast_loss_bootstrap.csv'))\n"
        "display(pd.read_csv(TEST_RUN / 'single_job/versus_simple_bootstrap.csv'))"
    )
    markdown(
        "The default isolated cases use 0.4 kW allocated IT power and PUE 1.2, "
        "so a two-hour job consumes a modeled 0.96 kWh. Starts minimize the "
        "energy-weighted whole-job path, not its lowest point. These overlapping "
        "cases are correlated counterfactuals, not one executable annual trace.\n\n"
        "Queue policies see only arrivals and immutable prior reservations. "
        "When accepted job sets differ, matched-job emissions comparisons are "
        "descriptive post-policy intersections. Rejected work is not carbon saved."
    )
    markdown("## 8. Sensitivities, negative outcomes, limitations, and deployment")
    code(
        "from gridshift.live import verify_deployment_fixture\n"
        "display(verify_deployment_fixture(ROOT, CONFIG))\n"
        "for name in ('sensitivity_summary.csv', 'energy_profile_sensitivity.csv', 'outage_state_replay.csv'):\n"
        "    display(pd.read_csv(ROOT / 'artifacts/sensitivities' / name))\n"
        "for path in sorted(VALIDATION_RESIDUALS.glob('model_*_job_uncertainty.json')):\n"
        "    display(json.loads(path.read_text()))\n"
        "display(pd.DataFrame({'limitation': RESULTS.get('limitations', [])}))\n"
        "manifest = json.loads((ROOT / 'data/manifest.json').read_text(encoding='utf-8'))\n"
        "print('Normalized data hash:', manifest.get('normalized_hash'))\n"
        "print('This notebook reports only stored outcomes. A missing row remains missing.')\n"
        "print('No model fitting, network request, or workload execution occurs in this notebook.')"
    )
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
            "gridshift": {
                "study_id": evidence.study_id,
                "execution": "skeleton generated; root workflow runs nbconvert --execute",
                "offline": True,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _select_columns(records: Sequence[Mapping[str, Any]], preferred: Sequence[str], *, limit: int | None = None) -> tuple[list[str], list[list[str]]]:
    names = [name for name in preferred if records and name in set().union(*(row.keys() for row in records))]
    if not names and records:
        names = _columns(records)[:6]
    rows = []
    for record in (records[:limit] if limit is not None else records):
        rows.append([_format(record.get(name), digits=4) for name in names])
    return names, rows


def _table_spec(records: Sequence[Mapping[str, Any]], preferred: Sequence[str], *, limit: int = 8) -> dict[str, Any]:
    names, rows = _select_columns(records, preferred, limit=limit)
    if not names:
        return {"headers": ["Status"], "rows": [["Not evaluated"]]}
    return {"headers": [_ascii(name.replace("_", " ")) for name in names], "rows": rows}


def _coverage_chart(evidence: Evidence) -> dict[str, Any] | None:
    records = evidence.source_tables.get("data_monthly_coverage", [])
    source = "full"
    if not records:
        records = evidence.diagnostic_tables.get("monthly_coverage.csv", [])
        source = "development"
    if not records:
        return None
    month_key = _field(records, "interval_start_utc", "local_month", "month_utc", "month")
    coverage_key = _field(records, "coverage", "coverage_fraction", "observed_share")
    if not month_key or not coverage_key:
        return None
    study = evidence.config.get("study", {})
    start = str(study.get("test_start", ""))[:7] if source == "full" else ""
    end = str(study.get("test_end", ""))[:7] if source == "full" else ""
    rows = []
    for row in records:
        month = str(row.get(month_key) or "")[:7]
        coverage = _number(row.get(coverage_key))
        if not month or coverage is None:
            continue
        if source == "full" and start and end and not (start <= month < end):
            continue
        rows.append((month, coverage))
    rows.sort()
    if not rows:
        return None
    return {
        "type": "line",
        "title": "Monthly observed coverage" if source == "full" else "Development coverage by month",
        "axis_title": "Observed share",
        "number_format_code": "0%",
        "y_min": 0,
        "y_max": 1,
        "categories": [month for month, _ in rows],
        "series": [{
            "name": "Coverage",
            "values": [value for _, value in rows],
            "color": "#127C74",
        }],
        "source": source,
    }


def _chart_spec(
    records: Sequence[Mapping[str, Any]],
    *,
    models: Sequence[Any],
    metric: str,
    category: str,
    title: str,
    axis_title: str,
    kind: str = "line",
    group_value: str | None = None,
) -> dict[str, Any] | None:
    selected_models = list(dict.fromkeys(str(model) for model in models if model is not None))
    if not selected_models:
        return None
    grouped: dict[str, dict[str, float | None]] = {model: {} for model in selected_models}
    categories: set[str] = set()
    for row in records:
        if group_value is not None and str(row.get("group", row.get("group_type", ""))).lower() != group_value:
            continue
        model = row.get("model_id", row.get("model"))
        if model is None or str(model) not in grouped:
            continue
        category_value = row.get(category)
        measure = _number(row.get(metric))
        if category_value is None:
            continue
        label = _format(category_value)
        categories.add(label)
        grouped[str(model)][label] = measure
    def category_order(label: str) -> tuple[int, str]:
        number = _number(label)
        return (0, f"{number:012.4f}") if number is not None else (1, label)
    ordered_categories = sorted(categories, key=category_order)
    series = []
    for index, model in enumerate(selected_models):
        values = [grouped[model].get(label) for label in ordered_categories]
        if any(value is not None for value in values):
            series.append({"name": model, "values": values, "color": ("#D2644A", "#127C74", "#687784")[index % 3]})
    if not ordered_categories or not series:
        return None
    return {
        "type": kind,
        "title": title,
        "axis_title": axis_title,
        "categories": ordered_categories,
        "series": series,
    }


def _primary_chart(evidence: Evidence) -> dict[str, Any] | None:
    rows = _default_primary_rows(evidence)
    metric = "mean_realized_grams"
    if not rows or not any(_number(row.get(metric)) is not None for row in rows):
        return None
    model = evidence.results.get("deployment_model")
    policies = []
    values = []
    for row in rows:
        policy = row.get("policy")
        if not policy or str(row.get("result_type", "scheduling")) != "scheduling":
            continue
        if policy == "forecast" and model is not None and str(row.get("model_id")) != str(model):
            continue
        if policy == "forecast" and model is None:
            continue
        value = _number(row.get(metric))
        if value is None:
            continue
        policies.append(str(policy) if row.get("model_id") in {None, model} else f"{policy} ({row.get('model_id')})")
        values.append(value)
    if not policies:
        return None
    return {
        "type": "bar",
        "title": "Mean realized emissions per eligible job",
        "axis_title": "gCO2",
        "categories": policies,
        "series": [{"name": "Mean realized emissions", "values": values, "color": "#127C74"}],
    }


def _presentation_content(evidence: Evidence) -> dict[str, Any]:
    champion = evidence.results.get("forecast_champion")
    simple = evidence.results.get("strongest_simple")
    deployment = evidence.results.get("deployment_model")
    val_rows = _common_metric_rows(evidence, "validation", (champion, simple))
    test_rows = _common_metric_rows(evidence, "test", (champion, simple))
    default_rows = _default_primary_rows(evidence)
    bootstrap = _bootstrap_rows(evidence)
    queue = evidence.source_tables.get("queue_summary", [])
    diag_summary = evidence.diagnostics
    quality_table = _table_spec(_quality_rows(evidence.quality), ("measure", "value"), limit=12)
    quality_labels = {
        "overall_coverage": "Overall coverage",
        "minimum_monthly_coverage": "Lowest monthly coverage",
        "minimum_test_monthly_coverage": "Lowest test-month coverage",
        "unique_utc_intervals": "Unique UTC intervals",
        "regular_grid": "Regular grid",
        "data_gate_pass": "Data gate passed",
        "availability_is_assumed": "Assumed availability",
    }
    quality_table["headers"] = ["Measure", "Value"]
    for row in quality_table["rows"]:
        row[0] = quality_labels.get(row[0], row[0].replace("_", " ").capitalize())
    coverage_chart = _coverage_chart(evidence)
    metric_tables = []
    for records in (val_rows, test_rows):
        rows = []
        for model in (champion, simple):
            losses = [_number(row.get("mae")) for row in records
                      if row.get("model_id") == model and row.get("group") == "all"]
            losses = [value for value in losses if value is not None]
            rows.append([str(model), _format(sum(losses) / len(losses)) if losses else "NA"])
        metric_tables.append({"headers": ["Model", "Mean endpoint MAE"], "rows": rows})
    val_metric_table, test_metric_table = metric_tables
    primary_table = _table_spec(
        [row for row in default_rows
         if row.get("policy") in {"earliest", "oracle"}
         or row.get("model_id") == deployment],
        ("policy", "mean_realized_grams", "paired_savings_pct"),
        limit=3,
    )
    primary_table["headers"] = ["Policy", "Mean gCO2", "Delta %"]
    bootstrap_table = _table_spec(
        bootstrap,
        ("block_days", "paired_job_count", "estimate_savings_pct", "ci95_savings_pct_low", "ci95_savings_pct_high", "is_primary_block"),
        limit=8,
    )
    queue_rows = []
    queue_groups = sorted({(_number(row.get("offered_load")), _number(row.get("slack_hours")))
                           for row in queue
                           if _number(row.get("offered_load")) is not None
                           and _number(row.get("slack_hours")) is not None})
    for load, slack in queue_groups:
        group = [row for row in queue if _number(row.get("offered_load")) == load
                 and _number(row.get("slack_hours")) == slack]
        values = []
        for policy, field in (("earliest", "rejection_rate"),
                              ("selected", "rejection_rate"),
                              ("selected", "matched_savings_pct")):
            numbers = [_number(row.get(field)) for row in group if row.get("policy") == policy]
            numbers = [value for value in numbers if value is not None]
            value = sum(numbers) / len(numbers) if numbers else None
            values.append(_format(100 * value if value is not None and field == "rejection_rate" else value))
        queue_rows.append([_format(load), _format(slack), *values])
    queue_table = {"headers": ["Load", "Slack h", "Reject early %", "Reject selected %", "Matched delta %"],
                   "rows": queue_rows}
    config_study = evidence.config.get("study", {})
    config_schedule = evidence.config.get("scheduling", {})
    references_note = {
        "question": "Sources S1, S2, S4, S5, and S9.",
        "data": "Source IDs S1-S8. See reports/gridshift_report.md References.",
        "diagnostics": "Source IDs S9-S13. Diagnostic figures and tables come from artifacts/diagnostics.",
        "forecast": "Source IDs S9-S13. Validation and test rows come from the content-addressed forecast_metrics.csv files.",
        "schedule": "Source ID S5. Energy and emissions are modeled under config values.",
        "results": "Source CSV tables and artifacts/results.json. No re-selection on test data.",
        "queue": "Source CSV table. Queue arrivals are synthetic and service outcomes remain part of the comparison.",
    }
    used_figures: set[str] = set()

    def figure_spec(preferred: str, alt: str) -> dict[str, str]:
        name = preferred if preferred in evidence.figures and preferred not in used_figures else next(
            candidate for candidate in evidence.figures if candidate not in used_figures
        )
        used_figures.add(name)
        return {"path": str(evidence.figures[name]), "alt": alt}

    slides = [
        {
            "title": "GridShift",
            "subtitle": "Carbon-aware GPU workload scheduling with classical time-series forecasts",
            "bullets": [f"Study ID {evidence.study_id}", "Target: NESO estimated GB intensity, gCO2/kWh"],
            "figure": figure_spec("series.png", "Stored development-period carbon-intensity series"),
            "notes": f"Introduce the study and its target. The figure is a stored development diagnostic, not a locked-test result. {references_note['data']}",
        },
        {
            "title": "Dashboard and research scope",
            "figure": (
                {"path": str(evidence.root / "artifacts/tests/dashboard-desktop.png"),
                 "alt": "Verified local GridShift scheduling workspace"}
                if (evidence.root / "artifacts/tests/dashboard_browser.json").is_file()
                and (evidence.root / "artifacts/tests/dashboard-desktop.png").is_file() else None
            ),
            "bullets": [
                "Do eligible forecasts improve feasible GPU placement?",
                "Compare earliest execution and simple forecasts.",
                "Model operational CO2, not avoided grid emissions.",
                "Local recommendations are predictions, not measured savings.",
            ],
            "notes": f"The question is bounded by declared duration, energy, deadline, and capacity assumptions. {references_note['question']}",
        },
        {
            "title": "Data coverage and quality",
            "bullets": [
                f"Observed slots: {_format(evidence.quality.get('observed'))} of {_format(evidence.quality.get('slots'))}.",
                "Missing actuals remain missing; provider forecasts stay separate.",
                "The quality gate and monthly coverage are reported from stored artifacts.",
            ],
            "table": quality_table,
            "chart": coverage_chart,
            "notes": f"Quality values come from artifacts/data/quality.json. Monthly coverage chart source: {evidence.table_paths.get('data_monthly_coverage', 'artifacts/diagnostics/monthly_coverage.csv')}. {references_note['data']}",
        },
        {
            "title": "Development diagnostics",
            "bullets": [
                f"Diagnostic boundary: {_ascii(diag_summary.get('development_end_exclusive_utc', 'not recorded'))}.",
                f"Development-only STL status: {_ascii(diag_summary.get('stl48', {}).get('status', 'not recorded'))}.",
                "ACF, periodogram, and stationarity checks guide candidates, not test conclusions.",
            ],
            "figure": figure_spec("stl48.png", "Stored development-only robust STL components"),
            "notes": f"The source files are diagnostics.json, adf.csv, kpss.csv, acf_pacf.csv, and the named figure. Centered STL is descriptive, not an online feature. {references_note['diagnostics']}",
        },
        {
            "title": "Forecast model catalogue",
            "bullets": [
                "AR, MA, ARMA, ARIMA, and daily-seasonal SARIMA.",
                "Persistence, seasonal-naive, and calendar-mean controls.",
                "Failed fits and null outcomes remain visible in the source tables.",
            ],
            "table": {
                "headers": ["Role", "Recorded choice"],
                "rows": [
                    ["Forecast champion", str(champion or "Not selected")],
                    ["Strongest simple baseline", str(simple or "Not selected")],
                    ["Scheduling model", str(deployment or "Not selected")],
                    ["Selection boundary", "Validation only"],
                ],
            },
            "notes": f"These selections are read from results.json and are not recomputed from test data. {references_note['forecast']}",
        },
        {
            "title": "Evaluation design",
            "bullets": [
                "Chronological development, validation, and locked-test partitions.",
                "Common eligible targets and counts by lead time.",
                "Paired block uncertainty for the primary scheduling contrast.",
                "AIC and BIC compare only compatible likelihood groups.",
            ],
            "table": {
                "headers": ["Design item", "Configured value"],
                "rows": [
                    ["Validation", f"{config_study.get('validation_start', 'Not recorded')} to {config_study.get('validation_end', 'Not recorded')}"],
                    ["Locked test", f"{config_study.get('test_start', 'Not recorded')} to {config_study.get('test_end', 'Not recorded')}"],
                    ["Horizons", _format(config_study.get("reported_horizons", "Not recorded"))],
                    ["Bootstrap resamples", _format(config_study.get("bootstrap_resamples", "Not recorded"))],
                ],
            },
            "notes": f"Study settings come from the passed config. The full configuration digest appears in the report. {references_note['forecast']}",
        },
        {
            "title": "Validation forecast outcomes",
            "bullets": [
                f"Validation champion: {champion or 'not selected'}.",
                f"Strongest simple baseline: {simple or 'not selected'}.",
                "The chart shows MAE by lead time only where the source table has a numeric value.",
            ],
            "table": val_metric_table,
            "chart": _chart_spec(
                val_rows,
                models=(champion, simple),
                metric="mae",
                category="horizon",
                title="Mean absolute error by lead time",
                axis_title="MAE (gCO2/kWh)",
                group_value="all",
            ),
            "notes": f"Validation scores are read from artifacts/runs/{evidence.study_id}/validation/forecast_metrics.csv. {references_note['results']}",
        },
        {
            "title": "Locked-test forecast outcomes",
            "bullets": [
                "Test rows report the validation-selected champion and simple baseline.",
                "The test does not change the selected model.",
                "Null metrics and zero-count groups remain unfilled.",
            ],
            "table": test_metric_table,
            "chart": _chart_spec(
                test_rows,
                models=(champion, simple),
                metric="mae",
                category="horizon",
                title="Locked-test MAE by lead time",
                axis_title="MAE (gCO2/kWh)",
                group_value="all",
            ),
            "notes": f"Test scores are read from artifacts/runs/{evidence.study_id}/test/forecast_metrics.csv. {references_note['results']}",
        },
        {
            "title": "Scheduling formulation",
            "bullets": [
                "Minimize forecast intensity integrated over full job energy.",
                "Keep deadlines, capacity, and reservations as hard constraints.",
                "Use an oracle only as an unattainable opportunity bound.",
            ],
            "table": {
                "headers": ["Declared assumption", "Value"],
                "rows": [
                    ["Default duration (hours)", _format(config_schedule.get("default_duration_hours"))],
                    ["Default slack (hours)", _format(config_schedule.get("default_slack_hours"))],
                    ["Power (kW)", _format(config_schedule.get("power_kw"))],
                    ["PUE", _format(config_schedule.get("pue"))],
                    ["Primary model", str(deployment or "Not selected")],
                ],
            },
            "notes": f"Scheduling values come from config. They are scenarios unless measured telemetry appears in a verified artifact. {references_note['schedule']}",
        },
        {
            "title": "Primary scheduling outcomes",
            "bullets": [
                f"{deployment}: {_format(evidence.results.get('primary_savings_pct'))}% modeled reduction against earliest execution.",
                f"95% paired block interval: {_format(evidence.results.get('primary_ci95_pct', [None, None])[0])}% to {_format(evidence.results.get('primary_ci95_pct', [None, None])[1])}%.",
            ],
            "table": primary_table,
            "chart": _primary_chart(evidence),
            "notes": f"Primary summary rows come from {evidence.source_stages.get('primary_summary')}. Bootstrap uncertainty comes from {evidence.source_stages.get('primary_bootstrap')}. A simple deployment choice does not establish added scheduling value from classical forecasting. {_result_sentence(evidence)} {references_note['results']}",
        },
        {
            "title": "Queue service and emissions",
            "bullets": [
                "Table values are arithmetic means across the three frozen seeds.",
                "Matched emissions differences are descriptive; accepted work differs.",
                "Lower emissions from rejected work are not savings.",
            ],
            "table": queue_table,
            "notes": f"Queue summary rows come from {evidence.source_stages.get('queue_summary')}. Full scenarios and policies remain in the source CSV and report. {references_note['queue']}",
        },
        {
            "title": "Backup equations and failures",
            "bullets": [
                "Job CO2 = sum(overlap hours x IT kW x PUE x intensity).",
                "Choose the minimum integrated forecast cost; obey release, deadline, and capacity.",
                "SARIMA uses AR, MA, and period-48 seasonal lag polynomials on differenced levels.",
                "Missing or stale forecasts disable carbon ranking; failed fits retain explicit fallbacks.",
                "Rejected queue work is not savings. Marginal intervals are not joint job-cost guarantees.",
                f"Frozen {deployment} timing benefit and classical forecast skill are separate findings.",
            ],
            "notes": (
                "Backup notes: realized job CO2 is the sum over intervals of overlap energy in kWh "
                "times estimated intensity in gCO2/kWh. The forecast scheduler minimizes the same "
                "integrated expression using the eligible forecast path. Failure cases include "
                "missing forecasts, incomplete truth coverage, infeasible deadlines, failed model "
                "fits, and unmatched queue work. Preserve each outcome in the tables. "
                f"{references_note['schedule']}"
            ),
        },
    ]
    if len(slides) != 12:
        raise ExportInputError(f"Presentation content must contain 12 slides, got {len(slides)}")
    for slide in slides:
        slide["notes"] = _ascii(slide.get("notes", ""))
    return {
        "schema_version": 1,
        "study_id": evidence.study_id,
        "selections": {
            "forecast_champion": champion,
            "strongest_simple": simple,
            "deployment_model": deployment,
        },
        "slides": slides,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(payload))


def _input_hashes(evidence: Evidence) -> dict[str, str]:
    inputs = {
        "results": evidence.root / "artifacts/results.json",
        "quality": evidence.root / "artifacts/data/quality.json",
        "diagnostics": evidence.root / "artifacts/diagnostics/diagnostics.json",
    }
    if (evidence.root / "data/manifest.json").is_file():
        inputs["data_manifest"] = evidence.root / "data/manifest.json"
    for name in ("dashboard_browser.json", "dashboard-desktop.png"):
        path = evidence.root / "artifacts/tests" / name
        if path.is_file():
            inputs[f"dashboard/{name}"] = path
    for relative in ("artifacts/protocol_freeze.json", "pyproject.toml", "uv.lock"):
        path = evidence.root / relative
        if path.is_file():
            inputs[relative] = path
    source_dir = evidence.root / "src/gridshift"
    if source_dir.is_dir():
        inputs.update(
            {
                f"source/{path.name}": path
                for path in sorted(source_dir.glob("*.py"))
                if path.is_file()
            }
        )
    inputs.update({key: path for key, path in evidence.table_paths.items() if path.is_file()})
    hashed = {key: _sha256(path) for key, path in inputs.items()}
    hashed["config_json"] = hashlib.sha256(_json_bytes(evidence.config)).hexdigest()
    return hashed


def _package_versions() -> dict[str, str]:
    distributions = {
        "gridshift": "gridshift",
        "numpy": "numpy",
        "pandas": "pandas",
        "scipy": "scipy",
        "statsmodels": "statsmodels",
        "reportlab": "reportlab",
        "nbconvert": "nbconvert",
        "nbformat": "nbformat",
        "python-pptx": "python-pptx",
    }
    versions = {}
    for label, distribution in distributions.items():
        try:
            versions[label] = package_metadata.version(distribution)
        except package_metadata.PackageNotFoundError:
            versions[label] = "not installed in exporter environment"
    return versions


def _generator_hash() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(__file__).with_name("presentation.mjs")):
        if not path.is_file():
            raise FileNotFoundError(f"Academic export generator source is missing: {path}")
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _existing_exports(root: Path) -> dict[str, Path]:
    paths = {
        "report_markdown": root / "reports/gridshift_report.md",
        "report_pdf": root / "reports/gridshift_report.pdf",
        "report_previews": root / "reports/gridshift_report_preview",
        "notebook": root / "notebooks/01_gridshift_study.ipynb",
        "notebook_html": root / "notebooks/01_gridshift_study.html",
        "presentation_content": root / "slides/gridshift_presentation_content.json",
        "presentation_source": root / "slides/gridshift_presentation.mjs",
        "presentation_pptx": root / "slides/gridshift_presentation.pptx",
        "presentation_pdf": root / "slides/gridshift_presentation.pdf",
        "export_manifest": root / "reports/export_manifest.json",
    }
    paths.update(
        {
            f"presentation_slide_{index:02d}": (
                root / "slides/gridshift_presentation_preview" / f"slide-{index:02d}.png"
            )
            for index in range(1, 13)
        }
    )
    return paths


def _reuse_or_refuse(root: Path, evidence: Evidence) -> dict[str, str] | None:
    paths = _existing_exports(root)
    present = [path for path in paths.values() if path.exists()]
    if not present:
        return None
    manifest_path = paths["export_manifest"]
    if not manifest_path.is_file():
        raise FileExistsError("Academic export outputs exist without a verified export manifest; refusing to overwrite them")
    manifest = _read_json(manifest_path, "export manifest")
    if manifest.get("study_id") != evidence.study_id:
        raise FileExistsError("Academic export manifest belongs to a different study_id; refusing to overwrite it")
    if manifest.get("input_hashes") != _input_hashes(evidence):
        raise FileExistsError("Verified inputs changed after the existing export; refusing to overwrite it")
    if manifest.get("generator_hash") != _generator_hash():
        raise FileExistsError("Export generator changed after the existing export; refusing to overwrite it")
    hashes = manifest.get("output_hashes", {})
    expected_files = [path for name, path in paths.items() if name != "export_manifest"]
    if not all(
        path.exists()
        and hashes.get(path.relative_to(root).as_posix()) == _path_hash(path)
        for path in expected_files
    ):
        raise FileExistsError("Academic export output hash differs from its manifest; refusing to overwrite it")
    return {name: str(path) for name, path in paths.items()}


def _run_presentation_generator(
    evidence: Evidence,
    content_path: Path,
    build_dir: Path,
    pptx_path: Path,
    pdf_path: Path,
    render_dir: Path,
) -> None:
    node = Path(
        os.environ.get(
            "RUNTIME_NODE",
            r"C:\Users\viraj\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe",
        )
    )
    node_modules = Path(
        os.environ.get(
            "RUNTIME_NODE_MODULES",
            r"C:\Users\viraj\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules",
        )
    )
    runtime_bin = Path(
        os.environ.get(
            "RUNTIME_BIN_DIR",
            r"C:\Users\viraj\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\override",
        )
    )
    runtime_python = Path(
        os.environ.get(
            "RUNTIME_PYTHON",
            r"C:\Users\viraj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
        )
    )
    script = Path(__file__).with_name("presentation.mjs")
    if not node.is_file():
        raise FileNotFoundError(f"Bundled Node executable not found: {node}")
    if not node_modules.is_dir():
        raise FileNotFoundError(f"Bundled Node modules not found: {node_modules}")
    if not runtime_bin.is_dir():
        raise FileNotFoundError(f"Bundled binary directory not found: {runtime_bin}")
    if not runtime_python.is_file():
        raise FileNotFoundError(f"Bundled Python executable not found: {runtime_python}")
    if not script.is_file():
        raise FileNotFoundError(f"Artifact Tool presentation source not found beside exports.py: {script}")

    shutil.copy2(script, build_dir / "presentation.mjs")
    env = os.environ.copy()
    env["RUNTIME_NODE"] = str(node)
    env["RUNTIME_NODE_MODULES"] = str(node_modules)
    env["RUNTIME_BIN_DIR"] = str(runtime_bin)
    env["RUNTIME_PYTHON"] = str(runtime_python)
    env["GRIDSHIFT_PRESENTATIONS_SKILL"] = os.environ.get(
        "GRIDSHIFT_PRESENTATIONS_SKILL",
        r"C:\Users\viraj\.codex\plugins\cache\openai-primary-runtime\presentations\26.1020.11127\skills\presentations",
    )
    command = [
        str(node),
        str(build_dir / "presentation.mjs"),
        str(content_path),
        str(build_dir),
        str(pptx_path),
        str(pdf_path),
        str(render_dir),
        str(evidence.root),
    ]
    subprocess.run(command, cwd=evidence.root, env=env, check=True)
    from reportlab.pdfgen.canvas import Canvas
    canvas = Canvas(str(pdf_path), pagesize=(960, 540), pageCompression=1)
    canvas.setTitle("GridShift presentation")
    slides = _read_json(content_path, "presentation content")["slides"]
    for index, slide in enumerate(slides, start=1):
        image = render_dir / f"slide-{index:02d}.png"
        if not image.is_file():
            raise ExportInputError(f"Validated slide render is missing: {image}")
        canvas.drawImage(str(image), 0, 0, width=960, height=540)
        text = canvas.beginText(54, 500)
        text.setFont("Helvetica", 12)
        text.setTextRenderMode(3)
        text.textLine(slide["title"])
        canvas.drawText(text)
        canvas.showPage()
    canvas.save()


def _verify_pdf(path: Path, expected_pages: int | None = None) -> int:
    bundled_python = Path(
        os.environ.get(
            "RUNTIME_PYTHON",
            r"C:\Users\viraj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
        )
    )
    if not path.is_file() or path.stat().st_size < 1000:
        raise ExportInputError(f"PDF is missing or unexpectedly small: {path}")
    if bundled_python.is_file():
        command = [
            str(bundled_python),
            "-c",
            "import json,sys; from pypdf import PdfReader; p=PdfReader(sys.argv[1]); "
            "print(json.dumps({'pages':len(p.pages),'text':''.join((x.extract_text() or '') for x in p.pages)}))",
            str(path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True)
        inspected = json.loads(result.stdout)
        pages = int(inspected["pages"])
        if expected_pages is not None and pages != expected_pages:
            raise ExportInputError(f"PDF contains {pages} pages; expected {expected_pages}: {path}")
        if not inspected.get("text", "").strip():
            raise ExportInputError(f"PDF has no extractable text: {path}")
        return pages
    return -1


def _render_pdf_pages(pdf_path: Path, render_dir: Path, expected_pages: int) -> list[Path]:
    renderer = Path(
        os.environ.get(
            "GRIDSHIFT_PDFTOPPM",
            r"C:\Users\viraj\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe",
        )
    )
    if not renderer.is_file():
        raise FileNotFoundError(f"Bundled Poppler renderer not found: {renderer}")
    render_dir.mkdir(parents=True, exist_ok=True)
    prefix = render_dir / "page"
    subprocess.run(
        [str(renderer), "-png", "-r", "110", str(pdf_path), str(prefix)],
        check=True,
        capture_output=True,
    )
    pages = sorted(render_dir.glob("page-*.png"))
    if len(pages) != expected_pages:
        raise ExportInputError(
            f"Rendered {len(pages)} PDF pages, expected {expected_pages}: {pdf_path}"
        )
    if any(path.stat().st_size < 1000 or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" for path in pages):
        raise ExportInputError(f"At least one rendered PDF page is empty or invalid: {pdf_path}")
    return pages


def _path_hash(path: Path) -> str:
    if path.is_file():
        return _sha256(path)
    if path.is_dir():
        digest = hashlib.sha256()
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(child.relative_to(path).as_posix().encode("utf-8"))
            digest.update(bytes.fromhex(_sha256(child)))
        return digest.hexdigest()
    raise FileNotFoundError(path)


def _publish(staged: Mapping[str, Path], destinations: Mapping[str, Path], manifest: Mapping[str, Any]) -> None:
    for name, destination in destinations.items():
        if destination.exists():
            raise FileExistsError(f"Refusing to replace existing academic export: {destination}")
    for destination in destinations.values():
        destination.parent.mkdir(parents=True, exist_ok=True)
    for name, source in staged.items():
        if name == "export_manifest":
            continue
        destination = destinations[name]
        source.replace(destination)
    manifest_path = destinations["export_manifest"]
    manifest_path.write_bytes(_json_bytes(manifest))


def _execute_notebook(root: Path, notebook: Path, work: Path) -> Path:
    kernel_prefix = work / "kernel-prefix"
    subprocess.run(
        [sys.executable, "-m", "ipykernel", "install", "--prefix", str(kernel_prefix),
         "--name", "gridshift", "--display-name", "GridShift"],
        check=True, capture_output=True,
    )
    environment = os.environ.copy()
    environment["JUPYTER_PATH"] = str(kernel_prefix / "share/jupyter")
    subprocess.run(
        [sys.executable, "-m", "nbconvert", "--to", "notebook", "--execute", "--inplace",
         "--ExecutePreprocessor.kernel_name=gridshift", "--ExecutePreprocessor.timeout=300", str(notebook)],
        cwd=root, env=environment, check=True,
    )
    executed = json.loads(notebook.read_text(encoding="utf-8"))
    code_cells = [cell for cell in executed["cells"] if cell["cell_type"] == "code"]
    if any(cell.get("execution_count") is None or any(output.get("output_type") == "error"
           for output in cell.get("outputs", [])) for cell in code_cells):
        raise ExportInputError("Notebook execution did not complete without errors")
    executed.setdefault("metadata", {}).setdefault("gridshift", {})["execution"] = (
        "EXECUTED_OFFLINE_WITHOUT_ERRORS"
    )
    notebook.write_bytes(_json_bytes(executed))
    subprocess.run(
        [sys.executable, "-m", "nbconvert", "--to", "html", str(notebook)],
        cwd=root, env=environment, check=True,
    )
    html = notebook.with_suffix(".html")
    if not html.is_file() or html.stat().st_size < 1000:
        raise ExportInputError("Executed notebook HTML is missing")
    return html


def export(root: str | Path, config: Mapping[str, Any]) -> dict[str, str]:
    """Generate local academic exports from a complete, verified artifact set.

    The function performs all input checks before creating output directories.
    It does not collect data, fit models, schedule jobs, or modify source results.
    """
    evidence = _load_evidence(root, config)
    reused = _reuse_or_refuse(evidence.root, evidence)
    if reused is not None:
        return reused

    base = evidence.root
    temp_root = base / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"gridshift-export-{evidence.study_id}-", dir=temp_root) as name:
        work = Path(name)
        report_md = work / "gridshift_report.md"
        report_pdf = work / "gridshift_report.pdf"
        report_renders = work / "report_pages"
        notebook = work / "01_gridshift_study.ipynb"
        content_json = work / "gridshift_presentation_content.json"
        presentation_source = work / "gridshift_presentation.mjs"
        presentation_pptx = work / "slides" / "gridshift_presentation.pptx"
        presentation_pdf = work / "slides" / "gridshift_presentation.pdf"
        renders = work / "slide_pngs"
        renders.mkdir()

        markdown = _markdown_report(evidence)
        report_md.write_text(markdown, encoding="utf-8", newline="\n")
        body_pages, total_pages = _build_pdf(report_pdf, evidence)
        report_page_count = _verify_pdf(report_pdf, expected_pages=total_pages)
        report_rendered_pages = _render_pdf_pages(
            report_pdf,
            report_renders,
            expected_pages=report_page_count,
        )

        notebook_doc = _markdown_notebook(evidence)
        notebook.write_bytes(_json_bytes(notebook_doc))
        notebook_check = json.loads(notebook.read_text(encoding="utf-8"))
        if notebook_check.get("nbformat") != 4 or len(notebook_check.get("cells", [])) < 10:
            raise ExportInputError("Generated notebook failed its nbformat structure check")
        if any(cell.get("cell_type") == "code" and cell.get("execution_count") is not None for cell in notebook_check["cells"]):
            raise ExportInputError("Notebook skeleton must not claim that its code cells were executed")
        notebook_html = _execute_notebook(base, notebook, work)

        presentation_data = _presentation_content(evidence)
        _write_json(content_json, presentation_data)
        _run_presentation_generator(
            evidence,
            content_json,
            work,
            presentation_pptx,
            presentation_pdf,
            renders,
        )
        _verify_pdf(presentation_pdf, expected_pages=12)
        if not presentation_pptx.is_file() or presentation_pptx.stat().st_size < 1000:
            raise ExportInputError("Finalized editable presentation is missing or unexpectedly small")
        rendered_slides = sorted(renders.glob("slide-*.png"))
        if len(rendered_slides) != 12 or any(
            path.stat().st_size < 1000 or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n"
            for path in rendered_slides
        ):
            raise ExportInputError(f"Expected 12 non-empty slide PNGs, found {len(rendered_slides)}")

        presentation_source.write_text(
            Path(__file__).with_name("presentation.mjs").read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
        outputs = _existing_exports(base)
        staged = {
            "report_markdown": report_md,
            "report_pdf": report_pdf,
            "report_previews": report_renders,
            "notebook": notebook,
            "notebook_html": notebook_html,
            "presentation_content": content_json,
            "presentation_source": presentation_source,
            "presentation_pptx": presentation_pptx,
            "presentation_pdf": presentation_pdf,
        }
        staged.update(
            {
                f"presentation_slide_{index:02d}": path
                for index, path in enumerate(rendered_slides, start=1)
            }
        )
        output_hashes = {
            Path(outputs[name]).relative_to(base).as_posix(): _path_hash(path)
            for name, path in staged.items()
        }
        manifest = {
            "schema_version": 1,
            "study_id": evidence.study_id,
            "input_hashes": _input_hashes(evidence),
            "generator_hash": _generator_hash(),
            "output_hashes": output_hashes,
            "report_body_pages_excluding_appendices": body_pages,
            "report_total_pages": total_pages,
            "report_rendered_pages": len(report_rendered_pages),
            "presentation_slides": 12,
            "presentation_slide_pngs": 12,
            "presentation_pdf_rendering": "Validated slide PNGs with searchable titles; editable charts and tables are in the PPTX",
            "notebook_execution": "EXECUTED_OFFLINE_WITHOUT_ERRORS",
            "python_version": platform.python_version(),
            "package_versions": _package_versions(),
            "missing_diagnostic_tables": list(evidence.missing_diagnostic_tables),
            "missing_diagnostic_figures": list(evidence.missing_diagnostic_figures),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        staged["export_manifest"] = work / "export_manifest.json"
        _write_json(staged["export_manifest"], manifest)
        _publish(staged, outputs, manifest)
        return {name: str(path) for name, path in outputs.items()}


__all__ = ["ExportInputError", "export"]
