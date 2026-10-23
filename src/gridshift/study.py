"""Content-addressed experiments and validation-only selections."""

import copy
import json
import platform
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf, pacf
from scipy.stats import jarque_bera

from . import baselines
from .artifacts import digest, freeze_protocol, json_bytes, log, require_freeze, write_json, software_digest
from .data import load
from .evaluation import primary_backtest
from .forecasting import ModelSpec, fit_model, rolling_forecasts, run_selection, _eligible_window, _forecast_metrics, cumulative_path_metrics


def forecast_config(config):
    study = config["study"]
    return {
        "training_window_days": study["window_days"],
        "publication_delay_slots": study["publication_delay_slots"],
        "refit_days": study["refit_days"],
        "horizon_slots": study["horizon_slots"],
        "reported_horizons": study["reported_horizons"],
        **config.get("forecast", {}),
    }


def identity(root, config):
    manifest = json.loads((Path(root) / "data/manifest.json").read_text())
    return digest(json_bytes({"data": manifest["normalized_hash"], "config": config}))[:16]


def run_dir(root, config, stage):
    return Path(root) / "artifacts/runs" / identity(root, config) / stage


def _forecast_task(args):
    root, spec, start, end, outpath, cfg = args
    series = load(root).actual
    artifacts = rolling_forecasts(series, ModelSpec.from_dict(spec), start, end, outpath, cfg, experiment_root=root)
    print(f"FORECAST {spec['name']} {start} saved={artifacts.forecasts}", flush=True)
    return str(artifacts.forecasts)


def selection(root, config):
    cfg = forecast_config(config)
    series = load(root).actual
    out = run_dir(root, config, "selection")
    if (out / "selection_summary.json").exists():
        return [ModelSpec.from_dict(x) for x in json.loads((out / "selection_summary.json").read_text())["selected"]]
    specs, ledger = run_selection(series.loc[series.index < pd.Timestamp("2025-01-01T00:00Z")], out, cfg)
    log(root, "selection", "Complete monthly comparable-group order search", "All attempts and convergence are retained", out / "selection_ledger.csv", "EXECUTED")
    return specs


