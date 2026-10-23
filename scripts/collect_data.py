from pathlib import Path
from gridshift.data import collect

if __name__ == "__main__":
    collect(Path(__file__).resolve().parents[1])
