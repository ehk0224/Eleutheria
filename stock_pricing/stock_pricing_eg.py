import yfinance as yf
import pandas as pd
import numpy as np

class FundamentalValuation:
    def __init__(self, ticker: str):
        self.ticker_str = ticker
        self.stock = yf.Ticker(ticker)
        self.info = self.stock.info
        
        # 抓取主要三大財務報表 (年報)
        self.financials = self.stock.financials
        self.balance_sheet = self.stock.balance_sheet
        self.cashflow = self.stock.cashflow

    def get_multiples(self) -> dict:
        """
        提取相對估值乘數 (P/E, P/B, P/S, EV/EBITDA)
        """
        return {
            "Ticker": self.ticker_str,
            "Trailing P/E": self.info.get("trailingPE"),
            "Forward P/E": self.info.get("forwardPE"),
            "P/B": self.info.get("priceToBook"),
            "P/S (TTM)": self.info.get("priceToSalesTrailing12Months"),
            "EV/EBITDA": self.info.get("enterpriseToEbitda"),
            "Market Cap": self.info.get("marketCap"),
            "Enterprise Value": self.info.get("enterpriseValue"),
            "Current Price": self.info.get("currentPrice") or self.info.get("regularMarketPrice")
        }

    def calculate_dcf(self, discount_rate: float = 0.09, terminal_growth: float = 0.025, projection_years: int = 5) -> dict:
        """
        簡易 DCF 模型 (Free Cash Flow to Firm / Equity)
        - 估算基期 FCF: 取最新一期 Operating Cash Flow - Capital Expenditure
        - 採用分析師預期營收/獲利成長率，或預設以歷史保守成長率推估
        """
        try:
            # 取得最新一期 Free Cash Flow
            if "Free Cash Flow" in self.cashflow.index:
                fcf_base = self.cashflow.loc["Free Cash Flow"].iloc[0]
            else:
                # 若無直接欄位，手動計算：營運現金流 - 資本支出
                ocf = self.cashflow.loc["Operating Cash Flow"].iloc[0]
                capex = abs(self.cashflow.loc["Capital Expenditure"].iloc[0])
                fcf_base = ocf - capex

            # 抓取預估成長率 (若無則預設 5%)
            growth_rate = self.info.get("earningsGrowth", 0.05)
            if growth_rate is None or np.isnan(growth_rate):
                growth_rate = 0.05

            # 預測期現金流折現
            pv_fcf = 0.0
            projected_fcf = fcf_base
            for i in range(1, projection_years + 1):
                projected_fcf *= (1 + growth_rate)
                pv_fcf += projected_fcf / ((1 + discount_rate) ** i)

            # 終值 (Terminal Value) 折現 (Gordon Growth Model)
            terminal_value = (projected_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
            pv_tv = terminal_value / ((1 + discount_rate) ** projection_years)

            # 企業價值與權益價值轉換
            enterprise_value = pv_fcf + pv_tv
            
            # 加回現金、扣除總負債
            total_cash = self.info.get("totalCash", 0)
            total_debt = self.info.get("totalDebt", 0)
            equity_value = enterprise_value + total_cash - total_debt
            
            shares_outstanding = self.info.get("sharesOutstanding")
            implied_share_price = equity_value / shares_outstanding if shares_outstanding else None

            return {
                "Base FCF": fcf_base,
                "Growth Rate (Est.)": growth_rate,
                "Discount Rate (WACC)": discount_rate,
                "Terminal Growth Rate": terminal_growth,
                "PV of Cash Flows": pv_fcf,
                "PV of Terminal Value": pv_tv,
                "DCF Implied Value/Share": implied_share_price
            }
        except Exception as e:
            return {"Error": f"DCF 計算失敗: {str(e)}"}

    def calculate_ddm(self, cost_of_equity: float = 0.08, terminal_growth: float = 0.02) -> dict:
        """
        高登股利折現模型 (Gordon Growth Model)
        - 適用於具備穩定配息歷史的公司
        """
        dividend_rate = self.info.get("dividendRate")  # 每股年度股利
        dividend_yield = self.info.get("dividendYield")

        if not dividend_rate or dividend_rate == 0:
            return {
                "Dividend Rate": 0,
                "DDM Implied Value/Share": None,
                "Note": "無股利發放或股利數據缺失，不適用 DDM 模型"
            }

        try:
            # P0 = D1 / (r - g) = D0 * (1 + g) / (r - g)
            if cost_of_equity <= terminal_growth:
                raise ValueError("必要報酬率 (Cost of Equity) 必須大於長期成長率 (Terminal Growth)")

            d1 = dividend_rate * (1 + terminal_growth)
            fair_value = d1 / (cost_of_equity - terminal_growth)

            return {
                "Trailing Annual Dividend (D0)": dividend_rate,
                "Projected Dividend (D1)": d1,
                "Dividend Yield": dividend_yield,
                "Cost of Equity": cost_of_equity,
                "Terminal Growth": terminal_growth,
                "DDM Implied Value/Share": fair_value
            }
        except Exception as e:
            return {"Error": f"DDM 計算失敗: {str(e)}"}

    def generate_summary(self) -> pd.DataFrame:
        """
        整合相對估值與絕對估值結果
        """
        multiples = self.get_multiples()
        dcf = self.calculate_dcf()
        ddm = self.calculate_ddm()

        summary_data = {
            "Metric / Parameter": [
                "Current Price",
                "Trailing P/E",
                "P/B",
                "P/S",
                "EV/EBITDA",
                "DCF Implied Fair Value",
                "DDM Implied Fair Value"
            ],
            "Value": [
                multiples.get("Current Price"),
                multiples.get("Trailing P/E"),
                multiples.get("P/B"),
                multiples.get("P/S (TTM)"),
                multiples.get("EV/EBITDA"),
                dcf.get("DCF Implied Value/Share"),
                ddm.get("DDM Implied Value/Share")
            ]
        }
        return pd.DataFrame(summary_data)


# ================== 執行範例 ==================
if __name__ == "__main__":
    ticker = "AAPL"
    analyzer = FundamentalValuation(ticker)

    print(f"=== {ticker} 估值指標彙總 ===")
    summary_df = analyzer.generate_summary()
    print(summary_df.to_string(index=False))

    print("\n=== 詳細 DCF 數據 ===")
    for k, v in analyzer.calculate_dcf().items():
        print(f"{k}: {v:,.2f}" if isinstance(v, (int, float)) else f"{k}: {v}")

    print("\n=== 詳細 DDM 數據 ===")
    for k, v in analyzer.calculate_ddm().items():
        print(f"{k}: {v:,.2f}" if isinstance(v, (int, float)) else f"{k}: {v}")