def forecasts(root, config, stage):
    root = Path(root).resolve()
    out = run_dir(root, config, stage)
    store = out / "forecasts"
    cfg = forecast_config(config)
    start, end = config["study"][stage + "_start"], config["study"][stage + "_end"]
    if stage == "test":
        frozen = require_freeze(root, config)
        if frozen["protocol"]["config"] != config:
            raise ValueError("Configuration differs from frozen protocol")
        specs = [ModelSpec.from_dict(s) for s in frozen["protocol"]["family_finalists"]]
    else:
        specs = selection(root, config)
    store.mkdir(parents=True, exist_ok=True)
    tasks = []
    for i, spec in enumerate(specs):
        path = store / f"model_{i:02d}.npz"
        if not path.exists() or not path.with_suffix(".json").exists():
            tasks.append((str(root), spec.to_dict(), start, end, str(path), cfg))
    if tasks:
        with ProcessPoolExecutor(max_workers=int(cfg.get("fit_workers", 2))) as pool:
            list(pool.map(_forecast_task, tasks))
    if not (store / "calendar_mean.npz").exists():
        baselines.rolling(load(root).actual, start, end, store, cfg, experiment_root=root)
    mapping = {spec.name: str(store / f"model_{i:02d}.npz") for i, spec in enumerate(specs)}
    mapping.update({name: str(store / f"{name}.npz") for name in baselines.BASELINES})
    metrics = []
    for name, path in mapping.items():
        table = pd.read_csv(Path(path).with_suffix(".metrics.csv"))
        table["model_id"] = name
        metrics.append(table)
    table = pd.concat(metrics, ignore_index=True)
    table.to_csv(out / "forecast_metrics.csv", index=False)
    write_json(out / "forecast_store.json", {name: Path(filename).relative_to(root).as_posix() for name, filename in mapping.items()})
    common = None
    for filename in mapping.values():
        with np.load(filename) as arrays:
            valid = ~arrays["fallback"]
            common = valid.copy() if common is None else common & valid
    common_tables = []
    truth = load(root).actual
    for name, filename in mapping.items():
        with np.load(filename) as arrays:
            mean = arrays["mean"].astype(float)
            mean[~common] = np.nan
            origins = pd.to_datetime(arrays["origins_ns"], utc=True)
            metric = _forecast_metrics(
                truth, origins, mean, arrays["std"],
                *(arrays[key] for key in ("lower80", "upper80", "lower95", "upper95")),
                arrays["fallback"], cfg,
            )
            metric["model_id"] = name
            metric["common_valid_origins"] = int(common.sum())
            common_tables.append(metric)
    common_table = pd.concat(common_tables, ignore_index=True)
    common_table.to_csv(out / "forecast_common_metrics.csv", index=False)
    path_tables = []
    for name, filename in mapping.items():
        with np.load(filename) as arrays:
            origins = pd.to_datetime(arrays["origins_ns"], utc=True)
            for comparison, mask in (("end_to_end", None), ("common_no_fallback", common)):
                metric = cumulative_path_metrics(truth, origins, arrays["mean"], cfg["reported_horizons"], mask)
                metric["model_id"], metric["comparison"] = name, comparison
                path_tables.append(metric)
    pd.concat(path_tables, ignore_index=True).to_csv(out / "forecast_path_metrics.csv", index=False)
    if stage == "validation":
        scores = common_table.loc[common_table.group == "all"].groupby("model_id").mae.mean()
        finalists = []
        for family in ("AR", "MA", "ARMA", "ARIMA", "SARIMA"):
            members = [s for s in specs if s.family == family]
            if not members:
                raise ValueError(f"Required family {family} has no eligible converged candidate")
            best = min(scores[s.name] for s in members)
            tied = [s for s in members if scores[s.name] <= best * 1.01]
            finalists.append(min(tied, key=lambda s: (sum(s.order[::2]) + sum(s.seasonal_order[:3]), s.transform != "identity", s.name)))
        best = scores.min()
        tied = [n for n in scores.index if scores[n] <= best * 1.01]
        spec_by_name = {spec.name: spec for spec in specs}
        def complexity(name):
            if name in baselines.BASELINES:
                return (0, baselines.BASELINES.index(name), 0, name)
            spec = spec_by_name[name]
            return (1, sum(spec.order[::2]) + sum(spec.seasonal_order[:3]), spec.transform != "identity", name)
        champion = min(tied, key=complexity)
        simple_scores = scores.loc[list(baselines.BASELINES)]
        simple = min(simple_scores.index[simple_scores <= simple_scores.min() * 1.01], key=complexity)
        write_json(out / "validation_choices.json", {
            "family_finalists": [s.to_dict() for s in finalists], "forecast_champion": champion,
            "best_classical": min([s.name for s in finalists], key=lambda n: (scores[n], complexity(n))),
            "strongest_simple": simple, "validation_mean_horizon_mae": scores.to_dict(),
        })
    return mapping


def backtest(root, config, stage):
    out = run_dir(root, config, stage)
    mapping = json.loads((out / "forecast_store.json").read_text())
    choices = json.loads((run_dir(root, config, "validation") / "validation_choices.json").read_text())
    names = [s["name"] for s in choices["family_finalists"]] + list(baselines.BASELINES)
    files = {name: Path(root) / mapping[name] for name in names}
    cfg = copy.deepcopy(config)
    cfg["scheduling"]["model_complexity"] = {
        value["name"]: sum(value["order"][::2]) + value["seasonal_order"][0]
        + value["seasonal_order"][2] + 1
        + int(not value["order"][1] and not value["seasonal_order"][1])
        for value in choices["family_finalists"]
    }
    cfg["scheduling"]["simple_model_ids"] = list(baselines.BASELINES)
    if stage == "test":
        frozen = require_freeze(root, config)
        cfg["scheduling"]["selected_model_id"] = frozen["protocol"]["deployment_model"]
        cfg["scheduling"]["selection_metadata"] = frozen["protocol"]["scheduling_selection"]
    result = primary_backtest(
        load(root).actual, files, config["study"][stage + "_start"],
        config["study"][stage + "_end"], out / "single_job", cfg,
        experiment_root=root,
    )
    if stage == "validation":
        choices["deployment_model"] = result["selected_model"]
        choices["scheduling_selection"] = {
            "validation_common_jobs": result["validation_common_jobs"],
            "selection_basis": result["selection_basis"],
        }
        write_json(out / "validation_choices.json", choices)
        pairs = result["pairs"]
        selected_pairs = pairs.loc[
            (pairs.scenario_id == "duration_2h_slack_10h")
            & (pairs.policy == "forecast") & (pairs.model_id == result["selected_model"])
        ].copy()
        daily = selected_pairs.set_index("release").resample("1D")[["baseline_grams", "policy_grams"]].sum()
        difference = daily.baseline_grams - daily.policy_grams
        pd.DataFrame({"lag_days": np.arange(29), "acf_daily_paired_savings": acf(difference, nlags=28)}).to_csv(
            out / "single_job/daily_loss_dependence.csv", index=False,
        )
    write_json(out / "single_job/completion.json", {"completed": True, "selected": result["selected_model"]})
    return result


