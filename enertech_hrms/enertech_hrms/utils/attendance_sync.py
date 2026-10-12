import frappe
from frappe.utils import getdate, get_datetime
from datetime import datetime, timedelta


def get_employee_shift(employee):
	"""Fetch employee's default shift with in_time and out_time."""
	emp = frappe.get_doc("Employee", employee)

	if not emp.default_shift:
		return None

	shift = frappe.get_doc("Shift Type", emp.default_shift)
	return {
		"shift_name": shift.name,
		"in_time": shift.start_time,
		"out_time": shift.end_time,
	}


def calculate_expected_working_hours(shift_data):
	"""Calculate expected working hours from shift duration."""
	if not shift_data:
		return None

	shift_in = datetime.strptime(str(shift_data["in_time"]), "%H:%M:%S")
	shift_out = datetime.strptime(str(shift_data["out_time"]), "%H:%M:%S")

	# Handle night shifts that cross midnight
	if shift_out <= shift_in:
		shift_out += timedelta(days=1)

	return (shift_out - shift_in).total_seconds() / 3600


def sync_attendance(employee, attendance_date, force_status=None, out_time_override=None):
	attendance_date = getdate(attendance_date)

	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]],
		},
		fields=["name", "time", "log_type"],
		order_by="time asc",
	)

	if not checkins:
		return

	first_checkin = checkins[0]
	last_checkin = checkins[-1]

	in_time = get_datetime(first_checkin.time)

	# Use the requested OUT time when provided (missed punch out approval),
	# otherwise use the last check-in of the day
	out_time = get_datetime(out_time_override) if out_time_override else get_datetime(last_checkin.time)

	total_seconds = (out_time - in_time).total_seconds()
	actual_hours = total_seconds / 3600 if total_seconds > 0 else 0

	# If force_status is given (e.g. missed punch out approved), use it as is
	if force_status:
		final_status = force_status
	else:
		shift_data = get_employee_shift(employee)
		expected_hours = calculate_expected_working_hours(shift_data)

		if expected_hours and actual_hours < expected_hours:
			final_status = "Half Day"
		else:
			final_status = "Present"

	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": attendance_date, "docstatus": ["!=", 2]},
		["name", "status", "docstatus"],
		as_dict=True,
	)

	if existing:
		if existing.status == final_status and not force_status:
			return

		doc = frappe.get_doc("Attendance", existing.name)
		doc.flags.ignore_permissions = True

		if doc.docstatus == 1:
			# Submitted: cancel it (keeps audit trail)
			doc.cancel()
		elif doc.docstatus == 0:
			# Draft: remove it so we don't create a duplicate
			frappe.delete_doc("Attendance", doc.name, force=1, ignore_permissions=True)

	att = frappe.new_doc("Attendance")
	att.flags.ignore_permissions = True
	att.employee = employee
	att.attendance_date = attendance_date
	att.status = final_status
	att.in_time = in_time
	att.out_time = out_time
	att.working_hours = actual_hours

	# HR-approved status must not be overridden by any working hours hook
	if force_status:
		att.flags.skip_working_hours_validation = True

	if final_status == "Half Day":
		att.half_day_status = "First Half"

	att.insert(ignore_permissions=True)
	att.submit()