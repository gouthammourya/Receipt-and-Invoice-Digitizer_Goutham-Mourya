import streamlit as st
from streamlit_option_menu import option_menu
import os
import datetime
import cv2
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
from validator import validate_receipt

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
        with c1:
            st.image(img, caption="Original Receipt", width=320)
        with c2:
            st.image(processed, caption="Preprocessed (OCR Ready)", width=320)

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
                    st.info("ℹ️ Used optimized rule-based extraction")
                    data = parse_receipt(ocr_text)

                # ---------- VALIDATION ----------
                errors = validate_receipt(data)
                if errors:
                    st.warning("⚠ Some fields were auto-corrected:")
                    for e in errors:
                        st.write("•", e)

                st.session_state.data = data
                st.session_state.filename = file.name

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

            if d["items"]:
                st.markdown("**Items**")
                st.table(pd.DataFrame(d["items"]))

        with right:
            st.metric("Subtotal", f"₹{d['subtotal']:.2f}")
            st.metric("Tax", f"₹{d['tax']:.2f}")
            st.metric("Total", f"₹{d['total']:.2f}")

        # ---------- SAVE ----------
        if st.button("💾 Save Receipt"):
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
            conn.commit()
            st.success("✅ Receipt saved successfully!")

# =====================================================
# ================= ANALYTICS =========================
# =====================================================
elif menu == "Analytics":
    st.title("📊 Analytics Dashboard")

    df = pd.read_sql("SELECT * FROM receipts", conn)

    if df.empty:
        st.warning("No data available.")
        st.stop()

    # ---------- DATE HANDLING ----------
    df["parsed_date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
        dayfirst=True
    )

    df["uploaded_at"] = pd.to_datetime(df["uploaded_at"])
    df["final_date"] = df["parsed_date"].fillna(df["uploaded_at"])
    df["month"] = df["final_date"].dt.strftime("%b %Y")

    # ---------- METRICS ----------
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("🧾 Total Receipts", len(df))
    c2.metric("💰 Total Spent", f"₹{df['total'].sum():,.2f}")
    c3.metric("📊 Avg Receipt", f"₹{df['total'].mean():,.2f}")
    c4.metric("🏪 Stores", df["store"].nunique())

    st.divider()

    # ---------- GRAPHS ----------
    g1, g2 = st.columns(2)

    with g1:
        fig1 = monthly_expense_chart(df)
        if fig1:
            st.pyplot(fig1)

    with g2:
        fig2 = spending_by_store_chart(df)
        if fig2:
            st.pyplot(fig2)

    st.divider()

    fig3 = monthly_trend_line_chart(df)
    if fig3:
        st.pyplot(fig3)

# =====================================================
# ================= HISTORY ===========================
# =====================================================
elif menu == "History":
    st.title("🕘 Receipt History")

    df = pd.read_sql("SELECT * FROM receipts", conn)

    # ---------- SEARCH ----------
    search_id = st.text_input("🔎 Search by Receipt ID")
    if search_id.isdigit():
        df = df[df.id == int(search_id)]

    st.dataframe(df, use_container_width=True)

    st.divider()

    # ---------- VIEW ----------
    view_id = st.number_input("👁 View Receipt by ID", min_value=1, step=1)
    if st.button("View Receipt"):
        cur.execute("SELECT * FROM receipts WHERE id=?", (view_id,))
        row = cur.fetchone()
        if row:
            st.json({
                "id": row[0],
                "filename": row[1],
                "store": row[2],
                "date": row[3],
                "subtotal": row[4],
                "tax": row[5],
                "total": row[6],
                "payment": row[7],
                "uploaded_at": row[8]
            })
        else:
            st.error("Receipt not found.")

    st.divider()

    # ---------- DELETE ----------
    delete_id = st.number_input("🗑 Delete Receipt by ID", min_value=1, step=1)
    confirm = st.checkbox("Confirm delete")

    if confirm and st.button("Delete Receipt"):
        cur.execute("DELETE FROM receipts WHERE id=?", (delete_id,))
        conn.commit()
        st.success(f"Receipt ID {delete_id} deleted.")
        st.rerun()
