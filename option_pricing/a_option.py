from dataclasses import dataclass

@dataclass(frozen=True)
class Option:
    spot: float
    strike: float
    maturity: float
    volatility: float
    rate: float = 0.0
    dividend_yield: float = 0.0
    option_type: str = "call"
    exercise: str = "european"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.spot <= 0 or self.strike <= 0:
            raise ValueError("spot and strike must be positive")
        if self.maturity < 0 or self.volatility < 0:
            raise ValueError("maturity and volatility cannot be negative")
        if self.option_type not in {"call", "put"}:
            raise ValueError("option_type must be 'call' or 'put'")
        if self.exercise not in {"european", "american"}:
            raise ValueError("exercise must be 'european' or 'american'")