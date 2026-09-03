frappe.ui.form.on("Missed Punch Out Request", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.date) {
			frm.set_value('date', frappe.datetime.get_today());
		}
	},

	employee(frm) {
		fetch_last_checkin(frm);
	},

	date(frm) {
		fetch_last_checkin(frm);
	}
});

function fetch_last_checkin(frm) {
	if (!frm.doc.employee || !frm.doc.date) return;

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Employee Checkin",
			filters: {
				employee: frm.doc.employee,
				time: ["between", [`${frm.doc.date} 00:00:00`, `${frm.doc.date} 23:59:59`]]
			},
			fields: ["time", "log_type"],
			order_by: "time desc",
			limit_page_length: 1
		},
		callback: function(r) {
			if (r.message && r.message.length) {
				frm.set_value('checkin_time', r.message[0].time);
			} else {
				frm.set_value('checkin_time', '');
			}
		}
	});
}