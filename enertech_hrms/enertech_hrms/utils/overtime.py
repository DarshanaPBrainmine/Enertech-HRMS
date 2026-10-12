# enertech_hrms/enertech_hrms/utils/overtime.py
#
# Calculates monthly overtime from Attendance and stores it in "Monthly Overtime Summary".
# Comp offs earned are added automatically to the employee's "Compensatory Off" leave balance.
# No salary / payment is created. HR handles payment manually.
#
# Rules (per employee, per month):
#   - Weekday extra hours = working_hours - STANDARD_HOURS (positive only), summed for the month
#   - Every full 8 extra hours      -> 1 Compensatory Off (added to leave balance)
#   - Remaining 4+ extra hours      -> 1 extra half day (for manual payment)
#   - Sunday with >= 6 working hrs  -> full day worked (for manual payment)
#     (Sunday hours are not added to the extra-hours pool)

import frappe
from frappe.utils import add_days, cint, flt, get_first_day, get_last_day, getdate, nowdate

# ---------------- Settings ----------------
STANDARD_HOURS = 8.5  # shift 9:30 to 18:00 for all employees
SUNDAY_MIN_HOURS = 6
HOURS_PER_COMP_OFF = 8
HOURS_PER_HALF_DAY = 4
SUMMARY_DOCTYPE = "Monthly Overtime Summary"

AUTO_ALLOCATE_COMP_OFF = True
COMP_OFF_LEAVE_TYPE = "Compensatory Off"
COMP_OFF_VALID_DAYS = 90  # used only when a new Leave Allocation has to be created
# ------------------------------------------


@frappe.whitelist()
def calculate_monthly_overtime(month, employee=None, recalculate=0):
	"""month: any date inside the month to calculate (YYYY-MM-DD)."""
	frappe.only_for("HR Manager")

	month_start = get_first_day(month)
	month_end = get_last_day(month)
	recalculate = cint(recalculate)

	emp_filters = {"status": "Active"}
	if employee:
		emp_filters["name"] = employee

	employees = frappe.get_all("Employee", filters=emp_filters, pluck="name")
	results = []

	for emp in employees:
		existing = frappe.db.get_value(
			SUMMARY_DOCTYPE,
			{"employee": emp, "month_start": month_start},
			["name", "comp_off_added_to_balance"],
			as_dict=True,
		)
		if existing and not recalculate:
			results.append({"employee": emp, "status": "already calculated"})
			continue

		already_allocated = flt(existing.comp_off_added_to_balance) if existing else 0
		values = get_overtime_values(emp, month_start, month_end)
		has_overtime = values["comp_off_days"] or values["extra_half_day"] or values["sunday_days"]

		# No overtime: no record needed (unless comp off was already given earlier, keep the trail)
		if not has_overtime and not already_allocated:
			if existing:  # stale record from an earlier run, attendance has changed since
				frappe.delete_doc(SUMMARY_DOCTYPE, existing.name, ignore_permissions=True)
			continue

		savepoint = "overtime_" + emp.replace("-", "_")
		frappe.db.savepoint(savepoint)
		try:
			values["comp_off_added_to_balance"] = already_allocated
			comp_off_to_add = values["comp_off_days"] - already_allocated

			if AUTO_ALLOCATE_COMP_OFF and comp_off_to_add > 0:
				values["leave_allocation"] = add_comp_off_balance(emp, comp_off_to_add)
				values["comp_off_added_to_balance"] = already_allocated + comp_off_to_add

			if existing:
				frappe.db.set_value(SUMMARY_DOCTYPE, existing.name, values)
			else:
				frappe.get_doc(
					{"doctype": SUMMARY_DOCTYPE, "employee": emp, "month_start": month_start, **values}
				).insert()

			result = {"employee": emp, **values}
			if comp_off_to_add < 0:
				result["warning"] = (
					"Comp off is now lower than already added to balance; "
					"reduce the Leave Allocation manually if needed"
				)
			results.append(result)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			frappe.log_error(title=f"Overtime calculation failed for {emp}")
			results.append({"employee": emp, "status": "error, see Error Log"})

	return results


def get_overtime_values(employee, month_start, month_end):
	attendance = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": ["in", ["Present", "Work From Home"]],
			"attendance_date": ["between", [month_start, month_end]],
		},
		fields=["attendance_date", "working_hours"],
	)

	total_extra = 0.0
	sunday_dates = []

	for a in attendance:
		hours = flt(a.working_hours)
		if getdate(a.attendance_date).weekday() == 6:  # Sunday
			if hours >= SUNDAY_MIN_HOURS:
				sunday_dates.append(str(a.attendance_date))
		elif hours > STANDARD_HOURS:
			total_extra += hours - STANDARD_HOURS

	comp_off = int(total_extra // HOURS_PER_COMP_OFF)
	remainder = total_extra - comp_off * HOURS_PER_COMP_OFF
	half_day = 1 if remainder >= HOURS_PER_HALF_DAY else 0

	return {
		"total_extra_hours": round(total_extra, 2),
		"comp_off_days": comp_off,
		"extra_half_day": half_day,
		"sunday_days": len(sunday_dates),
		"sunday_dates": ", ".join(sunday_dates),
	}


def add_comp_off_balance(employee, days):
	"""Add `days` to the employee's Compensatory Off leave balance. Returns the Leave Allocation name.

	Leave balance = sum of submitted Leave Ledger Entries. A submitted Leave Allocation creates a
	+N ledger entry. If an active allocation already exists we top it up (same approach HRMS uses
	for Compensatory Leave Request), otherwise we create and submit a new one.
	"""
	today = getdate(nowdate())

	active = frappe.get_all(
		"Leave Allocation",
		filters={
			"employee": employee,
			"leave_type": COMP_OFF_LEAVE_TYPE,
			"docstatus": 1,
			"from_date": ["<=", today],
			"to_date": [">=", today],
		},
		pluck="name",
		limit=1,
	)

	if active:
		allocation = frappe.get_doc("Leave Allocation", active[0])
		allocation.db_set("new_leaves_allocated", flt(allocation.new_leaves_allocated) + days)
		allocation.db_set("total_leaves_allocated", flt(allocation.total_leaves_allocated) + days)

		ledger = frappe.get_doc(
			{
				"doctype": "Leave Ledger Entry",
				"employee": employee,
				"employee_name": allocation.employee_name,
				"leave_type": COMP_OFF_LEAVE_TYPE,
				"transaction_type": "Leave Allocation",
				"transaction_name": allocation.name,
				"leaves": days,
				"from_date": today,
				"to_date": allocation.to_date,
				"is_carry_forward": 0,
				"is_expired": 0,
				"is_lwp": 0,
				"company": allocation.company,
			}
		)
		ledger.insert(ignore_permissions=True)
		ledger.submit()
		return allocation.name

	allocation = frappe.get_doc(
		{
			"doctype": "Leave Allocation",
			"employee": employee,
			"leave_type": COMP_OFF_LEAVE_TYPE,
			"from_date": today,
			"to_date": add_days(today, COMP_OFF_VALID_DAYS),
			"new_leaves_allocated": days,
		}
	)
	allocation.insert(ignore_permissions=True)
	allocation.submit()  # submitting creates the +N Leave Ledger Entry
	return allocation.name