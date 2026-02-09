"""
Taleemabad Financial Dashboard — Minimalist Redesign
"Whoever comes and reaches immediately gets it"

Design Principles:
1. ONE primary number per section
2. Story first, details on demand
3. Color = meaning (green = good, red = alert)
4. Progressive disclosure (click to expand)
5. Five-second rule: key message clear in 5 seconds
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.budget_2026 import (
    OPENING_BALANCE,
    TOTAL_INFLOWS,
    TOTAL_EXPENSES,
    PROJECTED_SURPLUS,
    EXCHANGE_RATE,
    MONTHLY_INFLOWS,
    MONTHLY_EXPENSES,
    MONTHLY_CASH_POSITION,
    GRANT_INCOME,
    TOTAL_GRANT_INCOME,
    PARTNER_REVENUE,
    HEADCOUNT,
    UNIT_ECONOMICS,
    NIETE_ICT_CONTRACT,
    FUNDRAISING_PIPELINE,
    FUNDRAISING_TARGET,
    BANK_BALANCES,
    EXPENSES,
    NON_SALARY_BREAKDOWN,
    SUBSCRIPTIONS,
    AI_BUILT_PRODUCTS,
    AI_ROI,
)
from models.cashflow_model import CashFlowModel
from models.scenario_model import ScenarioModel, ScenarioType
from models.sensitivity_model import SensitivityModel

# Page config - wide but clean
st.set_page_config(
    page_title="Taleemabad 2026 Budget",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",  # Start collapsed for focus
)

# Minimalist CSS
st.markdown("""
<style>
    /* Clean, minimal aesthetic */
    .main > div { padding-top: 2rem; }

    /* Hero number styling */
    .hero-number {
        font-size: 4rem;
        font-weight: 700;
        line-height: 1;
        margin: 0;
    }
    .hero-label {
        font-size: 1rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .hero-green { color: #10B981; }
    .hero-blue { color: #3B82F6; }
    .hero-red { color: #EF4444; }
    .hero-amber { color: #F59E0B; }

    /* Card styling */
    .insight-card {
        background: #F9FAFB;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    /* Reduce metric clutter */
    [data-testid="stMetric"] {
        background: transparent;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem;
    }

    /* Cleaner expanders */
    .streamlit-expanderHeader {
        font-size: 1rem;
        font-weight: 600;
    }

    /* Hide sidebar by default */
    section[data-testid="stSidebar"] {
        width: 0px;
    }

    /* Status indicators */
    .status-healthy {
        background: #D1FAE5;
        color: #065F46;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-warning {
        background: #FEF3C7;
        color: #92400E;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-danger {
        background: #FEE2E2;
        color: #991B1B;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def format_currency(value: float, compact: bool = True) -> str:
    """Format as compact currency."""
    if compact:
        if value >= 1_000_000:
            return f"${value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"${value/1_000:.0f}K"
    return f"${value:,.0f}"


# =============================================================================
# HEADER — ONE SENTENCE STORY
# =============================================================================
st.markdown("# Taleemabad 2026 Budget")

# The ONE thing you need to know
surplus_status = "healthy" if PROJECTED_SURPLUS > 500000 else ("warning" if PROJECTED_SURPLUS > 0 else "danger")
status_class = f"status-{surplus_status}"
status_text = "Healthy" if surplus_status == "healthy" else ("Caution" if surplus_status == "warning" else "At Risk")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"""
    <p class="hero-label">PROJECTED YEAR-END SURPLUS</p>
    <p class="hero-number hero-green">{format_currency(PROJECTED_SURPLUS)}</p>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <span class="{status_class}">{status_text}</span>
    """, unsafe_allow_html=True)

# One-line summary
st.caption(f"Starting with {format_currency(OPENING_BALANCE)} → Receiving {format_currency(TOTAL_INFLOWS)} → Spending {format_currency(TOTAL_EXPENSES)} → Ending with {format_currency(OPENING_BALANCE + PROJECTED_SURPLUS)}")

st.markdown("---")

# =============================================================================
# THREE STORY CARDS — What matters most
# =============================================================================
c1, c2, c3 = st.columns(3)

# Initialize models
model = CashFlowModel()
sensitivity_model = SensitivityModel()
grant_analysis = sensitivity_model.analyze_grant_dependency()

# Calculate key insights
avg_burn = model.get_average_monthly_burn()
runway_months = PROJECTED_SURPLUS / avg_burn if avg_burn > 0 else 0
top_grant_pct = max(g["amount"] for g in GRANT_INCOME.values()) / TOTAL_GRANT_INCOME * 100
current_students = sum(p.get("students", 0) for p in UNIT_ECONOMICS.values())

with c1:
    st.markdown("### 💰 Cash Position")
    runway_color = "hero-green" if runway_months >= 6 else ("hero-amber" if runway_months >= 3 else "hero-red")
    st.markdown(f"""
    <p class="hero-number {runway_color}">{runway_months:.1f}</p>
    <p class="hero-label">MONTHS RUNWAY</p>
    """, unsafe_allow_html=True)
    st.caption(f"After 2026 ends, at {format_currency(avg_burn)}/month burn rate")

with c2:
    st.markdown("### ⚠️ Risk Level")
    risk_color = "hero-red" if top_grant_pct > 35 else ("hero-amber" if top_grant_pct > 25 else "hero-green")
    st.markdown(f"""
    <p class="hero-number {risk_color}">{top_grant_pct:.0f}%</p>
    <p class="hero-label">TOP FUNDER SHARE</p>
    """, unsafe_allow_html=True)
    st.caption(f"Mulago = {format_currency(GRANT_INCOME['mulago']['amount'])} of {format_currency(TOTAL_GRANT_INCOME)}")

with c3:
    st.markdown("### 📊 Efficiency")
    avg_cost = (
        UNIT_ECONOMICS["niete_ict"]["students"] * UNIT_ECONOMICS["niete_ict"]["cost_per_child"] +
        UNIT_ECONOMICS["prevail_rawalpindi"]["students"] * UNIT_ECONOMICS["prevail_rawalpindi"]["cost_per_child"]
    ) / current_students if current_students > 0 else 0
    cost_color = "hero-green" if avg_cost <= 5 else ("hero-amber" if avg_cost <= 10 else "hero-red")
    st.markdown(f"""
    <p class="hero-number {cost_color}">${avg_cost:.2f}</p>
    <p class="hero-label">COST PER CHILD/YEAR</p>
    """, unsafe_allow_html=True)
    st.caption(f"Reaching {current_students:,} students across programs")

st.markdown("---")

# =============================================================================
# VISUAL STORY — One chart that tells it all
# =============================================================================
st.markdown("### Cash Flow Story")
st.caption("How money flows through 2026")

# Build cumulative cash position
positions = []
cumulative = OPENING_BALANCE
for month in MONTHS:
    net = MONTHLY_INFLOWS[month] - MONTHLY_EXPENSES[month]
    cumulative += net
    positions.append({
        "Month": month,
        "Cash Position": cumulative,
        "Net Flow": net,
    })

df = pd.DataFrame(positions)

# Simple area chart - the story
fig = go.Figure()

# Cash position line
fig.add_trace(go.Scatter(
    x=df["Month"],
    y=df["Cash Position"],
    fill="tozeroy",
    mode="lines+markers",
    name="Cash Position",
    line=dict(color="#3B82F6", width=3),
    fillcolor="rgba(59, 130, 246, 0.15)",
    hovertemplate="<b>%{x}</b><br>Cash: $%{y:,.0f}<extra></extra>"
))

# Safety threshold
fig.add_hline(y=500000, line_dash="dash", line_color="#EF4444",
              annotation_text="$500K safety threshold",
              annotation_position="top left")

fig.update_layout(
    height=350,
    margin=dict(l=0, r=0, t=20, b=0),
    yaxis_title=None,
    xaxis_title=None,
    showlegend=False,
    yaxis=dict(tickformat="$,.0f"),
    hovermode="x unified",
)

st.plotly_chart(fig, use_container_width=True)

# Key insight below chart
big_months = [(m, MONTHLY_INFLOWS[m]) for m in MONTHS if MONTHLY_INFLOWS[m] > 500000]
if big_months:
    big_months_text = ", ".join([f"**{m}** ({format_currency(v)})" for m, v in sorted(big_months, key=lambda x: -x[1])[:3]])
    st.info(f"📅 **Big inflow months:** {big_months_text} — these are when major grants land")

st.markdown("---")

# =============================================================================
# DETAILS ON DEMAND — Expandable sections
# =============================================================================
st.markdown("### Details")

# TAB 1: Where money comes from
with st.expander("💵 **Where the Money Comes From** — Grant breakdown", expanded=False):
    col1, col2 = st.columns([2, 1])

    with col1:
        grant_data = pd.DataFrame([
            {"Funder": k.replace("_", " ").title(), "Amount": v["amount"]}
            for k, v in GRANT_INCOME.items()
        ]).sort_values("Amount", ascending=True)

        fig = px.bar(
            grant_data,
            y="Funder",
            x="Amount",
            orientation="h",
            text="Amount",
            color_discrete_sequence=["#3B82F6"]
        )
        fig.update_traces(texttemplate="%{x:$,.0f}", textposition="outside")
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, yaxis_title=None, xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Summary**")
        st.metric("Total Grants", format_currency(TOTAL_GRANT_INCOME))
        st.metric("Total Partners", format_currency(sum(p["annual_total"] for p in PARTNER_REVENUE.values())))
        st.metric("# of Funders", len(GRANT_INCOME))

        st.markdown("---")
        st.markdown("**⚠️ Concentration Risk**")
        top_2 = GRANT_INCOME["mulago"]["amount"] + sum(
            GRANT_INCOME[k]["amount"] for k in ["prevail_general_ops", "prevail_implementation", "prevail_data_collection"]
        )
        st.write(f"Top 2 funders = **{top_2/TOTAL_GRANT_INCOME*100:.0f}%** of grants")
        st.caption("Target: No funder > 25%")

# TAB 2: Where money goes
with st.expander("💸 **Where the Money Goes** — Expense breakdown", expanded=False):
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**By Category**")
        expense_simple = pd.DataFrame([
            {"Category": "Head Office", "Amount": EXPENSES["subtotal_head_office"], "Pct": EXPENSES["subtotal_head_office"]/TOTAL_EXPENSES*100},
            {"Category": "Programs", "Amount": EXPENSES["program_operations"], "Pct": EXPENSES["program_operations"]/TOTAL_EXPENSES*100},
        ])

        fig = px.pie(expense_simple, values="Amount", names="Category", hole=0.6,
                     color_discrete_sequence=["#3B82F6", "#10B981"])
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), showlegend=True,
                         legend=dict(orientation="h", yanchor="bottom", y=-0.2))
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Head Office Breakdown** ($1.69M)")
        st.write(f"- Salaries: **{format_currency(EXPENSES['salaries_development_teams'])}** (70%)")
        st.write(f"- Non-Salary: **{format_currency(EXPENSES['non_salary_expenses'])}** (30%)")

        st.markdown("**Non-Salary Top Items:**")
        top_non_salary = sorted(NON_SALARY_BREAKDOWN.items(), key=lambda x: -x[1])[:3]
        for name, amount in top_non_salary:
            st.write(f"  • {name.replace('_', ' ').title()}: {format_currency(amount)}")

        st.markdown("---")
        st.markdown("**Programs Breakdown** ($874K)")
        st.write(f"- NIETE ICT: {format_currency(EXPENSES['niete_ict'])} (90K students)")
        st.write(f"- Rawalpindi: {format_currency(EXPENSES['prevail_rawalpindi'])} (37K students)")
        st.write(f"- Other: {format_currency(EXPENSES['programs_other'])}")

# TAB 3: Program efficiency
with st.expander("📊 **Program Efficiency** — Cost per child comparison", expanded=False):
    col1, col2 = st.columns([2, 1])

    with col1:
        efficiency_data = pd.DataFrame([
            {"Program": "Rawalpindi", "Cost/Child": UNIT_ECONOMICS["prevail_rawalpindi"]["cost_per_child"], "Students": 37000},
            {"Program": "NIETE ICT (Variable)", "Cost/Child": UNIT_ECONOMICS["niete_ict"]["cost_per_child"], "Students": 90000},
            {"Program": "NIETE ICT (Total)", "Cost/Child": UNIT_ECONOMICS["niete_ict"]["cost_per_child_total"], "Students": 90000},
        ])

        colors = ["#10B981" if c <= 5 else "#F59E0B" if c <= 10 else "#EF4444" for c in efficiency_data["Cost/Child"]]

        fig = px.bar(efficiency_data, x="Program", y="Cost/Child", text="Cost/Child",
                     color="Program", color_discrete_sequence=colors)
        fig.add_hline(y=5, line_dash="dash", line_color="#EF4444",
                     annotation_text="$5 target", annotation_position="top right")
        fig.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        fig.update_layout(height=300, margin=dict(l=0, r=40, t=20, b=0), showlegend=False,
                         yaxis=dict(range=[0, 18]), yaxis_title="$/child/year")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Key Insight**")
        st.success("""
        Rawalpindi is **3× more efficient** than NIETE ICT

        **Why?**
        - No $574K fixed costs
        - Lean staffing (6 vs 71)
        - Grant vs contract model
        """)

        st.markdown("---")
        st.markdown("**Scaling Implications**")
        add_100k = 100000 * UNIT_ECONOMICS["prevail_rawalpindi"]["cost_per_child"]
        st.write(f"To reach +100K students:")
        st.write(f"- At Rawalpindi rate: **{format_currency(add_100k)}/year**")
        st.write(f"- At NIETE rate: **{format_currency(100000 * 10.62)}/year**")

# TAB 4: AI Investment ROI
with st.expander("🤖 **AI Investment ROI** — What $84K in AI tools delivers", expanded=False):
    col1, col2 = st.columns([2, 1])

    with col1:
        # Team comparison chart
        products = []
        for key, prod in AI_BUILT_PRODUCTS.items():
            products.append({"Product": prod["name"], "Type": "Actual Team", "People": prod["team_size"]})
            products.append({"Product": prod["name"], "Type": "Without AI", "People": prod["traditional_team_estimate"]})

        team_df = pd.DataFrame(products)

        fig = px.bar(
            team_df,
            y="Product",
            x="People",
            color="Type",
            barmode="group",
            orientation="h",
            text="People",
            color_discrete_map={"Actual Team": "#10B981", "Without AI": "#E5E7EB"},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=250,
            margin=dict(l=0, r=40, t=20, b=0),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title=None,
            xaxis_title="Team Size (people)",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption("AI tools enable 6.5 people to do the work of 25 — a **3.8× multiplier**")

    with col2:
        st.markdown(f"""
        <p class="hero-number hero-green">{AI_ROI['benefits_to_cost_ratio']}×</p>
        <p class="hero-label">ROI ON AI SPEND</p>
        """, unsafe_allow_html=True)

        st.metric("AI Spend / Employee", f"${AI_ROI['ai_cost_per_employee']}/year",
                  help=f"${AI_ROI['annual_ai_spend']:,} ÷ {AI_ROI['headcount_avg']} avg headcount")
        st.metric("Virtual FTEs Added", f"+{AI_ROI['virtual_ftes_added']}",
                  help="Equivalent full-time employees replaced by AI tools")
        st.metric("Estimated Savings", f"${AI_ROI['estimated_savings_low']/1000:.0f}-{AI_ROI['estimated_savings_high']/1000:.0f}K/year")

    st.success(f"""
    **Key Insight:** Every $1 spent on AI tools saves $1.50-2.70 in equivalent labor costs.
    At **${AI_ROI['ai_cost_per_employee']}/employee/year**, AI tools are the highest-ROI line item in the budget.

    **Products built with AI:** Rumi (1,878 users, 40K+ conversations), Balochistan WSP (2,517 observations), SchoolPilot (232 schools)
    """)

# TAB 5: What-if scenarios
with st.expander("🎯 **What-If Analysis** — Scenario planning", expanded=False):
    scenario_model = ScenarioModel()
    scenario_model.run_all_scenarios()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Pre-built Scenarios**")
        comparison = scenario_model.compare_scenarios()

        scenario_data = pd.DataFrame([
            {"Scenario": s, "Surplus": comparison[s]["year_end_surplus"]}
            for s in ["Base Case", "Optimistic", "Pessimistic"]
        ])

        colors = ["#10B981" if s > 0 else "#EF4444" for s in scenario_data["Surplus"]]

        fig = px.bar(scenario_data, x="Scenario", y="Surplus", text="Surplus",
                     color="Scenario", color_discrete_sequence=colors)
        fig.update_traces(texttemplate="%{text:$,.0f}", textposition="outside")
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Custom Scenario**")
        revenue_mult = st.slider("Revenue", 0.5, 1.5, 1.0, 0.1, format="%.0f%%", key="rev_slider")
        expense_mult = st.slider("Expenses", 0.5, 1.5, 1.0, 0.1, format="%.0f%%", key="exp_slider")

        custom_surplus = PROJECTED_SURPLUS * revenue_mult / expense_mult
        delta_pct = (custom_surplus / PROJECTED_SURPLUS - 1) * 100

        st.metric("Custom Surplus", format_currency(custom_surplus),
                 delta=f"{delta_pct:+.0f}%" if delta_pct != 0 else None)

        if custom_surplus < 0:
            st.error("⚠️ This scenario results in a deficit!")

# TAB 6: Key risks
with st.expander("⚠️ **Key Risks** — What could go wrong", expanded=False):
    st.markdown("""
    | Risk | Impact | Mitigation |
    |------|--------|------------|
    | **Lose Mulago ($950K)** | Surplus drops to $315K | Diversify: target no funder >25% |
    | **Lose Prevail ($950K)** | Surplus drops to $315K | Build relationships with 3-4 new funders |
    | **NIETE ICT ends (June)** | 71 staff transition | Already in budget - no surprise |
    | **Exchange rate drops** | PKR budgets increase in USD | Budget uses PKR 283/USD |
    """)

    st.markdown("---")
    st.markdown("**Break-Even Points**")

    be_col1, be_col2 = st.columns(2)
    with be_col1:
        rev_break = sensitivity_model.find_break_even_point('revenue')
        st.metric("Revenue can drop by", f"{abs(rev_break):.0f}%", help="Before hitting zero surplus")
    with be_col2:
        exp_break = sensitivity_model.find_break_even_point('expenses')
        st.metric("Expenses can rise by", f"{exp_break:.0f}%", help="Before hitting zero surplus")

st.markdown("---")

# =============================================================================
# FOOTER — Quick actions
# =============================================================================
col1, col2 = st.columns(2)

with col1:
    # Export button
    audit_text = f"""
Taleemabad 2026 Budget Summary
Generated: {datetime.now().strftime('%Y-%m-%d')}

KEY NUMBERS
- Opening Balance: {format_currency(OPENING_BALANCE, False)}
- Total Inflows: {format_currency(TOTAL_INFLOWS, False)}
- Total Expenses: {format_currency(TOTAL_EXPENSES, False)}
- Year-End Surplus: {format_currency(PROJECTED_SURPLUS, False)}
- Runway: {runway_months:.1f} months

RISK FACTORS
- Top funder concentration: {top_grant_pct:.0f}%
- Grant diversification needed

EFFICIENCY
- Avg cost per child: ${avg_cost:.2f}/year
- Students reached: {current_students:,}

AI INVESTMENT ROI
- Annual AI spend: ${AI_ROI['annual_ai_spend']:,}
- AI cost per employee: ${AI_ROI['ai_cost_per_employee']}/year
- ROI: {AI_ROI['benefits_to_cost_ratio']}x
- Virtual FTEs added: {AI_ROI['virtual_ftes_added']}
- Estimated savings: ${AI_ROI['estimated_savings_low']:,}-${AI_ROI['estimated_savings_high']:,}/year
"""
    st.download_button("📥 Export Summary", audit_text, file_name="budget_summary.txt",
                       mime="text/plain", use_container_width=True)

with col2:
    st.link_button("📄 Source: Budget 2026 v2.0",
                   "https://docs.google.com/spreadsheets/d/1hqgmD7jKuCO3BVrkPpWZbQfjaxYDPf76oMZut_7QI-4/edit",
                   use_container_width=True)

st.caption("Data source: Budget 2026 v2.0 Draft Baseline Internal | Last updated: February 2026")
