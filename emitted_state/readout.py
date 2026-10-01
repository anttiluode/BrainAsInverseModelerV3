"""Training-only standardized quadratic ridge readout for evaluation."""

import numpy as np


def _quadratic_design(features):
    x = np.asarray(features, dtype=float)
    n, d = x.shape
    cols = [np.ones(n, dtype=float)]
    cols.extend(x[:, j] for j in range(d))
    cols.extend(x[:, i] * x[:, j] for i in range(d) for j in range(i, d))
    return np.column_stack(cols)


class QuadraticReadout:
    def __init__(self, ridge_factor=0.001):
        if not np.isfinite(ridge_factor) or ridge_factor < 0:
            raise ValueError("ridge_factor must be finite and nonnegative")
        self.ridge_factor = float(ridge_factor)

    def fit(self, features, targets):
        x = np.asarray(features, dtype=float)
        y = np.asarray(targets, dtype=float)
        if x.ndim != 2 or y.ndim not in (1, 2) or x.shape[0] != y.shape[0] or x.shape[0] == 0:
            raise ValueError("features/targets must share a nonempty sample axis")
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
            raise ValueError("features and targets must be finite")
        if y.ndim == 1:
            y = y[:, None]
        self.feature_mean_ = x.mean(axis=0)
        self.feature_scale_ = x.std(axis=0)
        self.feature_scale_[self.feature_scale_ < 1e-12] = 1.0
        z = (x - self.feature_mean_) / self.feature_scale_
        design = _quadratic_design(z)
        gram = design.T @ design
        penalty = np.eye(gram.shape[0]) * (self.ridge_factor * x.shape[0])
        penalty[0, 0] = 0.0
        self.coef_ = np.linalg.solve(gram + penalty, design.T @ y)
        self.input_dim_ = x.shape[1]
        self.output_dim_ = y.shape[1]
        return self

    def predict(self, features):
        if not hasattr(self, "coef_"):
            raise RuntimeError("fit must be called before predict")
        x = np.asarray(features, dtype=float)
        if x.ndim != 2 or x.shape[1] != self.input_dim_ or not np.all(np.isfinite(x)):
            raise ValueError("features must be a finite matrix with the fitted width")
        z = (x - self.feature_mean_) / self.feature_scale_
        return _quadratic_design(z) @ self.coef_


def normalized_rmse(truth, prediction, scale):
    truth = np.asarray(truth, dtype=float)
    prediction = np.asarray(prediction, dtype=float)
    if truth.shape != prediction.shape or not np.all(np.isfinite(truth)) or not np.all(np.isfinite(prediction)):
        raise ValueError("truth and prediction must be finite arrays with matching shape")
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be finite and positive")
    return float(np.sqrt(np.mean((truth - prediction) ** 2)) / scale)
