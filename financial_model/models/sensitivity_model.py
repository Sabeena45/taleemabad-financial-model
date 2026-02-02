"""
Sensitivity Analysis Model.
What-if analysis on key variables.
All data sourced from budget_2026.py only.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.budget_2026 import (
    OPENING_BALANCE,
    MONTHLY_INFLOWS,
    MONTHLY_EXPENSES,
    GRANT_INCOME,
    TOTAL_GRANT_INCOME,
    TOTAL_EXPENSES,
    PROJECTED_SURPLUS,
    EXCHANGE_RATE,
    PARTNER_REVENUE,
)
from .cashflow_model import CashFlowModel

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass
class SensitivityResult:
    """Result from a sensitivity analysis."""
    variable: str
    base_value: float
    test_value: float
    change_pct: float
    impact_on_surplus: float
    new_surplus: float
    impact_on_runway: float
    new_runway: float


class SensitivityModel:
    """
    Sensitivity analysis for what-if scenarios.

    Key variables to analyze:
    - Exchange rate (PKR/USD)
    - Grant amounts
    - Revenue timing
    - Expense levels
    """

    def __init__(self):
        self.base_inflows = MONTHLY_INFLOWS.copy()
        self.base_expenses = MONTHLY_EXPENSES.copy()
        self.base_surplus = PROJECTED_SURPLUS
        self.base_model = CashFlowModel()
        self.base_runway = self.base_model.get_year_end_position() / self.base_model.get_average_monthly_burn()

    def analyze_variable(
        self,
        variable: str,
        change_pct: float,
    ) -> SensitivityResult:
        """
        Analyze impact of changing a single variable.

        Args:
            variable: "revenue", "expenses", "grant_total"
            change_pct: Percentage change (-100 to +100)

        Returns:
            SensitivityResult with impact analysis
        """
        multiplier = 1 + (change_pct / 100)

        if variable == "revenue":
            adjusted_inflows = {m: v * multiplier for m, v in self.base_inflows.items()}
            model = CashFlowModel(inflows=adjusted_inflows, expenses=self.base_expenses)
            base_value = sum(self.base_inflows.values())
            test_value = sum(adjusted_inflows.values())

        elif variable == "expenses":
            adjusted_expenses = {m: v * multiplier for m, v in self.base_expenses.items()}
            model = CashFlowModel(inflows=self.base_inflows, expenses=adjusted_expenses)
            base_value = sum(self.base_expenses.values())
            test_value = sum(adjusted_expenses.values())

        elif variable == "grant_total":
            # Scale all grants by multiplier
            adjusted_inflows = self.base_inflows.copy()
            for grant_name, grant_data in GRANT_INCOME.items():
                for month, amount in grant_data.get("timing", {}).items():
                    adjustment = amount * (multiplier - 1)
                    adjusted_inflows[month] = adjusted_inflows.get(month, 0) + adjustment

            model = CashFlowModel(inflows=adjusted_inflows, expenses=self.base_expenses)
            base_value = TOTAL_GRANT_INCOME
            test_value = TOTAL_GRANT_INCOME * multiplier

        else:
            raise ValueError(f"Unknown variable: {variable}")

        new_surplus = model.get_year_end_position()
        new_runway = new_surplus / model.get_average_monthly_burn() if model.get_average_monthly_burn() > 0 else float('inf')

        return SensitivityResult(
            variable=variable,
            base_value=base_value,
            test_value=test_value,
            change_pct=change_pct,
            impact_on_surplus=new_surplus - self.base_surplus,
            new_surplus=new_surplus,
            impact_on_runway=new_runway - self.base_runway,
            new_runway=new_runway,
        )

    def run_sensitivity_table(
        self,
        variable: str,
        range_pct: List[float] = None,
    ) -> List[SensitivityResult]:
        """
        Run sensitivity analysis across a range of values.

        Args:
            variable: Variable to analyze
            range_pct: List of percentage changes (default: -30 to +30 by 10)

        Returns:
            List of SensitivityResults
        """
        if range_pct is None:
            range_pct = [-30, -20, -10, 0, 10, 20, 30]

        results = []
        for pct in range_pct:
            result = self.analyze_variable(variable, pct)
            results.append(result)

        return results

    def analyze_grant_dependency(self) -> Dict[str, Dict]:
        """
        Analyze dependency on each major grant.

        Returns:
            Dict with grant_name -> impact metrics
        """
        results = {}

        for grant_name, grant_data in GRANT_INCOME.items():
            grant_amount = grant_data["amount"]

            # Simulate removing this grant
            adjusted_inflows = self.base_inflows.copy()
            for month, amount in grant_data.get("timing", {}).items():
                adjusted_inflows[month] = adjusted_inflows.get(month, 0) - amount

            model = CashFlowModel(inflows=adjusted_inflows, expenses=self.base_expenses)

            new_surplus = model.get_year_end_position()
            avg_burn = model.get_average_monthly_burn()
            new_runway = new_surplus / avg_burn if avg_burn > 0 else float('inf')

            results[grant_name] = {
                "grant_amount": grant_amount,
                "percentage_of_total": grant_amount / TOTAL_GRANT_INCOME * 100,
                "impact_on_surplus": new_surplus - self.base_surplus,
                "new_surplus": new_surplus,
                "new_runway_months": new_runway,
                "critical": new_surplus < 0,
            }

        return results

    def analyze_exchange_rate(
        self,
        rates: List[float] = None,
    ) -> List[Dict]:
        """
        Analyze impact of exchange rate changes.

        Note: This mainly affects PKR-denominated items.
        Most budget figures are already in USD.

        Args:
            rates: List of PKR/USD rates to test

        Returns:
            List of impact analyses
        """
        if rates is None:
            # Test ±10%, ±20% from base rate
            rates = [
                EXCHANGE_RATE * 0.8,  # 226
                EXCHANGE_RATE * 0.9,  # 255
                EXCHANGE_RATE,        # 283
                EXCHANGE_RATE * 1.1,  # 311
                EXCHANGE_RATE * 1.2,  # 340
            ]

        results = []
        for rate in rates:
            # Calculate PKR value of USD surplus
            pkr_surplus = self.base_surplus * rate

            results.append({
                "exchange_rate": rate,
                "change_from_base_pct": (rate - EXCHANGE_RATE) / EXCHANGE_RATE * 100,
                "usd_surplus": self.base_surplus,  # Unchanged in USD
                "pkr_surplus": pkr_surplus,
                "pkr_change": pkr_surplus - (self.base_surplus * EXCHANGE_RATE),
            })

        return results

    def analyze_revenue_delay(
        self,
        months_delayed: int = 1,
    ) -> Dict:
        """
        Analyze impact of revenue arriving later than planned.

        Args:
            months_delayed: Number of months to delay inflows

        Returns:
            Impact analysis
        """
        # Shift inflows by N months
        adjusted_inflows = {m: 0 for m in MONTHS}

        for i, month in enumerate(MONTHS):
            original_amount = self.base_inflows.get(month, 0)
            new_month_idx = i + months_delayed

            if new_month_idx < len(MONTHS):
                new_month = MONTHS[new_month_idx]
                adjusted_inflows[new_month] = adjusted_inflows.get(new_month, 0) + original_amount
            # Amounts delayed beyond Dec are lost for the year

        model = CashFlowModel(inflows=adjusted_inflows, expenses=self.base_expenses)
        min_position = model.get_minimum_cash_month()

        # Calculate revenue lost due to delay
        lost_revenue = sum(self.base_inflows.values()) - sum(adjusted_inflows.values())

        return {
            "months_delayed": months_delayed,
            "lost_revenue": lost_revenue,
            "new_total_inflows": sum(adjusted_inflows.values()),
            "new_year_end_surplus": model.get_year_end_position(),
            "impact_on_surplus": model.get_year_end_position() - self.base_surplus,
            "minimum_cash": min_position.closing,
            "minimum_cash_month": min_position.month,
            "cash_negative_months": [p.month for p in model.positions if p.closing < 0],
        }

    def find_break_even_point(
        self,
        variable: str,
        search_range: Tuple[float, float] = (-50, 50),
    ) -> float:
        """
        Find the percentage change that results in zero surplus.

        Args:
            variable: Variable to analyze
            search_range: (min_pct, max_pct) to search

        Returns:
            Percentage change that results in break-even
        """
        # Binary search for break-even point
        low, high = search_range
        tolerance = 0.1

        while high - low > tolerance:
            mid = (low + high) / 2
            result = self.analyze_variable(variable, mid)

            if result.new_surplus > 0:
                if variable == "revenue":
                    high = mid  # Need to reduce revenue more
                else:
                    low = mid   # Need to increase expenses more
            else:
                if variable == "revenue":
                    low = mid
                else:
                    high = mid

        return (low + high) / 2

    def get_sensitivity_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Create a sensitivity matrix showing impact of ±10% changes.

        Returns:
            Matrix with variable -> {"-10%": impact, "+10%": impact}
        """
        variables = ["revenue", "expenses", "grant_total"]
        matrix = {}

        for var in variables:
            minus_10 = self.analyze_variable(var, -10)
            plus_10 = self.analyze_variable(var, 10)

            matrix[var] = {
                "-10%": minus_10.impact_on_surplus,
                "+10%": plus_10.impact_on_surplus,
            }

        return matrix

    def to_sensitivity_dataframe_dict(self, variable: str) -> List[Dict]:
        """Convert sensitivity results to list of dicts for DataFrame."""
        results = self.run_sensitivity_table(variable)

        return [
            {
                "Change (%)": r.change_pct,
                "New Value": r.test_value,
                "Impact on Surplus": r.impact_on_surplus,
                "New Surplus": r.new_surplus,
                "New Runway (Months)": round(r.new_runway, 1),
            }
            for r in results
        ]
