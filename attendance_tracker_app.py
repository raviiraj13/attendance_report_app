
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
    return max(0, math.ceil(
        (target * total - 100 * present) / (100 - target) - 1e-10
    ))


def classes_can_leave(present, total, target):
    if target <= 0:
        return math.inf
    if percentage(present, total) < target:
        return 0
    return max(0, math.floor(
        (100 * present / target) - total + 1e-10
    ))


def parse_attendance(text):
    rows = []
    for line in text.splitlines():
        parts = re.split(r"\t+", line.strip())
        if len(parts) < 9 or not parts[0].isdigit():
            continue
        try:
            rows.append([
                parts[2].strip(),
                int(parts[4]),
                int(parts[5]),
                int(parts[6]),
                int(parts[7])
            ])
        except (ValueError, IndexError):
            continue

    df = pd.DataFrame(
        rows,
        columns=["Subject", "Present", "OD", "Makeup", "Absent"]
    )

    if not df.empty:
        df["Effective Present"] = df["Present"] + df["OD"] + df["Makeup"]
        df["Total Classes"] = df["Present"] + df["Absent"]
        df["Attendance %"] = (
            df["Effective Present"]
            / df["Total Classes"].replace(0, float("nan")) * 100
        ).round(2)

    return df


# ---------- CURRENT ATTENDANCE INPUT ----------
st.subheader("1️⃣ Set your current attendance")

input_mode = st.radio(
    "How do you want to enter your attendance?",
    ["Enter totals manually", "Paste ERP report"],
    horizontal=True
)

if input_mode == "Enter totals manually":
    col1, col2 = st.columns(2)
    with col1:
        current_present = st.number_input(
            "Current attended classes/hours",
            min_value=0, value=292, step=1
        )
    with col2:
        current_absent = st.number_input(
            "Current missed classes/hours",
            min_value=0, value=104, step=1
        )

    event_present = 0
    event_absent = 0
    df = pd.DataFrame()

else:
    erp_text = st.text_area(
        "Paste complete ERP attendance report",
        height=220
    )

    event_col1, event_col2 = st.columns(2)
    with event_col1:
        event_present = st.number_input(
            "Additional event hours attended",
            min_value=0, value=12, step=1
        )
    with event_col2:
        event_absent = st.number_input(
            "Additional event hours missed",
            min_value=0, value=12, step=1
        )

    df = parse_attendance(erp_text)

    if df.empty:
        st.info("Paste the ERP table to calculate your current attendance.")
        st.stop()

    current_present = int(df["Effective Present"].sum()) + event_present
    current_absent = int(df["Absent"].sum()) + event_absent

current_total = current_present + current_absent
current_pct = percentage(current_present, current_total)

# ---------- TARGET ----------
st.subheader("2️⃣ Set your attendance target")

target = st.slider(
    "Target attendance (%)",
    min_value=1,
    max_value=100,
    value=75,
    step=1
)

c1, c2, c3 = st.columns(3)
c1.metric("Current attendance", f"{current_pct:.2f}%")
c2.metric("Attended", current_present)
c3.metric("Total classes", current_total)

if current_pct >= target:
    st.success(f"You currently meet your {target}% target.")
else:
    needed = classes_needed(current_present, current_total, target)
    st.warning(
        f"You need to attend {needed} consecutive classes without absence "
        f"to reach {target}%."
    )

# ---------- INTERACTIVE CLASS LEAVE ----------
st.divider()
st.subheader("3️⃣ Class leave → Present attendance")

leave_count = st.number_input(
    "How many upcoming classes will you miss?",
    min_value=0,
    max_value=10000,
    value=0,
    step=1,
    key="leave_count"
)

leave_total = current_total + leave_count
leave_pct = percentage(current_present, leave_total)

a, b, c = st.columns(3)
a.metric(
    "Attendance after leaving",
    f"{leave_pct:.2f}%",
    delta=f"{leave_pct - current_pct:+.2f}%"
)
b.metric("Attended classes", current_present)
c.metric("Total classes", leave_total)

if leave_pct >= target:
    st.success(f"You remain at or above {target}% after missing {leave_count} classes.")
else:
    st.error(f"You fall below {target}% after missing {leave_count} classes.")

# ---------- INTERACTIVE CLASS TAKE ----------
st.divider()
st.subheader("4️⃣ Class take → Present attendance")

take_count = st.number_input(
    "How many upcoming classes will you attend?",
    min_value=0,
    max_value=10000,
    value=20,
    step=1,
    key="take_count"
)

take_present = current_present + take_count
take_total = current_total + take_count
take_pct = percentage(take_present, take_total)

a, b, c = st.columns(3)
a.metric(
    "Attendance after attending",
    f"{take_pct:.2f}%",
    delta=f"{take_pct - current_pct:+.2f}%"
)
b.metric("Attended classes", take_present)
c.metric("Total classes", take_total)

if take_pct >= target:
    st.success(f"You meet your {target}% target after attending {take_count} classes.")
else:
    need = classes_needed(take_present, take_total, target)
    st.warning(f"You need {need} more consecutive attended classes to reach {target}%.")

# ---------- HOW MANY CLASSES CAN I LEAVE ----------
st.divider()
st.subheader("5️⃣ How many classes can I leave?")

st.caption(
    "This calculator assumes you attend the planned classes first, "
    "then considers how many more classes you could miss."
)

planned_take = st.number_input(
    "Classes you will attend before taking leave",
    min_value=0,
    max_value=10000,
    value=20,
    step=1,
    key="planned_take"
)

planned_present = current_present + planned_take
planned_total = current_total + planned_take
planned_pct = percentage(planned_present, planned_total)

safe_leave = classes_can_leave(planned_present, planned_total, target)

a, b = st.columns(2)
a.metric("Attendance after planned classes", f"{planned_pct:.2f}%")

if math.isinf(safe_leave):
    b.metric("Maximum classes you can leave", "Unlimited")
else:
    b.metric("Maximum classes you can leave", safe_leave)

if planned_pct < target:
    needed = classes_needed(planned_present, planned_total, target)
    st.warning(
        f"You are below target. Attend {needed} more classes without "
        "absence before considering additional leave."
    )
elif safe_leave == 0:
    st.warning("You cannot miss any more classes without falling below target.")
else:
    st.success(
        f"After attending {planned_take} classes, you can miss up to "
        f"{safe_leave} additional classes and remain at or above {target}%."
    )

# ---------- SUBJECT-WISE ERP DATA ----------
if not df.empty:
    st.divider()
    st.subheader("📚 Subject-wise attendance")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
