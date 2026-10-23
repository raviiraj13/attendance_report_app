
import streamlit as st
import pandas as pd
import math
import re

st.set_page_config(page_title="Interactive Attendance Tracker", layout="wide")
st.title("📊 Interactive Attendance Tracker")

# ---------- CALCULATIONS ----------
def percentage(present, total):
    return 100 * present / total if total > 0 else 0.0


def classes_needed(present, total, target):
    if percentage(present, total) >= target:
        return 0
    if target >= 100:
        return math.inf
    return max(
        0,
        math.ceil(
            (target * total - 100 * present) / (100 - target) - 1e-10
        )
    )


def classes_can_leave(present, total, target):
    if target <= 0:
        return math.inf
    if percentage(present, total) < target:
        return 0
    return max(
        0,
        math.floor(100 * present / target - total + 1e-10)
    )


# ---------- ERP PARSER ----------
def parse_attendance(text):
    rows = []

    for line in text.splitlines():
        parts = re.split(r"\t+", line.strip())

        if len(parts) < 9 or not parts[0].strip().isdigit():
            continue

        try:
            rows.append([
                parts[1].strip(),  # Subject code
                parts[2].strip(),  # Subject
                parts[3].strip(),  # Subject type
                int(parts[4]),
                int(parts[5]),
                int(parts[6]),
                int(parts[7]),
            ])
        except (ValueError, IndexError):
            continue

    df = pd.DataFrame(
        rows,
        columns=[
            "Subject Code", "Subject", "Subject Type",
            "Present", "OD", "Makeup", "Absent"
        ]
    )

    if df.empty:
        return df

    df["Effective Present"] = (
        df["Present"] + df["OD"] + df["Makeup"]
    )

    df["Total Classes"] = df["Present"] + df["Absent"]

    df["Attendance %"] = (
        df["Effective Present"]
        / df["Total Classes"].replace(0, float("nan"))
        * 100
    ).round(2)

    return df


# ---------- FIRST: PASTE ERP ATTENDANCE ----------
st.subheader("1️⃣ Paste your ERP attendance report")

erp_text = st.text_area(
    "Copy and paste the complete attendance table from your college ERP",
    height=260,
    placeholder=(
        "Paste the table with columns: #, Subject Code, Subject, "
        "Subject Type, Present, OD, Makeup, Absent, Percentage"
    )
)

df = parse_attendance(erp_text)

if df.empty:
    st.info("Paste your ERP report above to activate the attendance calculators.")
    st.stop()

st.success(f"Successfully loaded attendance for {len(df)} subjects.")

# ---------- TARGET ----------
st.subheader("2️⃣ Set your target")

target = st.slider(
    "Target attendance (%)",
    min_value=1,
    max_value=100,
    value=75,
    step=1
)

# ---------- EVENT HOURS ----------
st.subheader("📅 Additional event attendance")

st.caption(
    "Event hours affect aggregate attendance, not subject-wise attendance. "
    "For example, Techpravah: 12 present and 12 absent."
)

event_col1, event_col2 = st.columns(2)

with event_col1:
    event_present = st.number_input(
        "Event hours attended",
        min_value=0,
        value=12,
        step=1
    )

with event_col2:
    event_absent = st.number_input(
        "Event hours missed",
        min_value=0,
        value=12,
        step=1
    )

# ---------- SUBJECT-WISE ATTENDANCE ----------
st.subheader("3️⃣ Subject-wise attendance")

st.caption(
    f"🟢 Green = at or above {target}%  |  🔴 Red = below {target}%"
)

display_df = df.copy()

display_df["Status"] = display_df["Attendance %"].apply(
    lambda value: (
        "🟢 Above target"
        if pd.notna(value) and value >= target
        else "🔴 Below target"
    )
)

def color_attendance(value):
    if pd.isna(value):
        return ""
    if value >= target:
        return "background-color: #d4edda; color: #155724; font-weight: bold"
    return "background-color: #f8d7da; color: #721c24; font-weight: bold"


