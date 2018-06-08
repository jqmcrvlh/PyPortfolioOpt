"""
The ``risk_models`` module provides functions for estimating the covariance matrix given
historical returns. Because of the complexity of estimating covariance matrices
(and the importance of efficient computations), this module mostly provides a convenient
wrapper around the underrated `sklearn.covariance` module.

The format of the data input is the same as that in :ref:`expected-returns`.

**Currently implemented:**

- sample covariance
- mininum covariance determinant
- Shrunk covariance matrices:

    - manual shrinkage
    - Ledoit Wolf Shrinkage
    - Oracle Approximating Shrinkage
"""

import warnings
import numpy as np
import pandas as pd
from sklearn import covariance


def sample_cov(prices, frequency=252):
    """
    Calculate the annualised sample covariance matrix of (daily) asset returns.

    :param prices: adjusted closing prices of the asset, each row is a date
                   and each column is a ticker/id.
    :type prices: pd.DataFrame
    :param frequency: number of time periods in a year, defaults to 252 (the number
                      of trading days in a year)
    :type frequency: int, optional
    :return: annualised sample covariance matrix
    :rtype: pd.DataFrame
    """
    if not isinstance(prices, pd.DataFrame):
        warnings.warn("prices are not in a dataframe", RuntimeWarning)
        prices = pd.DataFrame(prices)
    daily_returns = prices.pct_change().dropna(how="all")
    return daily_returns.cov() * frequency


def min_cov_determinant(prices, frequency=252, random_state=None):
    """
    Calculate the minimum covariance determinant, an estimator of the covariance matrix
    that is more robust to noise.

    :param prices: adjusted closing prices of the asset, each row is a date
                   and each column is a ticker/id.
    :type prices: pd.DataFrame
    :param frequency: number of time periods in a year, defaults to 252 (the number
                      of trading days in a year)
    :type frequency: int, optional
    :param random_state: random seed to make results reproducible, defaults to None
    :type random_state: int, optional
    :return: annualised estimate of covariance matrix
    :rtype: pd.DataFrame
    """
    if not isinstance(prices, pd.DataFrame):
        warnings.warn("prices are not in a dataframe", RuntimeWarning)
        prices = pd.DataFrame(prices)
    assets = prices.columns
    X = prices.pct_change().dropna(how="all")
    X = np.nan_to_num(X.values)
    raw_cov_array = covariance.fast_mcd(X, random_state=random_state)[1]
    return pd.DataFrame(raw_cov_array, index=assets, columns=assets) * frequency


class CovarianceShrinkage:
    """
    Provide methods for computing shrinkage estimates of the covariance matrix, using the
    sample covariance matrix and choosing the structured estimator to be an identity matrix
    multiplied by the average sample variance. The shrinkage constant can be input manually,
    though there exist methods (notably Ledoit Wolf) to estimate the optimal value.

    Instance variables:

    - ``X`` (returns)
    - ``S`` (sample covariance matrix)
    - ``delta`` (shrinkage constant)
    """

    def __init__(self, prices, frequency=252):
        """
        :param prices: adjusted closing prices of the asset, each row is a date and each column is a ticker/id.
        :type prices: pd.DataFrame
        :param frequency: number of time periods in a year, defaults to 252 (the number of trading days in a year)
        :type frequency: int, optional
        """
        if not isinstance(prices, pd.DataFrame):
            warnings.warn("prices are not in a dataframe", RuntimeWarning)
            prices = pd.DataFrame(prices)
        self.frequency = frequency
        self.X = prices.pct_change().dropna(how="all")
        self.S = self.X.cov().values
        self.delta = None  # shrinkage constant

    def format_and_annualise(self, raw_cov_array):
        """
        Helper method which annualises the output of shrinkage calculations,
        and formats the result into a dataframe

        :param raw_cov_array: raw covariance matrix of daily returns
        :type raw_cov_array: np.ndarray
        :return: annualised covariance matrix
        :rtype: pd.DataFrame
        """
        assets = self.X.columns
        return (
            pd.DataFrame(raw_cov_array, index=assets, columns=assets) * self.frequency
        )

    def shrunk_covariance(self, delta=0.2):
        """
        Shrink a sample covariance matrix to the identity matrix (scaled by the average
        sample variance). This method does not estimate an optimal shrinkage parameter,
        it requires manual input.

        :param delta: shrinkage parameter, defaults to 0.2.
        :type delta: float, optional
        :return: shrunk sample covariance matrix
        :rtype: np.ndarray
        """
        self.delta = delta
        N = self.S.shape[1]
        # Shrinkage target
        mu = np.trace(self.S) / N
        F = np.identity(N) * mu
        # Shrinkage
        shrunk_cov = delta * F + (1 - delta) * self.S
        return self.format_and_annualise(shrunk_cov)

    def ledoit_wolf(self):
        """
        Calculate the Ledoit-Wolf shrinkage estimate.
        
        :return: shrunk sample covariance matrix
        :rtype: np.ndarray
        """
        X = np.nan_to_num(self.X.values)
        shrunk_cov, self.delta = covariance.ledoit_wolf(X)
        return self.format_and_annualise(shrunk_cov)

    def oracle_approximating(self):
        """
        Calculate the Oracle Approximating Shrinkage estimate

        :return: shrunk sample covariance matrix
        :rtype: np.ndarray
        """
        X = np.nan_to_num(self.X.values)
        shrunk_cov, self.delta = covariance.oas(X)
        return self.format_and_annualise(shrunk_cov)
