# AI Chatbot Setup Guide

## Overview

The financial dashboard now includes an **AI-powered chatbot** that helps users understand the dashboard and ask questions about the budget.

## Features

✅ **Context-Aware** - Knows which tab you're on and the current data
✅ **Suggested Questions** - Provides relevant questions based on the current tab
✅ **Conversational** - Maintains chat history for follow-up questions
✅ **Real Data** - Uses actual numbers from your 2026 budget
✅ **Expert Explanations** - Can explain any section of the dashboard

## Setup Instructions

### 1. Add Anthropic API Key to Railway

1. Go to your Railway dashboard: https://railway.app/
2. Select your `taleemabad-financial-model` project
3. Click on "Variables" tab
4. Add a new variable:
   - **Name:** `ANTHROPIC_API_KEY`
   - **Value:** Your Claude API key (from console.anthropic.com)

### 2. Get Claude API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new key
5. Copy the key (starts with `sk-ant-`)

### 3. Deploy

Once you add the API key to Railway, the chatbot will automatically activate on the next deployment.

## Using the Chatbot

### Location
The chatbot appears in the **sidebar** on every page.

### Suggested Questions
Each tab has contextual suggested questions:

**Executive Summary:**
- "What's our financial health for 2026?"
- "Explain the key metrics"
- "How much money do we have?"

**Runway Calculator:**
- "How long can we survive?"
- "Explain runway calculation"
- "What's our burn rate?"

**Grant Dependency:**
- "What if we lose Mulago?"
- "Are we too dependent on one grant?"
- "Which grants are critical?"

### Example Conversations

**Q:** "Explain the runway calculator"
**A:** The Runway Calculator shows how many months you can operate before running out of money. It's calculated as: Year-End Cash ÷ Average Monthly Burn. For Taleemabad in 2026, you'll have $1,265,175 at year-end and burn ~$213K/month, giving you 6 months of runway into 2027.

**Q:** "What happens if Mulago delays?"
**A:** Mulago is your largest grant at $950K (41% of total funding). If it delays, your year-end surplus drops from $1.27M to $315K, and runway decreases from 6 months to 1.5 months. Use the Grant Dependency tab to simulate this scenario.

**Q:** "How much to reach 200K students?"
**A:** Currently serving 127,000 students (90K NIETE ICT + 37K Rawalpindi). To reach 200K students, you need 73K more. At $10.62/child/year (NIETE ICT variable cost), that's $775K annually. Check the Growth Scenarios tab for detailed calculations.

## Cost Estimate

**Claude API Pricing:**
- Claude 3.5 Sonnet: $3 per million input tokens, $15 per million output tokens
- Average chat response: ~500 tokens (~$0.01 per response)
- Estimated cost: **$5-20/month** for typical usage (500-2000 questions)

## Troubleshooting

### "Chatbot unavailable: ANTHROPIC_API_KEY not set"

**Solution:** Add the API key to Railway environment variables (see Setup step 1)

### Chatbot is slow

**Solution:** Claude API typically responds in 1-3 seconds. If slower:
- Check Railway logs for errors
- Verify API key is valid
- Ensure you have API credits remaining

### Chat history disappears

**Expected:** Chat history is session-only (clears on page refresh). This is intentional to save API costs.

**Workaround:** Use the "Clear Chat" button to manually reset, or just refresh the page.

## Features Coming Soon

- 📊 Export chat history
- 📝 Save favorite responses
- 🔗 Direct links to relevant tabs from chat
- 📈 Usage analytics

## Security

- API key is stored securely in Railway environment variables
- Not exposed in browser
- Not committed to git
- Rate-limited to prevent abuse

---

**Last Updated:** February 3, 2026
**Status:** Production-ready
**Cost:** $5-20/month estimated
