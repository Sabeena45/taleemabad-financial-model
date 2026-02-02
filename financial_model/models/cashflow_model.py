"""
Cash Flow Forecasting Model.
All data sourced from budget_2026.py only.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.budget_2026 import (
    OPENING_BALANCE,
    MONTHLY_INFLOWS,
    MONTHLY_EXPENSES,
    MONTHLY_CASH_POSITION,
    GRANT_INCOME,
    PARTNER_REVENUE,
    TOTAL_INFLOWS,
    TOTAL_EXPENSES,
    PROJECTED_SURPLUS,
)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass
class MonthlyPosition:
    """Monthly cash position data."""
    month: str
    opening: float
    inflows: float
    outflows: float
    closing: float
    cumulative: float


class CashFlowModel:
    """
    Cash flow forecasting model based on 2026 budget data.
    """

    def __init__(
        self,
        opening_balance: float = OPENING_BALANCE,
        inflows: Optional[Dict[str, float]] = None,
        expenses: Optional[Dict[str, float]] = None,
    ):
        self.opening_balance = opening_balance
        self.inflows = inflows or MONTHLY_INFLOWS.copy()
        self.expenses = expenses or MONTHLY_EXPENSES.copy()
        self._calculate_positions()

    def _calculate_positions(self):
        """Calculate monthly cash positions."""
        self.positions = []
        cumulative = self.opening_balance

        for i, month in enumerate(MONTHS):
            opening = cumulative
            month_inflows = self.inflows.get(month, 0)
            month_outflows = self.expenses.get(month, 0)
            closing = opening + month_inflows - month_outflows
            cumulative = closing

            self.positions.append(MonthlyPosition(
                month=month,
                opening=opening,
                inflows=month_inflows,
                outflows=month_outflows,
                closing=closing,
                cumulative=cumulative,
            ))

    def get_position(self, month: str) -> Optional[MonthlyPosition]:
        """Get cash position for a specific month."""
        for pos in self.positions:
            if pos.month == month:
                return pos
        return None

    def get_year_end_position(self) -> float:
        """Get projected year-end cash position."""
        return self.positions[-1].closing if self.positions else 0

    def get_minimum_cash_month(self) -> MonthlyPosition:
        """Get the month with minimum cash position."""
        return min(self.positions, key=lambda p: p.closing)

    def get_low_cash_months(self, threshold: float = 500000) -> List[MonthlyPosition]:
        """Get months where cash falls below threshold."""
        return [p for p in self.positions if p.closing < threshold]

    def get_total_inflows(self) -> float:
        """Get total annual inflows."""
        return sum(self.inflows.values())

    def get_total_outflows(self) -> float:
        """Get total annual outflows."""
        return sum(self.expenses.values())

    def get_net_cash_flow(self) -> float:
        """Get net cash flow for the year."""
        return self.get_total_inflows() - self.get_total_outflows()

    def get_average_monthly_burn(self) -> float:
        """Get average monthly burn rate."""
        return self.get_total_outflows() / 12

    def get_inflow_by_category(self) -> Dict[str, Dict[str, float]]:
        """
        Break down inflows by category and timing.

        Returns:
            Dict with category -> {month: amount}
        """
        breakdown = {
            "grants": {},
            "partner_revenue": {},
            "rental": {},
        }

        # Grant timing from budget data
        for grant_name, grant_data in GRANT_INCOME.items():
            for month, amount in grant_data.get("timing", {}).items():
                if month not in breakdown["grants"]:
                    breakdown["grants"][month] = 0
                breakdown["grants"][month] += amount

        # Partner revenue
        for partner_name, partner_data in PARTNER_REVENUE.items():
            monthly = partner_data.get("monthly_usd", 0)
            start = partner_data.get("start_month")
            if monthly > 0 and start:
                start_idx = MONTHS.index(start) if start in MONTHS else 0
                for month in MONTHS[start_idx:]:
                    if month not in breakdown["partner_revenue"]:
                        breakdown["partner_revenue"][month] = 0
                    breakdown["partner_revenue"][month] += monthly

        return breakdown

    def get_runway_at_month(self, month: str, burn_rate: Optional[float] = None) -> float:
        """
        Calculate runway from a specific month.

        Args:
            month: Starting month
            burn_rate: Optional custom burn rate (defaults to average)

        Returns:
            Runway in months
        """
        position = self.get_position(month)
        if not position:
            return 0

        burn = burn_rate or self.get_average_monthly_burn()
        if burn <= 0:
            return float('inf')

        return position.closing / burn

    def to_dataframe_dict(self) -> List[Dict]:
        """Convert positions to list of dicts for DataFrame creation."""
        return [
            {
                "Month": p.month,
                "Opening": p.opening,
                "Inflows": p.inflows,
                "Outflows": p.outflows,
                "Closing": p.closing,
            }
            for p in self.positions
        ]

    def get_waterfall_data(self) -> List[Dict]:
        """
        Get data for waterfall chart visualization.

        Returns:
            List of dicts with measure, x, y for waterfall chart
        """
        data = [
            {"x": "Opening Balance", "y": self.opening_balance, "measure": "absolute"},
        ]

        for pos in self.positions:
            data.append({
                "x": f"{pos.month} Inflows",
                "y": pos.inflows,
                "measure": "relative",
            })
            data.append({
                "x": f"{pos.month} Outflows",
                "y": -pos.outflows,
                "measure": "relative",
            })

        data.append({
            "x": "Closing Balance",
            "y": self.get_year_end_position(),
            "measure": "total",
        })

        return data

    def __repr__(self):
        return (
            f"CashFlowModel("
            f"opening={self.opening_balance:,.0f}, "
            f"inflows={self.get_total_inflows():,.0f}, "
            f"outflows={self.get_total_outflows():,.0f}, "
            f"closing={self.get_year_end_position():,.0f})"
        )
