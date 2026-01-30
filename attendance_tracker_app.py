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
st.write("Upload CSV, paste CSV URL, or paste copied table data (Excel / portal).")

# ---------------- Functions ----------------
def compute_attendance(df):
    df.columns = df.columns.str.strip()
    df['Present'] = pd.to_numeric(df['Present'], errors='coerce').fillna(0)
    df['Absent'] = pd.to_numeric(df['Absent'], errors='coerce').fillna(0)
    df['Total'] = df['Present'] + df['Absent']
    df['Attendance%'] = df['Present'] / df['Total'] * 100
    return df

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
        row = df.iloc[i]
        ax.pie([row['Present'], row['Absent']],
               labels=['',''],
               colors=['#1abc9c','#f39c12'],
               startangle=90,
               wedgeprops={'width':0.4,'edgecolor':'white'})
        ax.text(0,0,f"{row['Attendance%']:.0f}%", ha='center', va='center',
                fontsize=10, fontweight='bold')
        ax.set_title(row['Subject'], fontsize=10)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

def target_attendance(present, total_classes, target_percent):
    x = sp.symbols('x')
    sol = sp.solve((present + x)/(total_classes + x) - target_percent/100, x)
    return max(0, int(sol[0])) if sol else 0

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

def generate_pdf(df, subject, target_percent, classes_needed,
                 total_present, total_absent, target_aggregate):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",18)
    pdf.cell(0,10,"Attendance Report",ln=True,align="C")
    pdf.ln(5)

    pdf.set_font("Arial","",12)
    total_classes = total_present + total_absent
    overall = (total_present/total_classes)*100 if total_classes else 0
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
    pdf.cell(0,6,f"Target %: {target_percent}",ln=True)
    pdf.cell(0,6,f"Classes needed: {classes_needed}",ln=True)
    pdf.cell(0,6,f"Target Aggregate: {target_aggregate}%",ln=True)

    return pdf.output(dest='S').encode('latin-1')

# ---------------- Input Section ----------------
input_option = st.radio(
    "How do you want to provide attendance data?",
    ("Upload File", "CSV URL", "Paste Data")
)

df = None

if input_option == "Upload File":
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
    if uploaded_file:
        df = compute_attendance(pd.read_csv(uploaded_file))

elif input_option == "CSV URL":
    url = st.text_input("Enter CSV URL")
    if url:
        df = compute_attendance(pd.read_csv(url))

elif input_option == "Paste Data":
    pasted_data = st.text_area(
        "📋 Paste copied table (Excel / portal / CSV)",
        height=280
    )
    if pasted_data.strip():
        try:
            df = compute_attendance(
                pd.read_csv(io.StringIO(pasted_data), sep=None, engine="python")
            )
            st.success("✅ Data converted successfully!")
        except Exception as e:
            st.error("❌ Failed to parse pasted data")
            st.code(str(e))

# ---------------- Analysis Section ----------------
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
    pdf = generate_pdf(df, subject, target, needed,
                       total_present, total_absent, target_ag)
    st.download_button("📥 Download PDF", pdf,
                       file_name="attendance_report.pdf",
                       mime="application/pdf")
