"""
Shared financial calculation utilities.
All calculations use only data from budget_2026.py.
"""

from typing import Dict, List, Optional
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.budget_2026 import (
    OPENING_BALANCE,
    TOTAL_EXPENSES,
    TOTAL_INFLOWS,
    MONTHLY_EXPENSES,
    MONTHLY_INFLOWS,
    GRANT_INCOME,
    TOTAL_GRANT_INCOME,
    EXCHANGE_RATE,
)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def calculate_runway(current_cash: float, monthly_burn: float) -> float:
    """
    Calculate runway in months.

    Args:
        current_cash: Available cash in USD
        monthly_burn: Average monthly expenses in USD

    Returns:
        Runway in months (float('inf') if burn rate is 0 or negative)
    """
    if monthly_burn <= 0:
        return float('inf')
    return current_cash / monthly_burn


def calculate_average_burn_rate(period: str = "full_year") -> float:
    """
    Calculate average monthly burn rate.

    Args:
        period: "full_year", "h1" (Jan-Jun), or "h2" (Jul-Dec)

    Returns:
        Average monthly burn rate in USD
    """
    if period == "h1":
        months = MONTHS[:6]
    elif period == "h2":
        months = MONTHS[6:]
    else:
        months = MONTHS

    total_expenses = sum(MONTHLY_EXPENSES.get(m, 0) for m in months)
    return total_expenses / len(months)


def calculate_cumulative_cash(
    opening_balance: float = OPENING_BALANCE,
    inflows: Optional[Dict[str, float]] = None,
    expenses: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Calculate cumulative cash position for each month.

    Args:
        opening_balance: Starting cash in USD
        inflows: Monthly inflows (defaults to budget data)
        expenses: Monthly expenses (defaults to budget data)

    Returns:
        Dict with month -> cumulative cash position
    """
    inflows = inflows or MONTHLY_INFLOWS
    expenses = expenses or MONTHLY_EXPENSES

    cumulative = {}
    cash = opening_balance

    for month in MONTHS:
        cash = cash + inflows.get(month, 0) - expenses.get(month, 0)
        cumulative[month] = cash

    return cumulative


def calculate_break_even(
    fixed_costs: float,
    variable_cost_ratio: float = 0.0,
) -> float:
    """
    Calculate break-even revenue point.

    Args:
        fixed_costs: Total fixed costs
        variable_cost_ratio: Variable costs as percentage of revenue (0-1)

    Returns:
        Break-even revenue amount
    """
    if variable_cost_ratio >= 1:
        return float('inf')
    return fixed_costs / (1 - variable_cost_ratio)


def calculate_grant_concentration() -> Dict[str, float]:
    """
    Calculate grant concentration metrics.

    Returns:
        Dict with concentration metrics:
        - largest_grant: Amount of largest single grant
        - largest_percentage: Percentage of total from largest grant
        - herfindahl_index: Sum of squared market shares (0-1, lower is more diversified)
        - diversification_score: 1 - largest_percentage (higher is better)
    """
    grants = {k: v["amount"] for k, v in GRANT_INCOME.items()}
    total = sum(grants.values())

    if total == 0:
        return {
            "largest_grant": 0,
            "largest_percentage": 0,
            "herfindahl_index": 0,
            "diversification_score": 1,
        }

    largest = max(grants.values())
    shares = [g / total for g in grants.values()]
    hhi = sum(s ** 2 for s in shares)

    return {
        "largest_grant": largest,
        "largest_percentage": largest / total,
        "herfindahl_index": hhi,
        "diversification_score": 1 - (largest / total),
    }


def simulate_grant_removal(grant_to_remove: str) -> Dict[str, float]:
    """
    Simulate impact of removing a grant from the portfolio.

    Args:
        grant_to_remove: Key of grant to remove (e.g., "mulago", "dovetail")

    Returns:
        Dict with impact metrics:
        - removed_amount: Amount of removed grant
        - new_total: New total grants
        - percentage_lost: Percentage of total lost
        - new_surplus: Projected surplus after removal
    """
    grant_to_remove = grant_to_remove.lower().replace(" ", "_")

    if grant_to_remove not in GRANT_INCOME:
        return {
            "error": f"Grant '{grant_to_remove}' not found",
            "available_grants": list(GRANT_INCOME.keys()),
        }

    removed_amount = GRANT_INCOME[grant_to_remove]["amount"]
    new_total = TOTAL_GRANT_INCOME - removed_amount

    # Calculate new surplus (simple: reduce inflows by grant amount)
    from data.budget_2026 import PROJECTED_SURPLUS
    new_surplus = PROJECTED_SURPLUS - removed_amount

    return {
        "removed_amount": removed_amount,
        "new_total": new_total,
        "percentage_lost": removed_amount / TOTAL_GRANT_INCOME,
        "new_surplus": new_surplus,
        "original_surplus": PROJECTED_SURPLUS,
    }


def calculate_growth_funding_gap(
    target_students: int,
    cost_per_student_per_year: float = 10.62,  # NIETE ICT variable cost/year; Rawalpindi is $3.53/year
) -> Dict[str, float]:
    """
    Calculate funding gap for student growth targets (annual cost basis).

    Args:
        target_students: Target number of students
        cost_per_student_per_year: Annual cost per student
            (default: $10.62 NIETE ICT variable, Rawalpindi: $3.53)

    Returns:
        Dict with funding gap analysis
    """
    from data.budget_2026 import UNIT_ECONOMICS

    current_students = sum(p["students"] for p in UNIT_ECONOMICS.values())
    additional_students = target_students - current_students
    additional_cost_per_year = additional_students * cost_per_student_per_year

    return {
        "current_students": current_students,
        "target_students": target_students,
        "additional_students": additional_students,
        "cost_per_student_per_year": cost_per_student_per_year,
        "additional_funding_needed_per_year": additional_cost_per_year,
    }


def convert_pkr_to_usd(amount_pkr: float, rate: float = EXCHANGE_RATE) -> float:
    """Convert PKR to USD."""
    return amount_pkr / rate


def convert_usd_to_pkr(amount_usd: float, rate: float = EXCHANGE_RATE) -> float:
    """Convert USD to PKR."""
    return amount_usd * rate


def get_low_cash_months(threshold: float = 500000) -> List[str]:
    """
    Get months where cash position falls below threshold.

    Args:
        threshold: Cash threshold in USD

    Returns:
        List of months with cash below threshold
    """
    cumulative = calculate_cumulative_cash()
    return [month for month, cash in cumulative.items() if cash < threshold]


__all__ = [
    "MONTHS",
    "calculate_runway",
    "calculate_average_burn_rate",
    "calculate_cumulative_cash",
    "calculate_break_even",
    "calculate_grant_concentration",
    "simulate_grant_removal",
    "calculate_growth_funding_gap",
    "convert_pkr_to_usd",
    "convert_usd_to_pkr",
    "get_low_cash_months",
]
