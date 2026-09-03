import frappe
from frappe.model.document import Document
from frappe import _
from enertech_hrms.enertech_hrms.utils.attendance_sync import sync_attendance


class MissedPunchOutRequest(Document):
	def validate(self):
		self.set_employee_from_user()
		self.validate_times()

	def set_employee_from_user(self):
		if not self.employee:
			employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
			if employee:
				self.employee = employee

	def validate_times(self):
		if self.checkin_time and self.requested_time:
			requested_datetime = f"{self.date} {self.requested_time}"
			if requested_datetime <= str(self.checkin_time):
				frappe.throw(_("Requested Time must be after the Last Log Time."))

	def on_update(self):
		if self.workflow_state == "Approved" and not self.synced:
			self.approve_and_sync()

	def approve_and_sync(self):
		requested_datetime = f"{self.date} {self.requested_time}"

		if not frappe.db.exists(
			"Employee Checkin",
			{"employee": self.employee, "time": requested_datetime}
		):
			frappe.get_doc({
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": requested_datetime,
				"log_type": "OUT"
			}).insert(ignore_permissions=True)

		sync_attendance(self.employee, self.date)

		self.db_set("synced", 1)