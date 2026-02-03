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
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title},
        gauge={
            "axis": {"range": [0, max_value]},
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
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
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


# Main content with tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Executive Summary",
    "💰 Cash Flow",
    "🎯 Scenarios",
    "🛡️ Grant Risk",
    "⏱️ Runway",
    "📈 Growth",
])


# =============================================================================
# TAB 1: EXECUTIVE SUMMARY
# =============================================================================
with tab1:
    st.session_state.current_tab = "Executive Summary"
    st.header("Executive Summary - 2026 Budget")

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
        {"Category": "Program Operations", "Amount": EXPENSES["program_operations"]},
        {"Category": "NIETE ICT", "Amount": EXPENSES["niete_ict"]},
        {"Category": "Prevail Rawalpindi", "Amount": EXPENSES["prevail_rawalpindi"]},
        {"Category": "Data Collection", "Amount": EXPENSES["data_collection"]},
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


# =============================================================================
# TAB 2: CASH FLOW FORECASTING
# =============================================================================
with tab2:
    st.session_state.current_tab = "Cash Flow Forecasting"
    st.header("Cash Flow Forecasting")

    model = CashFlowModel()

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Inflows", format_currency(model.get_total_inflows()))

    with col2:
        st.metric("Total Outflows", format_currency(model.get_total_outflows()))

    with col3:
        st.metric("Net Cash Flow", format_currency(model.get_net_cash_flow()))

    with col4:
        min_pos = model.get_minimum_cash_month()
        st.metric(
            "Minimum Cash",
            format_currency(min_pos.closing),
            delta=f"{min_pos.month}",
        )

    st.markdown("---")

    # Cumulative cash position chart
    st.subheader("Cumulative Cash Position")

    positions = model.to_dataframe_dict()
    df_positions = pd.DataFrame(positions)

    # Calculate cumulative
    cumulative = [OPENING_BALANCE]
    for i, row in df_positions.iterrows():
        cumulative.append(cumulative[-1] + row["Inflows"] - row["Outflows"])

    fig = go.Figure()

    # Area chart for cash position
    fig.add_trace(go.Scatter(
        x=["Opening"] + df_positions["Month"].tolist(),
        y=cumulative,
        fill="tozeroy",
        mode="lines+markers",
        name="Cash Position",
        line=dict(color="#3B82F6", width=2),
        fillcolor="rgba(59, 130, 246, 0.3)",
    ))

    # Add threshold line
    fig.add_hline(y=500000, line_dash="dash", line_color="red", annotation_text="Minimum Threshold ($500K)")

    fig.update_layout(
        height=400,
        yaxis_title="USD",
        xaxis_title="Month",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Monthly details table
    st.subheader("Monthly Details")

    df_display = df_positions.copy()
    df_display["Closing"] = cumulative[1:]  # Skip opening

    # Format for display
    for col in ["Opening", "Inflows", "Outflows", "Closing"]:
        df_display[col] = df_display[col].apply(lambda x: f"${x:,.0f}")

    st.dataframe(df_display, use_container_width=True, hide_index=True)


# =============================================================================
# TAB 3: SCENARIO ANALYSIS
# =============================================================================
with tab3:
    st.session_state.current_tab = "Scenario Analysis"
    st.header("Scenario Analysis")

    scenario_model = ScenarioModel()
    scenario_model.run_all_scenarios()

    # Scenario selector
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Custom Scenario")

        revenue_mult = st.slider(
            "Revenue Multiplier",
            min_value=0.5,
            max_value=1.5,
            value=1.0,
            step=0.05,
            format="%.0f%%",
            help="Adjust total revenue (1.0 = 100%)"
        )

        expense_mult = st.slider(
            "Expense Multiplier",
            min_value=0.5,
            max_value=1.5,
            value=1.0,
            step=0.05,
            help="Adjust total expenses"
        )

        grant_prob = st.slider(
            "Grant Probability",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.1,
            help="Probability of grants coming through"
        )

        # Run custom scenario
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
            st.markdown("**💾 Save Scenario**")

            scenario_name = st.text_input(
                "Scenario Name",
                key="save_scenario_name",
                placeholder="e.g., Conservative 2026"
            )

            if st.button("Save Scenario", use_container_width=True) and scenario_name:
                new_scenario = {
                    'name': scenario_name,
                    'timestamp': datetime.now().isoformat(),
                    'revenue_multiplier': revenue_mult,
                    'expense_multiplier': expense_mult,
                    'grant_probability': grant_prob,
                    'results': {
                        'surplus': custom_result.year_end_surplus,
                        'runway': custom_result.runway_months,
                    }
                }
                st.session_state.saved_scenarios.append(new_scenario)
                st.success(f"✓ Saved: {scenario_name}")

                # Also save to Google Sheets if connected
                if SHEETS_AVAILABLE and st.session_state.sheets_spreadsheet_id:
                    try:
                        client = GoogleSheetsClient()
                        client.write_scenario_results(
                            st.session_state.sheets_spreadsheet_id,
                            {
                                'name': scenario_name,
                                'timestamp': datetime.now().isoformat(),
                                'surplus': custom_result.year_end_surplus,
                                'runway': custom_result.runway_months,
                                'revenue_multiplier': revenue_mult,
                                'expense_multiplier': expense_mult,
                            }
                        )
                        st.caption("📤 Also saved to Google Sheets")
                    except Exception:
                        pass  # Silently fail if sheets sync fails

    with col2:
        st.subheader("Scenario Comparison")

        # Get all scenarios
        comparison = scenario_model.compare_scenarios()

        # Create comparison chart
        scenarios = list(comparison.keys())
        surpluses = [comparison[s]["year_end_surplus"] for s in scenarios]

        colors = ["#10B981" if s > 0 else "#EF4444" for s in surpluses]

        fig = go.Figure(go.Bar(
            x=scenarios,
            y=surpluses,
            marker_color=colors,
            text=[format_currency(s) for s in surpluses],
            textposition="outside",
        ))

        fig.update_layout(
            height=400,
            yaxis_title="Year-End Surplus (USD)",
            xaxis_title="Scenario",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Scenario details table
    st.subheader("Scenario Details")

    df_scenarios = pd.DataFrame(scenario_model.to_comparison_dataframe_dict())
    df_scenarios["Total Inflows"] = df_scenarios["Total Inflows"].apply(lambda x: f"${x:,.0f}")
    df_scenarios["Total Expenses"] = df_scenarios["Total Expenses"].apply(lambda x: f"${x:,.0f}")
    df_scenarios["Year-End Surplus"] = df_scenarios["Year-End Surplus"].apply(lambda x: f"${x:,.0f}")
    df_scenarios["Minimum Cash"] = df_scenarios["Minimum Cash"].apply(lambda x: f"${x:,.0f}")

    st.dataframe(df_scenarios, use_container_width=True, hide_index=True)

    # Monthly comparison chart
    st.subheader("Monthly Cash Position by Scenario")

    cash_flows = scenario_model.get_scenario_cash_flows()

    fig = go.Figure()
    colors = {"Base Case (Budget)": "#3B82F6", "Optimistic (Best Case)": "#10B981", "Pessimistic (Worst Case)": "#EF4444"}

    for scenario_name, monthly_data in cash_flows.items():
        fig.add_trace(go.Scatter(
            x=list(monthly_data.keys()),
            y=list(monthly_data.values()),
            mode="lines+markers",
            name=scenario_name,
            line=dict(color=colors.get(scenario_name, "#6B7280")),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="red")
    fig.update_layout(height=400, yaxis_title="Cash Position (USD)", legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    # Display saved scenarios
    if st.session_state.saved_scenarios:
        st.markdown("---")
        st.subheader("📋 Saved Scenarios")

        for i, scenario in enumerate(st.session_state.saved_scenarios):
            with st.expander(f"**{scenario['name']}** - {scenario['timestamp'][:10]}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Surplus", format_currency(scenario['results']['surplus']))
                with col2:
                    st.metric("Runway", f"{scenario['results']['runway']:.1f} months")
                with col3:
                    st.metric("Revenue", f"{scenario['revenue_multiplier']*100:.0f}%")
                with col4:
                    st.metric("Expenses", f"{scenario['expense_multiplier']*100:.0f}%")

                if st.session_state.admin_mode:
                    if st.button(f"🗑️ Delete", key=f"delete_scenario_{i}"):
                        st.session_state.saved_scenarios.pop(i)
                        st.rerun()


# =============================================================================
# TAB 4: GRANT DEPENDENCY ANALYSIS
# =============================================================================
with tab4:
    st.session_state.current_tab = "Grant Dependency Analysis"
    st.header("Grant Dependency Analysis")

    sensitivity_model = SensitivityModel()
    grant_analysis = sensitivity_model.analyze_grant_dependency()

    # Grant risk metrics
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Grant Portfolio")

        # Calculate concentration
        from utils.calculations import calculate_grant_concentration
        concentration = calculate_grant_concentration()

        st.metric(
            "Diversification Score",
            f"{concentration['diversification_score']*100:.0f}%",
            help="Higher is better (100% = perfectly diversified)"
        )

        st.metric(
            "Largest Grant Share",
            f"{concentration['largest_percentage']*100:.0f}%",
            help="Percentage of total from single largest grant"
        )

        # Grant list
        st.markdown("**Grant Amounts:**")
        for grant_name, data in grant_analysis.items():
            pct = data["percentage_of_total"]
            critical = "🔴" if data["critical"] else "🟢"
            st.write(f"{critical} **{grant_name.replace('_', ' ').title()}**: {format_currency(data['grant_amount'])} ({pct:.0f}%)")

    with col2:
        st.subheader("What-If: Remove a Grant")

        selected_grant = st.selectbox(
            "Select grant to simulate removal:",
            options=list(GRANT_INCOME.keys()),
            format_func=lambda x: x.replace("_", " ").title(),
        )

        if selected_grant:
            impact = grant_analysis[selected_grant]

            st.metric(
                "Impact on Surplus",
                format_currency(impact["impact_on_surplus"]),
                delta="Loss"
            )

            st.metric(
                "New Year-End Surplus",
                format_currency(impact["new_surplus"]),
                delta="Critical!" if impact["critical"] else "Manageable"
            )

            st.metric(
                "New Runway (Months)",
                f"{impact['new_runway_months']:.1f}",
            )

            if impact["critical"]:
                st.error("⚠️ Removing this grant would result in a deficit!")
            else:
                st.success("✅ Budget remains positive without this grant.")

    # Risk matrix visualization
    st.subheader("Grant Risk Matrix")

    # Create risk matrix data
    risk_data = []
    for grant_name, data in grant_analysis.items():
        risk_data.append({
            "Grant": grant_name.replace("_", " ").title(),
            "Amount": data["grant_amount"],
            "% of Total": data["percentage_of_total"],
            "Impact": abs(data["impact_on_surplus"]),
            "Critical": "Yes" if data["critical"] else "No",
        })

    df_risk = pd.DataFrame(risk_data)

    fig = px.scatter(
        df_risk,
        x="% of Total",
        y="Impact",
        size="Amount",
        color="Critical",
        hover_name="Grant",
        color_discrete_map={"Yes": "#EF4444", "No": "#10B981"},
        labels={"% of Total": "Concentration Risk (%)", "Impact": "Impact if Lost (USD)"},
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# TAB 5: RUNWAY CALCULATOR
# =============================================================================
with tab5:
    st.session_state.current_tab = "Runway Calculator"
    st.header("Runway Calculator")

    model = CashFlowModel()
    avg_burn = model.get_average_monthly_burn()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Current Runway")

        current_runway = model.get_year_end_position() / avg_burn

        # Runway gauge
        fig = create_gauge_chart(
            current_runway,
            max_value=24,
            title="Months of Runway"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.metric("Year-End Cash", format_currency(model.get_year_end_position()))
        st.metric("Average Monthly Burn", format_currency(avg_burn))

    with col2:
        st.subheader("Custom Runway Calculator")

        custom_cash = st.number_input(
            "Available Cash ($)",
            min_value=0,
            max_value=10_000_000,
            value=int(model.get_year_end_position()),
            step=100000,
        )

        custom_burn = st.number_input(
            "Monthly Burn Rate ($)",
            min_value=1,
            max_value=1_000_000,
            value=int(avg_burn),
            step=10000,
        )

        custom_runway = custom_cash / custom_burn if custom_burn > 0 else 0

        st.metric(
            "Calculated Runway",
            f"{custom_runway:.1f} months",
            delta=f"{custom_runway - current_runway:+.1f} vs current" if custom_runway != current_runway else None,
        )

        # Runway depletion chart
        st.subheader("Cash Depletion Timeline")

        months_forward = min(int(custom_runway) + 6, 36)
        depletion_data = []

        for i in range(months_forward):
            remaining = custom_cash - (custom_burn * i)
            depletion_data.append({
                "Month": i,
                "Cash": max(remaining, 0),
            })

        df_depletion = pd.DataFrame(depletion_data)

        fig = px.area(
            df_depletion,
            x="Month",
            y="Cash",
            labels={"Month": "Months from Now", "Cash": "Remaining Cash (USD)"},
        )
        fig.add_hline(y=0, line_dash="dash", line_color="red")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # Break-even analysis
    st.markdown("---")
    st.subheader("Break-Even Analysis")

    sensitivity_model = SensitivityModel()

    col1, col2 = st.columns(2)

    with col1:
        revenue_break_even = sensitivity_model.find_break_even_point("revenue")
        st.metric(
            "Revenue Break-Even",
            f"{revenue_break_even:+.0f}%",
            help="Revenue change that results in zero surplus"
        )

    with col2:
        expense_break_even = sensitivity_model.find_break_even_point("expenses")
        st.metric(
            "Expense Break-Even",
            f"{expense_break_even:+.0f}%",
            help="Expense increase that results in zero surplus"
        )


# =============================================================================
# TAB 6: GROWTH SCENARIOS
# =============================================================================
with tab6:
    st.session_state.current_tab = "Growth Scenarios"
    st.header("Growth Scenarios")

    # Current scale
    current_students = sum(p["students"] for p in UNIT_ECONOMICS.values())
    current_schools = sum(p.get("schools", 0) for p in PARTNER_REVENUE.values() if p.get("schools"))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Current Students", f"{current_students:,}")

    with col2:
        st.metric("Current Schools", f"{current_schools:,}")

    with col3:
        avg_cost = (
            UNIT_ECONOMICS["niete_ict"]["students"] * UNIT_ECONOMICS["niete_ict"]["cost_per_child"] +
            UNIT_ECONOMICS["prevail_rawalpindi"]["students"] * UNIT_ECONOMICS["prevail_rawalpindi"]["cost_per_child"]
        ) / current_students
        st.metric("Avg Cost/Student/Year", f"${avg_cost:.2f}")

    st.markdown("---")

    # NIETE ICT Contract Breakdown
    st.subheader("📊 NIETE ICT Contract Breakdown (Islamabad)")
    st.caption(f"Duration: {NIETE_ICT_CONTRACT['start_date']} - {NIETE_ICT_CONTRACT['end_date']} ({NIETE_ICT_CONTRACT['duration_months']} months = {UNIT_ECONOMICS['niete_ict']['duration_years']} years)")

    breakdown_col1, breakdown_col2 = st.columns(2)

    with breakdown_col1:
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

    with breakdown_col2:
        st.markdown("**Variable Costs (Per-child related)**")
        variable_costs = pd.DataFrame([
            {"Component": "Operational Cost Monitoring (24m)", "PKR": "214,624,754", "USD": "$758,392"},
            {"Component": "Outsourced Recruitment (24m)", "PKR": "314,795,250", "USD": "$1,112,349"},
            {"Component": "Management Fee (15%)", "PKR": "79,413,001", "USD": "$280,611"},
            {"Component": "**Subtotal Variable**", "PKR": "**608,833,005**", "USD": "**$2,151,352**"},
        ])
        st.dataframe(variable_costs, hide_index=True, use_container_width=True)

    # Total contract summary - Per Year metrics
    total_col1, total_col2, total_col3, total_col4 = st.columns(4)
    with total_col1:
        st.metric("Total Contract", f"${NIETE_ICT_CONTRACT['total_usd']:,}", help="771,376,857 PKR over 27 months")
    with total_col2:
        st.metric("Cost/Child/Year (Variable)", f"${UNIT_ECONOMICS['niete_ict']['cost_per_child']:.2f}", help="Variable costs ÷ students ÷ 2.25 years")
    with total_col3:
        st.metric("Cost/Child/Year (Total)", f"${UNIT_ECONOMICS['niete_ict']['cost_per_child_total']:.2f}", help="Total contract ÷ students ÷ 2.25 years")
    with total_col4:
        st.metric("Rawalpindi Cost/Year", f"${UNIT_ECONOMICS['prevail_rawalpindi']['cost_per_child']:.2f}", help="$250K ÷ 37K students ÷ 1.92 years")

    st.markdown("---")

    # Growth calculator
    st.subheader("Growth Funding Calculator (Annual Cost)")

    col1, col2 = st.columns([1, 1])

    with col1:
        target_students = st.slider(
            "Target Students",
            min_value=current_students,
            max_value=500_000,
            value=200_000,
            step=10_000,
        )

        cost_per_student = st.select_slider(
            "Cost per Student per Year",
            options=[3.53, 5.0, 7.5, 10.0, 10.62, 12.5, 13.46, 15.0, 20.0],
            value=10.62,
            help="Rawalpindi: $3.53/child/yr | NIETE ICT: $10.62/child/yr (variable) or $13.46/child/yr (total)"
        )

        additional_students = target_students - current_students
        additional_funding_annual = additional_students * cost_per_student

        st.metric("Additional Students", f"{additional_students:,}")
        st.metric("Additional Funding/Year", format_currency(additional_funding_annual))

    with col2:
        st.subheader("Cost Comparison (Per Year)")

        cost_comparison = pd.DataFrame([
            {"Program": "NIETE ICT (Variable)", "Cost/Student/Year": 10.62, "Students": 90000, "Contract": "$2.15M var", "Duration": "2.25 years"},
            {"Program": "NIETE ICT (Total)", "Cost/Student/Year": 13.46, "Students": 90000, "Contract": "$2.73M total", "Duration": "2.25 years"},
            {"Program": "Rawalpindi", "Cost/Student/Year": 3.53, "Students": 37000, "Contract": "$250K", "Duration": "1.92 years"},
        ])

        fig = px.bar(
            cost_comparison,
            x="Program",
            y="Cost/Student/Year",
            color="Program",
            text="Cost/Student/Year",
        )
        fig.update_layout(height=350, showlegend=False)
        fig.update_traces(texttemplate="$%{text:.1f}/yr", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        st.caption("💡 **All costs shown are per child per year**")
        st.caption("**Variable** = operational + recruitment + management (per-child related)")
        st.caption("**Total** = variable + fixed (research, CPD, establishment)")

    # Partner revenue projections
    st.subheader("Partner Revenue Projections")

    partner_data = []
    for name, data in PARTNER_REVENUE.items():
        if data["monthly_usd"] > 0:
            partner_data.append({
                "Partner": name.replace("_", " ").title(),
                "Monthly": data["monthly_usd"],
                "Annual": data["annual_total"],
                "Start": data["start_month"],
                "Schools": data["schools"],
            })

    df_partners = pd.DataFrame(partner_data)

    fig = px.bar(
        df_partners,
        x="Partner",
        y="Annual",
        color="Start",
        text="Annual",
        labels={"Annual": "Annual Revenue (USD)", "Start": "Start Month"},
    )
    fig.update_layout(height=400)
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # Fundraising pipeline
    st.subheader("Fundraising Pipeline")

    pipeline_data = []
    for funder, data in FUNDRAISING_PIPELINE.items():
        if data["amount"] > 0 and funder != "deficit":
            pipeline_data.append({
                "Funder": funder.replace("_", " ").title(),
                "Amount": data["amount"],
                "Type": data["type"],
                "Timing": data.get("timing", "TBD"),
            })

    df_pipeline = pd.DataFrame(pipeline_data)

    fig = px.bar(
        df_pipeline,
        y="Funder",
        x="Amount",
        color="Type",
        orientation="h",
        text="Amount",
        labels={"Amount": "USD"},
    )
    fig.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Fundraising Target", format_currency(FUNDRAISING_TARGET))
    with col2:
        deficit = FUNDRAISING_PIPELINE.get("deficit", {}).get("amount", 0)
        st.metric("Gap to Fill", format_currency(deficit), delta="Unfunded")


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
