frappe.listview_settings['Expense Claim'] = frappe.listview_settings['Expense Claim'] || {};
const _ec_onload = frappe.listview_settings['Expense Claim'].onload;

frappe.listview_settings['Expense Claim'].onload = function (listview) {
  if (_ec_onload) _ec_onload.call(this, listview);

  listview.page.add_inner_button(__('Travel Claim Report'), function () {
    const api = 'enertech_hrms.enertech_hrms.utils.travel_claim_report.';

    // list madhe select kelele vouchers (comma separated)
    const names = (listview.get_checked_items(true) || []).join(',');

    // list cha employee filter (?employee=EUPLC209 kinva Filter madhun)
    let employee = '';
    try {
      (listview.filter_area.get() || []).forEach((f) => {
        if (f[1] === 'employee' && f[2] === '=') employee = f[3];
      });
    } catch (e) {}

    const info = names
      ? __('{0} selected claim(s) will be downloaded.', [names.split(',').length])
      : employee
      ? __('Claims of employee {0} will be downloaded.', [employee])
      : __('Nothing selected, all claims of the company will be downloaded.');

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
        {
          fieldname: 'info',
          fieldtype: 'HTML',
          options: `<p class="text-muted">${info}</p>`,
        },
      ],
      primary_action_label: __('Download Excel'),
      primary_action(values) {
        const args = {
          company: values.company,
          from_date: values.from_date,
          to_date: values.to_date,
          names: names,
          employee: employee,
        };

        frappe.call({
          method: api + 'count_claims',
          args: args,
          freeze: true,
          freeze_message: __('Preparing report...'),
          callback(r) {
            if (!r.message) {
              frappe.msgprint(__('No claims found for the selected filters.'));
              return;
            }
            window.location.href = '/api/method/' + api + 'download?' + $.param(args);
            d.hide();
          },
        });
      },
    });

    d.show();
  });
};