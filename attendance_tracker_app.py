
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import math
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Attendance Tracker", layout="wide")
st.title("📊 Attendance Tracker")
st.caption("Paste your college ERP attendance report.")

PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR = "#F39C12"


# ---------------- HELPERS ----------------
def clean_text(text):
    return str(text).encode("latin-1", "replace").decode("latin-1")


def attendance_percentage(present, total):
    return present / total * 100 if total > 0 else 0.0


def parse_attendance(text):
    rows = []

    for line in text.splitlines():
        parts = re.split(r"\t+", line.strip())

        if len(parts) < 9 or not parts[0].strip().isdigit():
            continue

        try:
            subject = parts[2].strip()
            present = int(parts[4].strip())
            od = int(parts[5].strip())
            makeup = int(parts[6].strip())
            absent = int(parts[7].strip())
        except (ValueError, IndexError):
            continue

        rows.append([subject, present, od, makeup, absent])

    df = pd.DataFrame(
        rows,
        columns=["Subject", "Present", "OD", "Makeup", "Absent"]
    )

    if df.empty:
        return df

    df["Effective Present"] = (
        df["Present"] + df["OD"] + df["Makeup"]
    )
    df["Total Classes"] = df["Present"] + df["Absent"]

    df["Attendance%"] = (
        df["Effective Present"]
        / df["Total Classes"].replace(0, float("nan"))
        * 100
    ).round(2)

    df["Status"] = df["Attendance%"].apply(
        lambda x: "🟢" if pd.notna(x) and x >= 75 else "🔴"
    )

    return df.sort_values("Attendance%")


# ---------------- CLASSES NEEDED ----------------
def classes_needed(present, total, target):
    """Minimum consecutive classes attended to reach target."""
    if attendance_percentage(present, total) >= target:
        return 0

    if target >= 100:
        return math.inf

    return max(
        0,
        math.ceil(
            (target * total - 100 * present)
            / (100 - target) - 1e-10
        )
    )


# ---------------- CLASSES THAT CAN BE MISSED ----------------
def classes_can_leave(present, total, target):
    """Maximum additional absences while staying at/above target."""
    if target <= 0:
        return math.inf

    if attendance_percentage(present, total) < target:
        return 0

    return max(
        0,
        math.floor(100 * present / target - total + 1e-10)
    )


# ---------------- PIE CHART ----------------
def plot_attendance_percentage_pie(present, total):
    if total <= 0:
        return

    attended = min(100, max(0, attendance_percentage(present, total)))

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        [attended, 100 - attended],
        labels=[
            f"Attended {attended:.2f}%",
            f"Missed {100 - attended:.2f}%"
        ],
        autopct="%1.1f%%",
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        startangle=90
    )
    ax.set_title("Aggregate Attendance")
    st.pyplot(fig)
    plt.close(fig)


# ---------------- PDF ----------------
def generate_pdf(aggregate, df, event_present, event_absent,
                 total, attended):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Attendance Report", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Aggregate Attendance: {aggregate:.2f}%", ln=True)
    pdf.cell(0, 8, f"Attended hours: {attended}", ln=True)
    pdf.cell(0, 8, f"Total counted hours: {total}", ln=True)
    pdf.cell(
        0, 8,
        f"Event hours: {event_present} present, {event_absent} absent",
        ln=True
    )

    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Subject-wise Attendance", ln=True)
    pdf.set_font("Arial", "", 10)

    for _, row in df.iterrows():
        value = row["Attendance%"]
        value_text = f"{value:.2f}%" if pd.notna(value) else "N/A"
        pdf.multi_cell(
            0, 7, clean_text(f"{row['Subject']}: {value_text}")
        )

    return pdf.output(dest="S").encode("latin-1")


# ---------------- INPUT ----------------
text = st.text_area(
    "Paste Attendance Report",
    height=300,
    placeholder="Paste the tab-separated ERP table here..."
)

st.subheader("📅 Event Attendance")

col1, col2 = st.columns(2)

with col1:
    event_present = st.number_input(
        "Event hours attended", min_value=0, value=12, step=1
    )

with col2:
    event_absent = st.number_input(
        "Event hours absent", min_value=0, value=12, step=1
    )

target = st.number_input(
    "Target attendance (%)",
    min_value=1,
    max_value=100,
    value=75,
    step=1
)


