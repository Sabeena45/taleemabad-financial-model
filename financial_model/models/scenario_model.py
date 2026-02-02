"""
Scenario Analysis Model.
Supports base, optimistic, pessimistic, and custom scenarios.
All data sourced from budget_2026.py only.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.budget_2026 import (
    OPENING_BALANCE,
    MONTHLY_INFLOWS,
    MONTHLY_EXPENSES,
    TOTAL_INFLOWS,
    TOTAL_EXPENSES,
    PROJECTED_SURPLUS,
    GRANT_INCOME,
)
from .cashflow_model import CashFlowModel

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class ScenarioType(Enum):
    BASE = "base"
    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    CUSTOM = "custom"


@dataclass
class ScenarioResult:
    """Results from a scenario analysis."""
    scenario_type: ScenarioType
    name: str
    total_inflows: float
    total_expenses: float
    year_end_surplus: float
    minimum_cash: float
    minimum_cash_month: str
    runway_months: float
    assumptions: Dict[str, float]


class ScenarioModel:
    """
    Scenario analysis model for financial planning.

    Scenario multipliers:
    - Base: Budget as-is (100%)
    - Optimistic: +20% revenue, -10% expenses
    - Pessimistic: -30% revenue, +15% expenses
    """

    # Default scenario multipliers (based on typical sensitivity ranges)
    SCENARIO_PARAMS = {
        ScenarioType.BASE: {
            "revenue_multiplier": 1.0,
            "expense_multiplier": 1.0,
            "grant_probability": 1.0,
            "name": "Base Case (Budget)",
        },
        ScenarioType.OPTIMISTIC: {
            "revenue_multiplier": 1.2,  # +20%
            "expense_multiplier": 0.9,  # -10%
            "grant_probability": 1.0,
            "name": "Optimistic (Best Case)",
        },
        ScenarioType.PESSIMISTIC: {
            "revenue_multiplier": 0.7,  # -30%
            "expense_multiplier": 1.15,  # +15%
            "grant_probability": 0.7,  # 30% chance of grant not coming
            "name": "Pessimistic (Worst Case)",
        },
    }

    def __init__(self):
        self.base_inflows = MONTHLY_INFLOWS.copy()
        self.base_expenses = MONTHLY_EXPENSES.copy()
        self.scenarios = {}

    def run_scenario(
        self,
        scenario_type: ScenarioType = ScenarioType.BASE,
        revenue_multiplier: Optional[float] = None,
        expense_multiplier: Optional[float] = None,
        grant_probability: Optional[float] = None,
        excluded_grants: Optional[list] = None,
    ) -> ScenarioResult:
        """
        Run a specific scenario.

        Args:
            scenario_type: Type of scenario (BASE, OPTIMISTIC, PESSIMISTIC, CUSTOM)
            revenue_multiplier: Override revenue multiplier (0-2)
            expense_multiplier: Override expense multiplier (0-2)
            grant_probability: Probability of grants coming through (0-1)
            excluded_grants: List of grant keys to exclude

        Returns:
            ScenarioResult with analysis
        """
        # Get base parameters for scenario type
        params = self.SCENARIO_PARAMS.get(
            scenario_type,
            self.SCENARIO_PARAMS[ScenarioType.BASE]
        ).copy()

        # Override with custom parameters if provided
        if revenue_multiplier is not None:
            params["revenue_multiplier"] = revenue_multiplier
        if expense_multiplier is not None:
            params["expense_multiplier"] = expense_multiplier
        if grant_probability is not None:
            params["grant_probability"] = grant_probability

        # Calculate adjusted inflows
        adjusted_inflows = {}
        for month, amount in self.base_inflows.items():
            adjusted = amount * params["revenue_multiplier"] * params["grant_probability"]
            adjusted_inflows[month] = adjusted

        # Handle excluded grants
        if excluded_grants:
            for grant_key in excluded_grants:
                if grant_key in GRANT_INCOME:
                    grant_timing = GRANT_INCOME[grant_key].get("timing", {})
                    for month, amount in grant_timing.items():
                        if month in adjusted_inflows:
                            adjusted_inflows[month] -= amount

        # Calculate adjusted expenses
        adjusted_expenses = {
            month: amount * params["expense_multiplier"]
            for month, amount in self.base_expenses.items()
        }

        # Run cash flow model
        model = CashFlowModel(
            opening_balance=OPENING_BALANCE,
            inflows=adjusted_inflows,
            expenses=adjusted_expenses,
        )

        min_position = model.get_minimum_cash_month()
        avg_burn = model.get_average_monthly_burn()

        result = ScenarioResult(
            scenario_type=scenario_type,
            name=params.get("name", "Custom Scenario"),
            total_inflows=model.get_total_inflows(),
            total_expenses=model.get_total_outflows(),
            year_end_surplus=model.get_year_end_position(),
            minimum_cash=min_position.closing,
            minimum_cash_month=min_position.month,
            runway_months=model.get_year_end_position() / avg_burn if avg_burn > 0 else float('inf'),
            assumptions={
                "revenue_multiplier": params["revenue_multiplier"],
                "expense_multiplier": params["expense_multiplier"],
                "grant_probability": params["grant_probability"],
            },
        )

        self.scenarios[scenario_type] = result
        return result

    def run_all_scenarios(self) -> Dict[ScenarioType, ScenarioResult]:
        """Run all standard scenarios."""
        for scenario_type in [ScenarioType.BASE, ScenarioType.OPTIMISTIC, ScenarioType.PESSIMISTIC]:
            self.run_scenario(scenario_type)
        return self.scenarios

    def compare_scenarios(self) -> Dict[str, Dict]:
        """
        Compare all run scenarios.

        Returns:
            Dict with comparison metrics
        """
        if not self.scenarios:
            self.run_all_scenarios()

        comparison = {}
        for scenario_type, result in self.scenarios.items():
            comparison[result.name] = {
                "total_inflows": result.total_inflows,
                "total_expenses": result.total_expenses,
                "year_end_surplus": result.year_end_surplus,
                "minimum_cash": result.minimum_cash,
                "minimum_cash_month": result.minimum_cash_month,
                "runway_months": result.runway_months,
            }

        return comparison

    def get_scenario_cash_flows(self) -> Dict[str, Dict[str, float]]:
        """
        Get monthly cash positions for all scenarios.

        Returns:
            Dict with scenario_name -> {month: closing_balance}
        """
        if not self.scenarios:
            self.run_all_scenarios()

        cash_flows = {}

        for scenario_type, result in self.scenarios.items():
            # Re-run the model to get monthly data
            params = self.SCENARIO_PARAMS.get(scenario_type, self.SCENARIO_PARAMS[ScenarioType.BASE])

            adjusted_inflows = {
                month: amount * params["revenue_multiplier"] * params.get("grant_probability", 1.0)
                for month, amount in self.base_inflows.items()
            }
            adjusted_expenses = {
                month: amount * params["expense_multiplier"]
                for month, amount in self.base_expenses.items()
            }

            model = CashFlowModel(
                opening_balance=OPENING_BALANCE,
                inflows=adjusted_inflows,
                expenses=adjusted_expenses,
            )

            cash_flows[result.name] = {
                pos.month: pos.closing for pos in model.positions
            }

        return cash_flows

    def simulate_grant_loss(self, grant_key: str) -> ScenarioResult:
        """
        Simulate losing a specific grant.

        Args:
            grant_key: Key of grant to remove (e.g., "mulago", "dovetail")

        Returns:
            ScenarioResult showing impact
        """
        return self.run_scenario(
            scenario_type=ScenarioType.CUSTOM,
            excluded_grants=[grant_key],
        )

    def to_comparison_dataframe_dict(self) -> list:
        """Convert comparison to list of dicts for DataFrame."""
        if not self.scenarios:
            self.run_all_scenarios()

        rows = []
        for scenario_type, result in self.scenarios.items():
            rows.append({
                "Scenario": result.name,
                "Total Inflows": result.total_inflows,
                "Total Expenses": result.total_expenses,
                "Year-End Surplus": result.year_end_surplus,
                "Minimum Cash": result.minimum_cash,
                "Runway (Months)": round(result.runway_months, 1),
            })

        return rows
