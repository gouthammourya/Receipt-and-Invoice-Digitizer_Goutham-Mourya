import streamlit as st
from streamlit_option_menu import option_menu
import os, datetime, cv2
import pandas as pd
from pdf2image import convert_from_path

from ocr_utils import preprocess_image, extract_text
from ai_client import extract_and_map
from parser import parse_receipt
from database import create_table, get_connection, is_duplicate
from analytics import (
    monthly_expense_chart,
    spending_by_store_chart,
    monthly_trend_line_chart
)
from validator import build_validation_results

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="MydigiBill", layout="wide")

st.markdown("""
<style>
.stButton>button {
    background-color:#0ea5a4;
    color:white;
    border-radius:8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DB INIT ----------------
create_table()
conn = get_connection()
cur = conn.cursor()

# ---------------- VALIDATION BANNER UI ----------------
def show_validation_banners(results: dict):
    for title, (status, message) in results.items():
        bg = "#ecfdf5" if status else "#fef2f2"
        border = "#10b981" if status else "#ef4444"
        icon = "✅" if status else "❌"
        color = "#065f46" if status else "#7f1d1d"

        st.markdown(f"""
        <div style="
            background:{bg};
            border-left:6px solid {border};
            padding:12px;
            border-radius:8px;
            margin-bottom:10px;">
            <b>{icon} {title}</b><br>
            <span style="color:{color}">{message}</span>
        </div>
        """, unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.image("assets/logo.png", width=220)
    menu = option_menu(
        "Menu",
        ["Upload Receipt", "Analytics", "History"],
        icons=["cloud-upload", "bar-chart", "clock-history"]
    )

st.markdown("## 🧾 MydigiBill – Smart Receipt & Expense Tracker")

# =====================================================
# ================= UPLOAD RECEIPT ====================
# =====================================================
if menu == "Upload Receipt":

    file = st.file_uploader(
        "Upload Receipt (JPG / PNG / PDF)",
        type=["jpg", "png", "jpeg", "pdf"]
    )

    if file:
        if is_duplicate(file.name):
            st.warning("⚠ This receipt file already exists in the database.")
            st.stop()

        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.name}"

        with open(file_path, "wb") as f:
            f.write(file.read())

        # ---------- LOAD IMAGE ----------
        if file.type == "application/pdf":
            pages = convert_from_path(file_path)
            pages[0].save("uploads/tmp.jpg")
            img = cv2.imread("uploads/tmp.jpg")
        else:
            img = cv2.imread(file_path)

        if img is None:
            st.error("Failed to load image.")
            st.stop()

        processed = preprocess_image(img)

        # ---------- PREVIEW ----------
        c1, c2 = st.columns(2)
        c1.image(img, "Original Receipt", width=320)
        c2.image(processed, "Preprocessed (OCR Ready)", width=320)

        # ---------- EXTRACT ----------
        if st.button("🔍 Extract Data"):
            with st.spinner("Running OCR + AI mapping..."):

                ocr_text = extract_text(processed)
                if not ocr_text.strip():
                    st.error("No text detected from OCR.")
                    st.stop()

                try:
                    data = extract_and_map(ocr_text)
                    st.success("✅ Used Local AI (Ollama)")
                except Exception:
                    data = parse_receipt(ocr_text)
                    st.info("ℹ️ Used rule-based extraction")

                validation = build_validation_results(data, file.name)
                show_validation_banners(validation)

                totals_valid = validation["Total Validation"][0]
                if not totals_valid:
                    st.error("❌ Invalid totals detected. You can review the data, but saving is disabled.")

                st.session_state.data = data
                st.session_state.filename = file.name
                st.session_state.totals_valid = totals_valid

    # ---------- DISPLAY ----------
    if "data" in st.session_state:
        d = st.session_state.data

        st.markdown("### Extracted Receipt")

        left, right = st.columns([2, 1])

        with left:
            st.write("**Store:**", d["store"])
            st.write("**Date:**", d["date"])
            st.write("**Time:**", d["time"])
            st.write("**Payment:**", d["payment"])

            st.markdown("**Items**")
            if d["items"]:
                items_df = pd.DataFrame(d["items"]).copy()
                items_df["price"] = items_df["price"].apply(lambda x: f"${x:.2f}")

                st.dataframe(
                    items_df,
                    use_container_width=True,
                    column_config={
                        "name": st.column_config.TextColumn("Item"),
                        "price": st.column_config.TextColumn("Price")
                    }
                )
            else:
                st.info("ℹ️ No line items detected")

        with right:
            st.metric("Subtotal", f"${d['subtotal']:.2f}")
            st.metric("Tax", f"${d['tax']:.2f}")
            st.metric("Total", f"${d['total']:.2f}")

        # ---------- SAVE ----------
        if st.button("💾 Save Receipt", disabled=not st.session_state.get("totals_valid", True)):
            cur.execute("""
                INSERT INTO receipts VALUES
                (NULL,?,?,?,?,?,?,?,?)
            """, (
                st.session_state.filename,
                d["store"],
                d["date"],
                d["subtotal"],
                d["tax"],
                d["total"],
                d["payment"],
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            receipt_id = cur.lastrowid

            for item in d["items"]:
                cur.execute("""
                    INSERT INTO receipt_items (receipt_id, item_name, price)
                    VALUES (?,?,?)
                """, (receipt_id, item["name"], item["price"]))

            conn.commit()
            st.success("✅ Receipt & items saved successfully!")

# =====================================================
# ================= ANALYTICS =========================
# =====================================================
elif menu == "Analytics":
    st.title("📊 Analytics Dashboard")

    df = pd.read_sql("SELECT * FROM receipts", conn)
    if df.empty:
        st.warning("No data available.")
        st.stop()

    df["parsed_date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    df["uploaded_at"] = pd.to_datetime(df["uploaded_at"])
    df["final_date"] = df["parsed_date"].fillna(df["uploaded_at"])
    df["month"] = df["final_date"].dt.strftime("%b %Y")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🧾 Total Receipts", len(df))
    c2.metric("💰 Total Spent", f"${df['total'].sum():,.2f}")
    c3.metric("📊 Avg Receipt", f"${df['total'].mean():,.2f}")
    c4.metric("🏪 Stores", df["store"].nunique())

    st.divider()

    g1, g2 = st.columns(2)

    fig1 = monthly_expense_chart(df)
    if fig1:
        g1.plotly_chart(fig1, use_container_width=True)

    fig2 = spending_by_store_chart(df)
    if fig2:
        g2.plotly_chart(fig2, use_container_width=True)

    st.divider()

    fig3 = monthly_trend_line_chart(df)
    if fig3:
        st.plotly_chart(fig3, use_container_width=True)

# =====================================================
# ================= HISTORY ===========================
# =====================================================
elif menu == "History":
    st.title("🕘 Receipt History")

    df = pd.read_sql("SELECT * FROM receipts", conn)
    st.dataframe(df, use_container_width=True)

    st.divider()

    view_id = st.number_input("👁 View Receipt by ID", min_value=1, step=1)
    if st.button("View Receipt"):
        cur.execute("SELECT * FROM receipts WHERE id=?", (view_id,))
        r = cur.fetchone()

        if r:
            st.subheader("Receipt Details")
            st.write("**Store:**", r[2])
            st.write("**Date:**", r[3])
            st.write("**Payment:**", r[7])

            st.metric("Subtotal", f"${r[4]:.2f}")
            st.metric("Tax", f"${r[5]:.2f}")
            st.metric("Total", f"${r[6]:.2f}")

            cur.execute("""
                SELECT item_name, price
                FROM receipt_items
                WHERE receipt_id=?
            """, (view_id,))
            items = cur.fetchall()

            if items:
                items_df = pd.DataFrame(items, columns=["Item", "Price"])
                items_df["Price"] = items_df["Price"].apply(lambda x: f"${x:.2f}")

                st.dataframe(
                    items_df,
                    use_container_width=True,
                    column_config={
                        "Item": st.column_config.TextColumn("Item"),
                        "Price": st.column_config.TextColumn("Price")
                    }
                )
            else:
                st.info("No items found for this receipt.")
        else:
            st.error("Receipt not found.")

    st.divider()

    delete_id = st.number_input("🗑 Delete Receipt by ID", min_value=1, step=1)
    confirm = st.checkbox("Confirm delete")
    if confirm and st.button("Delete Receipt"):
        cur.execute("DELETE FROM receipt_items WHERE receipt_id=?", (delete_id,))
        cur.execute("DELETE FROM receipts WHERE id=?", (delete_id,))
        conn.commit()
        st.success(f"Receipt ID {delete_id} deleted.")
        st.rerun()
