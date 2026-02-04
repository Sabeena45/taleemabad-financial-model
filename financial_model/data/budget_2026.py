"""
Taleemabad Budget 2026 Data
Source: Taleemabad Budget 2026_v2.0 Google Sheet (ID: 1hqgmD7jKuCO3BVrkPpWZbQfjaxYDPf76oMZut_7QI-4)
Updated: January 2026

IMPORTANT: All data in this file comes ONLY from the budget PDF.
No hallucinated or external data is included.
Page references are provided for audit trail.
"""

# Exchange rate (Page 3)
EXCHANGE_RATE = 283  # PKR/USD

# Opening balance as of 1 January 2026 (Page 3, Page 14)
OPENING_BALANCE = 723248  # USD

# Opening bank balances breakdown (Page 14)
BANK_BALANCES = {
    "orenda_pvt_ltd": {
        "total_usd": 608946,
        "total_pkr": 172331625,
        "breakdown": {
            "general": {"usd": 340914, "pkr": 96478761},  # From Grants/Donations/Private Schools
            "niete_isb": {"usd": 200197, "pkr": 56655784},
            "balochistan": {"usd": 67834, "pkr": 19197080},
            "prevail_rawalpindi": {"usd": 0, "pkr": 0},
        }
    },
    "orenda_welfare_trust": {"usd": 37602, "pkr": 10641494},
    "wise_taleemabad_inc": {"usd": 76700, "pkr": 21706075},
}

# Grant income structure (Page 1, Page 4)
GRANT_INCOME = {
    "prevail_general_ops": {
        "amount": 500000,  # Was 800,000, reduced by 300,000
        "timing": {
            "Feb": 250000,
            "Nov": 250000,
        },
        "notes": "For general operations to HO in the form of grant"
    },
    "prevail_implementation": {
        "amount": 250000,
        "timing": {
            "Feb": 250000,
        },
        "notes": "Implementation budget of $198,000 with $50,000 surplus"
    },
    "prevail_data_collection": {
        "amount": 200000,
        "timing": {
            "Feb": 200000,
        },
        "notes": "Akademos will perform data collection ($127,000)"
    },
    "dovetail": {
        "amount": 400000,
        "timing": {
            "Jan": 200000,
            "Dec": 200000,
        },
        "notes": "Grant agreement"
    },
    "mulago": {
        "amount": 950000,
        "timing": {
            "Apr": 700000,
            "Nov": 250000,
        },
        "notes": "Grant agreement"
    },
    "niete_ict": {
        "amount": 638535,
        "timing": {
            "Feb": 244723,
            "Apr": 189587,
            "Jun": 204225,
        },
        "notes": "Revenue from Government Program - As per Agreement"
    },
}

# Total grant income (Page 1)
TOTAL_GRANT_INCOME = 2300000  # Was 2,400,000, reduced by 100,000

# Private partner revenue (Page 4, Page 5)
PARTNER_REVENUE = {
    "moawin": {
        "monthly_usd": 1123,
        "start_month": "Jan",
        "end_month": "Dec",
        "schools": 179,
        "students": 7024,
        "annual_total": 13474,
        "notes": "Figures taken as per original contract signed"
    },
    "muslim_hands": {
        "monthly_usd": 0,
        "start_month": None,
        "end_month": None,
        "schools": 0,
        "students": 0,
        "annual_total": 0,
        "notes": "May not work with us - Out of the league"
    },
    "pen": {
        "monthly_usd": 1279,
        "start_month": "Jun",
        "end_month": "Dec",
        "schools": 200,
        "students": 8000,
        "annual_total": 8952,  # 7 months (Jun-Dec)
        "notes": "Expected to start from June 2026 onwards"
    },
    "akhuwat": {
        "monthly_usd": 1599,
        "start_month": "Jun",
        "end_month": "Dec",
        "schools": 250,  # 250 of 300 schools to be onboarded
        "students": 10000,
        "annual_total": 11190,  # 7 months (Jun-Dec)
        "notes": "Has 300 schools, 250 expected onboarded. Starts June 2026"
    },
    "world_bank": {
        "monthly_usd": 12367,
        "start_month": "Jun",
        "end_month": "Dec",
        "schools": 500,
        "students": None,  # Not specified
        "annual_total": 86572,  # 7 months (Jun-Dec)
        "notes": "As per Agreement"
    },
    "sindh": {
        "monthly_usd": 2473,
        "start_month": "Jun",
        "end_month": "Dec",
        "schools": 100,
        "students": None,  # Not specified
        "annual_total": 17314,  # 7 months (Jun-Dec)
        "notes": "As per Agreement"
    },
}

