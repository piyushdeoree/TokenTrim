"""Cost forecasting.

Three simple, explainable methods are backtested on the tail of the history
and the best is chosen by MAE, preferring the simpler method when scores are
within ``SIMPLICITY_TOLERANCE``:

  moving_average        flat forecast = mean of the last N points
  exponential_smoothing flat forecast = smoothed level (simple ES)
  linear_regression     straight-line trend fit on all history

Moving-average and ES forecasts are flat by construction; only the linear
method extrapolates a trend. Forecasts are statistical projections, not
budgets or guarantees.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Union

import numpy as np

from . import config

SIMPLICITY_TOLERANCE = 0.05  # within 5% of best MAE -> prefer simpler method
_METHOD_ORDER = ["moving_average", "exponential_smoothing", "linear_regression"]  # simplest first


def _to_series(historical_cost: Sequence[Union[float, dict, tuple]]) -> List[float]:
    out = []
    for item in historical_cost:
        if isinstance(item, dict):
            val = item.get("cost")
        elif isinstance(item, (tuple, list)):
            val = item[-1]
        else:
            val = item
        if isinstance(val, bool) or val is None or not isinstance(val, (int, float)):
            raise TypeError(f"Invalid cost value: {item!r}")
        if val != val or val in (float("inf"), float("-inf")):
            raise ValueError("Cost values must be finite")
        if val < 0:
            raise ValueError("Cost values must be >= 0")
        out.append(float(val))
    return out


def _moving_average(y: np.ndarray, steps: int) -> np.ndarray:
    w = min(config.MOVING_AVERAGE_WINDOW, len(y))
    return np.full(steps, y[-w:].mean())


def _exp_smoothing(y: np.ndarray, steps: int) -> np.ndarray:
    a = config.EXP_SMOOTHING_ALPHA
    level = y[0]
    for v in y[1:]:
        level = a * v + (1 - a) * level
    return np.full(steps, level)


def _linear(y: np.ndarray, steps: int) -> np.ndarray:
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1) if len(y) > 1 else (0.0, y[0])
    future_x = np.arange(len(y), len(y) + steps)
    return slope * future_x + intercept


_METHODS = {
    "moving_average": _moving_average,
    "exponential_smoothing": _exp_smoothing,
    "linear_regression": _linear,
}


def _backtest(y: np.ndarray, horizon: int) -> Optional[dict]:
    holdout = max(1, min(horizon, len(y) // 4))
    if len(y) - holdout < config.MIN_HISTORY_POINTS:
        return None
    train, test = y[:-holdout], y[-holdout:]
    scores = {}
    for name, fn in _METHODS.items():
        pred = np.clip(fn(train, holdout), 0, None)
        scores[name] = {
            "MAE": float(np.mean(np.abs(test - pred))),
            "RMSE": float(np.sqrt(np.mean((test - pred) ** 2))),
        }
    return {"holdout_points": holdout, "scores": scores}


def _choose(scores: dict) -> str:
    best_mae = min(s["MAE"] for s in scores.values())
    for name in _METHOD_ORDER:
        if scores[name]["MAE"] <= best_mae * (1 + SIMPLICITY_TOLERANCE) + 1e-12:
            return name
    return _METHOD_ORDER[0]


def forecast_cost(
    historical_cost: Sequence[Union[float, dict, tuple]],
    forecast_period: str = "30_days",
    method: str = "auto",
) -> dict:
    """Forecast future spend from a daily cost series.

    ``historical_cost``: list of floats, ``(date, cost)`` tuples, or
    ``{"date":..., "cost":...}`` dicts, ordered oldest to newest, one per day.
    ``forecast_period``: one of config.FORECAST_HORIZONS.
    """
    if forecast_period not in config.FORECAST_HORIZONS:
        raise ValueError(f"forecast_period must be one of {list(config.FORECAST_HORIZONS)}")
    steps = config.FORECAST_HORIZONS[forecast_period]
    series = _to_series(historical_cost)
    if len(series) < config.MIN_HISTORY_POINTS:
        raise ValueError(
            f"Need at least {config.MIN_HISTORY_POINTS} historical points, got {len(series)}"
        )
    y = np.array(series)

    backtest = _backtest(y, steps)
    notes = []
    if method == "auto":
        if backtest:
            method = _choose(backtest["scores"])
        else:
            method = "moving_average"
            notes.append("History too short to backtest; defaulted to moving_average.")
    elif method not in _METHODS:
        raise ValueError(f"method must be 'auto' or one of {list(_METHODS)}")

    fc = np.clip(_METHODS[method](y, steps), 0, None)
    return {
        "historical_cost": series,
        "forecast": [float(v) for v in fc],
        "forecast_period": forecast_period,
        "estimated_future_cost": float(fc.sum()),
        "method": method,
        "backtest": backtest,
        "notes": notes,
        "disclaimer": "Statistical projection of past spend, not a guaranteed budget.",
    }
