from __future__ import annotations
import argparse
import math
from dataclasses import dataclass, replace
from typing import Callable
import numpy as np
import pandas as pd
import c_iv_calcu as c_iv_calcu
import b_option_model as b_option_model
from a_option import Option


class OptionChainAnalytics:
    """
    接收整批合約報價，調用定價引擎產出含 Greeks 與 IV 的分析表
    """
    @staticmethod
    def process_chain(
        spot: float,
        maturity: float,
        quotes_df: pd.DataFrame,
        rate: float = 0.05,
        dividend_yield: float = 0.013,  # SPY 約 1.3% 股息率
        exercise: str = "american",
        tree_steps: int = 150
    ) -> pd.DataFrame:
        """
        quotes_df 需包含: 'strike', 'market_price', 'option_type'
        """
        records = []
        for _, row in quotes_df.iterrows():
            k = float(row['strike'])
            price = float(row['market_price'])
            opt_type = str(row['option_type']).lower()

            base_opt = Option(
                spot=spot,
                strike=k,
                maturity=maturity,
                volatility=0.20,  # 初始佔位符
                rate=rate,
                dividend_yield=dividend_yield,
                option_type=opt_type,
                exercise=exercise
            )

            # 1. 調用現有引擎計算 Implied Volatility
            try:
                iv = c_iv_calcu.implied_volatility(base_opt, target_price=price, steps=tree_steps)
            except Exception:
                iv = np.nan

            # 2. 帶入解出的 IV 計算對應 Greeks
            if not np.isnan(iv) and iv > 0:
                solved_opt = replace(base_opt, volatility=iv)
                if exercise == "european":
                    greeks = b_option_model.black_scholes_greeks(solved_opt)
                else:
                    greeks = b_option_model.binomial_greeks(solved_opt, steps=tree_steps)
                
                delta = greeks.get("delta", np.nan)
                gamma = greeks.get("gamma", np.nan)
                # 換算為每日 Theta 衰退
                daily_theta = greeks.get("theta", np.nan) / 365.0
            else:
                delta = gamma = daily_theta = np.nan

            records.append({
                "strike": k,
                "option_type": opt_type,
                "market_price": price,
                "model_iv": iv,
                "delta": delta,
                "gamma": gamma,
                "daily_theta": daily_theta
            })

        return pd.DataFrame(records)