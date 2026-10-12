import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import time_diff_in_seconds

PERSONAL_LIMIT_MINS = 120

class GatePass(Document):
    def validate(self):
        if self.gate_pass_type == "Personal":
            self.official_type = None
        self.calculate_duration()
        self.validate_personal_limit()

    def calculate_duration(self):
        secs = time_diff_in_seconds(self.to_time, self.from_time)
        if secs <= 0:
            frappe.throw(_("To Time must be after From Time"))
        self.duration_mins = int(secs / 60)

    def validate_personal_limit(self):
        if self.gate_pass_type == "Personal" and self.duration_mins > PERSONAL_LIMIT_MINS:
            frappe.throw(
                _("Personal Gate Pass allowed only for {0} minutes ").format(PERSONAL_LIMIT_MINS)
            )