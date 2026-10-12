import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_datetime
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
		# checkin_time holds the FIRST check-in of the day
		if self.checkin_time and self.requested_time:
			requested_datetime = get_datetime(f"{self.date} {self.requested_time}")
			if requested_datetime <= get_datetime(self.checkin_time):
				frappe.throw(_("Requested Time must be after the First Check-in Time."))

	def on_change(self):
		# on_change fires on save, submit and update-after-submit,
		# so it works regardless of how the workflow changes the state
		if self.workflow_state == "Approved" and not self.synced:
			self.approve_and_sync()

	def approve_and_sync(self):
		requested_datetime = get_datetime(f"{self.date} {self.requested_time}")

		# 1. Create the OUT checkin if it doesn't already exist
		if not frappe.db.exists(
			"Employee Checkin",
			{"employee": self.employee, "time": requested_datetime},
		):
			frappe.get_doc({
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": requested_datetime,
				"log_type": "OUT",
			}).insert(ignore_permissions=True)

		# 2. Request is approved, so force attendance to Present
		#    using the requested time as the OUT time
		sync_attendance(
			self.employee,
			self.date,
			force_status="Present",
			out_time_override=requested_datetime,
		)

		# 3. Mark the request as synced
		self.db_set("synced", 1)