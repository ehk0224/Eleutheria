# Eleutheria

[中文版README](./README_zh_TW.md)

A pricing and valuation toolbox for financial instruments (in active development).

Currently provides two standalone modules: Option Pricing / Volatility Analysis, and Stock Fundamental Valuation. Additional asset classes and data pipelines will be added in future updates. The current focus is on reproducible pricing and analytical workflows.

## Features

### 1. `option_pricing` — Option Pricing & Volatility Signals

- European: Black–Scholes pricing and analytical Greeks (Delta / Gamma / Theta / Vega / Rho)
- European / American: Cox–Ross–Rubinstein (CRR) binomial tree pricing; American Greeks estimated via finite difference methods
- Implied Volatility: European solver using Newton–Raphson + Bisection; American solver via Bisection root-finding
- Option Chain Batch Processing: Computes IV, Greeks, and daily Theta from market quotes
- VRP Pipeline Demo: Calculates Volatility Risk Premium (VRP) using Parkinson Realized Volatility vs. ATM IV, computes rolling Z-scores, and generates rule-based long/short volatility signals

File Structure：

| File | Description |
|---|---|
| `a_option.py` | Contract specifications and input validation |
| `b_option_model.py` | BS / CRR pricing engines and Greeks calculation |
| `c_iv_calcu.py` | IV solver and CLI interface |
| `d_option_chain_analytics.py` | Full-chain IV and Greeks pipeline |
| `e_vrp_alpha_eg.py` | VRP signal demonstration (simulated quotes and OHLC) |

### 2. `stock_pricing` — Stock Relative & Absolute Valuation

- Fetches market quotes and financial statements via Yahoo Finance
- Relative Valuation: Trailing / Forward P/E, P/B, P/S, EV/EBITDA
- Absolute Valuation: Simplified DCF (base FCF + growth assumptions + Gordon terminal value), DDM (Gordon growth model)
- Outputs a summary valuation table alongside underlying assumptions

Currently provided as a single demonstration script: `stock_pricing_eg.py`. By default, the DCF growth rate uses `earningsGrowth`. Results may deviate significantly if data is missing or anomalous; always inspect input assumptions before use.

## Quick Start

```bash
git clone https://github.com/ehk0224/Eleutheria.git
cd Eleutheria
pip install numpy pandas yfinance