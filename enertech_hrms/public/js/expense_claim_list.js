frappe.listview_settings['Expense Claim'] = frappe.listview_settings['Expense Claim'] || {};
const _ec_onload = frappe.listview_settings['Expense Claim'].onload;

frappe.listview_settings['Expense Claim'].onload = function (listview) {
  if (_ec_onload) _ec_onload.call(this, listview);

  listview.page.add_inner_button(__('Travel Claim Report'), function () {
    const api = 'enertech_hrms.enertech_hrms.utils.travel_claim_report.';

    const d = new frappe.ui.Dialog({
      title: __('Download Travel Claim Report'),
      fields: [
        {
          fieldname: 'company',
          label: __('Company'),
          fieldtype: 'Link',
          options: 'Company',
          reqd: 1,
          default: frappe.defaults.get_user_default('Company'),
        },
        {
          fieldname: 'from_date',
          label: __('From Date'),
          fieldtype: 'Date',
          reqd: 1,
          default: frappe.datetime.month_start(),
        },
        {
          fieldname: 'to_date',
          label: __('To Date'),
          fieldtype: 'Date',
          reqd: 1,
          default: frappe.datetime.get_today(),
        },
      ],
      primary_action_label: __('Download Excel'),
      primary_action(values) {
        frappe.call({
          method: api + 'count_claims',
          args: values,
          freeze: true,
          freeze_message: __('Preparing report...'),
          callback(r) {
            if (!r.message) {
              frappe.msgprint(__('No claims found for the selected dates.'));
              return;
            }
            window.location.href =
              '/api/method/' + api + 'download?' + $.param(values);
            d.hide();
          },
        });
      },
    });

    d.show();
  });
};
