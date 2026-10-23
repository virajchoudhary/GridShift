"""Run official backtests only after checking all forecast information boundaries."""

import argparse
from pathlib import Path

import yaml

from gridshift.artifacts import write_json
from gridshift.replay import queue_backtest
from gridshift.study import backtest
from gridshift.verification import forecast_preflight


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["validation", "test"], default="test")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / "configs/study.yaml").read_text())
    receipt = forecast_preflight(root, config, args.stage)
    write_json(root / f"artifacts/tests/forecast_preflight_{args.stage}.json", receipt)
    backtest(root, config, args.stage)
    queue_backtest(root, config, args.stage)
    print(receipt)


if __name__ == "__main__":
    main()
