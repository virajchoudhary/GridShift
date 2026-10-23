"""GridShift commands. Scientific choices use validation artifacts only."""

import argparse
import json
from pathlib import Path

import yaml

from . import data, study
from .analysis import diagnose


def main():
    parser = argparse.ArgumentParser(prog="gridshift")
    parser.add_argument("command", choices=["collect", "audit", "diagnose", "select", "study", "backtest", "residuals", "sensitivities", "freeze", "queue", "certify", "export", "verify"])
    parser.add_argument("--config", default="configs/study.yaml")
    parser.add_argument("--root", default=".")
    parser.add_argument("--stage", choices=["validation", "test"], default="validation")
    parser.add_argument("--manifest")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    config = yaml.safe_load((root / args.config).read_text())
    command = args.command
    if command == "collect":
        data.collect(root, config["data"]["start"], config["data"]["end"], config["data"]["chunk_days"])
    elif command == "audit":
        print(json.dumps(data.audit(root), indent=2))
    elif command == "diagnose":
        import pandas as pd
        ledger = root / "artifacts/data/source_missingness.csv"
        if not ledger.is_file():
            data.verify_raw(root)
        print(diagnose(data.load(root).actual, root / "artifacts/diagnostics", pd.read_csv(ledger)))
    elif command == "select":
        study.selection(root, config)
    elif command == "study":
        study.forecasts(root, config, args.stage)
    elif command == "backtest":
        study.backtest(root, config, args.stage)
    elif command == "residuals":
        study.residuals(root, config)
    elif command == "freeze":
        print(study.freeze(root, config))
    elif command == "sensitivities":
        from .sensitivities import run
        run(root, config)
    elif command == "queue":
        from .replay import queue_backtest
        queue_backtest(root, config, args.stage)
    elif command == "export":
        from .results import certify
        from .live import build_deployment
        from .exports import export
        certify(root, config)
        build_deployment(root, config)
        export(root, config)
    elif command == "certify":
        from .results import certify
        print(certify(root, config)["headline"])
    elif command == "verify":
        from .verification import verify
        print(verify(root, config))


if __name__ == "__main__":
    main()
