import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate


class ServiceEngineerAttendence(Document):
	def validate(self):
		self.validate_gps()
		self.validate_accuracy()
		self.validate_duplicate_checkin()

	def validate_gps(self):
		if not self.latitude or not self.longitude:
			frappe.throw(_("Location not captured. Please allow GPS access and try again."))

	def validate_accuracy(self):
		if self.gps_accuracy and self.gps_accuracy > 100:
			frappe.msgprint(
				_("GPS accuracy is low ({0}m). Location may not be precise.").format(self.gps_accuracy),
				alert=True,
				indicator="orange",
			)

	def validate_duplicate_checkin(self):
		# Do not allow more than one Check In per day
		if self.checkin_type != "Check In":
			return

		day = getdate(self.timestamp)
		exists = frappe.db.exists(
			"Service Engineer Attendence",
			{
				"employee": self.employee,
				"checkin_type": "Check In",
				"docstatus": 1,
				"timestamp": ["between", [f"{day} 00:00:00", f"{day} 23:59:59"]],
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(_("Check In is already done for {0}.").format(day))

	def on_submit(self):
		self.push_to_employee_checkin()

		# Mark Present as soon as the engineer checks in; a missing Check Out is fine
		if self.checkin_type == "Check In":
			self.mark_present()

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

	def mark_present(self):
		att_date = getdate(self.timestamp)

		existing = frappe.db.get_value(
			"Attendance",
			{
				"employee": self.employee,
				"attendance_date": att_date,
				"docstatus": ["!=", 2],
			},
			["name", "status", "docstatus"],
			as_dict=True,
		)

		if existing:
			if existing.status == "Present":
				return

			# Do not touch the record if the employee is on leave
			if existing.status == "On Leave":
				return

			att = frappe.get_doc("Attendance", existing.name)
			if existing.docstatus == 0:
				att.status = "Present"
				att.save(ignore_permissions=True)
				att.submit()
				return

			# A submitted Absent / Half Day exists: cancel it and create a new Present record
			att.cancel()

		employee = frappe.db.get_value(
			"Employee", self.employee, ["employee_name", "company"], as_dict=True
		)

		attendance = frappe.get_doc({
			"doctype": "Attendance",
			"employee": self.employee,
			"employee_name": employee.employee_name,
			"company": employee.company,
			"attendance_date": att_date,
			"status": "Present",
		})
		attendance.insert(ignore_permissions=True)
		attendance.submit()