# Per school economics (Page 5)
PER_SCHOOL_ECONOMICS = {
    "fee_per_school_pkr": 7000,  # PKR per month
    "price_per_child_pkr": 47.5,  # PKR per month
    "avg_students_per_school": 40,
    "sales_tax_rate": 0.0476,  # ~4.76% based on Moawin calculation
}

# Total annual partner revenue (Page 1, Page 5)
TOTAL_PARTNER_REVENUE = 137502  # USD annual
# Previous estimate: 316,608 (difference of 179,106)

# Rental income (Page 4)
RENTAL_INCOME = {
    "child_life_tenant": {
        "annual_usd": 25246,
        "pkr_per_month": 555000,
        "payment_frequency": "Every third month",
        "timing": {
            "Jan": 5830,
            "Apr": 6472,
            "Jul": 6472,
            "Oct": 6472,
        }
    },
}

# Total inflows for 2026 (Page 3)
TOTAL_INFLOWS = 3101282  # USD

# Expense categories (Summary sheet)
EXPENSES = {
    # --- Head Office ($1,685,539) = Salaries + Non-Salary ---
    "salaries_development_teams": 1185942,  # Includes all dept salaries (Product, Strategy, etc.)
    "non_salary_expenses": 499598,  # See NON_SALARY_BREAKDOWN for itemization
    "subtotal_head_office": 1685539,

    # --- Program Operations ($873,817) = NIETE ICT + Prevail + Other ---
    # program_operations = niete_ict + prevail_rawalpindi + programs_other
    "program_operations": 873817,

    # Sub-items of program_operations (do NOT add to total separately):
    "niete_ict": 405793,
    "prevail_rawalpindi": 217423,  # Includes Akademos data collection ($95,406)
    "programs_other": 250601,
}

# Non-Salary Expenses breakdown (Summary sheet)
# Sub-items of non_salary_expenses ($499,598) — do NOT add to total separately
NON_SALARY_BREAKDOWN = {
    "office_expense": 116618,
    "utilities": 46253,
    "ai_cost": 84120,
    "employee_wellbeing": 126847,
    "subscriptions": 44616,
    "capex": 26502,
    "travel": 24558,
    "tax": 18290,
    "legal_professional": 11794,
}

# Total expenses (Page 3)
TOTAL_EXPENSES = 2559356  # USD

# Monthly expenses by period (Page 3)
MONTHLY_EXPENSES = {
    "Jan": 257913,
    "Feb": 222948,
    "Mar": 233955,
    "Apr": 250107,
    "May": 213767,
    "Jun": 212442,
    "Jul": 192577,
    "Aug": 205969,
    "Sep": 208570,
    "Oct": 188213,
    "Nov": 187948,
    "Dec": 184945,
}

# Projected surplus (Page 3)
PROJECTED_SURPLUS = 1265175  # USD at end of 2026

