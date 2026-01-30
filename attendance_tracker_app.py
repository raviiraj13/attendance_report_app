import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import sympy as sp
import io

# ---------------- Page Config ----------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")
st.title("📊 Attendance Tracker")
st.write("Upload CSV, paste CSV URL, or paste copied attendance tables (Excel / portal).")

# ---------------- Core Utilities ----------------
def finalize_df(df):
    df.columns = df.columns.str.strip()
    df['Present'] = pd.to_numeric(df['Present'], errors='coerce').fillna(0)
    df['Absent'] = pd.to_numeric(df['Absent'], errors='coerce').fillna(0)
    df['Total'] = df['Present'] + df['Absent']
    df['Attendance%'] = df['Present'] / df['Total'] * 100
    return df

# ---------------- Charts ----------------
def plot_bar_chart(df):
    plt.figure(figsize=(8,4))
    barplot = sns.barplot(x='Subject', y='Present', data=df, palette='Set2')
    for p in barplot.patches:
        barplot.annotate(f'{int(p.get_height())}',
                         (p.get_x() + p.get_width()/2, p.get_height()),
                         ha='center', va='bottom', fontsize=9)
    plt.xticks(rotation=60, ha='right', fontsize=9)
    plt.title("Present Classes per Subject")
    plt.tight_layout()
    st.pyplot(plt)
    plt.close()

def plot_donut_charts(df):
    n_rows = (len(df)+2)//3
    fig, axes = plt.subplots(n_rows, 3, figsize=(9, n_rows*3))
    axes = axes.flatten()
    for i, ax in enumerate(axes):
        if i >= len(df):
            ax.axis('off')
            continue
        r = df.iloc[i]
        ax.pie([r['Present'], r['Absent']],
               labels=['',''],
               colors=['#1abc9c','#f39c12'],
               startangle=90,
               wedgeprops={'width':0.4,'edgecolor':'white'})
        ax.text(0,0,f"{r['Attendance%']:.0f}%",
                ha='center', va='center', fontsize=10, fontweight='bold')
        ax.set_title(r['Subject'], fontsize=10)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

def plot_pie_chart(subject, present, absent):
    plt.figure(figsize=(5,5))
    plt.pie([present, absent],
            labels=['Present','Absent'],
            autopct='%1.1f%%',
            startangle=90,
            colors=['#1abc9c','#f39c12'],
            wedgeprops={'edgecolor':'white'})
    plt.title(f"Attendance for {subject}")
    st.pyplot(plt)
    plt.close()

# ---------------- Math Logic ----------------
def target_attendance(present, total, target):
    x = sp.symbols('x')
    sol = sp.solve((present+x)/(total+x) - target/100, x)
    return max(0, int(sol[0])) if sol else 0

# ---------------- PDF ----------------
def generate_pdf(df, subject, target, needed,
                 total_present, total_absent, target_ag):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",18)
    pdf.cell(0,10,"Attendance Report",ln=True,align="C")
    pdf.ln(4)

    total_classes = total_present + total_absent
    overall = (total_present/total_classes)*100 if total_classes else 0

    pdf.set_font("Arial","",12)
    pdf.cell(0,7,f"Overall Attendance: {overall:.1f}%",ln=True)
    pdf.cell(0,7,f"Total Present: {total_present}",ln=True)
    pdf.cell(0,7,f"Total Absent: {total_absent}",ln=True)

    pdf.ln(4)
    pdf.set_font("Arial","B",14)
    pdf.cell(0,8,"Subject-wise Attendance",ln=True)
    pdf.set_font("Arial","",11)

    for _, r in df.iterrows():
        pdf.cell(0,6,f"{r['Subject']} - {r['Attendance%']:.1f}%",ln=True)

    pdf.ln(4)
    pdf.set_font("Arial","B",14)
    pdf.cell(0,8,"Target Analysis",ln=True)
    pdf.set_font("Arial","",11)
    pdf.cell(0,6,f"Subject: {subject}",ln=True)
    pdf.cell(0,6,f"Target %: {target}",ln=True)
    pdf.cell(0,6,f"Classes needed: {needed}",ln=True)
    pdf.cell(0,6,f"Target Aggregate %: {target_ag}",ln=True)

    return pdf.output(dest='S').encode('latin-1')

# ---------------- Input Section ----------------
input_option = st.radio(
    "How do you want to provide attendance data?",
    ("Upload File", "CSV URL", "Paste Data")
)

df = None

# ---------- Upload ----------
if input_option == "Upload File":
    file = st.file_uploader("Upload CSV file", type=["csv"])
    if file:
        df = finalize_df(pd.read_csv(file))

# ---------- URL ----------
elif input_option == "CSV URL":
    url = st.text_input("Enter CSV file URL")
    if url:
        df = finalize_df(pd.read_csv(url))

# ---------- Paste ----------
elif input_option == "Paste Data":
    pasted = st.text_area("📋 Paste copied attendance table", height=320)

    if pasted.strip():
        try:
            try:
                df_raw = pd.read_csv(io.StringIO(pasted), sep=None, engine="python")
            except:
                df_raw = pd.read_csv(io.StringIO(pasted),
                                     delim_whitespace=True,
                                     header=None)

            df_raw = df_raw.dropna(axis=1, how="all")
            df_raw.columns = range(len(df_raw.columns))

            # Smart reconstruction for portal-style data
            df = pd.DataFrame()
            df["Present"] = pd.to_numeric(df_raw.iloc[:, -4], errors="coerce")
            df["Absent"] = pd.to_numeric(df_raw.iloc[:, -2], errors="coerce")
            df["Subject"] = df_raw.iloc[:, 2:-5].astype(str).agg(" ".join, axis=1)

            df = finalize_df(df)
            st.success("✅ Pasted data parsed successfully!")

        except Exception as e:
            st.error("❌ Could not parse pasted data")
            st.code(str(e))

# ---------------- Output Section ----------------
if df is not None:
    st.subheader("📋 Data Preview")
    st.dataframe(df)

    total_present = df['Present'].sum()
    total_absent = df['Absent'].sum()
    total_classes = total_present + total_absent
    overall = (total_present/total_classes)*100 if total_classes else 0

    st.subheader("📊 Aggregate Attendance")
    st.metric("Total Present", total_present)
    st.metric("Total Absent", total_absent)
    st.metric("Overall Attendance %", f"{overall:.1f}%")

    st.subheader("🎯 Target Attendance")
    target = st.number_input("Target %", 0, 100, 75)
    subject = st.selectbox("Select Subject", df['Subject'])
    row = df[df['Subject']==subject].iloc[0]
    needed = target_attendance(row['Present'], row['Total'], target)
    st.success(f"You need **{needed} more classes** in {subject}")

    st.subheader("🎯 Target Aggregate Attendance")
    target_ag = st.number_input("Target Aggregate %", 0, 100, 75)
    needed_ag = target_attendance(total_present, total_classes, target_ag)
    st.info(f"You need **{needed_ag} more classes overall**")

    st.subheader("📈 Charts")
    plot_pie_chart(subject, row['Present'], row['Absent'])
    plot_bar_chart(df)
    plot_donut_charts(df)

    st.subheader("📄 Download PDF")
    pdf_bytes = generate_pdf(df, subject, target, needed,
                             total_present, total_absent, target_ag)
    st.download_button("📥 Download PDF",
                       data=pdf_bytes,
                       file_name="attendance_report.pdf",
                       mime="application/pdf")
