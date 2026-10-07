"""Central configuration for the cost engine.

All paths and tunable constants live here so no other module hardcodes them.
"""
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
ARTIFACT_DIR = DATA_DIR / "artifacts"

# Pricing registry (user-editable JSON; see pricing.py)
PRICING_FILE = DATA_DIR / "pricing.json"

# Datasets
SYNTHETIC_DATASET_FILE = DATA_DIR / "synthetic_prompts.csv"
REAL_DATASET_FILE = DATA_DIR / "historical_prompts.csv"  # drop real logs here

# Trained model artifacts
PREDICTOR_FILE = ARTIFACT_DIR / "output_predictor.joblib"
METRICS_FILE = ARTIFACT_DIR / "prediction_metrics.json"

TOKENS_PER_MILLION = 1_000_000

# Prediction
RANDOM_STATE = 42
TEST_SIZE = 0.2
MIN_PREDICTED_OUTPUT_TOKENS = 1
# Fallback used only when no trained predictor exists (clearly flagged in output)
FALLBACK_OUTPUT_RATIO = 1.0  # predicted_output = ratio * input_tokens

# Forecasting
FORECAST_HORIZONS = {"7_days": 7, "30_days": 30, "90_days": 90}
MOVING_AVERAGE_WINDOW = 7
EXP_SMOOTHING_ALPHA = 0.3
MIN_HISTORY_POINTS = 3

# Recommendation
QUALITY_LEVELS = {"low": 1, "medium": 2, "high": 3}
