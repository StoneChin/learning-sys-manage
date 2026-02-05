#!/bin/bash
cd "$(dirname "$0")/.."
cd backend
python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
