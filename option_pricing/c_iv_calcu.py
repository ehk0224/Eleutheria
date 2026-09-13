from __future__ import annotations
import argparse
import math
from dataclasses import dataclass, replace
from typing import Callable
import numpy as np
import pandas as pd
import b_option_model as b_option_model
from a_option import Option


def implied_volatility(
    option: Option,
    target_price: float,
    steps: int = 120,
    tol: float = 1e-7,
    max_iter: int = 100,
) -> float:
    """
    Solve for implied volatility using a hybrid Newton-Raphson and bisection algorithm.
    """
    if target_price < 0:
        raise ValueError("target_price cannot be negative")

    # 內含價值下限
    intrinsic_val = b_option_model._intrinsic(option)
    if target_price <= intrinsic_val + 1e-6:
        # 若報價已低於或等於內含價值，IV 實質趨近於 0
        return 1e-4

    pricing: Callable[[Option], float] = (
        b_option_model.binomial_price if option.exercise == "american" else b_option_model.black_scholes_price
    )
    
    # 將下限調整為 1e-4，避免二元樹 u - d 趨近 0 導致分母爆炸
    low, high = 1e-4, 4.0
    low_price = pricing(replace(option, volatility=low))
    high_price = pricing(replace(option, volatility=high))

    # 邊界容錯處理
    if target_price <= low_price:
        return low
    if target_price >= high_price:
        return high

    # 美式選擇權：二分法
    if option.exercise == "american":
        for _ in range(max_iter):
            midpoint = (low + high) / 2.0
            midpoint_price = pricing(replace(option, volatility=midpoint), steps=steps)
            if abs(midpoint_price - target_price) < tol:
                return midpoint
            if midpoint_price < target_price:
                low = midpoint
            else:
                high = midpoint
        return (low + high) / 2.0

    # 歐式選擇權：混合法
    sigma = math.sqrt(2.0 * math.pi / option.maturity) * (target_price / option.spot)
    if not (low < sigma < high):
        sigma = 0.25

    for _ in range(max_iter):
        current_option = replace(option, volatility=sigma)
        price = b_option_model.black_scholes_price(current_option)
        diff = price - target_price

        if diff < 0:
            low = max(low, sigma)
        else:
            high = min(high, sigma)

        if abs(diff) < tol:
            return sigma

        greeks = b_option_model.black_scholes_greeks(current_option)
        vega = greeks["vega"]

        if math.isnan(vega) or vega < 1e-8:
            sigma = (low + high) / 2.0
            continue

        step = diff / vega
        candidate_sigma = sigma - step

        if candidate_sigma <= low or candidate_sigma >= high:
            sigma = (low + high) / 2.0
        else:
            sigma = candidate_sigma

    return (low + high) / 2.0


def _build_parser() -> argparse.ArgumentParser:
    """
    Build an argument parser for the option pricing script.
    """
    parser = argparse.ArgumentParser(description="Price European or American options.")
    parser.add_argument("--spot", type=float, required=True)
    parser.add_argument("--strike", type=float, required=True)
    parser.add_argument("--maturity", type=float, required=True, help="Years to expiry")
    parser.add_argument("--volatility", type=float, required=True, help="Annualized volatility, e.g. 0.20")
    parser.add_argument("--rate", type=float, default=0.05)
    parser.add_argument("--dividend-yield", type=float, default=0.0)
    parser.add_argument("--type", choices=["call", "put"], default="call", dest="option_type")
    parser.add_argument("--exercise", choices=["european", "american"], default="european")
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--market-price", type=float, help="Return implied volatility for this market price")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    option = Option(
        spot=args.spot,
        strike=args.strike,
        maturity=args.maturity,
        volatility=args.volatility,
        rate=args.rate,
        dividend_yield=args.dividend_yield,
        option_type=args.option_type,
        exercise=args.exercise,
    )
    print(f"Option: {option.exercise} {option.option_type}")
    if option.exercise == "european":
        print(f"Black-Scholes price: {b_option_model.black_scholes_price(option):.6f}")
        for name, value in b_option_model.black_scholes_greeks(option).items():
            print(f"{name}: {value:.6f}")
    tree_price = b_option_model.binomial_price(option, args.steps)
    print(f"Binomial price ({args.steps} steps): {tree_price:.6f}")
    for name, value in b_option_model.binomial_greeks(option, args.steps).items():
        print(f"tree {name}: {value:.6f}")
    if args.market_price is not None:
        print(f"Implied volatility: {implied_volatility(option, args.market_price, args.steps):.6f}")
