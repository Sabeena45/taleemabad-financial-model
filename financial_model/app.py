"""
Taleemabad Financial Modelling Dashboard
Streamlit app for scenario analysis, cash flow forecasting, and financial planning.

Source: Taleemabad Budget 2026 v2.0 Draft Baseline Internal
All data comes ONLY from the budget PDF - no hallucinated information.

Phase 2 Enhancements:
- Admin editing mode
- Scenario saving
- Export to Excel/PDF
- Google Sheets sync (optional)
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    SUBSCRIPTIONS,
)
from models.cashflow_model import CashFlowModel
from models.scenario_model import ScenarioModel, ScenarioType
from models.sensitivity_model import SensitivityModel

# Try to import chatbot (graceful fallback if not available)
try:
    from components.chatbot import FinancialChatbot
    CHATBOT_AVAILABLE = True
except ImportError:
    CHATBOT_AVAILABLE = False

# Try to import export functions (graceful fallback if not available)
try:
    from exports.excel_export import export_to_excel
    from exports.pdf_export import export_to_pdf
    EXPORTS_AVAILABLE = True
except ImportError:
    EXPORTS_AVAILABLE = False

# Try to import Google Sheets client
try:
    from integrations.sheets_client import GoogleSheetsClient, is_sheets_available
    SHEETS_AVAILABLE = is_sheets_available()
except ImportError:
    SHEETS_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Taleemabad Financial Model",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS from external file
from pathlib import Path
css_path = Path(__file__).parent / "styles" / "custom.css"
if css_path.exists():
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    # Fallback inline CSS if file not found
    st.markdown("""
    <style>
        .metric-card {
            background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
            padding: 20px;
            border-radius: 16px;
            color: white;
        }
        *:focus-visible {
            outline: 3px solid #8B5CF6;
            outline-offset: 2px;
        }
        button, input, select { min-height: 44px; }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False

if 'custom_assumptions' not in st.session_state:
    st.session_state.custom_assumptions = {
        'opening_balance': OPENING_BALANCE,
        'exchange_rate': EXCHANGE_RATE,
        'expense_multiplier': 1.0,
        'grant_probabilities': {name: 1.0 for name in GRANT_INCOME.keys()},
    }

if 'saved_scenarios' not in st.session_state:
    st.session_state.saved_scenarios = []

if 'sheets_spreadsheet_id' not in st.session_state:
    st.session_state.sheets_spreadsheet_id = ''

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_currency(value: float, prefix: str = "$") -> str:
    """Format number as currency."""
    if value >= 1_000_000:
        return f"{prefix}{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{prefix}{value/1_000:.0f}K"
    else:
        return f"{prefix}{value:,.0f}"


