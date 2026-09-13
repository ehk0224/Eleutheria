"""
Option pricing with Black-Scholes and a Cox-Ross-Rubinstein tree.

Black-Scholes prices European options. 
The binomial tree prices both European and American options 
and is also used for American implied volatility.
All rates, dividend yields, and volatility inputs are annualized decimals.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, replace
from a_option import Option



def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _intrinsic(option: Option, spot: float | None = None) -> float:
    price = option.spot if spot is None else spot
    if option.option_type == "call":
        return max(price - option.strike, 0.0)
    return max(option.strike - price, 0.0)


def black_scholes_price(option: Option) -> float:
    """
    Return the Black-Scholes price for a European option.
    """
    if option.exercise != "european":
        raise ValueError("Black-Scholes is implemented for European options only")
    if option.maturity == 0 or option.volatility == 0:
        discounted_strike = option.strike * math.exp(-option.rate * option.maturity)
        forward_spot = option.spot * math.exp(-option.dividend_yield * option.maturity)
        if option.option_type == "call":
            return max(forward_spot - discounted_strike, 0.0)
        return max(discounted_strike - forward_spot, 0.0)

    root_t = math.sqrt(option.maturity)
    d1 = (
        math.log(option.spot / option.strike)
        + (option.rate - option.dividend_yield + 0.5 * option.volatility**2) * option.maturity
    ) / (option.volatility * root_t)
    d2 = d1 - option.volatility * root_t
    discounted_spot = option.spot * math.exp(-option.dividend_yield * option.maturity)
    discounted_strike = option.strike * math.exp(-option.rate * option.maturity)
    if option.option_type == "call":
        return discounted_spot * _normal_cdf(d1) - discounted_strike * _normal_cdf(d2)
    return discounted_strike * _normal_cdf(-d2) - discounted_spot * _normal_cdf(-d1)


def black_scholes_greeks(option: Option) -> dict[str, float]:
    """
    Return analytical European Black-Scholes Greeks.
    """
    if option.exercise != "european":
        raise ValueError("Black-Scholes Greeks are for European options only")
    if option.maturity == 0 or option.volatility == 0:
        return {
            "delta": float("nan"),
            "gamma": float("nan"),
            "theta": float("nan"),
            "vega": float("nan"),
            "rho": float("nan"),
        }

    root_t = math.sqrt(option.maturity)
    d1 = (
        math.log(option.spot / option.strike)
        + (option.rate - option.dividend_yield + 0.5 * option.volatility**2) * option.maturity
    ) / (option.volatility * root_t)
    d2 = d1 - option.volatility * root_t
    density = math.exp(-0.5 * d1**2) / math.sqrt(2.0 * math.pi)
    sign = 1.0 if option.option_type == "call" else -1.0
    discount_div = math.exp(-option.dividend_yield * option.maturity)
    discount_rate = math.exp(-option.rate * option.maturity)

    delta = discount_div * (_normal_cdf(d1) if sign > 0 else _normal_cdf(d1) - 1.0)
    gamma = discount_div * density / (option.spot * option.volatility * root_t)
    theta = (
        -option.spot * discount_div * density * option.volatility / (2.0 * root_t)
        + sign
        * (
            option.dividend_yield * option.spot * discount_div * _normal_cdf(sign * d1)
            - option.rate * option.strike * discount_rate * _normal_cdf(sign * d2)
        )
    )
    vega = option.spot * discount_div * density * root_t
    rho = sign * option.strike * option.maturity * discount_rate * _normal_cdf(sign * d2)
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


def binomial_price(option: Option, steps: int = 120) -> float:
    """
    Return a Cox-Ross-Rubinstein price for a European or American option.
    """
    if steps < 1:
        raise ValueError("steps must be at least 1")
    if option.maturity == 0:
        return _intrinsic(option)
    if option.volatility == 0:
        european = replace(option, exercise="european")
        return black_scholes_price(european) if option.exercise == "european" else _intrinsic(option)

    dt = option.maturity / steps
    up = math.exp(option.volatility * math.sqrt(dt))
    down = 1.0 / up
    discount = math.exp(-option.rate * dt)
    probability = (math.exp((option.rate - option.dividend_yield) * dt) - down) / (up - down)

    values = [_intrinsic(option, option.spot * (up**j) * (down ** (steps - j))) for j in range(steps + 1)]

    for level in range(steps - 1, -1, -1):
        values = [
            discount * (probability * values[j + 1] + (1.0 - probability) * values[j])
            for j in range(level + 1)
        ]
        if option.exercise == "american":
            values = [
                max(values[j], _intrinsic(option, option.spot * (up**j) * (down ** (level - j))))
                for j in range(level + 1)
            ]
    return values[0]


def binomial_greeks(option: Option, steps: int = 120) -> dict[str, float]:
    """
    Estimate Greeks by central finite differences around the tree price.
    """
    spot_shift = max(option.spot * 0.01, 1e-4)
    volatility_shift = 0.01
    time_shift = min(max(option.maturity * 0.01, 1e-5), option.maturity / 2) if option.maturity else 1e-5
    rate_shift = 0.0001  # 1 bp

    def price(candidate: Option) -> float:
        return binomial_price(candidate, steps)

    up = replace(option, spot=option.spot + spot_shift)
    down = replace(option, spot=max(option.spot - spot_shift, 1e-8))
    vol_up = replace(option, volatility=option.volatility + volatility_shift)
    vol_down = replace(option, volatility=max(option.volatility - volatility_shift, 0.0))
    shorter = replace(option, maturity=max(option.maturity - time_shift, 0.0))
    rate_up = replace(option, rate=option.rate + rate_shift)
    rate_down = replace(option, rate=option.rate - rate_shift)

    return {
        "delta": (price(up) - price(down)) / (up.spot - down.spot),
        "gamma": (price(up) - 2.0 * price(option) + price(down)) / (spot_shift**2),
        "theta": (price(shorter) - price(option)) / time_shift,
        "vega": (price(vol_up) - price(vol_down)) / (2.0 * volatility_shift),
        "rho": (price(rate_up) - price(rate_down)) / (2.0 * rate_shift),
    }