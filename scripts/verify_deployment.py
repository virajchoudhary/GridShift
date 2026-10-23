"""Verify trusted inference offline, with an optional current official-data probe."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from gridshift.artifacts import digest, json_bytes, write_json
from gridshift.domain import Job
from gridshift.live import fetch_recent, predict_live, verify_deployment_fixture
from gridshift.scheduling import recommend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs/study.yaml").read_text())
    receipt = {"fixture": verify_deployment_fixture(root, config), "network_requested": args.network}
    if args.network:
        origin = pd.Timestamp.now(tz="UTC").floor("30min")
        observations = fetch_recent(origin)
        forecast, state = predict_live(root, config, observations, origin)
        assert np.isfinite(forecast.mean).all()
        job = Job("live_verification", origin, 2, origin + pd.Timedelta(hours=12))
        decision = recommend(job, forecast)
        assert decision.status == "scheduled" and decision.finish <= job.deadline
        receipt["current_prediction"] = {
            "origin": str(origin), "model_id": forecast.model_id,
            "observations_sha256": digest(json_bytes(observations.to_json(date_format="iso"))),
            "observed_slots": int(observations.notna().sum()), "observation_state": state,
            "start": str(decision.start), "finish": str(decision.finish),
            "predicted_grams": decision.predicted_grams,
            "scope": "Current official observations and conditional prediction; no realized saving scored",
        }
    receipt["passed"] = True
    receipt["actual_avoided_emissions_verified"] = False
    write_json(root / "artifacts/tests/deployment_runtime.json", receipt)
    print(receipt)


if __name__ == "__main__":
    main()