def create_gauge_chart(value: float, max_value: float, title: str) -> go.Figure:
    """Create a gauge chart for runway indicator."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"font": {"size": 48}, "suffix": " months"},
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"size": 16}},
        gauge={
            "axis": {"range": [0, max_value], "tickfont": {"size": 12}},
            "bar": {"color": "#10B981"},
            "steps": [
                {"range": [0, 3], "color": "#EF4444"},
                {"range": [3, 6], "color": "#F59E0B"},
                {"range": [6, 12], "color": "#10B981"},
                {"range": [12, max_value], "color": "#3B82F6"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 3,
            },
        }
    ))
    fig.update_layout(height=320, margin=dict(l=30, r=30, t=60, b=30))
    return fig


# Sidebar
with st.sidebar:
    st.image("https://taleemabad.com/wp-content/uploads/2023/03/taleemabad-logo.png", width=200)
    st.title("Financial Model")
    st.markdown("---")
    st.markdown("**Source:** Budget 2026 v2.0")
    st.markdown("**Updated:** January 2026")
    st.markdown("---")

    # Admin Mode Toggle
    st.markdown("### ⚙️ Settings")
    admin_mode = st.checkbox(
        "🔐 Edit Mode",
        value=st.session_state.admin_mode,
        key='admin_toggle',
        help="Enable to modify assumptions and save scenarios"
    )
    st.session_state.admin_mode = admin_mode

    if admin_mode:
        st.caption("✏️ Editing enabled - changes are session-only")

    st.markdown("---")

    st.markdown("### Quick Stats")
    # Use custom assumptions if in admin mode
    opening = st.session_state.custom_assumptions.get('opening_balance', OPENING_BALANCE)
    st.metric("Opening Balance", format_currency(opening))
    st.metric("Total Inflows", format_currency(TOTAL_INFLOWS))
    st.metric("Total Expenses", format_currency(TOTAL_EXPENSES))
    st.metric("Year-End Surplus", format_currency(PROJECTED_SURPLUS), delta=format_currency(PROJECTED_SURPLUS - opening))

    # Export Section
    st.markdown("---")
    st.markdown("### 📥 Export")

    if EXPORTS_AVAILABLE:
        # Initialize models for export
        export_model = CashFlowModel()
        export_scenario_model = ScenarioModel()
        export_sensitivity_model = SensitivityModel()

        col1, col2 = st.columns(2)
        with col1:
            try:
                excel_data = export_to_excel(
                    export_model,
                    export_scenario_model,
                    export_sensitivity_model,
                    st.session_state.custom_assumptions
                )
                st.download_button(
                    label="📊 Excel",
                    data=excel_data,
                    file_name=f"taleemabad_financial_model_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.button("📊 Excel", disabled=True, use_container_width=True)

        with col2:
            try:
                pdf_data = export_to_pdf(
                    export_model,
                    export_scenario_model,
                    export_sensitivity_model,
                    st.session_state.custom_assumptions
                )
                st.download_button(
                    label="📄 PDF",
                    data=pdf_data,
                    file_name=f"taleemabad_financial_model_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.button("📄 PDF", disabled=True, use_container_width=True)
    else:
        st.caption("Export requires: `pip install reportlab`")

    # Google Sheets Sync (if available)
    if SHEETS_AVAILABLE:
        st.markdown("---")
        st.markdown("### 🔗 Google Sheets")

        sheets_enabled = st.checkbox(
            "Enable Sheets Sync",
            key="sheets_sync_toggle",
            help="Sync data with Google Sheets"
        )

        if sheets_enabled:
            spreadsheet_id = st.text_input(
                "Spreadsheet ID",
                value=st.session_state.sheets_spreadsheet_id,
                help="From URL: docs.google.com/spreadsheets/d/[THIS_ID]/edit",
                key="sheets_id_input"
            )
            st.session_state.sheets_spreadsheet_id = spreadsheet_id

            if spreadsheet_id:
                if st.button("🔄 Sync from Sheet", use_container_width=True):
                    try:
                        client = GoogleSheetsClient()
                        assumptions = client.sync_assumptions(spreadsheet_id)
                        if assumptions:
                            st.session_state.custom_assumptions.update(assumptions)
                            st.success("✓ Synced!")
                            st.rerun()
                        else:
                            st.warning("No assumptions found in sheet")
                    except Exception as e:
                        st.error(f"Sync failed: {e}")


# =============================================================================
# AI CHATBOT ASSISTANT
# =============================================================================
if CHATBOT_AVAILABLE:
    # Initialize chatbot
    chatbot = FinancialChatbot()

    # Prepare dashboard context data
    model = CashFlowModel()
    dashboard_data = {
        'opening_balance': OPENING_BALANCE,
        'projected_surplus': PROJECTED_SURPLUS,
        'total_grants': TOTAL_GRANT_INCOME,
        'avg_burn': model.get_average_monthly_burn(),
        'runway_months': model.get_year_end_position() / model.get_average_monthly_burn(),
    }

    # Track current tab (initialize in session state)
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Executive Summary"

    # Render chatbot in sidebar
    chatbot.render_chat_widget(
        current_tab=st.session_state.current_tab,
        dashboard_data=dashboard_data
    )


# Main content with tabs (consolidated from 7 to 4)
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "💰 Financial Planning",
    "📈 Programs & Funding",
    "🔍 Insights",
])


# =============================================================================
# TAB 1: DASHBOARD (Executive Summary)
# =============================================================================
with tab1:
    st.session_state.current_tab = "Dashboard"
    st.header("📊 2026 Financial Dashboard")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Opening Balance",
            format_currency(OPENING_BALANCE),
            help="Cash on hand as of January 1, 2026"
        )

    with col2:
        st.metric(
            "Total Inflows",
            format_currency(TOTAL_INFLOWS),
            help="Grants + Partner Revenue + Rental"
        )

    with col3:
        st.metric(
            "Total Expenses",
            format_currency(TOTAL_EXPENSES),
            help="Head Office + Programs + Operations"
        )

    with col4:
        st.metric(
            "Projected Surplus",
            format_currency(PROJECTED_SURPLUS),
            delta=f"{(PROJECTED_SURPLUS/OPENING_BALANCE - 1)*100:+.0f}% vs Opening",
        )

    st.markdown("---")

    # Monthly cash flow chart
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Monthly Cash Flow")

        df_monthly = pd.DataFrame([
            {
                "Month": month,
                "Inflows": MONTHLY_INFLOWS[month],
                "Outflows": MONTHLY_EXPENSES[month],
                "Net": MONTHLY_INFLOWS[month] - MONTHLY_EXPENSES[month],
            }
            for month in MONTHS
        ])

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Inflows",
            x=df_monthly["Month"],
            y=df_monthly["Inflows"],
            marker_color="#10B981",
        ))
        fig.add_trace(go.Bar(
            name="Outflows",
            x=df_monthly["Month"],
            y=df_monthly["Outflows"],
            marker_color="#EF4444",
        ))
        fig.update_layout(
            barmode="group",
            height=400,
            yaxis_title="USD",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Grant Composition")

        grant_data = pd.DataFrame([
            {"Funder": k.replace("_", " ").title(), "Amount": v["amount"]}
            for k, v in GRANT_INCOME.items()
        ])

        fig = px.pie(
            grant_data,
            values="Amount",
            names="Funder",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Expense breakdown
    st.subheader("Expense Breakdown")

    expense_df = pd.DataFrame([
        {"Category": "Head Office (Salaries + Ops)", "Amount": EXPENSES["subtotal_head_office"]},
        {"Category": "NIETE ICT", "Amount": EXPENSES["niete_ict"]},
        {"Category": "Prevail Rawalpindi", "Amount": EXPENSES["prevail_rawalpindi"]},
        {"Category": "Programs (Other)", "Amount": EXPENSES["programs_other"]},
    ])

    fig = px.bar(
        expense_df,
        x="Amount",
        y="Category",
        orientation="h",
        color="Amount",
        color_continuous_scale="Blues",
    )
    fig.update_layout(height=300, showlegend=False, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

    st.info("""
    **Key Observations:**
    - Head Office accounts for 66% of total expenses ($1.69M)
    - Salaries are 46% of total budget ($1.19M)
    - Non-salary expenses ($500K) lack itemized breakdown - needs audit
    - Program costs are 34% of budget, covering 127K students
    """)


# =============================================================================
# TAB 2: FINANCIAL PLANNING (Cash Flow + Scenarios + Runway)
# =============================================================================
with tab2:
    st.session_state.current_tab = "Financial Planning"
    st.header("💰 Financial Planning")
    st.caption("Cash flow forecasting, scenario analysis, and runway calculations")

    # Initialize models
    model = CashFlowModel()
    scenario_model = ScenarioModel()
    scenario_model.run_all_scenarios()
    sensitivity_model = SensitivityModel()

    # Key metrics row at top
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Inflows", format_currency(model.get_total_inflows()))
    with col2:
        st.metric("Total Outflows", format_currency(model.get_total_outflows()))
    with col3:
        st.metric("Net Cash Flow", format_currency(model.get_net_cash_flow()))
    with col4:
        avg_burn = model.get_average_monthly_burn()
        current_runway = model.get_year_end_position() / avg_burn
        st.metric("Runway", f"{current_runway:.1f} months")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # CASH FLOW SECTION
    # -------------------------------------------------------------------------
    with st.expander("📈 **Cash Flow Forecast**", expanded=True):
        positions = model.to_dataframe_dict()
        df_positions = pd.DataFrame(positions)

        # Calculate cumulative
        cumulative = [OPENING_BALANCE]
        for i, row in df_positions.iterrows():
            cumulative.append(cumulative[-1] + row["Inflows"] - row["Outflows"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=["Opening"] + df_positions["Month"].tolist(),
            y=cumulative,
            fill="tozeroy",
            mode="lines+markers",
            name="Cash Position",
            line=dict(color="#3B82F6", width=2),
            fillcolor="rgba(59, 130, 246, 0.3)",
        ))
        fig.add_hline(y=500000, line_dash="dash", line_color="red", annotation_text="Minimum Threshold ($500K)")
        fig.update_layout(height=350, yaxis_title="USD", xaxis_title="Month")
        st.plotly_chart(fig, use_container_width=True)

        # Monthly details table
        show_cf_details = st.checkbox("📋 Show Monthly Details Table", key="show_cf_details")
        if show_cf_details:
            df_display = df_positions.copy()
            df_display["Closing"] = cumulative[1:]
            for col in ["Opening", "Inflows", "Outflows", "Closing"]:
                df_display[col] = df_display[col].apply(lambda x: f"${x:,.0f}")
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.info("""
        **Key Observations:**
        - Large inflow months: Feb ($946K), Apr ($897K), Nov ($519K)
        - Steady monthly burn: ~$213K average
        - Cash position stays above $500K threshold throughout 2026
        """)

    # -------------------------------------------------------------------------
    # SCENARIO ANALYSIS SECTION
    # -------------------------------------------------------------------------
    with st.expander("🎯 **Scenario Analysis**", expanded=False):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("##### Custom Scenario")
            revenue_mult = st.slider("Revenue Multiplier", 0.5, 1.5, 1.0, 0.05, format="%.2f", help="Adjust total revenue (1.0 = 100%)")
            expense_mult = st.slider("Expense Multiplier", 0.5, 1.5, 1.0, 0.05, help="Adjust total expenses")
            grant_prob = st.slider("Grant Probability", 0.0, 1.0, 1.0, 0.1, help="Probability of grants coming through")

            custom_result = scenario_model.run_scenario(
                ScenarioType.CUSTOM,
                revenue_multiplier=revenue_mult,
                expense_multiplier=expense_mult,
                grant_probability=grant_prob,
            )
            st.metric("Custom Surplus", format_currency(custom_result.year_end_surplus))
            st.metric("Runway (Months)", f"{custom_result.runway_months:.1f}")

            # Scenario Saving (Admin Mode only)
            if st.session_state.admin_mode:
                st.markdown("---")
                scenario_name = st.text_input("Scenario Name", key="save_scenario_name", placeholder="e.g., Conservative 2026")
                if st.button("💾 Save Scenario", use_container_width=True) and scenario_name:
                    st.session_state.saved_scenarios.append({
                        'name': scenario_name,
                        'timestamp': datetime.now().isoformat(),
                        'revenue_multiplier': revenue_mult,
                        'expense_multiplier': expense_mult,
                        'grant_probability': grant_prob,
                        'results': {'surplus': custom_result.year_end_surplus, 'runway': custom_result.runway_months}
                    })
                    st.success(f"✓ Saved: {scenario_name}")

        with col2:
            st.markdown("##### Scenario Comparison")
            comparison = scenario_model.compare_scenarios()
            scenarios = list(comparison.keys())
            surpluses = [comparison[s]["year_end_surplus"] for s in scenarios]
            colors = ["#10B981" if s > 0 else "#EF4444" for s in surpluses]

            fig = go.Figure(go.Bar(x=scenarios, y=surpluses, marker_color=colors, text=[format_currency(s) for s in surpluses], textposition="outside"))
            fig.update_layout(height=350, yaxis_title="Year-End Surplus (USD)")
            st.plotly_chart(fig, use_container_width=True)

        # Scenario details and saved scenarios
        show_scenario_details = st.checkbox("📊 Show Scenario Details Table", key="show_scenario_details")
        if show_scenario_details:
            df_scenarios = pd.DataFrame(scenario_model.to_comparison_dataframe_dict())
            for col in ["Total Inflows", "Total Expenses", "Year-End Surplus", "Minimum Cash"]:
                df_scenarios[col] = df_scenarios[col].apply(lambda x: f"${x:,.0f}")
            st.dataframe(df_scenarios, use_container_width=True, hide_index=True)

        if st.session_state.saved_scenarios:
            st.markdown("##### 📋 Saved Scenarios")
            for i, scenario in enumerate(st.session_state.saved_scenarios):
                show_saved = st.checkbox(f"**{scenario['name']}** - {scenario['timestamp'][:10]}", key=f"show_saved_{i}")
                if show_saved:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Surplus", format_currency(scenario['results']['surplus']))
                    with c2:
                        st.metric("Runway", f"{scenario['results']['runway']:.1f} months")
                    with c3:
                        st.metric("Revenue", f"{scenario['revenue_multiplier']*100:.0f}%")
                    with c4:
                        st.metric("Expenses", f"{scenario['expense_multiplier']*100:.0f}%")
                    if st.session_state.admin_mode:
                        if st.button(f"🗑️ Delete", key=f"delete_scenario_{i}"):
                            st.session_state.saved_scenarios.pop(i)
                            st.rerun()

        st.info("""
        **Key Observations:**
        - Base case: $1.27M surplus with 5.9 months runway
        - Pessimistic scenario: Surplus drops to $208K (30% revenue drop + 15% expense increase)
        - Even worst case maintains positive cash position
        """)

    # -------------------------------------------------------------------------
    # RUNWAY CALCULATOR SECTION
    # -------------------------------------------------------------------------
    with st.expander("⏱️ **Runway Calculator**", expanded=False):
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("##### Current Runway")
            fig = create_gauge_chart(current_runway, max_value=24, title="Months of Runway")
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Year-End Cash", format_currency(model.get_year_end_position()))
            st.metric("Average Monthly Burn", format_currency(avg_burn))

        with col2:
            st.markdown("##### Custom Calculator")
            custom_cash = st.number_input("Available Cash ($)", 0, 10_000_000, int(model.get_year_end_position()), 100000)
            custom_burn = st.number_input("Monthly Burn Rate ($)", 1, 1_000_000, int(avg_burn), 10000)
            custom_runway = custom_cash / custom_burn if custom_burn > 0 else 0
            st.metric("Calculated Runway", f"{custom_runway:.1f} months", delta=f"{custom_runway - current_runway:+.1f} vs current" if custom_runway != current_runway else None)

            # Depletion chart
            months_forward = min(int(custom_runway) + 6, 36)
            depletion_data = [{"Month": i, "Cash": max(custom_cash - (custom_burn * i), 0)} for i in range(months_forward)]
            fig = px.area(pd.DataFrame(depletion_data), x="Month", y="Cash", labels={"Month": "Months from Now", "Cash": "Remaining Cash (USD)"})
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)

        # Break-even analysis
        st.markdown("##### Break-Even Analysis")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Revenue Break-Even", f"{sensitivity_model.find_break_even_point('revenue'):+.0f}%", help="Revenue change for zero surplus")
        with c2:
            st.metric("Expense Break-Even", f"{sensitivity_model.find_break_even_point('expenses'):+.0f}%", help="Expense increase for zero surplus")

        st.info("""
        **Key Observations:**
        - Current runway: 5.9 months post-2026
        - Break-even requires 49% revenue decrease OR 49% expense increase
        - Strong financial cushion with $1.27M projected year-end surplus
        """)


# =============================================================================
# TAB 3: PROGRAMS & FUNDING (Growth + Grant Risk)
# =============================================================================
with tab3:
    st.session_state.current_tab = "Programs & Funding"
    st.header("📈 Programs & Funding")
    st.caption("Growth scenarios, cost efficiency, and grant dependency analysis")

    # Initialize
    sensitivity_model = SensitivityModel()
    grant_analysis = sensitivity_model.analyze_grant_dependency()

    # Key metrics row
    current_students = sum(p["students"] for p in UNIT_ECONOMICS.values())
    current_schools = sum(p.get("schools", 0) for p in PARTNER_REVENUE.values() if p.get("schools"))
    from utils.calculations import calculate_grant_concentration
    concentration = calculate_grant_concentration()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Students", f"{current_students:,}")
    with col2:
        st.metric("Total Schools", f"{current_schools:,}")
    with col3:
        st.metric("Total Grants", format_currency(TOTAL_GRANT_INCOME))
    with col4:
        st.metric("Diversification", f"{concentration['diversification_score']*100:.0f}%")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # GROWTH SCENARIOS SECTION
    # -------------------------------------------------------------------------
    with st.expander("🚀 **Growth Scenarios**", expanded=True):
        avg_cost = (
            UNIT_ECONOMICS["niete_ict"]["students"] * UNIT_ECONOMICS["niete_ict"]["cost_per_child"] +
            UNIT_ECONOMICS["prevail_rawalpindi"]["students"] * UNIT_ECONOMICS["prevail_rawalpindi"]["cost_per_child"]
        ) / current_students
        st.metric("Average Cost/Student/Year", f"${avg_cost:.2f}")

        # NIETE ICT Contract Breakdown (collapsible)
        show_niete = st.checkbox("📊 Show NIETE ICT Contract Breakdown (Islamabad)", key="show_niete")
        if show_niete:
            st.caption(f"Duration: {NIETE_ICT_CONTRACT['start_date']} - {NIETE_ICT_CONTRACT['end_date']} ({NIETE_ICT_CONTRACT['duration_months']} months)")

            bc1, bc2 = st.columns(2)
            with bc1:
                st.markdown("**Fixed Costs (One-time)**")
                fixed_costs = pd.DataFrame([
                    {"Component": "Research/TNA Primary", "PKR": "6,210,000", "USD": "$21,943"},
                    {"Component": "Virtual CPD Certification (L1-L3)", "PKR": "37,260,000", "USD": "$131,661"},
                    {"Component": "Research/TNA Induction Primary", "PKR": "6,210,000", "USD": "$21,943"},
                    {"Component": "Virtual Induction Certification", "PKR": "24,840,000", "USD": "$87,774"},
                    {"Component": "Establishment of Monitoring Cell", "PKR": "88,023,852", "USD": "$311,039"},
                    {"Component": "**Subtotal Fixed**", "PKR": "**162,543,852**", "USD": "**$574,360**"},
                ])
                st.dataframe(fixed_costs, hide_index=True, use_container_width=True)

            with bc2:
                st.markdown("**Variable Costs (Per-child related)**")
                variable_costs = pd.DataFrame([
                    {"Component": "Operational Cost Monitoring (24m)", "PKR": "214,624,754", "USD": "$758,392"},
                    {"Component": "Outsourced Recruitment (24m)", "PKR": "314,795,250", "USD": "$1,112,349"},
                    {"Component": "Management Fee (15%)", "PKR": "79,413,001", "USD": "$280,611"},
                    {"Component": "**Subtotal Variable**", "PKR": "**608,833,005**", "USD": "**$2,151,352**"},
                ])
                st.dataframe(variable_costs, hide_index=True, use_container_width=True)

            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1:
                st.metric("Total Contract", f"${NIETE_ICT_CONTRACT['total_usd']:,}")
            with tc2:
                st.metric("Cost/Child/Year (Variable)", f"${UNIT_ECONOMICS['niete_ict']['cost_per_child']:.2f}")
            with tc3:
                st.metric("Cost/Child/Year (Total)", f"${UNIT_ECONOMICS['niete_ict']['cost_per_child_total']:.2f}")
            with tc4:
                st.metric("Rawalpindi Cost/Year", f"${UNIT_ECONOMICS['prevail_rawalpindi']['cost_per_child']:.2f}")

        # Growth calculator
        st.markdown("##### Growth Funding Calculator")
        gc1, gc2 = st.columns([1, 1])

        with gc1:
            target_students = st.slider("Target Students", current_students, 500_000, 200_000, 10_000)
            cost_per_student = st.select_slider("Cost per Student per Year", options=[3.53, 5.0, 7.5, 10.0, 10.62, 12.5, 13.46, 15.0, 20.0], value=10.62, help="Rawalpindi: $3.53/child/yr | NIETE ICT: $10.62/child/yr (variable)")

            additional_students = target_students - current_students
            additional_funding_annual = additional_students * cost_per_student
            st.metric("Additional Students", f"{additional_students:,}")
            st.metric("Additional Funding/Year", format_currency(additional_funding_annual))

        with gc2:
            st.markdown("##### Cost Comparison (Per Year)")
            cost_comparison = pd.DataFrame([
                {"Program": "NIETE ICT (Variable)", "Cost/Student/Year": 10.62, "Students": 90000},
                {"Program": "NIETE ICT (Total)", "Cost/Student/Year": 13.46, "Students": 90000},
                {"Program": "Rawalpindi", "Cost/Student/Year": 3.53, "Students": 37000},
            ])
            fig = px.bar(cost_comparison, x="Program", y="Cost/Student/Year", color="Program", text="Cost/Student/Year")
            fig.update_layout(height=300, showlegend=False, yaxis=dict(range=[0, 18]), margin=dict(t=40, b=60))
            fig.update_traces(texttemplate="$%{text:.2f}/yr", textposition="outside", textfont=dict(size=14, color="#1A1A1A"))
            st.plotly_chart(fig, use_container_width=True)

        # Partner Revenue Projections (collapsible)
        show_partners = st.checkbox("📊 Show Partner Revenue Projections", key="show_partners")
        if show_partners:
            partner_data = [{"Partner": name.replace("_", " ").title(), "Monthly": data["monthly_usd"], "Annual": data["annual_total"], "Start": data["start_month"], "Schools": data["schools"]} for name, data in PARTNER_REVENUE.items() if data["monthly_usd"] > 0]
            df_partners = pd.DataFrame(partner_data)
            fig = px.bar(df_partners, x="Partner", y="Annual", color="Start", text="Annual", labels={"Annual": "Annual Revenue (USD)"})
            fig.update_layout(height=300)
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        # Fundraising pipeline (collapsible)
        show_pipeline = st.checkbox("🎯 Show Fundraising Pipeline", key="show_pipeline")
        if show_pipeline:
            pipeline_data = [{"Funder": funder.replace("_", " ").title(), "Amount": data["amount"], "Type": data["type"], "Timing": data.get("timing", "TBD")} for funder, data in FUNDRAISING_PIPELINE.items() if data["amount"] > 0 and funder != "deficit"]
            df_pipeline = pd.DataFrame(pipeline_data)
            fig = px.bar(df_pipeline, y="Funder", x="Amount", color="Type", orientation="h", text="Amount")
            fig.update_layout(height=300, yaxis={"categoryorder": "total ascending"})
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

            pc1, pc2 = st.columns(2)
            with pc1:
                st.metric("Fundraising Target", format_currency(FUNDRAISING_TARGET))
            with pc2:
                deficit = FUNDRAISING_PIPELINE.get("deficit", {}).get("amount", 0)
                st.metric("Gap to Fill", format_currency(deficit), delta="Unfunded")

        st.info("""
        **Key Observations:**
        - Rawalpindi model is 3× more cost-efficient ($3.53 vs $10.62/child/year)
        - NIETE ICT includes $574K in fixed costs (monitoring cell, CPD)
        - To reach 200K students: Need ~$776K/year additional funding at variable rate
        """)

    # -------------------------------------------------------------------------
    # GRANT DEPENDENCY SECTION
    # -------------------------------------------------------------------------
    with st.expander("⚠️ **Grant Dependency Risk**", expanded=False):
        gc1, gc2 = st.columns([1, 1])

        with gc1:
            st.markdown("##### Grant Portfolio")
            st.metric("Diversification Score", f"{concentration['diversification_score']*100:.0f}%", help="Higher is better (100% = perfectly diversified)")
            st.metric("Largest Grant Share", f"{concentration['largest_percentage']*100:.0f}%", help="Percentage from single largest grant")

            st.markdown("**Grant Amounts:**")
            for grant_name, data in grant_analysis.items():
                pct = data["percentage_of_total"]
                critical = "🔴" if data["critical"] else "🟢"
                st.write(f"{critical} **{grant_name.replace('_', ' ').title()}**: {format_currency(data['grant_amount'])} ({pct:.0f}%)")

        with gc2:
            st.markdown("##### What-If: Remove a Grant")
            selected_grant = st.selectbox("Select grant to simulate removal:", options=list(GRANT_INCOME.keys()), format_func=lambda x: x.replace("_", " ").title())

            if selected_grant:
                impact = grant_analysis[selected_grant]
                st.metric("Impact on Surplus", format_currency(impact["impact_on_surplus"]), delta="Loss")
                st.metric("New Year-End Surplus", format_currency(impact["new_surplus"]), delta="Critical!" if impact["critical"] else "Manageable")
                st.metric("New Runway (Months)", f"{impact['new_runway_months']:.1f}")

                if impact["critical"]:
                    st.error("⚠️ Removing this grant would result in a deficit!")
                else:
                    st.success("✅ Budget remains positive without this grant.")

        # Risk matrix
        st.markdown("##### Grant Risk Matrix")
        risk_data = [{"Grant": grant_name.replace("_", " ").title(), "Amount": data["grant_amount"], "% of Total": data["percentage_of_total"], "Impact": abs(data["impact_on_surplus"]), "Critical": "Yes" if data["critical"] else "No"} for grant_name, data in grant_analysis.items()]
        df_risk = pd.DataFrame(risk_data)
        fig = px.scatter(df_risk, x="% of Total", y="Impact", size="Amount", color="Critical", hover_name="Grant", color_discrete_map={"Yes": "#EF4444", "No": "#10B981"}, labels={"% of Total": "Concentration Risk (%)", "Impact": "Impact if Lost (USD)"})
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

        st.info("""
        **Key Observations:**
        - 82% of grants from 2 funders (Mulago + Prevail) - HIGH concentration risk
        - Losing either Mulago or Prevail drops surplus from $1.27M to ~$315K
        - Recommendation: Diversify so no funder >25% of total
        """)


# =============================================================================
# TAB 4: INSIGHTS & AUDIT
# =============================================================================
with tab4:
    st.session_state.current_tab = "Insights & Audit"
    st.header("🔍 Financial Insights & Audit")
    st.caption("AI-powered analysis of your budget data. All findings based on actual budget figures only.")

    # Financial Health Score
    col1, col2, col3, col4 = st.columns(4)

    # Calculate health metrics
    surplus_ratio = PROJECTED_SURPLUS / TOTAL_INFLOWS * 100
    runway_months = PROJECTED_SURPLUS / (TOTAL_EXPENSES / 12)
    grant_concentration = max(g["amount"] for g in GRANT_INCOME.values()) / TOTAL_GRANT_INCOME * 100

    with col1:
        health_score = min(100, int(50 + surplus_ratio + (runway_months * 2) - (grant_concentration / 2)))
        st.metric("Financial Health", f"{health_score}/100", help="Composite score based on surplus, runway, and diversification")

    with col2:
        st.metric("Surplus Ratio", f"{surplus_ratio:.1f}%", help="Projected surplus as % of inflows")

    with col3:
        st.metric("Post-2026 Runway", f"{runway_months:.1f} months", help="How long money lasts after Dec 2026")

    with col4:
        st.metric("Top Grant Concentration", f"{grant_concentration:.0f}%", delta="High Risk" if grant_concentration > 35 else "OK")

    st.markdown("---")

    # AI COSTS SECTION
    with st.expander("🤖 **AI & Technology Costs Analysis**", expanded=True):
        st.markdown("### Annual Technology Subscription Costs")

        # Calculate AI costs
        ai_tools = SUBSCRIPTIONS.get("ai_tools", {})
        productivity_tools = SUBSCRIPTIONS.get("productivity", {})

        ai_total = sum(tool.get("annual", 0) for tool in ai_tools.values())
        productivity_total = sum(tool.get("annual", 0) for tool in productivity_tools.values())
        total_subscriptions = ai_total + productivity_total

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("AI Tools", f"${ai_total:,}/year", help="LLMs, coding assistants, image gen")
        with col2:
            st.metric("Productivity", f"${productivity_total:,}/year", help="Adobe, Atlassian, etc.")
        with col3:
            pct_of_expenses = (total_subscriptions / TOTAL_EXPENSES) * 100
            st.metric("% of Total Budget", f"{pct_of_expenses:.1f}%")

        # AI costs breakdown chart
        ai_data = pd.DataFrame([
            {"Tool": name.replace("_", " ").title(), "Annual Cost": data.get("annual", 0), "Category": "AI"}
            for name, data in ai_tools.items()
        ])

        fig = px.bar(
            ai_data.sort_values("Annual Cost", ascending=True),
            y="Tool",
            x="Annual Cost",
            orientation="h",
            color="Annual Cost",
            color_continuous_scale="Reds",
            text="Annual Cost",
        )
        fig.update_layout(height=300, showlegend=False, title="AI Tool Costs (Annual)")
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        # LLM consolidation insight
        llm_providers = ["anthropic", "openai", "xai", "gemini"]
        llm_cost = sum(ai_tools.get(p, {}).get("annual", 0) for p in llm_providers)

        st.warning(f"""
        **⚠️ LLM Provider Consolidation Opportunity**

        You're paying **4 LLM providers** at $800/month each = **${llm_cost:,}/year**

        **Recommendation:** Consolidate to 1-2 providers to save **$19,200-$28,800/year**

        | Current | Recommended | Savings |
        |---------|-------------|---------|
        | Anthropic + OpenAI + xAI + Gemini | Anthropic + OpenAI | ~$19,200/yr |
        | All 4 providers | Single provider | ~$28,800/yr |
        """)

    # DEPARTMENT BUDGET ANALYSIS
    with st.expander("🏢 **Department Budget Analysis**", expanded=True):
        st.markdown("### Where Is the Money Going?")

        # Head Office breakdown
        head_office_breakdown = pd.DataFrame([
            {"Category": "Salaries (Dev Teams)", "Amount": EXPENSES["salaries_development_teams"], "% of Total": EXPENSES["salaries_development_teams"]/TOTAL_EXPENSES*100},
            {"Category": "Non-Salary Expenses", "Amount": EXPENSES["non_salary_expenses"], "% of Total": EXPENSES["non_salary_expenses"]/TOTAL_EXPENSES*100},
            {"Category": "Product", "Amount": EXPENSES["product"], "% of Total": EXPENSES["product"]/TOTAL_EXPENSES*100},
            {"Category": "Employee Wellbeing", "Amount": EXPENSES["employee_wellbeing"], "% of Total": EXPENSES["employee_wellbeing"]/TOTAL_EXPENSES*100},
            {"Category": "Strategy", "Amount": EXPENSES["strategy"], "% of Total": EXPENSES["strategy"]/TOTAL_EXPENSES*100},
            {"Category": "Subscriptions", "Amount": EXPENSES["subscriptions"], "% of Total": EXPENSES["subscriptions"]/TOTAL_EXPENSES*100},
            {"Category": "Tax", "Amount": EXPENSES["tax"], "% of Total": EXPENSES["tax"]/TOTAL_EXPENSES*100},
        ])

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("**Head Office ($1.69M = 66% of budget)**")
            fig = px.pie(
                head_office_breakdown,
                values="Amount",
                names="Category",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(height=350, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Program Operations ($874K = 34% of budget)**")
            program_breakdown = pd.DataFrame([
                {"Category": "NIETE ICT", "Amount": EXPENSES["niete_ict"]},
                {"Category": "Prevail Rawalpindi", "Amount": EXPENSES["prevail_rawalpindi"]},
                {"Category": "Programs Other", "Amount": EXPENSES["programs_other"]},
            ])
            fig = px.pie(
                program_breakdown,
                values="Amount",
                names="Category",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(height=350, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # Red flags
        st.error(f"""
        **🔴 Red Flags Identified**

        1. **Non-Salary Expenses: ${EXPENSES['non_salary_expenses']:,}** (20% of budget)
           - No itemized breakdown available in budget
           - **Action:** Request detailed breakdown from finance team

        2. **Program Operations Breakdown (${EXPENSES['program_operations']:,} total):**
           | Program | Cost | Students | Cost/Student |
           |---------|------|----------|--------------|
           | NIETE ICT | ${EXPENSES['niete_ict']:,} | 90,000 | $4.51 |
           | Prevail Rawalpindi | ${EXPENSES['prevail_rawalpindi']:,} | 37,000 | $5.88 |
           | Programs Other | ${EXPENSES['programs_other']:,} | TBD | TBD |

           **Note:** Program Operations is the combined total of the above three sub-items
        """)

    # HEADCOUNT EFFICIENCY
    with st.expander("👥 **Headcount Efficiency Trend**", expanded=False):
        st.markdown("### Staff Changes: Jan-Jun vs Jul-Dec 2026")

        # Prepare headcount data
        jan_jun = HEADCOUNT["jan_jun_2026"]["by_department"]
        jul_dec = HEADCOUNT["jul_dec_2026"]["by_department"]

        dept_names = list(jan_jun.keys())
        headcount_df = pd.DataFrame({
            "Department": [d.replace("_", " ").upper() for d in dept_names],
            "Jan-Jun": [jan_jun[d] for d in dept_names],
            "Jul-Dec": [jul_dec[d] for d in dept_names],
        })
        headcount_df["Change"] = headcount_df["Jul-Dec"] - headcount_df["Jan-Jun"]
        headcount_df["% Change"] = (headcount_df["Change"] / headcount_df["Jan-Jun"].replace(0, 1) * 100).round(0)

        # Filter to show significant departments
        significant_depts = headcount_df[headcount_df["Jan-Jun"] >= 5].sort_values("Change")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Jan-Jun 2026",
            y=significant_depts["Department"],
            x=significant_depts["Jan-Jun"],
            orientation="h",
            marker_color="#3B82F6",
        ))
        fig.add_trace(go.Bar(
            name="Jul-Dec 2026",
            y=significant_depts["Department"],
            x=significant_depts["Jul-Dec"],
            orientation="h",
            marker_color="#10B981",
        ))
        fig.update_layout(
            barmode="group",
            height=400,
            title="Headcount by Department",
            xaxis_title="Staff Count",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Staff (Jan-Jun)", HEADCOUNT["jan_jun_2026"]["total"])
        with col2:
            st.metric("Total Staff (Jul-Dec)", HEADCOUNT["jul_dec_2026"]["total"])
        with col3:
            reduction = HEADCOUNT["jan_jun_2026"]["total"] - HEADCOUNT["jul_dec_2026"]["total"]
            st.metric("Reduction", f"-{reduction}", delta=f"-{reduction/HEADCOUNT['jan_jun_2026']['total']*100:.0f}%")

        st.info("""
        **Key Observations:**
        - **NIETE ICT:** 71 → 0 (project ends June 2026)
        - **Digital Learning:** 29 → 15 (48% reduction)
        - **Engineering:** 32 → 32 (no change) ⚠️

        **Question:** With NIETE ICT ending and DL shrinking, is 32 engineers still justified?
        """)

    # COST PER CHILD EFFICIENCY
    with st.expander("💰 **Cost Per Child Efficiency**", expanded=False):
        st.markdown("### Program Cost Efficiency Comparison")

        efficiency_data = pd.DataFrame([
            {
                "Program": "NIETE ICT (Islamabad)",
                "Students": 90000,
                "2026 Budget": EXPENSES["niete_ict"],
                "Cost/Child/Year": UNIT_ECONOMICS["niete_ict"]["cost_per_child"],
                "Duration": "Apr 2024 - Jun 2026",
            },
            {
                "Program": "Rawalpindi",
                "Students": 37000,
                "2026 Budget": EXPENSES["prevail_rawalpindi"],
                "Cost/Child/Year": UNIT_ECONOMICS["prevail_rawalpindi"]["cost_per_child"],
                "Duration": "Aug 2025 - Jun 2027",
            },
            {
                "Program": "Programs Other",
                "Students": "TBD",
                "2026 Budget": EXPENSES["programs_other"],
                "Cost/Child/Year": "TBD",
                "Duration": "Ongoing",
            },
        ])

        st.dataframe(efficiency_data, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            # Cost per child comparison chart
            cost_comparison = pd.DataFrame([
                {"Program": "Rawalpindi", "Cost/Child/Year": 3.53, "Type": "Most Efficient"},
                {"Program": "NIETE ICT (Variable)", "Cost/Child/Year": 10.62, "Type": "Standard"},
                {"Program": "NIETE ICT (Total)", "Cost/Child/Year": 13.46, "Type": "With Fixed"},
            ])
            fig = px.bar(
                cost_comparison,
                x="Program",
                y="Cost/Child/Year",
                color="Type",
                text="Cost/Child/Year",
                color_discrete_map={"Most Efficient": "#10B981", "Standard": "#3B82F6", "With Fixed": "#F59E0B"},
            )
            fig.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
            fig.update_layout(height=300, showlegend=True, title="Cost Per Child Per Year")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Why the difference?**")
            st.markdown("""
            | Factor | NIETE ICT | Rawalpindi |
            |--------|-----------|------------|
            | Fixed Costs | $574K (monitoring cell, CPD) | Minimal |
            | Staff | 71 dedicated staff | 6 staff |
            | Duration | 27 months | 23 months |
            | Model | Government contract | Grant-funded |

            **Insight:** Rawalpindi is 3× more cost-efficient because it doesn't carry fixed cost overhead.
            """)

    # REVENUE CONCENTRATION RISK
    with st.expander("⚠️ **Revenue Concentration Risk**", expanded=False):
        st.markdown("### Grant Dependency Analysis")

        # Calculate grant percentages
        grant_risk_data = []
        for name, data in GRANT_INCOME.items():
            pct = data["amount"] / TOTAL_GRANT_INCOME * 100
            risk = "🔴 Critical" if pct > 30 else ("🟡 Medium" if pct > 15 else "🟢 Low")
            grant_risk_data.append({
                "Funder": name.replace("_", " ").title(),
                "Amount": data["amount"],
                "% of Total": pct,
                "Risk Level": risk,
            })

        risk_df = pd.DataFrame(grant_risk_data).sort_values("Amount", ascending=False)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.dataframe(risk_df, use_container_width=True, hide_index=True)

        with col2:
            fig = px.pie(
                risk_df,
                values="Amount",
                names="Funder",
                color="Risk Level",
                color_discrete_map={"🔴 Critical": "#EF4444", "🟡 Medium": "#F59E0B", "🟢 Low": "#10B981"},
                hole=0.4,
            )
            fig.update_layout(height=300, title="Grant Portfolio Risk")
            st.plotly_chart(fig, use_container_width=True)

        # Top 2 concentration
        top_2_pct = (GRANT_INCOME["mulago"]["amount"] + GRANT_INCOME["prevail_general_ops"]["amount"] + GRANT_INCOME["prevail_implementation"]["amount"] + GRANT_INCOME["prevail_data_collection"]["amount"]) / TOTAL_GRANT_INCOME * 100

        st.error(f"""
        **🚨 High Concentration Risk**

        **{top_2_pct:.0f}% of grants from just 2 funders (Mulago + Prevail)**

        | Scenario | Impact |
        |----------|--------|
        | Lose Mulago ($950K) | Surplus drops to $315K, runway to 1.5 months |
        | Lose Prevail ($950K) | Surplus drops to $315K, runway to 1.5 months |
        | Lose both | **Deficit of $635K** |

        **Recommendation:** Diversify funding sources. Target no single funder >25% of total.
        """)

    # RECOMMENDATIONS SUMMARY
    st.markdown("---")
    st.subheader("📋 Recommendations Summary")

    rec_col1, rec_col2 = st.columns(2)

    with rec_col1:
        st.markdown("""
        **🔴 High Priority (Do Now)**

        1. **Consolidate LLM providers** (4→2)
           - Potential savings: $19-29K/year
           - Action: Choose Anthropic + OpenAI

        2. **Get Programme Ops student count**
           - Cannot calculate cost efficiency without it
           - Action: Request from programs team

        3. **Itemize Non-Salary Expenses**
           - $499K with no breakdown
           - Action: Request detailed list from finance
        """)

    with rec_col2:
        st.markdown("""
        **🟡 Medium Priority (This Quarter)**

        4. **Review Engineering headcount post-June**
           - NIETE ICT ends, DL shrinks 48%
           - Engineering stays at 32 - is this justified?

        5. **Diversify grant portfolio**
           - 82% from 2 funders is risky
           - Target: No funder >25% of total

        6. **Replit subscription review**
           - $2,300/month seems high
           - Potential savings: $15-20K/year
        """)

    # Download audit report
    st.markdown("---")
    audit_summary = f"""
