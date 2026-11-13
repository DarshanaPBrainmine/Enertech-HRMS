frappe.ui.form.on("Work From Home Check IN - OUT", {
    employee(frm) {
        check_eligibility(frm);
    },
});

function check_eligibility(frm) {
    frm.dashboard.clear_headline();

    if (!frm.doc.employee) {
        frm.enable_save();
        return;
    }

    frappe.call({
        method: "enertech_hrms.enertech_hrms.doctype.work_from_home_check_in___out.work_from_home_check_in___out.check_wfh_eligibility",
        args: { employee: frm.doc.employee },
        callback(r) {
            if (r.message && r.message.eligible) {
                frm.dashboard.set_headline_alert(__("Eligible for Work From Home Check-in"), "green");
                frm.enable_save();
            } else {
                frm.dashboard.set_headline_alert(__("Work From Home Check-in is only available for Work From Home employees."), "red");
                frm.disable_save();
            }
        },
    });
}