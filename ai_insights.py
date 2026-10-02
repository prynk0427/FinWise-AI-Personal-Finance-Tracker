"""
ai_insights.py – Rule-based spending analysis and personalised saving suggestions.

DISCLAIMER: This module uses deterministic, rule-based analysis.
It does NOT use machine learning or artificial intelligence.
Insights are for educational and informational purposes only and do NOT
constitute professional financial advice.
"""

from __future__ import annotations

import pandas as pd
from finance import monthly_summary, category_spending, CURRENCY_SYMBOL

C = CURRENCY_SYMBOL  # local alias


# ──────────────────────────────────────────────
# Thresholds
# ──────────────────────────────────────────────

SAVINGS_RATE_GOOD  = 20.0   # % of income saved – healthy target
SAVINGS_RATE_LOW   = 10.0   # % below which we flag low savings
SPIKE_THRESHOLD    = 0.30   # 30 % month-over-month increase = unusual spike
TOP_CATEGORY_PCT   = 0.40   # flagged if one category > 40 % of total expenses


# ──────────────────────────────────────────────
# Main insight generator
# ──────────────────────────────────────────────

def generate_insights(df: pd.DataFrame) -> list[dict]:
    """
    Analyse transaction data and return a list of insight dicts:
        {
            "type":    "positive" | "warning" | "info",
            "title":   str,
            "message": str,
        }

    All insights are rule-based pattern recognition – NOT predictions.
    """
    insights: list[dict] = []

    if df.empty:
        insights.append({
            "type":    "info",
            "title":   "No Data Yet",
            "message": "Add some transactions to start receiving personalised insights.",
        })
        return insights

    # ── 1. Savings-rate check ──────────────────────────────────────────────
    monthly = monthly_summary(df)
    if not monthly.empty:
        recent = monthly.iloc[-1]
        if recent["income"] > 0:
            rate = recent["savings"] / recent["income"] * 100
            if rate >= SAVINGS_RATE_GOOD:
                insights.append({
                    "type":    "positive",
                    "title":   "Great Savings Rate",
                    "message": (
                        f"You saved {rate:.1f}% of your income last month. "
                        f"Financial planners often suggest aiming for 20% or more – keep it up!"
                    ),
                })
            elif rate >= SAVINGS_RATE_LOW:
                insights.append({
                    "type":    "info",
                    "title":   "Moderate Savings Rate",
                    "message": (
                        f"Your savings rate last month was {rate:.1f}%. "
                        "Consider looking for small areas to cut back to reach the 20% goal."
                    ),
                })
            else:
                insights.append({
                    "type":    "warning",
                    "title":   "Low Savings Rate",
                    "message": (
                        f"You saved only {rate:.1f}% of your income last month. "
                        "Review your largest expense categories to identify potential savings."
                    ),
                })

    # ── 2. Highest spending category ──────────────────────────────────────
    expenses = df[df["type"] == "Expense"]
    if not expenses.empty:
        total_exp = expenses["amount"].sum()
        cat_totals = (
            expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
        )
        top_cat   = cat_totals.index[0]
        top_amt   = cat_totals.iloc[0]
        top_pct   = top_amt / total_exp * 100

        if top_pct >= TOP_CATEGORY_PCT * 100:
            insights.append({
                "type":    "warning",
                "title":   f"High Spending on {top_cat}",
                "message": (
                    f"{top_cat} accounts for {top_pct:.1f}% of your total expenses "
                    f"({C}{top_amt:,.2f}). Consider whether there are ways to reduce this."
                ),
            })
        else:
            insights.append({
                "type":    "info",
                "title":   f"Top Spending Category: {top_cat}",
                "message": (
                    f"Your highest spending category is {top_cat} at "
                    f"{C}{top_amt:,.2f} ({top_pct:.1f}% of total expenses)."
                ),
            })

    # ── 3. Month-over-month spending spike detection ───────────────────────
    if len(monthly) >= 2:
        prev_exp = monthly.iloc[-2]["expenses"]
        curr_exp = monthly.iloc[-1]["expenses"]
        if prev_exp > 0:
            change = (curr_exp - prev_exp) / prev_exp
            if change >= SPIKE_THRESHOLD:
                insights.append({
                    "type":    "warning",
                    "title":   "Unusual Spending Increase",
                    "message": (
                        f"Your expenses increased by {change * 100:.1f}% compared to the "
                        f"previous month ({C}{prev_exp:,.2f} → {C}{curr_exp:,.2f}). "
                        "Review your recent transactions for unexpected charges."
                    ),
                })
            elif change <= -SPIKE_THRESHOLD:
                insights.append({
                    "type":    "positive",
                    "title":   "Spending Decreased",
                    "message": (
                        f"Great news! Your expenses dropped by {abs(change) * 100:.1f}% "
                        f"compared to the previous month ({C}{prev_exp:,.2f} → {C}{curr_exp:,.2f})."
                    ),
                })

    # ── 4. Category-level month-over-month spikes ─────────────────────────
    if len(monthly) >= 2 and not expenses.empty:
        months = sorted(df["date"].dt.to_period("M").astype(str).unique())
        if len(months) >= 2:
            prev_month = months[-2]
            curr_month = months[-1]
            prev_cat = category_spending(df, month=prev_month).set_index("category")["amount"]
            curr_cat = category_spending(df, month=curr_month).set_index("category")["amount"]

            for cat in curr_cat.index:
                if cat in prev_cat.index and prev_cat[cat] > 0:
                    pct_chg = (curr_cat[cat] - prev_cat[cat]) / prev_cat[cat]
                    if pct_chg >= SPIKE_THRESHOLD and curr_cat[cat] >= 500:
                        insights.append({
                            "type":    "warning",
                            "title":   f"{cat} Spending Spike",
                            "message": (
                                f"{cat} spending rose {pct_chg * 100:.1f}% month-over-month "
                                f"({C}{prev_cat[cat]:,.2f} → {C}{curr_cat[cat]:,.2f})."
                            ),
                        })

    # ── 5. Rule-based saving tips ──────────────────────────────────────────
    tips = _saving_tips(df)
    insights.extend(tips)

    return insights


