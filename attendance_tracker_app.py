import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import sympy as sp
import re

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

# ---------------- CHARTS ----------------
def plot_aggregate_pie(total_present, total_absent):
    plt.figure(figsize=(5,5))
    plt.pie(
        [total_present, total_absent],
        labels=["Present", "Absent"],
        autopct="%1.1f%%",
        startangle=90,
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        wedgeprops={"edgecolor": "white"}
    )
    plt.title("Aggregate Attendance")
    st.pyplot(plt)
    plt.close()

def plot_bar_chart(df):
    plt.figure(figsize=(9,4))
    palette = sns.color_palette("Set2", len(df))
    sns.barplot(
        x="Subject",
        y="Present",
        data=df,
        palette=palette
    )
    plt.xticks(rotation=60, ha="right")
    plt.title("Present Classes per Subject", fontsize=13)
    st.pyplot(plt)
    plt.close()

def plot_pie_chart(subject, present, absent):
    plt.figure(figsize=(5,5))
    plt.pie(
        [present, absent],
        labels=["Present","Absent"],
        autopct="%1.1f%%",
        startangle=90,
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        wedgeprops={"edgecolor":"white"}
    )
    plt.title(f"{subject} Attendance")
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
            0, 0, f"{r['Attendance%']:.0f}%",
            ha="center", va="center",
            fontsize=12, fontweight="bold"
        )
        ax.set_title(r["Subject"], fontsize=10)

    st.pyplot(fig)
    plt.close()

# ---------------- PDF ----------------
def generate_pdf(df, subject, target, needed,
                 total_present, total_absent, target_ag):

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",18)
    pdf.cell(0,10,"Attendance Report",ln=True,align="C")
    pdf.ln(6)

    total_classes = total_present + total_absent
    overall = (total_present / total_classes) * 100 if total_classes else 0

    pdf.set_font("Arial","",12)
    pdf.cell(0,7,f"Overall Attendance: {overall:.1f}%",ln=True)
    pdf.cell(0,7,f"Total Present: {total_present}",ln=True)
    pdf.cell(0,7,f"Total Absent: {total_absent}",ln=True)

    pdf.ln(6)
    pdf.set_font("Arial","B",14)
    pdf.cell(0,8,"Subject-wise Attendance",ln=True)
    pdf.set_font("Arial","",11)

    for _, r in df.iterrows():
        pdf.cell(0,6,f"{r['Subject']} - {r['Attendance%']:.1f}%",ln=True)

    pdf.ln(6)
    pdf.set_font("Arial","B",14)
    pdf.cell(0,8,"Target Summary",ln=True)
    pdf.set_font("Arial","",11)
    pdf.cell(0,6,f"Target Aggregate %: {target_ag}",ln=True)
    pdf.cell(0,6,f"Subject Target %: {target}",ln=True)
    pdf.cell(0,6,f"Classes needed (subject): {needed}",ln=True)

    return pdf.output(dest="S").encode("latin-1")

# ---------------- INPUT ----------------
st.subheader("📋 Paste Attendance Data")
pasted = st.text_area(
    "Paste directly from your college portal / Excel",
    height=300
)

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
    st.subheader("📋 Attendance Overview")
    st.dataframe(df)

    total_present = df["Present"].sum()
    total_absent = df["Absent"].sum()
    total_classes = total_present + total_absent
    overall = (total_present / total_classes) * 100 if total_classes else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Present", total_present)
    col2.metric("Total Absent", total_absent)
    col3.metric("Overall %", f"{overall:.1f}%")

    # ✅ Aggregate Pie Chart (same colors)
    plot_aggregate_pie(total_present, total_absent)

    # -------- TARGET AGGREGATE --------
    st.markdown("## 🎯 Target Aggregate Attendance")
    target_ag = st.number_input("Set your target aggregate (%)", 0, 100, 75)

    if target_ag > overall:
        need = classes_to_attend(total_present, total_classes, target_ag)
        st.warning(f"📌 Attend **{need} more classes** to reach {target_ag}%")
    elif target_ag < overall:
        leave = classes_can_leave(total_present, total_classes, target_ag)
        st.success(f"😌 You can **leave {leave} classes** and still stay at {target_ag}%")
    else:
        st.info("✅ You are exactly at your target aggregate attendance")

    # -------- TARGET SUBJECT --------
    st.markdown("## 🎯 Target Subject Attendance")
    target = st.number_input("Set subject target (%)", 0, 100, 75)
    subject = st.selectbox("Select Subject", df["Subject"])
    row = df[df["Subject"] == subject].iloc[0]
    needed = classes_to_attend(row["Present"], row["Total"], target)
    st.info(f"📘 Attend **{needed} more classes** in **{subject}** to reach {target}%")

    # -------- CHARTS --------
    st.subheader("📈 Visual Insights")
    plot_pie_chart(subject, row["Present"], row["Absent"])
    plot_bar_chart(df)
    plot_donut_charts(df)

    # -------- PDF DOWNLOAD --------
    st.subheader("📄 Download Report")
    pdf = generate_pdf(
        df, subject, target, needed,
        total_present, total_absent, target_ag
    )
    st.download_button(
        "📥 Download PDF",
        pdf,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )
