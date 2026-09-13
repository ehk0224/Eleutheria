# Eleutheria

[English](./README.md)

金融商品定價與估值工具箱（開發中）。

目前提供兩個獨立模組：選擇權定價／波動率分析，以及股票基本面估值。之後會再擴充其他資產與資料接線，現階段以可重現的定價與分析流程為主。

## 目前功能

### 1. `option_pricing` — 選擇權定價與波動率訊號

- 歐式：Black–Scholes 價格與解析 Greeks（Delta / Gamma / Theta / Vega / Rho）
- 歐式／美式：Cox–Ross–Rubinstein 二元樹定價；美式 Greeks 以有限差分估計
- 隱含波動率：歐式用 Newton–Raphson + 二分法；美式用二分法反解
- 選擇權鏈批次處理：由市場報價產出 IV、Greeks、每日 Theta
- VRP 示範流程：Parkinson 已實現波動 vs ATM IV，計算 VRP 與滾動 Z-score，輸出偏多／偏空波動的規則訊號

檔案對應：

| 檔案 | 內容 |
|---|---|
| `a_option.py` | 合約參數與輸入檢查 |
| `b_option_model.py` | BS / CRR 定價與 Greeks |
| `c_iv_calcu.py` | IV 求解與 CLI |
| `d_option_chain_analytics.py` | 整條鏈的 IV + Greeks |
| `e_vrp_alpha_eg.py` | VRP 訊號示範（模擬報價與 OHLC） |

### 2. `stock_pricing` — 股票相對／絕對估值

- 由 Yahoo Finance 拉取報價與財報
- 相對估值：Trailing / Forward P/E、P/B、P/S、EV/EBITDA
- 絕對估值：簡化 DCF（基期 FCF + 成長假設 + Gordon 終值）、DDM（Gordon）
- 輸出一張彙總表與分項假設

目前為單檔示範：`stock_pricing_eg.py`。DCF 成長率預設取 `earningsGrowth`，資料缺失或異常時結果會明顯偏離，使用時需檢查假設。

## 快速開始

```bash
git clone https://github.com/ehk0224/Eleutheria.git
cd Eleutheria
pip install numpy pandas yfinance