# ──────────────────────────────────────────────
# Rule-based saving tips
# ──────────────────────────────────────────────

_TIPS: dict[str, str] = {
    "Food": (
        "Meal prepping and cooking at home can significantly reduce food costs. "
        "Try planning your weekly meals and buying in bulk for staple items."
    ),
    "Shopping": (
        "Before making non-essential purchases, try a 48-hour wait rule to avoid impulse buying. "
        "Compare prices online before visiting stores."
    ),
    "Entertainment": (
        "Review your subscriptions – streaming, gaming, music. "
        "Consider sharing family plans or rotating services monthly."
    ),
    "Travel": (
        "Booking flights and accommodation in advance and travelling mid-week can cut costs. "
        "Set up price alerts on booking platforms."
    ),
    "Bills": (
        "Compare utility providers annually. Small reductions in electricity, internet, or "
        "insurance premiums can add up over a year."
    ),
    "Healthcare": (
        "Preventive care – regular check-ups and healthy habits – can lower long-term "
        "healthcare costs. Check if your employer offers wellness benefits."
    ),
    "Education": (
        "Look for free or discounted courses on platforms like Coursera, edX, or your local library. "
        "Many skills can be learned at low or no cost."
    ),
}


def _saving_tips(df: pd.DataFrame) -> list[dict]:
    """Return targeted saving tips for the user's top-3 expense categories."""
    tips: list[dict] = []
    expenses = df[df["type"] == "Expense"]
    if expenses.empty:
        return tips

    top_cats = (
        expenses.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )

    for cat in top_cats:
        if cat in _TIPS:
            tips.append({
                "type":    "info",
                "title":   f"Saving Tip: {cat}",
                "message": _TIPS[cat],
            })

    return tips


# ──────────────────────────────────────────────
# Budget breach summary
# ──────────────────────────────────────────────

def budget_breach_insights(bva_df: pd.DataFrame) -> list[dict]:
    """
    Given a budget-vs-actual DataFrame (from finance.budget_vs_actual),
    return insight dicts for categories that are over or near their budget.
    """
    insights: list[dict] = []
    if bva_df.empty:
        return insights

    for _, row in bva_df.iterrows():
        if row["status"] == "Exceeded":
            insights.append({
                "type":    "warning",
                "title":   f"Budget Exceeded: {row['category']}",
                "message": (
                    f"You spent {C}{row['actual']:,.2f} against a budget of {C}{row['budget']:,.2f} "
                    f"({row['pct']:.1f}% used). Consider adjusting your spending or budget."
                ),
            })
        elif row["status"] == "Near Limit":
            insights.append({
                "type":    "info",
                "title":   f"Approaching Budget: {row['category']}",
                "message": (
                    f"You've used {row['pct']:.1f}% of your {row['category']} budget "
                    f"({C}{row['actual']:,.2f} of {C}{row['budget']:,.2f}). "
                    "Be mindful of remaining spending this month."
                ),
            })

    return insights
