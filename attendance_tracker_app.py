import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import sympy as sp
import re
import io

# ---------------- Page Config ----------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")
st.title("📊 Attendance Tracker")
st.caption("Paste attendance data directly from your college portal")

# ---------------- COLOR THEME ----------------
PRESENT_COLOR = "#4CAF50"
ABSENT_COLOR  = "#FF7043"

# ---------------- SAFE PASTE PARSER ----------------
def smart_parse_pasted_data(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []

    for line in lines:
        if "\t" in line:
            parts = line.split("\t")
        else:
            parts = re.split(r"\s{2,}", line)

        joined = " ".join(parts).lower()
        if "present" in joined and "absent" in joined:
            continue

        if len(parts) >= 9:
            try:
                present = int(parts[-5])
                absent = int(parts[-2])
                subject = " ".join(parts[2:-6]).strip()
                rows.append([subject, present, absent])
            except:
                continue

        elif len(parts) == 3:
            try:
                subject = parts[0].strip()
                present = int(parts[1])
                absent = int(parts[2])
                rows.append([subject, present, absent])
            except:
                continue

    if not rows:
        raise ValueError("No valid attendance rows found")

    df = pd.DataFrame(rows, columns=["Subject", "Present", "Absent"])
    df["Total"] = df["Present"] + df["Absent"]
    df["Attendance%"] = (df["Present"] / df["Total"]) * 100
    return df

# ---------------- UTILITIES ----------------
def classes_to_attend(present, total, target):
    x = sp.symbols("x")
    sol = sp.solve((present + x) / (total + x) - target / 100, x)
    return max(0, int(sol[0])) if sol else 0

def classes_can_leave(present, total, target):
    leave = 0
    while (present / (total + leave)) * 100 >= target:
        leave += 1
    return max(0, leave - 1)

# ---------------- CHART GENERATORS (RETURN IMAGE BYTES) ----------------
def pie_chart_image(subject, present, absent):
    fig, ax = plt.subplots(figsize=(4,4))
    ax.pie(
        [present, absent],
        labels=["Present","Absent"],
        autopct="%1.1f%%",
        startangle=90,
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        wedgeprops={"edgecolor":"white"}
    )
    ax.set_title(f"{subject} Attendance")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def bar_chart_image(df):
    fig, ax = plt.subplots(figsize=(6,3))
    palette = sns.color_palette("Set2", len(df))
    sns.barplot(x="Subject", y="Present", data=df, palette=palette, ax=ax)
    ax.set_title("Present Classes per Subject")
    ax.tick_params(axis="x", rotation=60)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def donut_charts_image(df):
    cols = 3
    rows = (len(df) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(6, rows * 2.5))
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
        ax.text(0, 0, f"{r['Attendance%']:.0f}%",
                ha="center", va="center", fontsize=10, fontweight="bold")
        ax.set_title(r["Subject"], fontsize=9)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

# ---------------- PDF WITH CHARTS ----------------
def generate_pdf_with_charts(df, subject, target, needed,
                             total_present, total_absent, target_ag):

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    pdf.set_font("Arial","B",18)
    pdf.cell(0,10,"Attendance Report",ln=True,align="C")
    pdf.ln(5)

    total_classes = total_present + total_absent
    overall = (total_present / total_classes) * 100 if total_classes else 0

    pdf.set_font("Arial","",12)
    pdf.cell(0,7,f"Overall Attendance: {overall:.1f}%",ln=True)
    pdf.cell(0,7,f"Total Present: {total_present}",ln=True)
    pdf.cell(0,7,f"Total Absent: {total_absent}",ln=True)
    pdf.ln(5)

    # -------- Charts --------
    pie = pie_chart_image(subject,
                          df[df["Subject"]==subject]["Present"].iloc[0],
                          df[df["Subject"]==subject]["Absent"].iloc[0])
    bar = bar_chart_image(df)
    donut = donut_charts_image(df)

    pdf.image(pie, x=30, w=150)
    pdf.add_page()
    pdf.image(bar, x=15, w=180)
    pdf.add_page()
    pdf.image(donut, x=10, w=190)

    return pdf.output(dest="S").encode("latin-1")

# ---------------- INPUT ----------------
st.subheader("📋 Paste Attendance Data")
pasted = st.text_area("Paste directly from your college portal / Excel", height=300)

df = None
if pasted.strip():
    try:
        df = smart_parse_pasted_data(pasted)
        st.success("✅ Attendance data parsed successfully!")
    except Exception as e:
        st.error("❌ Unable to parse pasted data")
        st.code(str(e))

# ---------------- OUTPUT ----------------
if df is not None:
    total_present = df["Present"].sum()
    total_absent = df["Absent"].sum()
    total_classes = total_present + total_absent
    overall = (total_present / total_classes) * 100 if total_classes else 0

    st.dataframe(df)

    st.markdown("## 🎯 Target Aggregate Attendance")
    target_ag = st.number_input("Target aggregate (%)", 0, 100, 75)

    st.markdown("## 🎯 Target Subject Attendance")
    target = st.number_input("Target subject (%)", 0, 100, 75)
    subject = st.selectbox("Select Subject", df["Subject"])
    row = df[df["Subject"] == subject].iloc[0]
    needed = classes_to_attend(row["Present"], row["Total"], target)

    st.subheader("📄 Download PDF (with charts)")
    pdf_bytes = generate_pdf_with_charts(
        df, subject, target, needed,
        total_present, total_absent, target_ag
    )

    st.download_button(
        "📥 Download Full PDF Report",
        pdf_bytes,
        file_name="attendance_report_with_charts.pdf",
        mime="application/pdf"
    )
