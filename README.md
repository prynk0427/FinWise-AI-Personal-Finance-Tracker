# 💰 FinWise AI – AI-Based Personal Finance Tracker

A modern, interactive personal finance tracker built with **Python**, **Streamlit**, **Pandas**, **Plotly**, and **SQLite**.  
Track your income, expenses, budgets, and savings goals — all in one clean dashboard.

> ⚠️ **Disclaimer:** FinWise AI is for **educational and informational purposes only**.  
> It does **not** provide professional financial advice. Always consult a qualified financial adviser before making financial decisions.

---

## 📋 Features

| Feature | Description |
|---|---|
| 📊 Dashboard | Overview of income, expenses, savings rate, and cumulative balance |
| 💳 Transactions | Add, filter, and delete income & expense records; export to CSV |
| 📋 Budgets | Set monthly category budgets and track actual vs. budgeted spending |
| 🎯 Savings Goals | Create goals with target amounts and deadlines; track progress |
| 🤖 AI Insights | Rule-based spending analysis, anomaly alerts, and personalised saving tips |

---

## 🗂️ Project Structure

```
FinWise_AI/
├── app.py              # Main Streamlit application
├── database.py         # SQLite database setup and CRUD operations
├── finance.py          # Financial calculations and summary helpers
├── ai_insights.py      # Rule-based spending analysis and saving suggestions
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
└── data/
    └── finwise.db      # SQLite database (auto-created on first run)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- pip

### Installation

1. **Clone or download the project:**
   ```bash
   git clone https://github.com/your-username/FinWise_AI.git
   cd FinWise_AI
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   streamlit run app.py
   ```

5. Open your browser at **http://localhost:8501**

---

## 🎮 Usage Guide

### Dashboard
The home page shows your overall financial health at a glance:
- **KPI cards** — Total Income, Total Expenses, Total Savings, Savings Rate
- **Monthly line chart** — Income vs. Expenses trend with savings bars
- **Spending pie chart** — Category breakdown of all expenses
- **Cumulative balance chart** — Your running balance over time

### Transactions
- Use the **Add New Transaction** expander to log income or expenses
- Filter records by date range, type, and category
- Delete a transaction by entering its ID
- Export filtered results as a **CSV file**

### Budgets
- Enter a month (format `YYYY-MM`) to manage that month's budgets
- Use **Set or Update a Budget** to assign a spending limit per category
- View progress bars with colour-coded statuses:
  - 🟢 On Track — below 80% of budget
  - 🟡 Near Limit — between 80–99%
  - 🔴 Exceeded — over 100%
- Export the budget report as CSV

### Savings Goals
- Add goals with a name, target amount, current savings, and deadline
- View progress bars and days remaining for each goal
- Update or delete existing goals using the edit form

### AI Insights
- Automatically analyses your spending patterns
- Alerts you to month-over-month spending spikes
- Provides targeted saving tips for your top expense categories
- Highlights budget breaches and near-limit warnings
- All insights are **rule-based** — not machine learning

---

## 🛠️ Technologies

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Core language |
| Streamlit | ≥1.28 | Web UI framework |
| Pandas | ≥2.0 | Data manipulation |
| Plotly | ≥5.17 | Interactive charts |
| SQLite | Built-in | Local data storage |

---

## 🗄️ Database Schema

### `transactions`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| date | TEXT | Transaction date (YYYY-MM-DD) |
| type | TEXT | `Income` or `Expense` |
| category | TEXT | Expense/income category |
| amount | REAL | Transaction amount (> 0) |
| payment_method | TEXT | Payment method used |
| description | TEXT | Optional notes |

### `budgets`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| category | TEXT | Expense category |
| amount | REAL | Monthly budget limit |
| month | TEXT | Month (YYYY-MM) |

### `savings_goals`
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Primary key |
| name | TEXT | Goal name |
| target_amount | REAL | Total target |
| saved_amount | REAL | Amount saved so far |
| deadline | TEXT | Target date (YYYY-MM-DD) |
| description | TEXT | Optional notes |

---

## 📦 Sample Data

On first run, the app automatically seeds **39 sample transactions** covering January–June 2025, plus **7 monthly budgets** and **4 savings goals**, so the dashboard is immediately populated and ready to explore.

---

## 🤖 About AI Insights

The "AI Insights" page uses **deterministic rule-based analysis** — it is NOT powered by a machine-learning model. It checks:

- **Savings rate** vs. the commonly cited 20% target
- **Top spending categories** as a share of total expenses
- **Month-over-month spending spikes** (≥ 30% increase)
- **Category-level anomalies** across consecutive months
- **Budget breaches** and near-limit warnings

Saving tips are matched to the user's top expense categories using a fixed lookup table.

---

## 📄 Licence

This project is provided for educational purposes. No warranty is given. Use at your own risk.
