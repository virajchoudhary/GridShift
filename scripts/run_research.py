"""Run the locked study with bounded CPU threads and resumable artifacts."""

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from gridshift.cli import main

if __name__ == "__main__":
    main()
