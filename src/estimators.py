"""Simple estimators used as stage-appropriate educational benchmarks."""
import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils.validation import check_array, check_is_fitted


class LatestGradeRegressor(RegressorMixin, BaseEstimator):
    """Return the (imputed) latest observed period grade, without fitting G3."""
    def fit(self, X, y=None):
        values = check_array(X)
        if values.shape[1] != 1:
            raise ValueError('Latest-grade baseline requires one G2 column.')
        self.n_features_in_ = 1
        return self

    def predict(self, X):
        check_is_fitted(self)
        values = check_array(X)
        if values.shape[1] != 1:
            raise ValueError('Latest-grade baseline requires one G2 column.')
        return values[:, 0]