if text.strip():
    df = parse_attendance(text)

    if df.empty:
        st.error(
            "No subject rows detected. Please paste the complete "
            "tab-separated attendance table."
        )
        st.stop()

    st.success("Attendance report parsed successfully!")

    # ---------------- SUBJECT TABLE ----------------
    st.subheader("📚 Subject-wise Attendance")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ---------------- AGGREGATE CALCULATION ----------------
    subject_present = int(df["Present"].sum())
    total_od = int(df["OD"].sum())
    total_makeup = int(df["Makeup"].sum())
    subject_absent = int(df["Absent"].sum())

    subject_attended = subject_present + total_od + total_makeup
    subject_total = subject_present + subject_absent

    aggregate_present = subject_attended + event_present
    total_classes = subject_total + event_present + event_absent

    aggregate_attendance = attendance_percentage(
        aggregate_present, total_classes
    )

    # ---------------- SUMMARY ----------------
    st.subheader("📈 Overall Summary")

    c1, c2, c3 = st.columns(3)
    c1.metric("Subject Present", subject_present)
    c2.metric("Subject Absent", subject_absent)
    c3.metric("Subject Total", subject_total)

    c4, c5, c6 = st.columns(3)
    c4.metric("OD", total_od)
    c5.metric("Makeup", total_makeup)
    c6.metric("Event Hours", event_present + event_absent)

    st.metric(
        "Subject-only Attendance",
        f"{attendance_percentage(subject_attended, subject_total):.2f}%"
    )

    st.metric(
        "Aggregate Attendance (including events)",
        f"{aggregate_attendance:.2f}%"
    )

    st.caption(
        f"Aggregate = {aggregate_present} attended / "
        f"{total_classes} total hours."
    )

    plot_attendance_percentage_pie(
        aggregate_present, total_classes
    )

    # ---------------- TARGET OPTIMIZER ----------------
    st.subheader("🎯 Aggregate Target Optimizer")

    need = classes_needed(
        aggregate_present, total_classes, target
    )

    if aggregate_attendance < target:
        if math.isinf(need):
            st.warning("This target cannot be reached under these assumptions.")
        else:
            st.warning(
                f"Attend {need} consecutive classes without absence "
                f"to reach {target}%."
            )
    else:
        safe_leave = classes_can_leave(
            aggregate_present, total_classes, target
        )

        st.success(
            f"You can miss up to {safe_leave} additional classes "
            f"and remain at or above {target}%."
        )

    # ---------------- ATTENDANCE FORECAST ----------------
    st.subheader("🔮 Attendance Forecast & Leave Planner")

    st.caption(
        "Enter the number of future classes you expect to attend "
        "and the number you may miss."
    )

    col1, col2 = st.columns(2)

    with col1:
        attend_x = st.number_input(
            "Future classes you will attend",
            min_value=0,
            max_value=10000,
            value=20,
            step=1,
            key="future_attend"
        )

    with col2:
        leave_x = st.number_input(
            "Future classes you might miss",
            min_value=0,
            max_value=10000,
            value=0,
            step=1,
            key="future_leave"
        )

    # Projection after attending classes
    projected_present = aggregate_present + attend_x
    projected_total = total_classes + attend_x

    attendance_after_attending = attendance_percentage(
        projected_present, projected_total
    )

    st.markdown("### 📈 Attendance after attending classes")

    m1, m2, m3 = st.columns(3)

    m1.metric(
        "Projected attendance",
        f"{attendance_after_attending:.2f}%",
        delta=f"{attendance_after_attending - aggregate_attendance:+.2f}%"
    )
    m2.metric("Attended hours", projected_present)
    m3.metric("Total hours", projected_total)

    # Projection after both attendance and absence
    final_total = projected_total + leave_x

    final_attendance = attendance_percentage(
        projected_present, final_total
    )

    st.markdown("### 🧮 After attending and missing classes")

    f1, f2, f3 = st.columns(3)

    f1.metric("Final attendance", f"{final_attendance:.2f}%")
    f2.metric("Attended hours", projected_present)
    f3.metric("Total hours", final_total)

    if final_attendance >= target:
        st.success(
            f"Your final attendance will be {final_attendance:.2f}%, "
            f"meeting your {target}% target."
        )
    else:
        st.warning(
            f"Your final attendance will be {final_attendance:.2f}%, "
            f"below your {target}% target."
        )

    # ---------------- SAFE LEAVE AFTER PLANNED ATTENDANCE ----------------
    st.markdown("### 🏖️ How many classes can I leave?")

    safe_leave = classes_can_leave(
        projected_present, projected_total, target
    )

    if math.isinf(safe_leave):
        st.success("There is no attendance limit for a 0% target.")
    elif safe_leave == 0:
        st.warning(
            f"After attending {attend_x} classes, you cannot miss "
            f"any additional classes and remain at {target}%."
        )
    else:
        st.success(
            f"After attending {attend_x} classes, you can miss up to "
            f"{safe_leave} more classes and remain at or above {target}%."
        )

    # ---------------- RECOVERY CALCULATION ----------------
    st.markdown("### 🔄 Recovery Calculator")

    recovery = classes_needed(
        projected_present, final_total, target
    )

    if final_attendance >= target:
        st.info("Your final projected attendance already meets the target.")
    elif math.isinf(recovery):
        st.info("The target cannot be reached under these assumptions.")
    else:
        st.info(
            f"After your planned absences, attend {recovery} consecutive "
            f"classes without missing any to reach {target}%."
        )

    # ---------------- SUBJECT-WISE OPTIMIZER ----------------
    st.subheader("🎯 Subject-wise Target Optimizer")

    subject = st.selectbox("Select Subject", df["Subject"])
    row = df[df["Subject"] == subject].iloc[0]

    sub_present = int(row["Effective Present"])
    sub_total = int(row["Total Classes"])
    sub_attendance = attendance_percentage(sub_present, sub_total)

    sub_need = classes_needed(sub_present, sub_total, target)

    if sub_attendance < target:
        if math.isinf(sub_need):
            st.warning(f"{subject}: target cannot be reached.")
        else:
            st.warning(
                f"{subject}: attend {sub_need} consecutive classes "
                f"to reach {target}%."
            )
    else:
        sub_leave = classes_can_leave(sub_present, sub_total, target)
        st.success(
            f"{subject}: you can miss up to {sub_leave} classes "
            f"before falling below {target}%."
        )

    # ---------------- PDF DOWNLOAD ----------------
    pdf = generate_pdf(
        aggregate_attendance,
        df,
        event_present,
        event_absent,
        total_classes,
        aggregate_present
    )

    st.download_button(
        "📄 Download Attendance PDF",
        data=pdf,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )

else:
    st.info("Paste your ERP attendance table to calculate attendance.")
    
