# Forecasting Methodology

Code: `cost_engine/forecasting.py`.

## Input and output

Input: ordered daily cost series (floats, `(date, cost)` tuples, or `{date, cost}` dicts). Horizons: 7, 30 and 90 days. Output: `historical_cost`, `forecast`, `forecast_period`, `estimated_future_cost` (sum of the forecast), plus the chosen `method` and `backtest` scores.

## Methods

| Method | Forecast shape | Why included |
|---|---|---|
| Moving average (window 7) | flat | simplest, robust to noise |
| Simple exponential smoothing (alpha 0.3) | flat | weights recent days more |
| Linear regression on time index | straight line | captures steady growth/decline |

Forecasts are clipped at zero.

## Selection

For `method="auto"`, the last `min(horizon, n/4)` points are held out; each method is fit on the earlier points and scored by MAE and RMSE. The best MAE wins, but a simpler method is preferred if its MAE is within 5% of the best (order: moving average, exponential smoothing, linear regression). With too little history (fewer than 3 training points after holdout) it defaults to moving average and says so in `notes`.

## Limitations

- No seasonality (e.g. weekday/weekend) or event modelling.
- Flat methods cannot represent trends; linear extrapolation over 90 days can drift far from reality.
- One short holdout window is a weak basis for selection; treat the choice as indicative.
- No uncertainty intervals yet.
- The tests use constructed series only; no real spend history has been evaluated. Report real backtest scores once historical data is available.