def freeze(root, config):
    import xml.etree.ElementTree as ET
    import shutil
    out = run_dir(root, config, "validation")
    choices = json.loads((out / "validation_choices.json").read_text())
    if not (out / "single_job/completion.json").exists() or not choices.get("deployment_model"):
        raise ValueError("Validation scheduling must complete before freeze")
    core = Path(root) / "artifacts/tests/core.xml"
    if not core.exists():
        raise ValueError("Core tests are required before freeze")
    suites = ET.parse(core).getroot().findall(".//testsuite")
    if not suites or any(int(s.get("failures", 0)) or int(s.get("errors", 0)) for s in suites):
        raise ValueError("Failing core tests block protocol freeze")
    receipt_path = Path(root) / "artifacts/tests/core_receipt.json"
    if not receipt_path.exists():
        raise ValueError("Run scripts/test_project.py to bind tests to the current source")
    receipt = json.loads(receipt_path.read_text())
    if (
        receipt.get("passed") is not True
        or receipt.get("software_hash") != software_digest(root)
        or receipt.get("junit_sha256") != digest(core.read_bytes())
    ):
        raise ValueError("Passing test receipt is incompatible with current source or JUnit bytes")
    snapshot = Path(root) / "artifacts/pretest_tests"
    snapshot.mkdir(parents=True, exist_ok=True)
    for source in (core, receipt_path):
        destination = snapshot / source.name
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise ValueError("Pretest evidence snapshot already exists with different bytes")
        shutil.copy2(source, destination)
    if not (out / "queue/completion.json").exists():
        raise ValueError("Validation queue replay must complete before freeze")
    if not (out / "residuals/ljung_box.csv").exists():
        raise ValueError("Residual diagnostics must complete before freeze")
    if not (Path(root) / "artifacts/sensitivities/completion.json").exists():
        raise ValueError("Declared bounded sensitivities must complete before freeze")
    protocol = {
        "config": config, **choices,
        "study_id": identity(root, config),
        "software_hash": software_hash(root),
        "software_scope": "Scientific modules including live joint-path uncertainty, analysis, sensitivities, results, CLI, and scripts/run_research.py",
        "validation_artifact_hashes": {
            p.relative_to(root).as_posix(): digest(p.read_bytes())
            for directory in (
                out, run_dir(root, config, "selection"),
                Path(root) / "artifacts/diagnostics", Path(root) / "artifacts/data",
                Path(root) / "artifacts/sensitivities", Path(root) / "data/raw",
                Path(root) / "specifications",
                snapshot,
            )
            for p in sorted(directory.rglob("*")) if p.is_file()
        },
        "pretest_evidence_scope": "Validation, selection, development diagnostics, source audit, sensitivities, raw source snapshots, and byte-identical specification copies",
        "protocol_amendments_hash": digest((Path(root) / "PROTOCOL_AMENDMENTS.md").read_bytes()),
        "sources": ["specifications/GRIDSHIFT_PROJECT_PLAN.md", "specifications/GRIDSHIFT_SOURCE_AUDIT.md"],
        "accounting": "Modeled intensity-weighted operational CO2, not actual avoided emissions",
        "primary_contrast": "default isolated selected schedule versus earliest feasible",
        "queue_inference": "Completion intersection descriptive when accepted sets differ",
        "secondary_intervals": "Descriptive; no family-wise significance claims",
    }
    protocol["validation_artifact_hashes"].update({
        relative: digest((Path(root) / relative).read_bytes())
        for relative in ("data/manifest.json", "configs/study.yaml", "pyproject.toml", "uv.lock")
    })
    return freeze_protocol(root, protocol)


