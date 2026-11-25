import frappe
from datetime import datetime, time
from frappe.utils import add_days, cint, get_datetime, get_first_day, getdate

# Email templates live in: custom_brainmine_erp_hrms/templates/emails/
WARNING_TEMPLATE = "late_checkin"
HALF_DAY_TEMPLATE = "late_checkin_halfday"


# ---------------------------------------------------------------------------
# Doc event hooks
# ---------------------------------------------------------------------------

def mark_late(doc, method=None):
    """before_save / before_submit: detect late entry, set late count and mark half day."""
    settings = _get_settings()
    if not settings:
        return

    # Reset first so that edits to the attendance are always re-evaluated
    doc.late_entry = doc.custom_late_count = doc.custom_late_half_day = 0

    if _minutes_late(doc) <= _threshold(doc, settings):
        return

    doc.late_entry = 1
    doc.custom_late_count = _next_late_count(doc)

    # Limit reached: convert this attendance to a half day
    if doc.custom_late_count >= settings.limit:
        doc.custom_late_half_day = 1
        doc.status = "Half Day"
        if doc.meta.has_field("half_day_status"):
            doc.half_day_status = "Present"


def send_late_mail(doc, method=None):
    """on_submit: send a warning mail, or a half day mail when the limit is reached."""
    settings = _get_settings()
    if not (settings and doc.late_entry and doc.custom_late_count):
        return

    emp = frappe.db.get_value(
        "Employee", doc.employee, ["employee_name", "company_email"], as_dict=True
    )
    shift_start = _shift_start(doc)
    check_in = _check_in_time(doc)
    if not (emp and emp.company_email and shift_start and check_in):
        return

    is_half_day = doc.custom_late_half_day
    try:
        frappe.sendmail(
            recipients=[emp.company_email],
            subject=(
                "Half Day Marked - Repeated Late Check-Ins"
                if is_half_day
                else f"Late Check-In Reminder ({doc.custom_late_count} of {settings.limit - 1})"
            ),
            template=HALF_DAY_TEMPLATE if is_half_day else WARNING_TEMPLATE,
            args={
                "employee_name": emp.employee_name,
                "checkin_time": check_in.strftime("%I:%M %p"),
                "expected_checkin": shift_start.strftime("%I:%M %p"),
                "late_count": doc.custom_late_count,
                "late_limit": settings.limit,
            },
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
    except Exception:
        # A mail failure must never block the attendance submission
        frappe.log_error(title="Late mail failed", message=frappe.get_traceback())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_settings():
    """Return settings only if marking is enabled and a limit is configured, else None."""
    doc = frappe.get_cached_doc("Late Settings")
    limit = cint(doc.late_limit_for_half_day)
    if not (doc.enable_late_entry_marking and limit):
        return None
    return frappe._dict(threshold=cint(doc.late_threshold_minutes), limit=limit)


def _threshold(doc, settings):
    """Per-employee grace override if set, else the global threshold from Late Settings."""
    override = cint(
        frappe.get_cached_value("Employee", doc.employee, "custom_late_grace_override_minutes")
    )
    return override or settings.threshold


def _shift_name(doc):
    """Shift on the attendance, else the employee's default shift."""
    return doc.shift or frappe.get_cached_value("Employee", doc.employee, "default_shift")


def _shift_start(doc):
    """Return attendance date combined with the shift start time, or None if unavailable."""
    shift = _shift_name(doc)
    if not shift:
        return None
    start_time = frappe.get_cached_value("Shift Type", shift, "start_time")
    if not start_time:
        return None
    return datetime.combine(getdate(doc.attendance_date), time.min) + start_time


def _check_in_time(doc):
    """Return the attendance in_time, else the first IN checkin of that day."""
    if doc.in_time:
        return get_datetime(doc.in_time)

    att_date = getdate(doc.attendance_date)
    first_in = frappe.db.get_value(
        "Employee Checkin",
        {
            "employee": doc.employee,
            "log_type": "IN",
            "time": ["between", [f"{att_date} 00:00:00", f"{att_date} 23:59:59"]],
        },
        "time",
        order_by="time asc",
    )
    return get_datetime(first_in) if first_in else None


def _minutes_late(doc):
    """Return minutes elapsed since shift start at check-in (0 if not applicable)."""
    if doc.status not in ("Present", "Half Day"):
        return 0
    check_in = _check_in_time(doc)
    shift_start = _shift_start(doc)
    if not (check_in and shift_start):
        return 0
    return (check_in - shift_start).total_seconds() / 60


def _next_late_count(doc):
    """Return the late count for this attendance.

    Only lates from the current month and before the current date are considered.
    The count restarts at 1 on a new month, or right after a half day was marked.
    """
    att_date = getdate(doc.attendance_date)
    month_start = get_first_day(att_date)

    # First day of the month: nothing earlier to count
    if att_date == month_start:
        return 1

    prev = frappe.db.get_value(
        "Attendance",
        {
            "employee": doc.employee,
            "docstatus": ["!=", 2],
            "late_entry": 1,
            "name": ["!=", doc.name or ""],
            "attendance_date": ["between", [month_start, add_days(att_date, -1)]],
        },
        ["custom_late_count", "custom_late_half_day"],
        order_by="attendance_date desc, creation desc",
        as_dict=True,
    )

    if not prev or prev.custom_late_half_day:
        return 1
    return (prev.custom_late_count or 0) + 1