// Shows the day's Service Engineer Location Logs at the bottom of the form.
// Works for HR "Attendance" and "Service Engineer Attendence".

const SE_LOG_BOX = "se-location-logs";

function se_show_day_logs(frm, employee, date) {
	$(frm.layout.wrapper).find("#" + SE_LOG_BOX).remove();
	if (!employee || !date || frm.is_new()) return;

	frappe.call({
		method: "enertech_hrms.enertech_hrms.utils.location_tracking.get_day_logs",
		args: { employee: employee, date: date },
		callback(r) {
			const logs = r.message || [];
			const esc = frappe.utils.escape_html;

			let rows = logs.map((l, i) => {
				const time = (l.timestamp || "").split(" ")[1]?.split(".")[0] || "";
				const acc = l.accuracy ? Math.round(l.accuracy) + " m" : "-";
				const map = `https://www.google.com/maps?q=${l.latitude},${l.longitude}`;
				return `<tr>
					<td>${i + 1}</td>
					<td><b>${time}</b></td>
					<td>${esc(l.address || "")}</td>
					<td>${acc}</td>
					<td><a href="${map}" target="_blank">Map</a></td>
				</tr>`;
			}).join("");

			if (!rows) {
				rows = `<tr><td colspan="5" class="text-muted text-center">${__("No location logs for this date")}</td></tr>`;
			}

			const html = `
				<div id="${SE_LOG_BOX}" class="form-section card-section" style="margin-top:15px">
					<div class="section-head">${__("Location Logs")} (${logs.length})</div>
					<div style="overflow-x:auto">
						<table class="table table-bordered table-sm">
							<thead><tr>
								<th>#</th><th>${__("Time")}</th><th>${__("Address")}</th>
								<th>${__("Accuracy")}</th><th>${__("Map")}</th>
							</tr></thead>
							<tbody>${rows}</tbody>
						</table>
					</div>
				</div>`;
			$(frm.layout.wrapper).append(html);
		},
	});
}

frappe.ui.form.on("Attendance", {
	refresh(frm) {
		se_show_day_logs(frm, frm.doc.employee, frm.doc.attendance_date);
	},
});

frappe.ui.form.on("Service Engineer Attendence", {
	refresh(frm) {
		const date = (frm.doc.timestamp || "").split(" ")[0];
		se_show_day_logs(frm, frm.doc.employee, date);
	},
});