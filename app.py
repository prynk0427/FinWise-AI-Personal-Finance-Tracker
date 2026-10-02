"""
app.py – FinWise AI: AI-Based Personal Finance Tracker
Main Streamlit application entry point.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import io
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import database as db
import finance as fin
import ai_insights as ai

C = fin.CURRENCY_SYMBOL  # ₹

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="FinWise AI",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────

st.markdown(
    """
    <style>
        /* ── Sidebar ───────────────────────────── */
        [data-testid="stSidebar"] {background-color: #0f172a;}
        /* Scope color only to text elements – avoids overriding Streamlit's
           own alert boxes (blank yellow box bug). */
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] div.stRadio,
        [data-testid="stSidebar"] div.stMarkdown,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {color: #e2e8f0 !important;}
        [data-testid="stSidebar"] .stRadio label {
            font-size: 0.95rem; padding: 4px 0;
        }
        /* Sidebar disclaimer – explicit override */
        .sidebar-disclaimer {
            background: #1e293b; border: 1px solid #334155;
            border-radius: 8px; padding: 10px 14px;
            font-size: 0.80rem; color: #94a3b8 !important;
            line-height: 1.5;
        }

        /* ── Main content ──────────────────────── */
        /* Metric cards */
        div[data-testid="metric-container"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 18px 22px;
        }
        div[data-testid="metric-container"] label {
            font-size: 0.85rem !important;
            font-weight: 600;
            color: #64748b !important;
        }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: 700;
        }

        /* Section headers */
        h2 {color: #0f172a; font-weight: 700; margin-top: 0.3rem;}
        h3 {color: #1e293b; font-weight: 600;}

        /* Insight alert boxes */
        .alert-warning {
            background: #fef3c7; border-left: 4px solid #f59e0b;
            padding: 10px 14px; border-radius: 6px; margin: 6px 0;
            color: #78350f;
        }
        .alert-positive {
            background: #d1fae5; border-left: 4px solid #10b981;
            padding: 10px 14px; border-radius: 6px; margin: 6px 0;
            color: #064e3b;
        }
        .alert-info {
            background: #dbeafe; border-left: 4px solid #3b82f6;
            padding: 10px 14px; border-radius: 6px; margin: 6px 0;
            color: #1e3a5f;
        }

        /* Demo data banner */
        .demo-banner {
            background: #fef9c3; border: 1px solid #fde047;
            border-left: 4px solid #eab308;
            border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
            color: #713f12; font-size: 0.92rem;
        }

        /* Empty state */
        .empty-state {
            text-align: center; padding: 48px 24px;
            color: #94a3b8; font-size: 1rem;
        }
        .empty-state strong { color: #64748b; }

        /* Chart wrapper card */
        .chart-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 8px;
        }

        /* Progress bar label row */
        .prog-row {
            display: flex; justify-content: space-between;
            margin-bottom: 2px; font-size: 0.88rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Bootstrap database
# ─────────────────────────────────────────────

db.init_db()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def fmt(amount: float) -> str:
    """Format a number as Indian Rupees with comma separation."""
    return f"{C}{amount:,.2f}"


def month_label(yyyymm: str) -> str:
    """Convert '2025-01' → 'Jan 2025' for readable chart axes."""
    try:
        return datetime.strptime(yyyymm + "-01", "%Y-%m-%d").strftime("%b %Y")
    except ValueError:
        return yyyymm


# Shared chart layout defaults
_CHART_LAYOUT = dict(
    font=dict(family="Segoe UI, system-ui, sans-serif", size=13, color="#1f2328"),
    plot_bgcolor="#f8fafc",
    paper_bgcolor="#ffffff",
    margin=dict(t=50, b=60, l=70, r=30),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        bgcolor="rgba(0,0,0,0)", font=dict(size=12),
    ),
    hoverlabel=dict(bgcolor="#1e293b", font_color="#f1f5f9", font_size=13),
)

_YAXIS_INR = dict(
    tickprefix=C,
    showgrid=True,
    gridcolor="#e2e8f0",
    gridwidth=1,
    zeroline=True,
    zerolinecolor="#cbd5e1",
    tickfont=dict(size=12),
)

_XAXIS_BASE = dict(
    showgrid=False,
    tickfont=dict(size=12),
    linecolor="#cbd5e1",
)


def _render_insight(insight: dict) -> None:
    """Render a colour-coded insight card."""
    css_class = {
        "warning":  "alert-warning",
        "positive": "alert-positive",
        "info":     "alert-info",
    }.get(insight["type"], "alert-info")
    icon = {"warning": "⚠️", "positive": "✅", "info": "💡"}.get(insight["type"], "💡")
    st.markdown(
        f'<div class="{css_class}">'
        f'<strong>{icon} {insight["title"]}</strong><br>'
        f'<span style="font-size:0.9rem;">{insight["message"]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<h2 style='color:#38bdf8; margin-bottom:0;'>💰 FinWise AI</h2>"
        "<p style='color:#94a3b8; font-size:0.8rem; margin-top:2px;'>"
        "Personal Finance Tracker</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["📊 Dashboard", "💳 Transactions", "📋 Budgets",
         "🎯 Savings Goals", "🤖 AI Insights"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(
        "<div class='sidebar-disclaimer'>"
        "<strong style='color:#cbd5e1;'>⚠️ Disclaimer</strong><br>"
        "FinWise AI is for <em>educational and informational purposes only</em>. "
        "It does <strong>not</strong> provide professional financial advice. "
        "Consult a qualified financial adviser before making financial decisions."
        "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Data loader  (ttl=None + explicit clear on mutation)
# ─────────────────────────────────────────────

@st.cache_data(ttl=None)
def _load_transactions() -> pd.DataFrame:
    return db.get_all_transactions()


def refresh() -> None:
    """Invalidate all data caches and rerun."""
    st.cache_data.clear()
    st.rerun()


df_all = _load_transactions()

# ─────────────────────────────────────────────
# Demo-data banner  (shown only when demo rows exist)
# ─────────────────────────────────────────────

_has_demo = db.has_demo_data()
if _has_demo:
    st.markdown(
        "<div class='demo-banner'>"
        "🧪 <strong>Demo data is active.</strong> "
        "All figures below use sample data for illustration only — "
        "they do not reflect real transactions. "
        "Add your own data and click <em>Remove demo data</em> when ready."
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("🗑️ Remove all demo data", type="secondary",
                 key="btn_clear_demo"):
        db.clear_demo_data()
        refresh()


# ══════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ══════════════════════════════════════════════════════════════════

if page == "📊 Dashboard":
    st.title("📊 Financial Dashboard")
    st.markdown(
        f"<p style='color:#64748b; margin-top:-8px;'>"
        f"Overview as of <strong>{datetime.today().strftime('%B %d, %Y')}</strong></p>",
        unsafe_allow_html=True,
    )

    if df_all.empty:
        st.markdown(
            "<div class='empty-state'>"
            "📭 <strong>No transactions yet.</strong><br>"
            "Head over to the <em>Transactions</em> page to add your first record."
            "</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # ── KPI metrics ────────────────────────────────────────────────
    summary = fin.compute_summary(df_all)
    s_rate  = fin.savings_rate(summary)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Total Income",   fmt(summary["income"]))
    c2.metric("💸 Total Expenses", fmt(summary["expenses"]))
    c3.metric("🏦 Net Savings",    fmt(summary["savings"]))
    c4.metric("📈 Savings Rate",   f"{s_rate}%",
              delta="Good" if s_rate >= 20 else ("Fair" if s_rate >= 10 else "Low"),
              delta_color="normal" if s_rate >= 20 else "inverse")

    st.markdown("---")

    # ── Monthly Income vs Expenses — grouped bar chart ─────────────
    monthly = fin.monthly_summary(df_all)
    if not monthly.empty:
        st.subheader("📅 Monthly Income vs Expenses")

        monthly["month_label"] = monthly["month"].apply(month_label)

        fig_monthly = go.Figure()
        fig_monthly.add_trace(go.Bar(
            name="Income",
            x=monthly["month_label"], y=monthly["income"],
            marker=dict(color="#10b981", line=dict(width=0)),
            text=monthly["income"].apply(lambda v: f"{C}{v/1000:.0f}K" if v >= 1000 else f"{C}{v:.0f}"),
            textposition="outside",
            textfont=dict(size=11, color="#065f46"),
            hovertemplate="<b>%{x}</b><br>Income: " + C + "%{y:,.0f}<extra></extra>",
        ))
        fig_monthly.add_trace(go.Bar(
            name="Expenses",
            x=monthly["month_label"], y=monthly["expenses"],
            marker=dict(color="#ef4444", line=dict(width=0)),
            text=monthly["expenses"].apply(lambda v: f"{C}{v/1000:.0f}K" if v >= 1000 else f"{C}{v:.0f}"),
            textposition="outside",
            textfont=dict(size=11, color="#7f1d1d"),
            hovertemplate="<b>%{x}</b><br>Expenses: " + C + "%{y:,.0f}<extra></extra>",
        ))
        fig_monthly.add_trace(go.Bar(
            name="Net Savings",
            x=monthly["month_label"], y=monthly["savings"],
            marker=dict(color="#3b82f6", opacity=0.75, line=dict(width=0)),
            text=monthly["savings"].apply(lambda v: f"{C}{v/1000:.0f}K" if v >= 1000 else f"{C}{v:.0f}"),
            textposition="outside",
            textfont=dict(size=11, color="#1e3a5f"),
            hovertemplate="<b>%{x}</b><br>Savings: " + C + "%{y:,.0f}<extra></extra>",
        ))

        fig_monthly.update_layout(
            **_CHART_LAYOUT,
            barmode="group",
            height=420,
            title=dict(text="Monthly Financial Overview", font=dict(size=15, color="#1e293b"), x=0),
            xaxis=dict(**_XAXIS_BASE, title="Month", title_font=dict(size=12)),
            yaxis=dict(**_YAXIS_INR, title=f"Amount ({C})", title_font=dict(size=12)),
            bargap=0.25,
            bargroupgap=0.05,
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

    st.markdown("---")
    col_left, col_right = st.columns([5, 5])

    # ── Spending by Category — donut chart ─────────────────────────
    with col_left:
        st.subheader("🗂️ Spending by Category")
        cat_data = fin.category_spending(df_all)
        if not cat_data.empty:
            # Percentage labels for hover
            total_exp = cat_data["amount"].sum()
            cat_data["pct"] = (cat_data["amount"] / total_exp * 100).round(1)
            cat_data["label"] = cat_data.apply(
                lambda r: f"{r['category']}<br>{C}{r['amount']:,.0f} ({r['pct']:.1f}%)", axis=1
            )

            DONUT_COLORS = [
                "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
                "#8b5cf6", "#06b6d4", "#f97316", "#ec4899",
            ]
            fig_pie = go.Figure(go.Pie(
                labels=cat_data["category"],
                values=cat_data["amount"],
                customdata=cat_data[["pct", "amount"]].values,
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Amount: " + C + "%{customdata[1]:,.2f}<br>"
                    "Share: %{customdata[0]:.1f}%<extra></extra>"
                ),
                hole=0.42,
                pull=[0.04] * len(cat_data),
                marker=dict(colors=DONUT_COLORS[:len(cat_data)],
                            line=dict(color="#ffffff", width=2)),
                textinfo="percent",
                textposition="outside",
                textfont=dict(size=12),
                direction="clockwise",
                sort=True,
            ))
            fig_pie.update_layout(
                **{k: v for k, v in _CHART_LAYOUT.items()
                   if k not in ("legend", "margin")},
                height=400,
                margin=dict(t=50, b=20, l=20, r=20),
                title=dict(text="All-Time Category Breakdown", font=dict(size=13, color="#1e293b"), x=0),
                showlegend=True,
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1.02,
                    font=dict(size=12),
                    bgcolor="rgba(0,0,0,0)",
                ),
                annotations=[dict(
                    text=f"<b>{C}{total_exp/1000:.1f}K</b><br>Total",
                    x=0.5, y=0.5, font_size=14, showarrow=False,
                    font=dict(color="#1e293b"),
                )],
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.markdown(
                "<div class='empty-state'>No expense data yet.</div>",
                unsafe_allow_html=True,
            )

    # ── Recent transactions ─────────────────────────────────────────
    with col_right:
        st.subheader("🕒 Recent Transactions")
        recent = df_all.head(10).copy()
        recent["date"]   = recent["date"].dt.strftime("%d %b %Y")
        recent["amount"] = recent["amount"].apply(fmt)
        recent["type_icon"] = recent["type"].map({"Income": "🟢", "Expense": "🔴"})
        st.dataframe(
            recent[["date", "type_icon", "category", "amount", "description"]].rename(
                columns={"type_icon": ""}
            ),
            use_container_width=True,
            hide_index=True,
            height=380,
        )

    # ── Cumulative Balance Over Time ────────────────────────────────
    st.markdown("---")
    st.subheader("📉 Cumulative Balance Over Time")
    sorted_df = df_all.sort_values("date").copy()
    sorted_df["signed"]     = sorted_df.apply(
        lambda r: r["amount"] if r["type"] == "Income" else -r["amount"], axis=1
    )
    sorted_df["cumulative"] = sorted_df["signed"].cumsum()
    sorted_df["date_str"]   = sorted_df["date"].dt.strftime("%d %b %Y")

    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(
        x=sorted_df["date"],
        y=sorted_df["cumulative"],
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.15)",
        line=dict(color="#3b82f6", width=2.5),
        name="Balance",
        customdata=sorted_df[["date_str", "category", "type"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Balance: " + C + "%{y:,.2f}<br>"
            "%{customdata[2]}: %{customdata[1]}<extra></extra>"
        ),
    ))
    # Add zero line
    fig_area.add_hline(y=0, line_dash="dot", line_color="#94a3b8", line_width=1)

    fig_area.update_layout(
        **_CHART_LAYOUT,
        height=360,
        title=dict(text="Running Balance (Income − Expenses)", font=dict(size=15, color="#1e293b"), x=0),
        xaxis=dict(**_XAXIS_BASE, title="Date", title_font=dict(size=12)),
        yaxis=dict(**_YAXIS_INR, title=f"Balance ({C})", title_font=dict(size=12)),
    )
    st.plotly_chart(fig_area, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# PAGE: Transactions
# ══════════════════════════════════════════════════════════════════

elif page == "💳 Transactions":
    st.title("💳 Transactions")

    # ── Add transaction ────────────────────────────────────────────
    with st.expander("➕ Add New Transaction", expanded=False):
        with st.form("add_tx_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            tx_type = c1.selectbox("Type", ["Income", "Expense"])
            tx_date = c2.date_input("Date", value=date.today())
            c3, c4  = st.columns(2)
            amount  = c3.number_input(f"Amount ({C})", min_value=0.01, step=1.0, format="%.2f")
            cats    = fin.INCOME_CATEGORIES if tx_type == "Income" else fin.EXPENSE_CATEGORIES
            category = c4.selectbox("Category", cats)
            c5, c6  = st.columns(2)
            payment = c5.selectbox("Payment Method", fin.PAYMENT_METHODS)
            desc    = c6.text_input("Description (optional)")
            if st.form_submit_button("✅ Add Transaction", type="primary"):
                if amount <= 0:
                    st.error("Amount must be greater than 0.")
                else:
                    db.add_transaction(tx_date, tx_type, category, amount, payment, desc)
                    st.success(f"{tx_type} of {fmt(amount)} added successfully!")
                    refresh()

    st.markdown("---")

    # ── Filters ────────────────────────────────────────────────────
    st.subheader("🔍 Filter Transactions")
    fc1, fc2, fc3, fc4 = st.columns(4)
    f_start = fc1.date_input("From", value=date(2025, 1, 1), key="tx_from")
    f_end   = fc2.date_input("To",   value=date.today(),     key="tx_to")
    f_type  = fc3.selectbox("Type", ["All", "Income", "Expense"], key="tx_type")
    all_cats = ["All"] + sorted(fin.EXPENSE_CATEGORIES + fin.INCOME_CATEGORIES)
    f_cat   = fc4.selectbox("Category", all_cats, key="tx_cat")

    filtered = fin.filter_transactions(df_all, f_start, f_end, f_type, f_cat)
    # Sort newest first
    filtered = filtered.sort_values("date", ascending=False)

    st.caption(f"{len(filtered)} transaction(s) found")

    if filtered.empty:
        st.markdown(
            "<div class='empty-state'>"
            "📭 No transactions match your filters.<br>"
            "<small>Adjust the filters above or add a new transaction.</small>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        # Formatted display copy
        disp = filtered.copy()
        disp["Date"]           = disp["date"].dt.strftime("%d %b %Y")
        disp["Type"]           = disp["type"]
        disp["Category"]       = disp["category"]
        disp["Amount"]         = disp["amount"].apply(fmt)
        disp["Payment"]        = disp["payment_method"]
        disp["Description"]    = disp["description"]
        disp["Demo"]           = disp["is_demo"].apply(lambda x: "🧪" if x else "")

        st.dataframe(
            disp[["id", "Date", "Type", "Category", "Amount",
                  "Payment", "Description", "Demo"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "Amount": st.column_config.TextColumn("Amount (₹)"),
            },
        )

        # ── Edit a transaction ─────────────────────────────────────
        with st.expander("✏️ Edit a Transaction", expanded=False):
            tx_ids = filtered["id"].tolist()
            edit_id = st.selectbox(
                "Select Transaction ID to edit",
                tx_ids,
                format_func=lambda i: (
                    f"#{i} — {filtered.loc[filtered['id']==i,'date'].values[0]}"
                    f" | {filtered.loc[filtered['id']==i,'category'].values[0]}"
                    f" | {fmt(float(filtered.loc[filtered['id']==i,'amount'].values[0]))}"
                ),
                key="edit_tx_select",
            )
            edit_row = filtered[filtered["id"] == edit_id].iloc[0]
            with st.form("edit_tx_form"):
                ec1, ec2 = st.columns(2)
                e_type   = ec1.selectbox("Type", ["Income", "Expense"],
                                         index=["Income","Expense"].index(edit_row["type"]))
                e_date   = ec2.date_input("Date",
                                          value=pd.to_datetime(edit_row["date"]).date())
                ec3, ec4 = st.columns(2)
                e_amount = ec3.number_input(f"Amount ({C})", value=float(edit_row["amount"]),
                                            min_value=0.01, step=1.0, format="%.2f")
                e_cats   = fin.INCOME_CATEGORIES if e_type == "Income" else fin.EXPENSE_CATEGORIES
                e_cat_idx = e_cats.index(edit_row["category"]) if edit_row["category"] in e_cats else 0
                e_cat    = ec4.selectbox("Category", e_cats, index=e_cat_idx)
                ec5, ec6 = st.columns(2)
                pay_idx  = fin.PAYMENT_METHODS.index(edit_row["payment_method"]) \
                           if edit_row["payment_method"] in fin.PAYMENT_METHODS else 0
                e_pay    = ec5.selectbox("Payment Method", fin.PAYMENT_METHODS, index=pay_idx)
                e_desc   = ec6.text_input("Description", value=edit_row["description"])
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    db.update_transaction(edit_id, e_date, e_type, e_cat,
                                          e_amount, e_pay, e_desc)
                    st.success(f"Transaction #{edit_id} updated.")
                    refresh()

        # ── Delete ────────────────────────────────────────────────
        st.subheader("🗑️ Delete a Transaction")
        del_col1, del_col2 = st.columns([3, 1])
        del_id = del_col1.number_input(
            "Enter Transaction ID to delete",
            min_value=int(filtered["id"].min()),
            max_value=int(filtered["id"].max()),
            step=1, format="%d", key="del_tx_id",
        )
        if del_col2.button("Delete", type="secondary", key="btn_del_tx"):
            if int(del_id) in filtered["id"].values:
                db.delete_transaction(int(del_id))
                st.success(f"Transaction #{del_id} deleted.")
                refresh()
            else:
                st.error("ID not found in current filter view.")

        # ── Export ─────────────────────────────────────────────────
        st.markdown("---")
        export_df = filtered.drop(columns=["is_demo"], errors="ignore")
        export_df = export_df.copy()
        export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")
        csv_buf = io.StringIO()
        export_df.to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ Export as CSV",
            data=csv_buf.getvalue(),
            file_name="finwise_transactions.csv",
            mime="text/csv",
        )

        # ── Monthly breakdown chart ────────────────────────────────
        st.markdown("---")
        st.subheader("📊 Monthly Breakdown")
        monthly_f = fin.monthly_summary(filtered)
        if not monthly_f.empty:
            monthly_f["month_label"] = monthly_f["month"].apply(month_label)
            fig_tx_bar = go.Figure()
            fig_tx_bar.add_trace(go.Bar(
                name="Income",
                x=monthly_f["month_label"], y=monthly_f["income"],
                marker_color="#10b981",
                text=monthly_f["income"].apply(
                    lambda v: f"{C}{v/1000:.0f}K" if v >= 1000 else f"{C}{v:.0f}"),
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Income: " + C + "%{y:,.0f}<extra></extra>",
            ))
            fig_tx_bar.add_trace(go.Bar(
                name="Expenses",
                x=monthly_f["month_label"], y=monthly_f["expenses"],
                marker_color="#ef4444",
                text=monthly_f["expenses"].apply(
                    lambda v: f"{C}{v/1000:.0f}K" if v >= 1000 else f"{C}{v:.0f}"),
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Expenses: " + C + "%{y:,.0f}<extra></extra>",
            ))
            fig_tx_bar.update_layout(
                **_CHART_LAYOUT,
                barmode="group", height=380,
                title=dict(text="Monthly Income vs Expenses", font=dict(size=14, color="#1e293b"), x=0),
                xaxis=dict(**_XAXIS_BASE, title="Month"),
                yaxis=dict(**_YAXIS_INR, title=f"Amount ({C})"),
            )
            st.plotly_chart(fig_tx_bar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# PAGE: Budgets
# ══════════════════════════════════════════════════════════════════

elif page == "📋 Budgets":
    st.title("📋 Budget Management")

    current_month = datetime.today().strftime("%Y-%m")
    month_input   = st.text_input("Select Month (YYYY-MM)", value=current_month,
                                   placeholder="e.g. 2025-06")

    try:
        datetime.strptime(month_input, "%Y-%m")
        valid_month = True
    except ValueError:
        st.error("⚠️ Please enter a valid month in YYYY-MM format (e.g. 2025-06).")
        valid_month = False

    if valid_month:
        m_label = month_label(month_input)

        # ── Set / update budget ────────────────────────────────────
        with st.expander("➕ Set or Update a Budget", expanded=False):
            with st.form("budget_form", clear_on_submit=True):
                bc1, bc2 = st.columns(2)
                b_cat    = bc1.selectbox("Category", fin.EXPENSE_CATEGORIES)
                b_amount = bc2.number_input(
                    f"Monthly Budget ({C})", min_value=1.0, step=100.0, format="%.2f"
                )
                if st.form_submit_button("💾 Save Budget", type="primary"):
                    db.upsert_budget(b_cat, b_amount, month_input)
                    st.success(f"Budget for {b_cat} set to {fmt(b_amount)} for {m_label}.")
                    refresh()

        # ── Budget vs actual ───────────────────────────────────────
        budgets_df = db.get_budgets(month_input)
        bva        = fin.budget_vs_actual(df_all, budgets_df, month_input)

        if bva.empty:
            st.markdown(
                "<div class='empty-state'>"
                f"📋 No budgets set for <strong>{m_label}</strong>.<br>"
                "Use <em>Set or Update a Budget</em> above to get started."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.subheader(f"📊 Budget vs Actual — {m_label}")

            # Summary status cards
            exceeded  = int((bva["status"] == "Exceeded").sum())
            near_lim  = int((bva["status"] == "Near Limit").sum())
            on_track  = int((bva["status"] == "On Track").sum())
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("✅ On Track",    on_track)
            sc2.metric("⚠️ Near Limit",  near_lim)
            sc3.metric("🚨 Exceeded",    exceeded)

            # Progress bars
            st.markdown("---")
            for _, row in bva.iterrows():
                pct_capped  = min(float(row["pct"]) / 100, 1.0)
                pct_display = float(row["pct"])
                colour = (
                    "🔴" if row["status"] == "Exceeded"
                    else "🟡" if row["status"] == "Near Limit"
                    else "🟢"
                )
                remaining_budget = max(float(row["budget"]) - float(row["actual"]), 0)
                st.markdown(
                    f"<div class='prog-row'>"
                    f"<span><b>{colour} {row['category']}</b></span>"
                    f"<span style='color:#64748b;'>"
                    f"{fmt(row['actual'])} of {fmt(row['budget'])} — "
                    f"<b style='color:{'#ef4444' if row['status']=='Exceeded' else '#10b981'};'>"
                    f"{pct_display:.1f}%</b> used"
                    f" | Remaining: {fmt(remaining_budget)}"
                    f"</span></div>",
                    unsafe_allow_html=True,
                )
                st.progress(pct_capped)

            # Grouped bar chart with value labels
            st.markdown("---")
            st.subheader("📈 Budget vs Actual Chart")
            fig_bva = go.Figure()
            fig_bva.add_trace(go.Bar(
                name="Budget",
                x=bva["category"], y=bva["budget"],
                marker=dict(color="#3b82f6", line=dict(width=0)),
                text=bva["budget"].apply(fmt),
                textposition="outside",
                textfont=dict(size=11),
                hovertemplate="<b>%{x}</b><br>Budget: " + C + "%{y:,.0f}<extra></extra>",
            ))
            fig_bva.add_trace(go.Bar(
                name="Actual Spend",
                x=bva["category"], y=bva["actual"],
                marker=dict(color="#ef4444", line=dict(width=0)),
                text=bva["actual"].apply(fmt),
                textposition="outside",
                textfont=dict(size=11),
                hovertemplate="<b>%{x}</b><br>Actual: " + C + "%{y:,.0f}<extra></extra>",
            ))
            fig_bva.update_layout(
                **{k: v for k, v in _CHART_LAYOUT.items() if k != "margin"},
                barmode="group", height=420,
                title=dict(text=f"Budget vs Actual Spending — {m_label}",
                           font=dict(size=14, color="#1e293b"), x=0),
                xaxis=dict(**_XAXIS_BASE, title="Category", title_font=dict(size=12)),
                yaxis=dict(**_YAXIS_INR, title=f"Amount ({C})", title_font=dict(size=12)),
                margin=dict(t=60, b=70, l=80, r=30),
            )
            st.plotly_chart(fig_bva, use_container_width=True)

            # ── Remove budget ──────────────────────────────────────
            st.markdown("---")
            st.subheader("🗑️ Remove a Budget")
            if not budgets_df.empty:
                rb1, rb2 = st.columns([3, 1])
                del_bid  = rb1.number_input(
                    "Budget ID to remove",
                    min_value=int(budgets_df["id"].min()),
                    max_value=int(budgets_df["id"].max()),
                    step=1, format="%d", key="del_budget_id",
                )
                if rb2.button("Remove", type="secondary", key="btn_del_budget"):
                    if int(del_bid) in budgets_df["id"].values:
                        db.delete_budget(int(del_bid))
                        st.success(f"Budget #{del_bid} removed.")
                        refresh()
                    else:
                        st.error(f"Budget ID {del_bid} not found for {m_label}.")

                # Show IDs for reference
                with st.expander("📋 Budget IDs for this month"):
                    ref = budgets_df[["id", "category", "amount"]].copy()
                    ref["amount"] = ref["amount"].apply(fmt)
                    st.dataframe(ref, hide_index=True, use_container_width=True)

            # Export
            csv_buf = io.StringIO()
            bva.to_csv(csv_buf, index=False)
            st.download_button(
                "⬇️ Export Budget Report as CSV",
                data=csv_buf.getvalue(),
                file_name=f"finwise_budget_{month_input}.csv",
                mime="text/csv",
            )


# ══════════════════════════════════════════════════════════════════
# PAGE: Savings Goals
# ══════════════════════════════════════════════════════════════════

elif page == "🎯 Savings Goals":
    st.title("🎯 Savings Goals")

    # ── Add goal form ──────────────────────────────────────────────
    with st.expander("➕ Add a New Savings Goal", expanded=False):
        with st.form("goal_form", clear_on_submit=True):
            gc1, gc2 = st.columns(2)
            g_name   = gc1.text_input("Goal Name")
            g_desc   = gc2.text_input("Description (optional)")
            gc3, gc4, gc5 = st.columns(3)
            g_target = gc3.number_input(f"Target Amount ({C})", min_value=1.0,
                                        step=500.0, format="%.2f")
            g_saved  = gc4.number_input(f"Amount Already Saved ({C})", min_value=0.0,
                                        step=100.0, format="%.2f")
            g_dead   = gc5.date_input("Target Deadline",
                                       value=date(date.today().year + 1, 12, 31))
            if st.form_submit_button("✅ Add Goal", type="primary"):
                if not g_name.strip():
                    st.error("Goal name cannot be empty.")
                elif g_saved > g_target:
                    st.error("Saved amount cannot exceed target amount.")
                else:
                    db.add_savings_goal(g_name.strip(), g_target, g_saved, g_dead, g_desc)
                    st.success(f"Goal '{g_name}' added!")
                    refresh()

    st.markdown("---")

    # ── Display goals ──────────────────────────────────────────────
    goals_df = db.get_savings_goals()
    if goals_df.empty:
        st.markdown(
            "<div class='empty-state'>"
            "🎯 No savings goals yet.<br>"
            "<small>Add your first goal using the form above.</small>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        # Summary metrics
        total_targets = float(goals_df["target_amount"].sum())
        total_saved   = float(goals_df["saved_amount"].sum())
        total_remain  = total_targets - total_saved
        overall_pct   = (total_saved / total_targets * 100) if total_targets > 0 else 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🎯 Total Target",   fmt(total_targets))
        m2.metric("💰 Total Saved",    fmt(total_saved))
        m3.metric("⏳ Remaining",      fmt(total_remain))
        m4.metric("📊 Overall Progress", f"{overall_pct:.1f}%")

        st.markdown("---")
        st.subheader("📌 Goal Progress")

        for _, row in goals_df.iterrows():
            progress  = min(float(row["saved_amount"]) / float(row["target_amount"]), 1.0)
            pct_done  = progress * 100
            remaining = float(row["target_amount"]) - float(row["saved_amount"])
            deadline  = pd.to_datetime(row["deadline"])
            days_left = (deadline - pd.Timestamp.now()).days
            demo_badge = " 🧪" if row.get("is_demo", 0) else ""

            with st.container():
                ca, cb = st.columns([4, 1])
                ca.markdown(
                    f"**{row['name']}{demo_badge}**"
                    + (f" — *{row['description']}*" if row["description"] else "")
                )
                status_badge = (
                    "🎉 Completed!" if progress >= 1.0
                    else f"⏳ {days_left}d left" if days_left >= 0
                    else "🔴 Overdue"
                )
                cb.markdown(
                    f"<div style='text-align:right;font-size:0.88rem;'>"
                    f"{status_badge}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='prog-row'>"
                    f"<span style='color:#64748b;'>{fmt(row['saved_amount'])} saved "
                    f"of {fmt(row['target_amount'])}</span>"
                    f"<span><b style='color:#3b82f6;'>{pct_done:.1f}%</b> complete"
                    f" — remaining: <b>{fmt(remaining)}</b></span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.progress(progress)
                st.markdown("")   # spacer

        st.markdown("---")

        # ── Edit / delete ──────────────────────────────────────────
        st.subheader("✏️ Update a Goal")
        with st.form("edit_goal_form"):
            goal_ids = goals_df["id"].tolist()
            sel_id   = st.selectbox(
                "Select Goal",
                goal_ids,
                format_func=lambda i: (
                    f"#{i} – {goals_df.loc[goals_df['id']==i,'name'].values[0]}"
                ),
            )
            sel_row  = goals_df[goals_df["id"] == sel_id].iloc[0]
            ue1, ue2 = st.columns(2)
            u_name   = ue1.text_input("Name",        value=sel_row["name"])
            u_desc   = ue2.text_input("Description", value=sel_row["description"])
            ue3, ue4, ue5 = st.columns(3)
            u_target = ue3.number_input(
                f"Target ({C})", value=float(sel_row["target_amount"]),
                min_value=1.0, step=500.0, format="%.2f",
            )
            u_saved  = ue4.number_input(
                f"Saved ({C})", value=float(sel_row["saved_amount"]),
                min_value=0.0, step=100.0, format="%.2f",
            )
            u_dead   = ue5.date_input(
                "Deadline", value=pd.to_datetime(sel_row["deadline"]).date()
            )
            ub1, ub2 = st.columns(2)
            if ub1.form_submit_button("💾 Update Goal", type="primary"):
                if u_saved > u_target:
                    st.error("Saved amount cannot exceed target amount.")
                else:
                    db.update_savings_goal(sel_id, u_name, u_target, u_saved, u_dead, u_desc)
                    st.success("Goal updated.")
                    refresh()
            if ub2.form_submit_button("🗑️ Delete Goal", type="secondary"):
                db.delete_savings_goal(sel_id)
                st.success("Goal deleted.")
                refresh()

        # ── Goals overview chart ───────────────────────────────────
        st.markdown("---")
        st.subheader("📊 Goals Overview")

        goals_chart = goals_df.copy()
        goals_chart["progress_pct"] = (
            goals_chart["saved_amount"] / goals_chart["target_amount"] * 100
        ).clip(upper=100).round(1)

        fig_goals = go.Figure()
        fig_goals.add_trace(go.Bar(
            name="Target",
            x=goals_chart["target_amount"], y=goals_chart["name"],
            orientation="h",
            marker=dict(color="#cbd5e1", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Target: " + C + "%{x:,.0f}<extra></extra>",
        ))
        fig_goals.add_trace(go.Bar(
            name="Saved",
            x=goals_chart["saved_amount"], y=goals_chart["name"],
            orientation="h",
            marker=dict(color="#3b82f6", line=dict(width=0)),
            text=goals_chart["progress_pct"].apply(lambda p: f"{p:.0f}%"),
            textposition="inside",
            textfont=dict(color="#ffffff", size=12),
            hovertemplate="<b>%{y}</b><br>Saved: " + C + "%{x:,.0f}<extra></extra>",
        ))
        fig_goals.update_layout(
            **{k: v for k, v in _CHART_LAYOUT.items() if k != "margin"},
            barmode="overlay",
            height=max(300, len(goals_chart) * 60 + 120),
            title=dict(text="Target vs Saved Amount", font=dict(size=14, color="#1e293b"), x=0),
            xaxis=dict(
                **{k: v for k, v in _XAXIS_BASE.items() if k != "showgrid"},
                tickprefix=C, title=f"Amount ({C})",
                showgrid=True, gridcolor="#e2e8f0",
            ),
            yaxis=dict(tickfont=dict(size=12), title="Goal",
                       autorange="reversed"),
            margin=dict(t=60, b=60, l=160, r=60),
        )
        st.plotly_chart(fig_goals, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# PAGE: AI Insights
# ══════════════════════════════════════════════════════════════════

elif page == "🤖 AI Insights":
    st.title("🤖 Financial Insights")

    st.markdown(
        '<div class="alert-info" style="margin-bottom:12px;">'
        "<strong>ℹ️ How these insights work</strong><br>"
        "<span style='font-size:0.9rem;'>"
        "All suggestions are generated by <em>deterministic, rule-based pattern analysis</em> "
        "of your transaction history. No machine-learning model is used. "
        "These insights are for <strong>educational and informational purposes only</strong> "
        "and do not constitute professional financial advice."
        "</span></div>",
        unsafe_allow_html=True,
    )

    if df_all.empty:
        st.markdown(
            "<div class='empty-state'>"
            "🤖 No transaction data to analyse.<br>"
            "<small>Add transactions and insights will appear automatically.</small>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # ── Spending insights ─────────────────────────────────────────
    st.subheader("🔍 Spending Analysis")
    insights = ai.generate_insights(df_all)
    for ins in insights:
        _render_insight(ins)

    # ── Budget alerts ─────────────────────────────────────────────
    current_month = datetime.today().strftime("%Y-%m")
    budgets_df    = db.get_budgets(current_month)
    if not budgets_df.empty:
        bva        = fin.budget_vs_actual(df_all, budgets_df, current_month)
        budget_ins = ai.budget_breach_insights(bva)
        if budget_ins:
            st.markdown("---")
            st.subheader(f"📋 Budget Alerts — {month_label(current_month)}")
            for ins in budget_ins:
                _render_insight(ins)

    # ── Category spending bar chart ───────────────────────────────
    st.markdown("---")
    st.subheader("📊 All-Time Spending by Category")
    cat_data = fin.category_spending(df_all)
    if not cat_data.empty:
        cat_data["pct"] = (cat_data["amount"] / cat_data["amount"].sum() * 100).round(1)
        cat_data["label"] = cat_data.apply(
            lambda r: f"{C}{r['amount']:,.0f} ({r['pct']:.1f}%)", axis=1
        )
        INSIGHT_COLORS = [
            "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
            "#8b5cf6", "#06b6d4", "#f97316",
        ]
        fig_cat = go.Figure(go.Bar(
            x=cat_data["amount"],
            y=cat_data["category"],
            orientation="h",
            marker=dict(
                color=INSIGHT_COLORS[:len(cat_data)],
                line=dict(width=0),
            ),
            text=cat_data["label"],
            textposition="outside",
            textfont=dict(size=12),
            hovertemplate="<b>%{y}</b><br>Spent: " + C + "%{x:,.2f}<extra></extra>",
        ))
        fig_cat.update_layout(
            **{k: v for k, v in _CHART_LAYOUT.items() if k != "margin"},
            height=max(320, len(cat_data) * 52 + 120),
            title=dict(text="Total Expenses by Category", font=dict(size=14, color="#1e293b"), x=0),
            xaxis=dict(**{k: v for k, v in _XAXIS_BASE.items() if k != "showgrid"},
                       tickprefix=C, title=f"Total Spent ({C})",
                       showgrid=True, gridcolor="#e2e8f0"),
            yaxis=dict(tickfont=dict(size=13), title="Category",
                       autorange="reversed"),
            margin=dict(t=60, b=60, l=130, r=160),
        )
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No expense data to display.")

    # ── Monthly spending trend by category ───────────────────────
    st.markdown("---")
    st.subheader("📅 Monthly Spending Trend by Category")
    expenses_df = df_all[df_all["type"] == "Expense"].copy()
    if not expenses_df.empty:
        expenses_df["month"]       = expenses_df["date"].dt.to_period("M").astype(str)
        expenses_df["month_label"] = expenses_df["month"].apply(month_label)
        pivot = (
            expenses_df.groupby(["month", "month_label", "category"])["amount"]
            .sum().reset_index()
            .sort_values("month")
        )
        fig_trend = px.line(
            pivot, x="month_label", y="amount", color="category",
            markers=True,
            labels={
                "amount":      f"Spent ({C})",
                "month_label": "Month",
                "category":    "Category",
            },
            color_discrete_sequence=[
                "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
                "#8b5cf6", "#06b6d4", "#f97316",
            ],
        )
        fig_trend.update_traces(line=dict(width=2.5), marker=dict(size=8))
        fig_trend.update_layout(
            **{k: v for k, v in _CHART_LAYOUT.items() if k != "legend"},
            height=420,
            title=dict(text="Monthly Expense Trends per Category",
                       font=dict(size=14, color="#1e293b"), x=0),
            xaxis=dict(**_XAXIS_BASE, title="Month", title_font=dict(size=12)),
            yaxis=dict(**_YAXIS_INR, title=f"Amount Spent ({C})", title_font=dict(size=12)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No expense data to display.")

    # ── Monthly income vs expenses summary ────────────────────────
    st.markdown("---")
    st.subheader("📈 Monthly Income vs Expenses Summary")
    monthly_ins = fin.monthly_summary(df_all)
    if not monthly_ins.empty:
        monthly_ins["month_label"]   = monthly_ins["month"].apply(month_label)
        monthly_ins["savings_rate%"] = (
            monthly_ins["savings"] / monthly_ins["income"].replace(0, pd.NA) * 100
        ).fillna(0).round(1)

        fig_summary = go.Figure()
        fig_summary.add_trace(go.Bar(
            name="Income",
            x=monthly_ins["month_label"], y=monthly_ins["income"],
            marker_color="#10b981",
            hovertemplate="<b>%{x}</b><br>Income: " + C + "%{y:,.0f}<extra></extra>",
        ))
        fig_summary.add_trace(go.Bar(
            name="Expenses",
            x=monthly_ins["month_label"], y=monthly_ins["expenses"],
            marker_color="#ef4444",
            hovertemplate="<b>%{x}</b><br>Expenses: " + C + "%{y:,.0f}<extra></extra>",
        ))
        fig_summary.add_trace(go.Scatter(
            name="Savings Rate %",
            x=monthly_ins["month_label"], y=monthly_ins["savings_rate%"],
            mode="lines+markers+text",
            yaxis="y2",
            line=dict(color="#f59e0b", width=2.5, dash="dot"),
            marker=dict(size=8, color="#f59e0b"),
            text=monthly_ins["savings_rate%"].apply(lambda v: f"{v:.0f}%"),
            textposition="top center",
            textfont=dict(size=11, color="#b45309"),
            hovertemplate="<b>%{x}</b><br>Savings Rate: %{y:.1f}%<extra></extra>",
        ))
        fig_summary.update_layout(
            **_CHART_LAYOUT,
            barmode="group", height=420,
            title=dict(text="Monthly Totals with Savings Rate",
                       font=dict(size=14, color="#1e293b"), x=0),
            xaxis=dict(**_XAXIS_BASE, title="Month"),
            yaxis=dict(**_YAXIS_INR, title=f"Amount ({C})"),
            yaxis2=dict(
                title="Savings Rate (%)",
                overlaying="y", side="right",
                ticksuffix="%", showgrid=False,
                range=[0, 110],
                tickfont=dict(size=11, color="#b45309"),
                title_font=dict(size=12, color="#b45309"),
            ),
        )
        st.plotly_chart(fig_summary, use_container_width=True)

    # ── Export monthly summary ────────────────────────────────────
    st.markdown("---")
    monthly_export = fin.monthly_summary(df_all)
    csv_buf = io.StringIO()
    monthly_export.to_csv(csv_buf, index=False)
    st.download_button(
        "⬇️ Export Monthly Summary as CSV",
        data=csv_buf.getvalue(),
        file_name="finwise_monthly_summary.csv",
        mime="text/csv",
    )
