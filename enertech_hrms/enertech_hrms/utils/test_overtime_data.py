# Run in: bench --site <site-name> console     (STAGING ONLY)
#
# Creates fake submitted Attendance for ONE test employee in ONE past month, so overtime can be tested
# without real check-ins. Pick an employee with no attendance in that month and joined before it.
#
#   exec(open("/home/frappe/staging-bench/apps/enertech_hrms/test_overtime_data.py").read())
#   create_test_attendance("EUPLC211", "2026-06-01")
#   # then call the API for that employee (see steps), then:
#   delete_test_attendance("EUPLC211", "2026-06-01")
#
# Expected result for the data below (standard hours 8.5):
#   12 weekdays x 9.5 hrs  -> 12.0 extra hrs -> 1 comp off + 1 extra half day (12 = 8 + 4)
#   1st Sunday 6.0 hrs     -> counts (sunday_days = 1)
#   2nd Sunday 5.9 hrs     -> does not count
#   2 weekdays x 8.0 hrs   -> no extra

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, getdate


def create_test_attendance(employee, month):
	start, end = get_first_day(month), get_last_day(month)
	company = frappe.db.get_value("Employee", employee, "company")

	if frappe.db.exists("Attendance", {"employee": employee, "attendance_date": ["between", [start, end]], "docstatus": ["<", 2]}):
		print("Employee already has attendance in this month, pick another employee/month")
		return

	weekday_extra_left = 12
	normal_weekdays_left = 2
	sundays_seen = 0
	day = getdate(start)

	while day <= getdate(end):
		hours = None
		if day.weekday() == 6:
			sundays_seen += 1
			if sundays_seen == 1:
				hours = 6.0
			elif sundays_seen == 2:
				hours = 5.9
		elif day.weekday() < 5:
			if weekday_extra_left > 0:
				hours = 9.5
				weekday_extra_left -= 1
			elif normal_weekdays_left > 0:
				hours = 8.0
				normal_weekdays_left -= 1

		if hours is not None:
			att = frappe.get_doc({
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": day,
				"status": "Present",
				"working_hours": hours,
				"company": company,
			})
			att.insert(ignore_permissions=True)
			att.submit()
		day = add_days(day, 1)

	frappe.db.commit()
	print("Test attendance created")


def delete_test_attendance(employee, month):
	start, end = get_first_day(month), get_last_day(month)
	names = frappe.get_all("Attendance", filters={"employee": employee, "attendance_date": ["between", [start, end]]}, pluck="name")
	for name in names:
		doc = frappe.get_doc("Attendance", name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Attendance", name, force=True)
	frappe.db.delete("Monthly Overtime Summary", {"employee": employee, "month_start": start})
	frappe.db.commit()
	print(f"Deleted {len(names)} attendance records and the summary. Cancel/delete the test Leave Allocation manually.")