import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate
from enertech_hrms.enertech_hrms.utils.attendance_sync import sync_attendance


class ServiceEngineerAttendence(Document):
	def validate(self):
		self.validate_gps()
		self.validate_accuracy()

	def validate_gps(self):
		if not self.latitude or not self.longitude:
			frappe.throw(_("Location not captured. Please allow GPS access and try again."))

	def validate_accuracy(self):
		if self.gps_accuracy and self.gps_accuracy > 100:
			frappe.msgprint(
				_("GPS accuracy is low ({0}m). Location may not be precise.").format(self.gps_accuracy),
				alert=True,
				indicator="orange"
			)

	def on_submit(self):
		self.push_to_employee_checkin()
		sync_attendance(self.employee, getdate(self.timestamp))

	def push_to_employee_checkin(self):
		log_type = "IN" if self.checkin_type == "Check In" else "OUT"

		checkin = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": self.employee,
			"log_type": log_type,
			"time": self.timestamp,
			"latitude": self.latitude,
			"longitude": self.longitude,
		})
		checkin.insert(ignore_permissions=True)

		self.db_set("sync_status", "Synced")