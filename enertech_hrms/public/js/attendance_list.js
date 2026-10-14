// apps/enertech_hrms/enertech_hrms/public/js/attendance_list.js
// Adds a "Monthly Report" button on Attendance list view.

(function () {
	const settings = (frappe.listview_settings["Attendance"] =
		frappe.listview_settings["Attendance"] || {});
	const prev_onload = settings.onload;

	settings.onload = function (listview) {
		if (prev_onload) prev_onload(listview);

		listview.page.add_inner_button(__("Monthly Report"), () => {
			const now = new Date();
			const months = [
				"January", "February", "March", "April", "May", "June",
				"July", "August", "September", "October", "November", "December",
			];

			const d = new frappe.ui.Dialog({
				title: __("Employee Wise Attendance Report"),
				fields: [
					{ fieldname: "month", label: __("Month"), fieldtype: "Select",
					  options: months, default: months[now.getMonth()], reqd: 1 },
					{ fieldname: "year", label: __("Year"), fieldtype: "Int",
					  default: now.getFullYear(), reqd: 1 },
					{ fieldname: "company", label: __("Company"), fieldtype: "Link",
					  options: "Company" },
					{ fieldname: "location", label: __("Location (title)"), fieldtype: "Data",
					  default: "Pirangut" },
					{ fieldtype: "Column Break" },
					{ fieldname: "shift_start", label: __("Shift Start (HH:MM)"),
					  fieldtype: "Data", default: "09:30" },
					{ fieldname: "shift_end", label: __("Shift End (HH:MM)"),
					  fieldtype: "Data", default: "18:00" },
					{ fieldname: "grace", label: __("Late Grace (minutes)"),
					  fieldtype: "Int", default: 15 },
				],
				primary_action_label: __("Download Excel"),
				primary_action(v) {
					const params = new URLSearchParams({
						month: months.indexOf(v.month) + 1,
						year: v.year,
						location: v.location || "",
						company: v.company || "",
						shift_start: v.shift_start || "09:30",
						shift_end: v.shift_end || "18:00",
						grace: v.grace || 0,
					});
					window.open(
						"/api/method/enertech_hrms.enertech_hrms.utils.employee_wise_attendance.download_report?" +
							params.toString()
					);
					d.hide();
				},
			});
			d.show();
		});
	};
})();