styled_df = display_df.style.map(
    color_attendance,
    subset=["Attendance %"]
)

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# ---------- AGGREGATE ----------
subject_present = int(df["Present"].sum())
subject_od = int(df["OD"].sum())
subject_makeup = int(df["Makeup"].sum())
subject_absent = int(df["Absent"].sum())

subject_attended = subject_present + subject_od + subject_makeup
subject_total = subject_present + subject_absent

aggregate_present = subject_attended + event_present
aggregate_absent = subject_absent + event_absent
aggregate_total = subject_total + event_present + event_absent

current_pct = percentage(aggregate_present, aggregate_total)

st.subheader("4️⃣ Overall attendance")

c1, c2, c3 = st.columns(3)

c1.metric("Aggregate attendance", f"{current_pct:.2f}%")
c2.metric("Attended hours", aggregate_present)
c3.metric("Total hours", aggregate_total)

if current_pct >= target:
    st.success(f"Your aggregate attendance meets the {target}% target.")
else:
    need = classes_needed(aggregate_present, aggregate_total, target)
    st.warning(
        f"Attend {need} consecutive classes without absence "
        f"to reach {target}%."
    )


# ---------- CLASS LEAVE SIMULATOR ----------
st.divider()
st.subheader("5️⃣ Class leave → attendance")

leave_count = st.number_input(
    "How many upcoming classes will you miss?",
    min_value=0,
    max_value=10000,
    value=0,
    step=1,
    key="leave_count"
)

leave_total = aggregate_total + leave_count
leave_pct = percentage(aggregate_present, leave_total)

a, b, c = st.columns(3)
a.metric(
    "Attendance after leaving",
    f"{leave_pct:.2f}%",
    delta=f"{leave_pct - current_pct:+.2f}%"
)
b.metric("Attended hours", aggregate_present)
c.metric("Total hours", leave_total)

if leave_pct >= target:
    st.success(f"You remain at or above {target}% after this leave.")
else:
    st.error(f"You will fall below your {target}% target.")


# ---------- CLASS TAKE SIMULATOR ----------
st.divider()
st.subheader("6️⃣ Class take → attendance")

take_count = st.number_input(
    "How many upcoming classes will you attend?",
    min_value=0,
    max_value=10000,
    value=20,
    step=1,
    key="take_count"
)

take_present = aggregate_present + take_count
take_total = aggregate_total + take_count
take_pct = percentage(take_present, take_total)

a, b, c = st.columns(3)
a.metric(
    "Attendance after attending",
    f"{take_pct:.2f}%",
    delta=f"{take_pct - current_pct:+.2f}%"
)
b.metric("Attended hours", take_present)
c.metric("Total hours", take_total)

if take_pct >= target:
    st.success(f"You meet your {target}% target after attending these classes.")
else:
    needed = classes_needed(take_present, take_total, target)
    st.warning(f"Attend {needed} more consecutive classes to reach {target}%.")


# ---------- SAFE LEAVE CALCULATOR ----------
st.divider()
st.subheader("7️⃣ How many classes can I leave?")

planned_take = st.number_input(
    "Classes you plan to attend before taking leave",
    min_value=0,
    max_value=10000,
    value=20,
    step=1,
    key="planned_take"
)

planned_present = aggregate_present + planned_take
planned_total = aggregate_total + planned_take
planned_pct = percentage(planned_present, planned_total)

safe_leave = classes_can_leave(
    planned_present, planned_total, target
)

a, b = st.columns(2)
a.metric("Attendance after planned classes", f"{planned_pct:.2f}%")

if math.isinf(safe_leave):
    b.metric("Maximum classes you can leave", "Unlimited")
else:
    b.metric("Maximum classes you can leave", safe_leave)

if planned_pct < target:
    needed = classes_needed(planned_present, planned_total, target)
    st.warning(
        f"You are below target. Attend {needed} more classes "
        "without absence before considering leave."
    )
elif safe_leave == 0:
    st.warning("You cannot miss any more classes without falling below target.")
else:
    st.success(
        f"After attending {planned_take} classes, you can miss up to "
        f"{safe_leave} additional classes and stay at or above {target}%."
    )
    
