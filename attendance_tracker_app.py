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
st.write("Upload CSV, paste CSV URL, or paste attendance table (Excel / portal).")

# ---------------- SAFE & CORRECT PASTE PARSER ----------------
def smart_parse_pasted_data(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []

    for line in lines:
        # split by tab OR multiple spaces
        if "\t" in line:
            parts = line.split("\t")
        else:
            parts = re.split(r"\s{2,}", line)

        joined = " ".join(parts).lower()
        if "present" in joined and "absent" in joined:
            continue

        # PORTAL FORMAT
        if len(parts) >= 9:
            try:
                present = int(parts[-5])   # ✅ correct
                absent = int(parts[-2])    # ✅ correct
                subject = " ".join(parts[2:-6]).strip()
                rows.append([subject, present, absent])
            except:
                continue

        # SIMPLE CSV / EXCEL FORMAT
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

# ---------------- Utilities ----------------
def finalize_df(df):
    df["Present"] = pd.to_numeric(df["Present"], errors="coerce").fillna(0)
    df["Absent"] = pd.to_numeric(df["Absent"], errors="coerce").fillna(0)
    df["Total"] = df["Present"] + df["Absent"]
    df["Attendance%"] = (df["Present"] / df["Total"]) * 100
    return df

def target_attendance(present, total, target):
    x = sp.symbols("x")
    sol = sp.solve((present + x) / (total + x) - target / 100, x)
    return max(0, int(sol[0])) if sol else 0

# ---------------- Charts ----------------
def plot_bar_chart(df):
    plt.figure(figsize=(8,4))
    sns.barplot(x="Subject", y="Present", data=df)
    plt.xticks(rotation=60, ha="right")
    plt.title("Present Classes per Subject")
    st.pyplot(plt)
    plt.close()

def plot_pie_chart(subject, present, absent):
    plt.figure(figsize=(5,5))
    plt.pie([present, absent],
            labels=["Present","Absent"],
            autopct="%1.1f%%",
            startangle=90)
    plt.title(f"Attendance for {subject}")
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
        ax.pie([r["Present"], r["Absent"]],
               startangle=90,
               wedgeprops=dict(width=0.4))
        ax.set_title(f"{r['Subject']}\n{r['Attendance%']:.0f}%")

    st.pyplot(fig)
    plt.close()

# ---------------- PDF ----------------
def generate_pdf(df, subject, target, needed,
                 total_present, total_absent, target_ag):
    pdf = FPDF()
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
    pdf.set_font("Arial","B",14)
    pdf.cell(0,8,"Subject-wise Attendance",ln=True)
    pdf.set_font("Arial","",11)

    for _, r in df.iterrows():
        pdf.cell(0,6,f"{r['Subject']} - {r['Attendance%']:.1f}%",ln=True)

    pdf.ln(5)
    pdf.set_font("Arial","B",14)
    pdf.cell(0,8,"Target Analysis",ln=True)
    pdf.set_font("Arial","",11)
    pdf.cell(0,6,f"Subject: {subject}",ln=True)
    pdf.cell(0,6,f"Target %: {target}",ln=True)
    pdf.cell(0,6,f"Classes needed: {needed}",ln=True)
    pdf.cell(0,6,f"Target Aggregate %: {target_ag}",ln=True)

    return pdf.output(dest="S").encode("latin-1")

# ---------------- Input ----------------
option = st.radio(
    "How do you want to provide attendance data?",
    ("Upload CSV", "CSV URL", "Paste Data")
)

df = None

if option == "Upload CSV":
    file = st.file_uploader("Upload CSV", type=["csv"])
    if file:
        df = finalize_df(pd.read_csv(file))

elif option == "CSV URL":
    url = st.text_input("Enter CSV URL")
    if url:
        df = finalize_df(pd.read_csv(url))

elif option == "Paste Data":
    pasted = st.text_area("📋 Paste attendance table here", height=350)
    if pasted.strip():
        try:
            df = smart_parse_pasted_data(pasted)
            st.success("✅ Pasted data parsed correctly!")
        except Exception as e:
            st.error("❌ Unable to parse pasted data")
            st.code(str(e))

# ---------------- Output ----------------
if df is not None:
    st.subheader("📋 Data Preview")
    st.dataframe(df)

    total_present = df["Present"].sum()
    total_absent = df["Absent"].sum()
    total_classes = total_present + total_absent
    overall = (total_present / total_classes) * 100 if total_classes else 0

    st.subheader("📊 Aggregate Attendance")
    st.metric("Total Present", total_present)
    st.metric("Total Absent", total_absent)
    st.metric("Overall Attendance %", f"{overall:.1f}%")

    st.subheader("🎯 Target Attendance")
    target = st.number_input("Target %", 0, 100, 75)
    subject = st.selectbox("Select Subject", df["Subject"])
    row = df[df["Subject"] == subject].iloc[0]
    needed = target_attendance(row["Present"], row["Total"], target)
    st.success(f"You need **{needed} more classes** in {subject}")

    st.subheader("🎯 Target Aggregate Attendance")
    target_ag = st.number_input("Target Aggregate %", 0, 100, 75)
    needed_ag = target_attendance(total_present, total_classes, target_ag)
    st.info(f"You need **{needed_ag} more classes overall**")

    st.subheader("📈 Charts")
    plot_pie_chart(subject, row["Present"], row["Absent"])
    plot_bar_chart(df)
    plot_donut_charts(df)

    st.subheader("📄 Download PDF")
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