# Headcount (Page 2, Page 6-9)
HEADCOUNT = {
    "jan_jun_2026": {
        "total": 203,
        "core": 126,  # Excluding NIETE ICT project staff
        "by_department": {
            "a_and_f": 8,
            "admin": 7,
            "bsf": 6,
            "data_impact": 8,
            "dl": 29,  # Digital Learning
            "engineering": 32,
            "lt": 6,  # Leadership Team
            "p_and_c": 8,
            "prevail_rawalpindi_payroll": 6,
            "product": 14,
            "programs": 3,
            "project_niete_ict": 71,
            "strategy": 5,
        }
    },
    "jul_dec_2026": {
        "total": 117,
        "core": 111,
        "by_department": {
            "a_and_f": 7,
            "admin": 7,
            "bsf": 6,
            "data_impact": 8,
            "dl": 15,  # Reduced from 29
            "engineering": 32,
            "lt": 6,
            "p_and_c": 8,
            "prevail_rawalpindi_payroll": 6,
            "product": 14,
            "programs": 2,
            "project_niete_ict": 0,  # Project ends
            "strategy": 6,
        }
    },
}

# NIETE ICT Contract Breakdown (Islamabad)
# Full contract breakdown in PKR (inclusive of tax)
NIETE_ICT_CONTRACT = {
    "location": "Islamabad",
    "students": 90000,
    "start_date": "Apr 2024",
    "end_date": "Jun 2026",
    "duration_months": 27,
    "total_pkr": 771376857,
    "total_usd": 2726287,  # At 283 PKR/USD
    "breakdown_pkr": {
        # Fixed costs
        "research_tna_primary": 6210000,
        "virtual_cpd_certification_l1_l3": 37260000,
        "research_tna_induction_primary": 6210000,
        "virtual_induction_certification_primary": 24840000,
        "establishment_monitoring_cell_primary": 88023852,
        # Variable costs
        "operational_cost_monitoring_cell_24m": 214624754,
        "outsourced_recruitment_24m": 314795250,
        "outcome_based_management_fee_15pct": 79413001,  # 5% automatic + 10% outcome = 15%
    },
    "breakdown_usd": {
        # Fixed costs (at 283 PKR/USD)
        "research_tna_primary": 21943,
        "virtual_cpd_certification_l1_l3": 131661,
        "research_tna_induction_primary": 21943,
        "virtual_induction_certification_primary": 87774,
        "establishment_monitoring_cell_primary": 311039,
        # Variable costs
        "operational_cost_monitoring_cell_24m": 758392,
        "outsourced_recruitment_24m": 1112349,
        "outcome_based_management_fee_15pct": 280611,
    },
    "fixed_costs_usd": 574360,  # Sum of fixed costs
    "variable_costs_usd": 2151352,  # Sum of variable costs (for cost per child calc)
}

# Unit economics - Cost per child PER YEAR
# NIETE ICT (Islamabad): Apr 2024 - Jun 2026 (27 months = 2.25 years)
# Prevail Rawalpindi: Aug 2025 - Jun 2027 (23 months = 1.92 years)
UNIT_ECONOMICS = {
    "niete_ict": {
        "students": 90000,
        "total_contract_usd": 2726287,  # 771,376,857 PKR at 283
        "fixed_costs_usd": 574360,
        "variable_costs_usd": 2151352,
        # Per-year costs (primary metric)
        "cost_per_child": 10.62,  # USD/year (variable costs / students / 2.25 years)
        "cost_per_child_total": 13.46,  # USD/year (total contract / students / 2.25 years)
        # Full contract costs (for reference)
        "cost_per_child_contract": 23.90,  # USD total (variable costs / students)
        "cost_per_child_contract_total": 30.29,  # USD total (total contract / students)
        "start_date": "Apr 2024",
        "end_date": "Jun 2026",
        "duration_months": 27,
        "duration_years": 2.25,
        "location": "Islamabad",
    },
    "prevail_rawalpindi": {
        "students": 37000,
        "total_contract_usd": 250000,
        # Per-year costs (primary metric)
        "cost_per_child": 3.53,  # USD/year (total contract / students / 1.92 years)
        # Full contract costs (for reference)
        "cost_per_child_contract": 6.76,  # USD total (total contract / students)
        "start_date": "Aug 2025",
        "end_date": "Jun 2027",
        "duration_months": 23,
        "duration_years": 1.92,
        "location": "Rawalpindi",
    },
}

# Akademos contract details (Page 1)
AKADEMOS_CONTRACT = {
    "total_pkr": 36000000,
    "total_usd": 127208,
    "milestones": {
        "contract_signing_10pct": {"timing": "Jan 2026", "pkr": 3600000, "usd": 12721},
        "training_completion_10pct": {"timing": "Feb 2026", "pkr": 3600000, "usd": 12721},
        "round_1_completion_15pct": {"timing": "Feb-Mar 2026", "pkr": 5400000, "usd": 19081},
        "round_2_completion_25pct": {"timing": "Apr 2026", "pkr": 9000000, "usd": 31802},
        "round_3_completion_15pct": {"timing": "Aug 2026", "pkr": 5400000, "usd": 19081},
        "round_4_completion_25pct": {"timing": "Mar 2027", "pkr": 9000000, "usd": 31802},
    },
    "notes": "To be included in outflows under Rawalpindi program against Data collection expense"
}

# Fundraising pipeline for FY 2026 (Page 13)
FUNDRAISING_PIPELINE = {
    "mulago": {
        "amount": 250000,
        "type": "Renewal",
        "timing": "Dec 2026",
        "notes": "Will come near dec 2026"
    },
    "prevail": {
        "amount": 500000,
        "type": "Renewal",
        "timing": "Dec 2026",
        "notes": "Will come near dec 2026"
    },
    "dovetail": {
        "amount": 350000,
        "type": "Renewal",
        "timing": "Dec 2026",
        "notes": "Will come near dec 2026"
    },
    "rippleworks": {
        "amount": 1000000,
        "type": "New",
        "timing": "Dec 2025",
        "probability": 0.5,  # 50-50
        "notes": "50-50 - Probably near december 2025"
    },
    "gsma": {
        "amount": 331000,
        "type": "New",
        "timing": None,
        "notes": "Leave"
    },
    "vitol": {
        "amount": 200000,
        "type": "New",
        "timing": "Mar/Apr 2026",
        "notes": "Will be next year 2026 near march or April"
    },
    "agency_fund_youth_impact": {
        "amount": 250000,
        "type": "New",
        "timing": None,
        "notes": "Leave"
    },
    "deficit": {
        "amount": 319000,
        "type": "Gap",
        "timing": None,
        "notes": "Funding gap to be filled"
    },
}

# Total fundraising target (Page 13)
FUNDRAISING_TARGET = 3200000  # USD

# Monthly inflows (Page 4)
MONTHLY_INFLOWS = {
    "Jan": 206953,
    "Feb": 945846,
    "Mar": 1123,
    "Apr": 897182,
    "May": 1123,
    "Jun": 223066,
    "Jul": 25313,
    "Aug": 18841,
    "Sep": 18841,
    "Oct": 25313,
    "Nov": 518841,
    "Dec": 218841,
}

# Subscription costs (Page 12)
SUBSCRIPTIONS = {
    "ai_tools": {
        "cursor": {"monthly": 500, "annual": 6000},
        "lovable": {"monthly": 500, "annual": 6000},
        "github": {"monthly": 500, "annual": 6000},
        "replit": {"monthly": 2300, "annual": 27600},
        "anthropic": {"monthly": 800, "annual": 9600},
        "openai": {"monthly": 800, "annual": 9600},
        "xai": {"monthly": 800, "annual": 9600},
        "gemini": {"monthly": 800, "annual": 9600},
        "midjourney": {"monthly": 10, "annual": 120},
    },
    "productivity": {
        "adobe": {"monthly": 69, "annual": 828},
        "atlassian": {"monthly": 850, "annual": 10200},
        "bitwarden": {"monthly": 16, "annual": 192},
        "figma": {"monthly": 120, "annual": 1440},
        "google_cloud": {"monthly": 400, "annual": 4800},
        "microsoft_office_azure": {"monthly": 150, "annual": 1800},
        "microsoft_store": {"monthly": 750, "annual": 9000},
        "miro": {"monthly": 110, "annual": 1320},
        "linkedin": {"monthly": 300, "annual": 3600},
    },
}

