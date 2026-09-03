import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, nowdate
from enertech_hrms.enertech_hrms.utils.attendance_sync import sync_attendance


class ClientSideAttendance(Document):
	def validate(self):
		self.validate_visits()

	def validate_visits(self):
		if not self.visits:
			frappe.throw(_("Please add at least one client visit."))

		seen_clients = set()

		for row in self.visits:
			if not row.check_in_time:
				frappe.throw(_("Row #{0}: Check In Time is required.").format(row.idx))

			if row.check_out_time and row.check_out_time <= row.check_in_time:
				frappe.throw(
					_("Row #{0}: Check Out Time must be after Check In Time.").format(row.idx)
				)

			if row.client in seen_clients:
				frappe.throw(
					_("Row #{0}: Duplicate visit entry for client {1}.").format(row.idx, row.client)
				)
			seen_clients.add(row.client)

	def on_submit(self):
		self.push_visits_to_employee_checkin()

		if getdate(self.date) < getdate(nowdate()):
			sync_attendance(self.employee, self.date)

	def push_visits_to_employee_checkin(self):
		for row in self.visits:
			checkin_time = f"{self.date} {row.check_in_time}"

			if not frappe.db.exists(
				"Employee Checkin",
				{"employee": self.employee, "time": checkin_time}
			):
				frappe.get_doc({
					"doctype": "Employee Checkin",
					"employee": self.employee,
					"time": checkin_time,
					"log_type": "IN"
				}).insert(ignore_permissions=True)

			if row.check_out_time:
				checkout_time = f"{self.date} {row.check_out_time}"

				if not frappe.db.exists(
					"Employee Checkin",
					{"employee": self.employee, "time": checkout_time}
				):
					frappe.get_doc({
						"doctype": "Employee Checkin",
						"employee": self.employee,
						"time": checkout_time,
						"log_type": "OUT"
					}).insert(ignore_permissions=True)