# Taleemabad Financial Audit Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Key Metrics
- Financial Health Score: {health_score}/100
- Surplus Ratio: {surplus_ratio:.1f}%
- Post-2026 Runway: {runway_months:.1f} months
- Top Grant Concentration: {grant_concentration:.0f}%

## AI Costs
- Total AI Tools: ${ai_total:,}/year
- LLM Providers: ${llm_cost:,}/year (4 providers)
- Potential Savings: $19,200-$28,800/year

## Red Flags
1. Non-Salary Expenses: ${EXPENSES['non_salary_expenses']:,} (no itemization)
2. Programs Other: ${EXPENSES['programs_other']:,} (student count TBD)
3. Grant Concentration: {top_2_pct:.0f}% from 2 funders

## Recommendations
1. Consolidate LLM providers (save $19-29K/year)
2. Get Programs Other student count
3. Itemize Non-Salary Expenses
4. Review Engineering headcount post-June
5. Diversify grant portfolio (<25% per funder)
"""

    st.download_button(
        label="📥 Download Audit Report (TXT)",
        data=audit_summary,
        file_name=f"taleemabad_audit_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        use_container_width=True,
    )


# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6B7280; font-size: 12px;">
    Taleemabad Financial Model | Data Source: Budget 2026 v2.0 Draft Baseline Internal |
    All figures from budget PDF only - no external data
    </div>
    """,
    unsafe_allow_html=True,
)
