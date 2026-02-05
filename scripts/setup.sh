#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "Creating conda environment learning-sys..."
conda create -n learning-sys python=3.10 -y 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate learning-sys
echo "Installing Python dependencies..."
pip install -r requirements.txt -q
echo "Initializing database..."
cd backend && python init_db.py && cd ..
echo "Installing frontend dependencies..."
npm install
echo "Setup complete. Run: npm run dev (frontend) and uvicorn main:app --reload --port 8000 (from backend/)"