# Monthly cash position projection (Page 3)
MONTHLY_CASH_POSITION = {
    "Jan": {"income_at_disposal": 930201, "expenses": 257913, "surplus": 672288},
    "Feb": {"income_at_disposal": 1618134, "expenses": 222948, "surplus": 1395186},
    "Mar": {"income_at_disposal": 1396309, "expenses": 233955, "surplus": 1162353},
    "Apr": {"income_at_disposal": 2059535, "expenses": 250107, "surplus": 1809427},
    "May": {"income_at_disposal": 1810550, "expenses": 213767, "surplus": 1596783},
    "Jun": {"income_at_disposal": 1819849, "expenses": 212442, "surplus": 1607407},
    "Jul": {"income_at_disposal": 1632720, "expenses": 192577, "surplus": 1440143},
    "Aug": {"income_at_disposal": 1458984, "expenses": 205969, "surplus": 1253014},
    "Sep": {"income_at_disposal": 1271855, "expenses": 208570, "surplus": 1063286},
    "Oct": {"income_at_disposal": 1088598, "expenses": 188213, "surplus": 900385},
    "Nov": {"income_at_disposal": 1419226, "expenses": 187948, "surplus": 1231278},
    "Dec": {"income_at_disposal": 1450119, "expenses": 184945, "surplus": 1265175},
}

# Revenue change summary (Page 1)
REVENUE_CHANGES = {
    "moawin": {"old": 4947, "new": 1123, "difference": -3824},
    "muslim_hands": {"old": 4947, "new": 0, "difference": -4947},
    "pen": {"old": 4947, "new": 1279, "difference": -3668},
    "akhuwat": {"old": 4947, "new": 1599, "difference": -3348},
    "total_monthly": {"old": 19788, "new": 4000, "difference": -15788},
    "total_annual": {"old": 316608, "new": 137502, "difference": -179106},
}


def get_monthly_inflow(month: str) -> float:
    """Get total inflow for a specific month."""
    return MONTHLY_INFLOWS.get(month, 0)


def get_monthly_expense(month: str) -> float:
    """Get total expense for a specific month."""
    return MONTHLY_EXPENSES.get(month, 0)


def get_grant_by_funder(funder: str) -> dict:
    """Get grant details by funder name."""
    return GRANT_INCOME.get(funder.lower().replace(" ", "_"), {})


def calculate_runway(current_cash: float, monthly_burn: float) -> float:
    """Calculate runway in months."""
    if monthly_burn <= 0:
        return float('inf')
    return current_cash / monthly_burn


def get_total_students() -> int:
    """Get total students across all programs."""
    return sum(p["students"] for p in UNIT_ECONOMICS.values())


# Export all constants for easy access
__all__ = [
    "EXCHANGE_RATE",
    "OPENING_BALANCE",
    "BANK_BALANCES",
    "GRANT_INCOME",
    "TOTAL_GRANT_INCOME",
    "PARTNER_REVENUE",
    "PER_SCHOOL_ECONOMICS",
    "TOTAL_PARTNER_REVENUE",
    "RENTAL_INCOME",
    "TOTAL_INFLOWS",
    "EXPENSES",
    "NON_SALARY_BREAKDOWN",
    "TOTAL_EXPENSES",
    "MONTHLY_EXPENSES",
    "PROJECTED_SURPLUS",
    "HEADCOUNT",
    "UNIT_ECONOMICS",
    "AKADEMOS_CONTRACT",
    "FUNDRAISING_PIPELINE",
    "FUNDRAISING_TARGET",
    "MONTHLY_INFLOWS",
    "SUBSCRIPTIONS",
    "MONTHLY_CASH_POSITION",
    "REVENUE_CHANGES",
]
