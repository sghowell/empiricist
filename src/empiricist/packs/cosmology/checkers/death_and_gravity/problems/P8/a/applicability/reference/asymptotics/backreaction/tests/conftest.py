import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for ancestor in (ROOT, ROOT.parent, ROOT.parent.parent, ROOT.parent.parent.parent,
                 ROOT.parent.parent.parent.parent):
    sys.path.insert(0, str(ancestor/"src"))
