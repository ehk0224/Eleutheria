from __future__ import annotations
import argparse
import math
from dataclasses import dataclass, replace
from typing import Callable
import numpy as np
import pandas as pd
import d_option_chain_analytics as oca

class VRPAlphaEngine:
    """
    負責歷史行情波動率與 ATM IV 比對，產出決策訊號
    """
    def __init__(self, rv_window: int = 20, z_window: int = 60):
        self.rv_window = rv_window
        self.z_window = z_window

    def compute_parkinson_rv(self, ohlc_df: pd.DataFrame) -> pd.Series:
        """
        利用 High/Low 計算極值已實現波動率（Parkinson RV）
        """
        factor = 1.0 / (4.0 * math.log(2.0))
        hl_ratio = np.log(ohlc_df['high'] / ohlc_df['low']) ** 2
        rv = np.sqrt(252 * factor * hl_ratio.rolling(window=self.rv_window).mean())
        return rv

    def extract_atm_iv(self, chain_metrics_df: pd.DataFrame, spot: float) -> float:
        """
        從處理好的合約鏈中，篩選最接近 ATM (Delta 接近 0.5 的 Call 或接近現價) 的 ModelIV
        """
        calls = chain_metrics_df[chain_metrics_df['option_type'] == 'call'].dropna(subset=['model_iv', 'delta'])
        if calls.empty:
            return np.nan
        # 尋找 Delta 與 0.5 差距最小者
        calls = calls.assign(delta_diff=(calls['delta'] - 0.5).abs())
        atm_row = calls.sort_values(by=['delta_diff', 'strike']).iloc[0]
        return float(atm_row['model_iv'])

    def evaluate_signal(self, current_atm_iv: float, historical_rv: pd.Series, historical_vrp_spread: pd.Series) -> dict:
        """
        計算最新單日 VRP 與 Z-Score，輸出決策判斷
        """
        latest_rv = historical_rv.iloc[-1]
        current_vrp = current_atm_iv - latest_rv

        # 納入歷史 VRP 時序計算 Z-Score
        combined_spread = pd.concat([historical_vrp_spread, pd.Series([current_vrp])]).dropna()
        rolling_mean = combined_spread.tail(self.z_window).mean()
        rolling_std = combined_spread.tail(self.z_window).std()
        
        z_score = (current_vrp - rolling_mean) / rolling_std if rolling_std > 1e-6 else 0.0

        # 決策邏輯
        if z_score > 1.5:
            action = "SHORT_VOLATILITY"
            strategy = "期權定價過度昂貴（恐慌溢價過高）。建議賣出 ATM Straddle / Strangle 或建立 Bear Call / Bull Put 信用價差收取權利金，並動態對沖 Delta。"
        elif z_score < -1.5:
            action = "LONG_VOLATILITY"
            strategy = "期權定價過度低估。建議買入 Straddle（跨式）或 Calendar Spread，做多 Gamma 與 Vega。"
        else:
            action = "NEUTRAL"
            strategy = "VRP 處於正常套利區間內，不具備統計顯著進場優勢。"

        return {
            "current_atm_iv": current_atm_iv,
            "latest_rv": latest_rv,
            "vrp_spread": current_vrp,
            "z_score": z_score,
            "action": action,
            "strategy": strategy
        }


