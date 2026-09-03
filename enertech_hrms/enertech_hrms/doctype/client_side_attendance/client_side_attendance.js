frappe.ui.form.on("Client Side Attendance", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.date) {
			frm.set_value('date', frappe.datetime.get_today());
		}
	}
});

frappe.ui.form.on("Client Side Visit Detail", {
	check_in_time: function(frm, cdt, cdn) {
		validate_row_times(frm, cdt, cdn);
	},
	check_out_time: function(frm, cdt, cdn) {
		validate_row_times(frm, cdt, cdn);
	}
});

function validate_row_times(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (row.check_in_time && row.check_out_time) {
		if (row.check_out_time <= row.check_in_time) {
			frappe.msgprint(__("Check Out Time must be after Check In Time."));
			frappe.model.set_value(cdt, cdn, 'check_out_time', '');
		}
	}
}
