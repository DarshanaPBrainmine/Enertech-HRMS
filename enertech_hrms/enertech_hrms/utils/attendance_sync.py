import frappe
from frappe.utils import getdate, get_datetime
from datetime import datetime


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

	shift_in = datetime.strptime(str(shift_data["in_time"]), "%H:%M:%S").time()
	shift_out = datetime.strptime(str(shift_data["out_time"]), "%H:%M:%S").time()

	shift_start = datetime.combine(datetime.today().date(), shift_in)
	shift_end = datetime.combine(datetime.today().date(), shift_out)

	total_seconds = (shift_end - shift_start).total_seconds()
	return total_seconds / 3600


def sync_attendance(employee, attendance_date):
	attendance_date = getdate(attendance_date)

	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]]
		},
		fields=["name", "time", "log_type"],
		order_by="time asc"
	)

	if not checkins:
		return

	first_checkin = checkins[0]
	last_checkin = checkins[-1]

	in_time = get_datetime(first_checkin.time)
	out_time = get_datetime(last_checkin.time)
	total_seconds = (out_time - in_time).total_seconds()
	actual_hours = total_seconds / 3600 if total_seconds > 0 else 0

	shift_data = get_employee_shift(employee)
	expected_hours = calculate_expected_working_hours(shift_data)

	if expected_hours and actual_hours < expected_hours:
		final_status = "Half Day"
	else:
		final_status = "Present"

	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": attendance_date},
		["name", "status"],
		as_dict=True
	)

	if existing:
		if existing.status == final_status:
			return

		frappe.db.set_value("Attendance", existing.name, "docstatus", 2, update_modified=False)
		frappe.db.delete("Attendance", {"name": existing.name})
		frappe.db.commit()

	att = frappe.new_doc("Attendance")
	att.flags.ignore_permissions = True
	att.employee = employee
	att.attendance_date = attendance_date
	att.status = final_status
	att.in_time = first_checkin.time
	att.out_time = last_checkin.time

	if final_status == "Half Day":
		att.half_day_status = "First Half"

	att.insert(ignore_permissions=True)
	att.submit()