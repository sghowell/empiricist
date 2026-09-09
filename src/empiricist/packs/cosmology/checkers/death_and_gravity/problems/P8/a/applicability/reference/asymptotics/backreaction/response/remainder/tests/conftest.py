import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for ancestor in (ROOT, *list(ROOT.parents)[:6]):
    sys.path.insert(0, str(ancestor/"src"))