def run_vrp_pipeline_example():
    """
    對齊輸入與輸出的完整示範流程
    """
    # -------------------------------------------------------------
    # 1. 使用者初始輸入設定 (以 SPY 為例)
    # -------------------------------------------------------------
    spot_price = 500.0          # 標的當前現價
    dte_days = 30               # 距到期日天數
    maturity = dte_days / 365.0 # 年化到期時間
    risk_free_rate = 0.05       # 無風險利率 5%
    div_yield = 0.013           # SPY 股息率約 1.3%
    exercise_style = "american" # 美式期權

    # 模擬當前期權鏈報價 (實際環境替換為 yfinance 或券商 API 資料)
    quotes_data = {
        "strike": [490.0, 495.0, 500.0, 505.0, 510.0, 490.0, 495.0, 500.0, 505.0, 510.0],
        "market_price": [14.5, 11.0, 8.2, 5.5, 3.4, 3.2, 4.8, 7.0, 9.8, 13.1],
        "option_type": ["call", "call", "call", "call", "call", "put", "put", "put", "put", "put"]
    }
    quotes_df = pd.DataFrame(quotes_data)

    # 模擬現貨歷史 100 天 OHLC 資料 (實際應傳入真實歷史行情)
    np.random.seed(42)
    base_price = 480.0 + np.cumsum(np.random.normal(0.2, 2.0, 100))
    ohlc_df = pd.DataFrame({
        "open": base_price,
        "high": base_price + np.random.uniform(1.0, 3.0, 100),
        "low": base_price - np.random.uniform(1.0, 3.0, 100),
        "close": base_price + np.random.normal(0, 1.0, 100)
    })

    # -------------------------------------------------------------
    # 2. 處理期權鏈 (OptionChainAnalytics)
    # -------------------------------------------------------------
    print(">>> 正在批次計算期權鏈 IV 與 Greeks...")
    chain_analytics = oca.OptionChainAnalytics()
    chain_metrics_df = chain_analytics.process_chain(
        spot=spot_price,
        maturity=maturity,
        quotes_df=quotes_df,
        rate=risk_free_rate,
        dividend_yield=div_yield,
        exercise=exercise_style,
        tree_steps=100  # 示範加速，生產環境建議 150-200
    )
    print("\n--- 期權鏈計算成果 (前 10 筆) ---")
    print(chain_metrics_df[["strike", "option_type", "market_price", "model_iv", "delta", "gamma", "daily_theta"]].head(10))

    # -------------------------------------------------------------
    # 3. 計算波動率與 VRP 決策訊號 (VRPAlphaEngine)
    # -------------------------------------------------------------
    vrp_engine = VRPAlphaEngine(rv_window=20, z_window=60)

    # 3.1 計算歷史 Parkinson RV
    historical_rv = vrp_engine.compute_parkinson_rv(ohlc_df)

    # 3.2 提取當前 ATM IV
    current_atm_iv = vrp_engine.extract_atm_iv(chain_metrics_df, spot=spot_price)

    # 3.3 對齊歷史 VRP 基準：
    # 若沒有存儲歷史 IV，可用 VIX 近似，或利用基準水準模擬歷史滾動 VRP (一般介於 +1% ~ +4%)
    # 這裡以歷史 RV 為基底加上歷史常態波動溢價，建構出 historical_vrp_spread
    simulated_hist_iv = historical_rv * 1.10 + 0.015  # 模擬歷史上隱含波動率通常高於已實現波動率
    historical_vrp_spread = (simulated_hist_iv - historical_rv).dropna()

    # 3.4 評估信號
    decision = vrp_engine.evaluate_signal(
        current_atm_iv=current_atm_iv,
        historical_rv=historical_rv,
        historical_vrp_spread=historical_vrp_spread
    )

    # -------------------------------------------------------------
    # 4. 輸出決策結果
    # -------------------------------------------------------------
    print("\n--- VRP Alpha 決策報表 ---")
    print(f"當前 ATM 隱含波動率 (IV)   : {decision['current_atm_iv']:.2%}")
    print(f"最新 Parkinson 已實現 (RV) : {decision['latest_rv']:.2%}")
    print(f"當前波動率風險溢價 (VRP)   : {decision['vrp_spread']:.2%}")
    print(f"VRP 滾動 Z-Score           : {decision['z_score']:.2f}")
    print(f"交易行動建議               : {decision['action']}")
    print(f"策略說明                   : {decision['strategy']}")


if __name__ == "__main__":
    run_vrp_pipeline_example()