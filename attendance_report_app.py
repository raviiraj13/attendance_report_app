import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF

st.set_page_config(page_title="Attendance Report Generator", layout="wide")
st.title("📊 Attendance Report Generator")

st.write("""
Upload your attendance CSV file.
The CSV should have the following columns:
- Subject
- Present
- Absent
""")

uploaded_file = st.file_uploader("Choose CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if 'Total' not in df.columns:
        df['Total'] = df['Present'] + df['Absent']
    if 'Attendance%' not in df.columns:
        df['Attendance%'] = df['Present'] / df['Total'] * 100

    st.subheader("Preview")
    st.dataframe(df)

    # Bar chart
    st.subheader("Bar Chart")
    plt.figure(figsize=(10,5))
    barplot = sns.barplot(x='Subject', y='Present', data=df, palette='Set2')
    for p in barplot.patches:
        barplot.annotate(f'{int(p.get_height())}', 
                         (p.get_x() + p.get_width()/2, p.get_height()),
                         ha='center', va='bottom')
    plt.xticks(rotation=45)
    st.pyplot(plt)
    plt.close()

    # Donut charts
    st.subheader("Donut Charts")
    fig, axes = plt.subplots(4, 3, figsize=(15,15))
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

    # Insights
    st.subheader("Insights")
    insights_text = f"""
- **Average Attendance:** {df['Attendance%'].mean():.2f}%
- **Highest Attendance:** {df.loc[df['Attendance%'].idxmax()]['Subject']} ({df['Attendance%'].max():.0f}%)
- **Lowest Attendance:** {df.loc[df['Attendance%'].idxmin()]['Subject']} ({df['Attendance%'].min():.0f}%)

**Recommendations:**
- Focus on subjects with low attendance.
- Encourage interactive sessions to improve participation.
- Monitor weekly trends to maintain attendance.
"""
    st.markdown(insights_text)

    # PDF
    pdf_file = "attendance_report.pdf"
    pdf = FPDF('P', 'mm', 'A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=10)

    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "Attendance Report", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "Insights", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 6, insights_text)

    pdf.output(pdf_file)

    with open(pdf_file, "rb") as f:
        st.download_button(
            label="📥 Download Attendance Report PDF",
            data=f,
            file_name=pdf_file,
            mime="application/pdf"
        )
