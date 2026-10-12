// enertech_hrms/enertech_hrms/doctype/monthly_overtime_summary/monthly_overtime_summary_list.js
// Adds a "Calculate Overtime" button on the Monthly Overtime Summary list page.

frappe.listview_settings["Monthly Overtime Summary"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Calculate Overtime"), () => {
			frappe.prompt(
				[
					{
						fieldname: "month",
						label: __("Any date of the month"),
						fieldtype: "Date",
						reqd: 1,
						default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
					},
					{
						fieldname: "recalculate",
						label: __("Recalculate (overwrite existing)"),
						fieldtype: "Check",
						default: 0,
					},
				],
				(values) => {
					frappe.call({
						method: "enertech_hrms.enertech_hrms.utils.overtime.calculate_monthly_overtime",
						args: { month: values.month, recalculate: values.recalculate ? 1 : 0 },
						freeze: true,
						freeze_message: __("Calculating overtime..."),
						callback(r) {
							const rows = r.message || [];
							frappe.msgprint(__("Done. {0} employees have overtime in this month.", [rows.length]));
							listview.refresh();
						},
					});
				},
				__("Calculate Overtime"),
				__("Calculate")
			);
		});
	},
};