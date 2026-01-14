import matplotlib.pyplot as plt
import pandas as pd

# ---------------- STANDARD GRAPH SIZES ----------------
BAR_SIZE = (6, 3.5)
LINE_SIZE = (6, 3.5)
PIE_SIZE = (5, 5)


# ---------------- MONTHLY BAR CHART ----------------
def monthly_expense_chart(df):
    if df.empty or "month" not in df.columns:
        return None

    fig, ax = plt.subplots(figsize=BAR_SIZE)

    df.groupby("month")["total"].sum().plot(
        kind="bar",
        ax=ax,
        color="#0ea5a4"
    )

    ax.set_title("Monthly Expenses")
    ax.set_ylabel("Amount (₹)")
    ax.set_xlabel("Month")
    fig.tight_layout()
    return fig


# ---------------- SPENDING BY STORE (PIE) ----------------
def spending_by_store_chart(df):
    if df.empty or "store" not in df.columns:
        return None

    store_data = df.groupby("store")["total"].sum()

    if store_data.empty:
        return None

    fig, ax = plt.subplots(figsize=PIE_SIZE)

    ax.pie(
        store_data,
        labels=store_data.index,
        autopct="%1.0f%%",
        startangle=90
    )

    ax.set_title("Spending by Store")
    fig.tight_layout()
    return fig


# ---------------- MONTHLY TREND LINE CHART ----------------
def monthly_trend_line_chart(df):
    """
    Line chart showing expense trend over time (by receipt/upload date)
    """
    if df.empty or "final_date" not in df.columns:
        return None

    trend_df = (
        df.groupby(pd.Grouper(key="final_date", freq="M"))["total"]
        .sum()
        .reset_index()
    )

    if trend_df.empty:
        return None

    fig, ax = plt.subplots(figsize=LINE_SIZE)

    ax.plot(
        trend_df["final_date"],
        trend_df["total"],
        marker="o",
        linewidth=2
    )

    ax.set_title("Monthly Expense Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Amount (₹)")
    fig.autofmt_xdate()
    fig.tight_layout()

    return fig
