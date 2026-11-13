import frappe
from frappe import _
from frappe.model.document import Document


class WorkFromHomeCheckINOUT(Document):

    def validate(self):
        self.validate_wfh_eligibility()

    def validate_wfh_eligibility(self):
        work_mode = frappe.db.get_value("Employee", self.employee, "custom_work_mode")

        if work_mode != "Work From Home":
            frappe.throw(
                _("Work From Home Check-in is only available for employees whose Work Mode is set to Work From Home."),
                title=_("Not Allowed"),
            )

    def on_submit(self):
        # Only create Employee Checkin. HRMS auto attendance creates Attendance later.
        frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": self.employee,
            "time": self.time,
            "log_type": self.log_type,
            "skip_auto_attendance": 0,
        }).insert(ignore_permissions=True)

    def on_cancel(self):
        name = frappe.db.get_value("Employee Checkin", {
            "employee": self.employee,
            "time": self.time,
            "log_type": self.log_type,
            "attendance": ["is", "not set"],
        })
        if name:
            frappe.delete_doc("Employee Checkin", name, ignore_permissions=True)


@frappe.whitelist()
def check_wfh_eligibility(employee, date=None):
    if not employee:
        return {"eligible": False}

    work_mode = frappe.db.get_value("Employee", employee, "custom_work_mode")
    return {"eligible": work_mode == "Work From Home"}