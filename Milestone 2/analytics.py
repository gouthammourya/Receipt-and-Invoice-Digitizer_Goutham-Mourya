import plotly.express as px

def monthly_expense_chart(df):
    return px.bar(
        df.groupby("month")["total"].sum().reset_index(),
        x="month",
        y="total",
        title="Monthly Expenses",
        color="total"
    )

def spending_by_store_chart(df):
    return px.pie(
        df,
        names="store",
        values="total",
        title="Spending by Store"
    )

def monthly_trend_line_chart(df):
    return px.line(
        df.sort_values("final_date"),
        x="final_date",
        y="total",
        title="Expense Trend Over Time",
        markers=True
    )
