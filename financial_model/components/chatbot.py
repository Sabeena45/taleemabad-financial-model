"""
AI Chatbot Component for Financial Dashboard
Provides intelligent, context-aware assistance using Claude API.
"""

import streamlit as st
import anthropic
import os
from typing import List, Dict, Optional
from datetime import datetime


class FinancialChatbot:
    """
    AI-powered chatbot that helps users understand the financial dashboard.
    Context-aware: knows which tab the user is on and their current data.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize chatbot with Claude API."""
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def get_system_context(self, current_tab: str, dashboard_data: Dict) -> str:
        """
        Build context about the dashboard state for Claude.
        """
        context = f"""You are a helpful financial analyst assistant embedded in Taleemabad's Financial Dashboard.

CURRENT CONTEXT:
- User is viewing: {current_tab}
- Opening Balance: ${dashboard_data.get('opening_balance', 0):,.0f}
- Year-End Projected Surplus: ${dashboard_data.get('projected_surplus', 0):,.0f}
- Total Grants 2026: ${dashboard_data.get('total_grants', 0):,.0f}
- Average Monthly Burn: ${dashboard_data.get('avg_burn', 0):,.0f}
- Current Runway: {dashboard_data.get('runway_months', 0):.1f} months

KEY PROGRAMS:
- NIETE ICT (Islamabad): 90,000 students, $10.62/child/year (variable), $13.46/child/year (total)
- Rawalpindi: 37,000 students, $3.53/child/year

MAJOR GRANTS:
- Mulago: $950,000 (41% of total)
- Prevail: $950,000 (41% of total)
- NIETE-ICT: $638,535 (government contract)
- Dovetail: $400,000

EXPENSE BREAKDOWN:
- Head Office: $1,685,539 (66% - salaries, operations, subscriptions)
- Program Operations: $873,817 (general field operations)
- NIETE ICT: $405,793 (Islamabad government contract)
- Prevail Rawalpindi: $217,423 (specific program)
- Data Collection: $95,406 (Akademos research)

AI & TECHNOLOGY COSTS (Annual):
- Total AI Tools: $84,120/year (3.3% of budget)
- LLM Providers: $38,400/year (Anthropic, OpenAI, xAI, Gemini @ $800/mo each)
- Replit: $27,600/year (highest single tool)
- Potential LLM savings: $19,200-$28,800/year by consolidating

AUDIT RED FLAGS:
- 82% of grants from 2 funders (Mulago + Prevail) - high concentration risk
- Non-Salary Expenses: $499,598 with no itemized breakdown
- Programme Operations: $873,817 but student count unknown (can't calculate efficiency)
- 4 LLM providers instead of 1-2 (redundant)

YOUR ROLE:
- Explain financial concepts clearly and concisely
- Help users understand the dashboard tabs and metrics
- Answer "what-if" questions based on the data
- Suggest which tab to visit for specific questions
- Use real numbers from the context above

STYLE:
- Be conversational but professional
- Use examples from Taleemabad's actual data
- Keep responses under 200 words unless asked for detail
- Use bullet points for clarity
- Format numbers with $ and commas

If asked to explain a tab:
- Executive Summary: Overview of 2026 budget health
- Cash Flow: Month-by-month inflows/outflows
- Scenarios: Stress-test the budget (optimistic/pessimistic)
- Grant Dependency: Analyze risk if grants fall through
- Runway: Calculate how long money lasts
- Growth: Plan expansion and funding needs
- Insights & Audit: AI-powered analysis with cost optimization recommendations

RECOMMENDATIONS TO MENTION WHEN RELEVANT:
1. Consolidate LLM providers (4→2) to save $19-29K/year
2. Get Programme Ops student count to calculate efficiency
3. Request Non-Salary Expenses itemization ($499K)
4. Review Engineering headcount after June (NIETE ICT ends)
5. Diversify grants - target no funder >25% of total
"""
        return context

    def generate_response(
        self,
        user_message: str,
        chat_history: List[Dict],
        current_tab: str,
        dashboard_data: Dict
    ) -> str:
        """
        Generate AI response using Claude API.
        """
        if not self.client:
            return "⚠️ Chatbot unavailable: ANTHROPIC_API_KEY not set. Please add it to Railway environment variables."

        # Build message history for Claude
        messages = []
        for msg in chat_history[-10:]:  # Keep last 10 messages for context
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self.get_system_context(current_tab, dashboard_data),
                messages=messages
            )

            return response.content[0].text

        except Exception as e:
            return f"⚠️ Error: {str(e)}"

    def render_chat_widget(
        self,
        current_tab: str,
        dashboard_data: Dict
    ):
        """
        Render the chat interface in Streamlit sidebar with enhanced accessibility.
        Uses custom CSS classes from the design system for consistent styling.
        """
        st.sidebar.markdown("---")

        # Accessible header with ARIA
        st.sidebar.markdown("""
            <h3 id="chat-heading" style="margin-bottom: 1rem;">
                💬 Ask the AI Assistant
            </h3>
        """, unsafe_allow_html=True)

        # Check if API key is available
        if not self.client:
            st.sidebar.markdown("""
                <div role="alert" aria-live="polite" class="chat-message" style="background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 0.75rem;">
                    <strong>⚠️ Chatbot disabled</strong><br>
                    <span style="font-size: 0.85rem;">Add ANTHROPIC_API_KEY to Railway environment variables</span>
                </div>
            """, unsafe_allow_html=True)
            return

        # Initialize chat history in session state
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Suggested questions based on current tab
        suggestions = self._get_suggested_questions(current_tab)

        with st.sidebar.expander("💡 Suggested Questions", expanded=False):
            for suggestion in suggestions:
                if st.button(suggestion, key=f"suggest_{hash(suggestion)}", use_container_width=True):
                    # Add suggestion to chat
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": suggestion,
                        "timestamp": datetime.now()
                    })
                    # Generate response
                    response = self.generate_response(
                        suggestion,
                        st.session_state.chat_history[:-1],
                        current_tab,
                        dashboard_data
                    )
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "timestamp": datetime.now()
                    })
                    st.rerun()

        # Chat history display with accessibility
        if st.session_state.chat_history:
            # Create accessible chat container
            st.sidebar.markdown("""
                <div class="chat-container" role="log" aria-label="Chat conversation" aria-live="polite" aria-relevant="additions">
            """, unsafe_allow_html=True)

            chat_container = st.sidebar.container(height=400)
            with chat_container:
                for idx, msg in enumerate(st.session_state.chat_history[-6:]):  # Show last 6 messages
                    role = msg["role"]
                    content = msg["content"]

                    # Use custom styled messages with ARIA
                    if role == "user":
                        st.sidebar.markdown(f"""
                            <div class="chat-message chat-message-user" role="listitem" aria-label="You said">
                                {content}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.sidebar.markdown(f"""
                            <div class="chat-message chat-message-assistant" role="listitem" aria-label="Assistant replied">
                                {content}
                            </div>
                        """, unsafe_allow_html=True)

            st.sidebar.markdown("</div>", unsafe_allow_html=True)

            # Clear chat button with accessibility
            if st.sidebar.button("🗑️ Clear Chat", use_container_width=True, help="Clear all chat messages"):
                st.session_state.chat_history = []
                st.rerun()

        # Chat input with accessibility label
        user_input = st.sidebar.chat_input("Ask a question...", key="chat_input")

        if user_input:
            # Add user message
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now()
            })

            # Generate AI response
            response = self.generate_response(
                user_input,
                st.session_state.chat_history[:-1],
                current_tab,
                dashboard_data
            )

            # Add assistant response
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now()
            })

            st.rerun()

    def _get_suggested_questions(self, current_tab: str) -> List[str]:
        """Get suggested questions based on current tab."""
        suggestions = {
            "Executive Summary": [
                "What's our financial health for 2026?",
                "Explain the key metrics",
                "How much money do we have?"
            ],
            "Cash Flow Forecasting": [
                "When do we receive grants?",
                "Which months are tight?",
                "Explain cash flow basics"
            ],
            "Scenario Analysis": [
                "What's the worst case scenario?",
                "How do I stress-test the budget?",
                "What if revenue drops 20%?"
            ],
            "Grant Dependency Analysis": [
                "What if we lose Mulago?",
                "Are we too dependent on one grant?",
                "Which grants are critical?"
            ],
            "Runway Calculator": [
                "How long can we survive?",
                "Explain runway calculation",
                "What's our burn rate?"
            ],
            "Growth Scenarios": [
                "What's our cost per child?",
                "How much to reach 200K students?",
                "Explain NIETE ICT contract"
            ],
            "Insights & Audit": [
                "Where can we cut costs?",
                "Are our AI subscriptions too high?",
                "Which department is overspending?",
                "What are the red flags in our budget?"
            ]
        }

        return suggestions.get(current_tab, [
            "What can this dashboard do?",
            "Explain the budget overview",
            "Where should I start?"
        ])
