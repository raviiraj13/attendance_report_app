import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import sympy as sp

# --------------------------
# Step 1: Streamlit Page Setup
# --------------------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")
st.title("📊 Attendance Tracker")
st.write("""
Upload your attendance CSV file with columns: **Subject, Present, Absent**.
The app will show aggregate attendance, charts, target calculations, and generate a PDF report.
""")

# --------------------------
# Step 2: Functions
# --------------------------
def load_data(uploaded_file):
    """Load CSV and calculate total and attendance % if missing"""
    df = pd.read_csv(uploaded_file)
    if 'Total' not in df.columns:
        df['Total'] = df['Present'] + df['Absent']
    if 'Attendance%' not in df.columns:
        df['Attendance%'] = df['Present'] / df['Total'] * 100
    return df

def plot_bar_chart(df):
    """Bar chart of Present classes"""
    plt.figure(figsize=(10,5))
    barplot = sns.barplot(x='Subject', y='Present', data=df, palette='Set2')
    for p in barplot.patches:
        barplot.annotate(f'{int(p.get_height())}', 
                         (p.get_x() + p.get_width()/2, p.get_height()),
                         ha='center', va='bottom')
    plt.xticks(rotation=45)
    plt.title("Present Classes per Subject")
    st.pyplot(plt)
    plt.close()

def plot_donut_charts(df):
    """Donut chart per subject"""
    n_rows = (len(df) + 2) // 3
    fig, axes = plt.subplots(n_rows, 3, figsize=(15, n_rows*4))
    axes = axes.flatten()
    for i, ax in enumerate(axes):
        if i >= len(df):
            ax.axis('off')
            continue
        row = df.iloc[i]
        values = [row['Present'], row['Absent']]
        ax.pie(values, labels=['',''], colors=['#1abc9c','#f39c12'],
               startangle=90, wedgeprops={'width':0.4,'edgecolor':'white'})
        ax.text(0,0,f"{row['Attendance%']:.0f}%", ha='center', va='center', fontsize=14, fontweight='bold')
        ax.set_title(row['Subject'], fontsize=12, fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

def target_attendance(present, total_classes, target_percent):
    """Calculate additional classes needed to reach target attendance"""
    x = sp.symbols('x')
    solution = sp.solve((present + x) / (total_classes + x) - target_percent/100, x)
    return int(solution[0]) if solution else 0

def plot_pie_chart(subject, present, absent):
    """Pie chart for single subject"""
    values = [present, absent]
    labels = ['Present', 'Absent']
    colors = ['#1abc9c', '#f39c12']
    plt.figure(figsize=(6,6))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90,
            colors=colors, wedgeprops={'edgecolor':'white'})
    plt.title(f"Attendance for {subject}")
    st.pyplot(plt)
    plt.close()

def generate_pdf(df, subject, target_percent, classes_needed, total_present, total_absent):
    """Generate PDF report"""
    pdf = FPDF('P', 'mm', 'A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=10)

    # Title
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "Attendance Report", ln=True, align='C')
    pdf.ln(10)

    # Aggregate attendance
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "Aggregate Attendance", ln=True)
    pdf.set_font("Arial", '', 12)
    total_classes = total_present + total_absent
    overall_attendance = total_present / total_classes * 100 if total_classes > 0 else 0
    pdf.cell(0, 6, f"Total Present: {total_present}", ln=True)
    pdf.cell(0, 6, f"Total Absent: {total_absent}", ln=True)
    pdf.cell(0, 6, f"Overall Attendance: {overall_attendance:.1f}%", ln=True)
    pdf.ln(5)

    # Table of subjects
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "Subjects Attendance Data", ln=True)
    pdf.set_font("Arial", '', 12)
    for idx, r in df.iterrows():
        pdf.cell(0, 6, f"{r['Subject']}: Present {r['Present']}, Absent {r['Absent']}, Attendance {r['Attendance%']:.1f}%", ln=True)
    pdf.ln(5)

    # Target attendance info
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, f"Target Attendance Calculation for {subject}", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 6, f"Target: {target_percent}%", ln=True)
    pdf.cell(0, 6, f"Classes needed to reach target: {classes_needed}", ln=True)

    # Return PDF as bytes
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return pdf_bytes

# --------------------------
# Step 3: Streamlit Interface
# --------------------------
st.write("Upload your attendance CSV file:")
uploaded_file = st.file_uploader("CSV file", type="csv")

if uploaded_file:
    df = load_data(uploaded_file)
    st.subheader("Preview")
    st.dataframe(df)

    # --------------------------
    # Aggregate Attendance Section
    # --------------------------
    st.subheader("📊 Aggregate Attendance")
    total_present = df['Present'].sum()
    total_absent = df['Absent'].sum()
    total_classes = total_present + total_absent
    overall_attendance = total_present / total_classes * 100 if total_classes > 0 else 0

    st.metric("Total Present Classes", total_present)
    st.metric("Total Absent Classes", total_absent)
    st.metric("Overall Attendance %", f"{overall_attendance:.1f}%")

    # Pie chart for aggregate attendance
    values = [total_present, total_absent]
    labels = ['Present', 'Absent']
    colors = ['#1abc9c', '#f39c12']
    plt.figure(figsize=(6,6))
    plt.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        wedgeprops={'edgecolor':'white'}
    )
    plt.title("Aggregate Attendance")
    st.pyplot(plt)
    plt.close()

    # --------------------------
    # Target attendance
    # --------------------------
    st.subheader("🎯 Target Attendance Calculator")
    target = st.number_input("Enter your target attendance (%)", min_value=0, max_value=100, value=75, step=1)
    subject = st.selectbox("Select a subject", df['Subject'])
    row = df[df['Subject'] == subject].iloc[0]
    present = row['Present']
    total_classes = row['Total']
    classes_needed = target_attendance(present, total_classes, target)
    st.write(f"✅ You need to attend **{classes_needed} more classes** in {subject} to reach {target}% attendance.")

    st.subheader(f"Pie Chart for {subject}")
    plot_pie_chart(subject, present, row['Absent'])

    # --------------------------
    # Charts (after insights)
    # --------------------------
    st.subheader("Bar Chart of Present Classes")
    plot_bar_chart(df)

    st.subheader("Donut Charts per Subject")
    plot_donut_charts(df)

    # --------------------------
    # PDF Download
    # --------------------------
    st.subheader("📄 Download PDF Report")
    pdf_bytes = generate_pdf(df, subject, target, classes_needed, total_present, total_absent)
    st.download_button(
        label="📥 Download PDF",
        data=pdf_bytes,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )
