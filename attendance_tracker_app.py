import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import sympy as sp
import math
import re

# ---------------- Page Config ----------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")
st.title("📊 Attendance Tracker")
st.caption("Paste attendance data directly from your college portal")

# ---------------- MODERN COLOR THEME ----------------
PRESENT_COLOR = "#4F46E5"   # Indigo
ABSENT_COLOR  = "#F97316"   # Orange
BAR_COLORS    = ["#6366F1", "#22C55E", "#F59E0B", "#EF4444", "#06B6D4"]

# ---------------- SAFE PASTE PARSER ----------------
def smart_parse_pasted_data(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []

    for line in lines:
        parts = line.split("\t") if "\t" in line else re.split(r"\s{2,}", line)
        joined = " ".join(parts).lower()

        if "present" in joined and "absent" in joined:
            continue

        try:
            if len(parts) >= 9:
                subject = " ".join(parts[2:-6])
                present = int(parts[-5])
                absent = int(parts[-2])
            elif len(parts) == 3:
                subject, present, absent = parts
                present, absent = int(present), int(absent)
            else:
                continue

            rows.append([subject.strip(), present, absent])
        except:
            continue

    if not rows:
        raise ValueError("No valid attendance rows found")

    df = pd.DataFrame(rows, columns=["Subject", "Present", "Absent"])
    df["Total"] = df["Present"] + df["Absent"]

    df["Attendance%"] = df.apply(
        lambda r: (r["Present"] / r["Total"] * 100) if r["Total"] > 0 else 0,
        axis=1
    )

    df["Status"] = df["Attendance%"].apply(
        lambda x: "Safe ✅" if x >= 75 else "Risk ⚠️"
    )

    return df.sort_values("Attendance%")

# ---------------- UTILITIES ----------------
def classes_to_attend(present, total, target):
    x = sp.symbols("x")
    sol = sp.solve((present + x) / (total + x) - target / 100, x)
    return max(0, math.ceil(sol[0])) if sol else 0

def classes_can_leave(present, total, target):
    if total == 0:
        return 0
    leave = 0
    while (present / (total + leave)) * 100 >= target:
        leave += 1
    return max(0, leave - 1)

# ---------------- CHARTS ----------------
def plot_aggregate_pie(present, absent):
    plt.figure(figsize=(5,5))
    plt.pie(
        [present, absent],
        labels=["Present", "Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90,
        wedgeprops={"edgecolor": "white"}
    )
    plt.title("Aggregate Attendance")
    st.pyplot(plt)
    plt.close()

def plot_bar_chart(df):
    plt.figure(figsize=(9,4))
    colors = BAR_COLORS * (len(df)//len(BAR_COLORS) + 1)
    plt.bar(df["Subject"], df["Present"], color=colors[:len(df)])
    plt.xticks(rotation=60, ha="right")
    plt.ylabel("Classes Present")
    plt.title("Present Classes per Subject")
    st.pyplot(plt)
    plt.close()

def plot_subject_pie(subject, present, absent):
    plt.figure(figsize=(5,5))
    plt.pie(
        [present, absent],
        labels=["Present", "Absent"],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90,
        wedgeprops={"edgecolor": "white"}
    )
    plt.title(subject)
    st.pyplot(plt)
    plt.close()

def plot_donut_charts(df):
    cols = 3
    rows = (len(df) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(9, rows * 3))
    axes = axes.flatten()

    for i, ax in enumerate(axes):
        if i >= len(df):
            ax.axis("off")
            continue

        r = df.iloc[i]
        ax.pie(
            [r["Present"], r["Absent"]],
            startangle=90,
            colors=[PRESENT_COLOR, ABSENT_COLOR],
            wedgeprops={"width":0.35, "edgecolor":"white"}
        )
        ax.text(
            0, 0,
            f"{r['Attendance%']:.0f}%",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold"
        )
        ax.set_title(r["Subject"], fontsize=10)

    st.pyplot(fig)
    plt.close()

# ---------------- PDF ----------------
def generate_pdf(df, total_present, total_absent):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",18)
    pdf.cell(0,10,"Attendance Report",ln=True,align="C")

    total = total_present + total_absent
    overall = (total_present / total) * 100 if total else 0

    pdf.set_font("Arial","",12)
    pdf.ln(6)
    pdf.cell(0,7,f"Overall Attendance: {overall:.1f}%",ln=True)

    pdf.ln(4)
    for _, r in df.iterrows():
        pdf.cell(
            0, 6,
            f"{r['Subject']} - {r['Attendance%']:.1f}% ({r['Status']})",
            ln=True
        )

    return pdf.output(dest="S").encode("latin-1")

# ---------------- INPUT ----------------
pasted = st.text_area("📋 Paste attendance data", height=300)
df = None

if pasted.strip():
    try:
        df = smart_parse_pasted_data(pasted)
        st.success("✅ Attendance parsed successfully")
    except Exception as e:
        st.error("❌ Parsing failed")
        st.code(str(e))

# ---------------- OUTPUT ----------------
if df is not None:
    st.subheader("📋 Attendance Overview")
    st.dataframe(df)

    total_present = df["Present"].sum()
    total_absent = df["Absent"].sum()
    total_classes = total_present + total_absent
    overall = (total_present / total_classes) * 100 if total_classes else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Present", total_present)
    c2.metric("Absent", total_absent)
    c3.metric("Overall %", f"{overall:.1f}")

    plot_aggregate_pie(total_present, total_absent)

    st.markdown("## 🎯 Target Aggregate")
    target_ag = st.number_input("Target (%)", 0, 100, 75)

    if target_ag > overall:
        need = classes_to_attend(total_present, total_classes, target_ag)
        st.warning(f"📌 Attend **{need} more classes** to reach {target_ag}%")
    else:
        leave = classes_can_leave(total_present, total_classes, target_ag)
        st.success(f"😌 You can **leave {leave} classes** and still stay at {target_ag}%")

    st.markdown("## 📈 Visual Insights")

    subject = st.selectbox("Select Subject", df["Subject"])
    row = df[df["Subject"] == subject].iloc[0]

    plot_subject_pie(subject, row["Present"], row["Absent"])
    plot_bar_chart(df)
    plot_donut_charts(df)

    st.subheader("📄 Download Report")
    pdf = generate_pdf(df, total_present, total_absent)
    st.download_button(
        "📥 Download PDF",
        pdf,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )
