"""
finance.py – Financial calculations and summary helpers for FinWise AI.
"""

from __future__ import annotations

import pandas as pd
from datetime import date


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

CURRENCY_SYMBOL = "₹"

EXPENSE_CATEGORIES = [
    "Food",
    "Shopping",
    "Education",
    "Travel",
    "Bills",
    "Healthcare",
    "Entertainment",
    "Other",
]

INCOME_CATEGORIES = [
    "Salary",
    "Freelance",
    "Investments",
    "Business",
    "Other",
]

PAYMENT_METHODS = [
    "Cash",
    "Credit Card",
    "Debit Card",
    "Bank Transfer",
    "Mobile Payment",
    "Other",
]


# ──────────────────────────────────────────────
# Core summary helpers
# ──────────────────────────────────────────────

def compute_summary(df: pd.DataFrame) -> dict:
    """
    Return total income, total expenses, savings, and balance
    from a transactions DataFrame.
    """
    if df.empty:
        return {"income": 0.0, "expenses": 0.0, "savings": 0.0, "balance": 0.0}

    income   = float(df.loc[df["type"] == "Income",  "amount"].sum())
    expenses = float(df.loc[df["type"] == "Expense", "amount"].sum())
    savings  = max(income - expenses, 0.0)
    balance  = income - expenses
    return {
        "income":   round(income,   2),
        "expenses": round(expenses, 2),
        "savings":  round(savings,  2),
        "balance":  round(balance,  2),
    }


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame with columns: month, income, expenses, savings
    grouped by calendar month (YYYY-MM).
    """
    if df.empty or "type" not in df.columns:
        return pd.DataFrame(columns=["month", "income", "expenses", "savings"])

    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.to_period("M").astype(str)

    income_monthly = (
        tmp[tmp["type"] == "Income"]
        .groupby("month")["amount"]
        .sum()
        .rename("income")
    )
    expense_monthly = (
        tmp[tmp["type"] == "Expense"]
        .groupby("month")["amount"]
        .sum()
        .rename("expenses")
    )

    summary = pd.concat([income_monthly, expense_monthly], axis=1).fillna(0.0)
    summary["savings"] = summary["income"] - summary["expenses"]
    summary = summary.reset_index().sort_values("month")
    return summary


def category_spending(df: pd.DataFrame, month: str | None = None) -> pd.DataFrame:
    """
    Return total spending per expense category.
    Optionally filter to a specific YYYY-MM month.
    """
    if df.empty or "type" not in df.columns:
        return pd.DataFrame(columns=["category", "amount"])
    expenses = df[df["type"] == "Expense"].copy()
    if month:
        expenses = expenses[expenses["date"].dt.to_period("M").astype(str) == month]

    if expenses.empty:
        return pd.DataFrame(columns=["category", "amount"])

    result = (
        expenses.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )
    return result


def filter_transactions(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    tx_type: str | None = None,
    category: str | None = None,
) -> pd.DataFrame:
    """Apply optional filters to the transactions DataFrame."""
    if df.empty or "type" not in df.columns:
        return df.copy()
    result = df.copy()
    if start_date:
        result = result[result["date"] >= pd.Timestamp(start_date)]
    if end_date:
        result = result[result["date"] <= pd.Timestamp(end_date)]
    if tx_type and tx_type != "All":
        result = result[result["type"] == tx_type]
    if category and category != "All":
        result = result[result["category"] == category]
    return result


def budget_vs_actual(
    df: pd.DataFrame, budgets_df: pd.DataFrame, month: str
) -> pd.DataFrame:
    """
    Return a DataFrame comparing budgeted vs. actual spending per category
    for the given YYYY-MM month, including a percentage and status column.
    """
    spending = category_spending(df, month=month)

    if budgets_df.empty:
        if spending.empty:
            return pd.DataFrame(columns=["category", "budget", "actual", "pct", "status"])
        spending = spending.rename(columns={"amount": "actual"})
        spending["budget"] = 0.0
        spending["pct"]    = 100.0
        spending["status"] = "No Budget Set"
        return spending

    merged = budgets_df[["category", "amount"]].rename(columns={"amount": "budget"})
    if not spending.empty:
        merged = merged.merge(
            spending.rename(columns={"amount": "actual"}),
            on="category",
            how="left",
        )
    else:
        merged["actual"] = 0.0

    merged["actual"] = merged["actual"].fillna(0.0)
    merged["pct"] = (merged["actual"] / merged["budget"] * 100).round(1)

    def _status(row: pd.Series) -> str:
        if row["pct"] >= 100:
            return "Exceeded"
        if row["pct"] >= 80:
            return "Near Limit"
        return "On Track"

    merged["status"] = merged.apply(_status, axis=1)
    return merged.sort_values("pct", ascending=False).reset_index(drop=True)


def savings_rate(summary: dict) -> float:
    """Return savings as a percentage of income (0–100)."""
    if summary["income"] == 0:
        return 0.0
    return round(summary["savings"] / summary["income"] * 100, 1)


def top_expense_categories(df: pd.DataFrame, n: int = 3) -> list[dict]:
    """Return the top-n expense categories with their totals."""
    spending = category_spending(df)
    return spending.head(n).to_dict(orient="records")
