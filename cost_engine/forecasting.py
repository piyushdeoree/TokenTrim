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
import math
from decimal import Decimal, InvalidOperation

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
        if isinstance(val, bool) or val is None or not isinstance(val, (int, float, Decimal)):
            raise TypeError(f"Invalid cost value: {item!r}")
        if isinstance(val, Decimal):
            if not val.is_finite(): raise ValueError("Cost values must be finite")
            if val < 0: raise ValueError("Cost values must be >= 0")
        else:
            if not math.isfinite(val): raise ValueError("Cost values must be finite")
            if val < 0: raise ValueError("Cost values must be >= 0")
        try: converted = float(val)
        except (OverflowError, ValueError): raise ValueError("Cost value exceeds forecasting numeric range") from None
        if not math.isfinite(converted): raise ValueError("Cost value exceeds forecasting numeric range")
        out.append(converted)
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
    *, periods: Optional[int] = None,
) -> dict:
    """Forecast future spend from a daily cost series.

    ``historical_cost``: list of floats, ``(date, cost)`` tuples, or
    ``{"date":..., "cost":...}`` dicts, ordered oldest to newest, one per day.
    ``forecast_period``: one of config.FORECAST_HORIZONS.
    """
    if forecast_period not in config.FORECAST_HORIZONS:
        raise ValueError(f"forecast_period must be one of {list(config.FORECAST_HORIZONS)}")
    steps = config.FORECAST_HORIZONS[forecast_period] if periods is None else periods
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("periods must be a positive integer")
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
    if not np.isfinite(fc).all():
        raise ValueError("forecast values exceeded the supported finite numeric range")
    residual = (backtest["scores"][method]["MAE"] if backtest else float(np.std(y)))
    if not math.isfinite(residual):
        raise ValueError("forecast uncertainty exceeded the supported finite numeric range")
    future_total = float(fc.sum())
    if not math.isfinite(future_total):
        raise ValueError("estimated future cost exceeded the supported finite numeric range")
    lower = [float(max(0, v-residual*1.96)) for v in fc]
    upper = [float(v+residual*1.96) for v in fc]
    if not all(math.isfinite(value) for value in (*lower, *upper)):
        raise ValueError("forecast range exceeded the supported finite numeric range")
    return {
        "historical_cost": series,
        "forecast": [float(v) for v in fc],
        "forecast_period": forecast_period if periods is None else f"{steps}_periods",
        "forecast_steps": steps,
        "estimated_future_cost": future_total,
        "forecast_range": {"lower": lower, "upper": upper},
        "method": method,
        "backtest": backtest,
        "notes": notes,
        "disclaimer": "Statistical projection of past spend, not a guaranteed budget.",
        "assumptions": {"frequency":"daily","uncertainty":"1.96 x holdout MAE" if backtest else "1.96 x historical standard deviation","historical_values_are_actuals":True},
    }


def aggregate_usage_costs(records, frequency="daily", *, group_by: Optional[str] = None):
    """Aggregate dated actual usage costs, filling absent periods with zero.

    ``group_by`` may be ``model`` or ``provider`` and returns a group key on
    every row. Costs are accumulated as Decimal and converted at the API edge.
    """
    from datetime import date, datetime, timedelta
    if frequency not in {"daily", "weekly", "monthly"}:
        raise ValueError("frequency must be daily, weekly, or monthly")
    if group_by not in {None, "model", "provider"}:
        raise ValueError("group_by must be model, provider, or None")
    buckets = {}
    observed = []

    def period_key(day):
        if frequency == "daily": return day.isoformat()
        if frequency == "weekly": return day.fromordinal(day.toordinal() - day.weekday()).isoformat()
        return f"{day.year:04d}-{day.month:02d}"

    for index, row in enumerate(records):
        if not isinstance(row, dict): raise TypeError(f"record {index} must be a mapping")
        stamp = row.get("date") or row.get("created_at")
        if not stamp: raise ValueError(f"record {index} needs date or created_at")
        try:
            day = date.fromisoformat(stamp[:10]) if isinstance(stamp, str) else (stamp.date() if isinstance(stamp, datetime) else stamp)
            if not isinstance(day, date): raise TypeError
        except (ValueError, TypeError, AttributeError):
            raise ValueError(f"record {index} has an invalid date") from None
        try:
            amount = Decimal(str(row.get("cost")))
        except (InvalidOperation, TypeError):
            raise ValueError(f"record {index} has an invalid cost") from None
        if not amount.is_finite() or amount < 0:
            raise ValueError(f"record {index} cost must be finite and non-negative")
        group = row.get(group_by) if group_by else None
        if group_by and (not isinstance(group, str) or not group.strip()):
            raise ValueError(f"record {index} needs a non-empty {group_by}")
        key = period_key(day)
        bucket_key = (key, group)
        buckets[bucket_key] = buckets.get(bucket_key, Decimal(0)) + amount
        observed.append(day)

    if not observed:
        return []
    if frequency == "daily":
        start, end = min(observed), max(observed)
        day = start
        period_keys = []
        while day <= end:
            period_keys.append(period_key(day))
            day += timedelta(days=1)
    elif frequency == "weekly":
        start = min(observed) - timedelta(days=min(observed).weekday())
        end = max(observed) - timedelta(days=max(observed).weekday())
        period_keys = []
        while start <= end:
            period_keys.append(period_key(start))
            start += timedelta(days=7)
    else:
        start = min(observed).replace(day=1)
        end = max(observed).replace(day=1)
        period_keys = []
        while start <= end:
            period_keys.append(period_key(start))
            start = start.replace(year=start.year + (start.month == 12), month=1 if start.month == 12 else start.month + 1)
    groups = sorted({group for _, group in buckets}) if group_by else [None]
    result = []
    for group in groups:
        for key in period_keys:
            try: number = float(buckets.get((key, group), Decimal(0)))
            except (OverflowError, ValueError): raise ValueError("aggregated cost exceeds forecasting numeric range") from None
            if not math.isfinite(number): raise ValueError("aggregated cost exceeds forecasting numeric range")
            item = {"period": key, "cost": number}
            if group_by: item[group_by] = group
            result.append(item)
    return result


def forecast_usage_costs(records, *, frequency="daily", periods=1, method="auto", group_by=None):
    """Project the next daily, weekly, or monthly periods from actual usage rows."""
    if frequency not in {"daily", "weekly", "monthly"}:
        raise ValueError("frequency must be daily, weekly, or monthly")
    grouped = aggregate_usage_costs(records, frequency=frequency, group_by=group_by)
    groups = sorted({row.get(group_by) for row in grouped}) if group_by else [None]
    projections = []
    for group in groups:
        values = [row["cost"] for row in grouped if not group_by or row[group_by] == group]
        forecast = forecast_cost(values, "30_days", method, periods=periods)
        projections.append({"group": group, "frequency": frequency, **forecast})
    return projections if group_by else projections[0]
