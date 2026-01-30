import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import math
import re

# ---------------- Page Config ----------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")
st.title("📊 Attendance Tracker")
st.caption("Paste attendance data directly from your college portal")

# ---------------- COLORS ----------------
PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR = "#F39C12"

# ---------------- PARSER ----------------
def parse_data(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []

    for line in lines:
        parts = line.split("\t") if "\t" in line else re.split(r"\s{2,}", line)
        try:
            if len(parts) >= 3:
                subject = parts[0]
                present = int(parts[-2])
                absent = int(parts[-1])
                rows.append([subject, present, absent])
        except:
            continue

    if not rows:
        raise ValueError("No valid rows found")

    df = pd.DataFrame(rows, columns=["Subject", "Present", "Absent"])
    df["Total"] = df["Present"] + df["Absent"]
    df["Attendance%"] = (df["Present"] / df["Total"]) * 100

    df["Status"] = df["Attendance%"].apply(lambda x: "🟢" if x >= 75 else "🔴")
    return df.sort_values("Attendance%")

# ---------------- INPUT ----------------
pasted = st.text_area("📋 Paste attendance data", height=250)

if pasted.strip():
    try:
        df = parse_data(pasted)
        st.success("✅ Attendance parsed successfully")
    except Exception as e:
        st.error("❌ Could not parse data")
        st.stop()

    # ---------------- TABLE ----------------
    st.subheader("📋 Attendance Overview")

    def style_status(row):
        if row["Status"] == "🔴":
            return [""] * 4 + ["background-color:#FDEDEC; font-weight:bold; text-align:center;"]
        else:
            return [""] * 4 + ["background-color:#E8F8F5; font-weight:bold; text-align:center;"]

    st.dataframe(df.style.apply(style_status, axis=1))

    # ---------------- AGGREGATE ----------------
    total_present = df["Present"].sum()
    total_absent = df["Absent"].sum()
    total_classes = total_present + total_absent
    aggregate = (total_present / total_classes) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Present", total_present)
    c2.metric("Total Absent", total_absent)
    c3.metric("Aggregate %", f"{aggregate:.2f}")

    # ---------------- PIE ----------------
    st.subheader("📈 Aggregate Attendance")
    fig, ax = plt.subplots()
    ax.pie(
        [total_present, total_absent],
        labels=["Present", "Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90
    )
    st.pyplot(fig)

    # ==================================================
    # 🧮 WHAT-IF SECTION (RECODED & GUARANTEED WORKING)
    # ==================================================
    st.markdown("---")
    st.subheader("🧮 What if I leave some classes?")

    leave_classes = st.number_input(
        "Enter number of classes you plan to leave",
        min_value=0,
        step=1,
        value=0
    )

    new_total = total_classes + leave_classes
    new_aggregate = (total_present / new_total) * 100 if new_total > 0 else 0

    st.markdown(
        f"""
        ### 📊 New Aggregate Attendance  
        **{new_aggregate:.2f}%**
        """
    )

    if new_aggregate < 75:
        st.error("🔴 Warning: Attendance will fall below 75%")
    else:
        st.success("🟢 Safe: Attendance stays above 75%")

    # ---------------- SUBJECT TARGET ----------------
    st.markdown("---")
    st.subheader("🎯 Subject-wise Target")

    subject = st.selectbox("Select subject", df["Subject"])
    target = st.number_input("Target %", 0, 100, 75)

    row = df[df["Subject"] == subject].iloc[0]

    x = 0
    while (row["Present"] / (row["Total"] + x)) * 100 >= target:
        x += 1

    st.info(f"You can leave **{max(0, x-1)}** classes in **{subject}**")