def software_hash(root):
    return software_digest(root)


def residuals(root, config):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from statsmodels.graphics.gofplots import qqplot
    out = run_dir(root, config, "validation")
    choices = json.loads((out / "validation_choices.json").read_text())
    dest = out / "residuals"
    dest.mkdir(exist_ok=True)
    series = load(root).actual
    cfg = forecast_config(config)
    ledger = pd.read_csv(run_dir(root, config, "selection") / "selection_ledger.csv")
    rows = []
    distribution_rows = []
    for i, value in enumerate(choices["family_finalists"]):
        spec = ModelSpec.from_dict(value)
        anchors = ledger.loc[(ledger.name == spec.name) & ledger.converged, "anchor"]
        anchor = pd.Timestamp(anchors.sort_values().iloc[-1])
        history, start, cutoff = _eligible_window(series, anchor, cfg)
        fit = fit_model(history, spec, cfg, training_start=start, training_cutoff=cutoff)
        if not fit.result.mle_retvals["converged"]:
            raise ValueError("Representative residual fit did not converge")
        residual = pd.Series(fit.result.filter_results.standardized_forecasts_error[0][cfg["loglikelihood_burn"]:])
        valid = history.notna().to_numpy()[cfg["loglikelihood_burn"]:]
        residual.loc[~valid] = np.nan
        residual.to_csv(dest / f"model_{i:02d}_innovations.csv", index=False)
        # Use a contiguous observed innovation segment, never compress outages.
        segment_id = residual.isna().cumsum()
        segments = [v.dropna() for _, v in residual.groupby(segment_id)]
        longest = max(segments, key=len)
        lb = acorr_ljungbox(longest, lags=[12, 48, 96], model_df=sum(spec.order[::2]) + spec.seasonal_order[0] + spec.seasonal_order[2])
        lb["model_id"] = spec.name
        lb["n_contiguous"] = len(longest)
        rows.append(lb.reset_index(names="lag"))
        jb = jarque_bera(longest)
        distribution_rows.append({"model_id": spec.name, "n": len(longest), "jarque_bera": float(jb.statistic),
                                  "normality_p_value": float(jb.pvalue), "mean": float(longest.mean()),
                                  "variance": float(longest.var()), "skew": float(longest.skew()),
                                  "excess_kurtosis": float(longest.kurtosis())})
        pd.DataFrame({"lag": np.arange(97), "acf": acf(longest, nlags=96), "pacf": pacf(longest, nlags=96, method="ywm")}).to_csv(dest / f"model_{i:02d}_acf_pacf.csv", index=False)
        write_json(dest / f"model_{i:02d}_parameters.json", {"spec": value, "parameter_names": fit.result.param_names, "parameters": fit.result.params.tolist(), "training_cutoff": str(cutoff)})
        from .domain import Job
        from .live import joint_job_costs
        job = Job("conditional_uncertainty_example", anchor, 2, anchor + pd.Timedelta(hours=12))
        uncertainty = joint_job_costs(fit, job, anchor, simulations=1000, seed=config["study"]["seed"])
        write_json(dest / f"model_{i:02d}_job_uncertainty.json", {
            **uncertainty, "model_id": spec.name, "origin": str(anchor),
            "chosen_start": str(anchor), "duration_hours": 2, "energy_kwh": float(job.energy_kwh.sum()),
            "scope": "Representative validation conditional joint-path example; not calibrated job-cost coverage",
        })
        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        axes[0, 0].plot(longest.to_numpy(), linewidth=.6)
        axes[0, 0].set_title("Standardized one-step innovations")
        axes[0, 1].hist(longest, bins=40, color="#168577")
        axes[0, 1].set_title("Innovation distribution")
        axes[1, 0].stem(np.arange(97), acf(longest, nlags=96))
        axes[1, 0].set_title("Innovation ACF")
        qqplot(longest, line="s", ax=axes[1, 1])
        fig.suptitle(spec.name)
        fig.tight_layout()
        fig.savefig(dest / f"model_{i:02d}_diagnostics.png", dpi=130)
        plt.close(fig)
    pd.concat(rows).to_csv(dest / "ljung_box.csv", index=False)
    pd.DataFrame(distribution_rows).to_csv(dest / "innovation_distribution.csv", index=False)
