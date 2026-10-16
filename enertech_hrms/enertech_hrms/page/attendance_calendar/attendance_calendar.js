frappe.pages['attendance-calendar'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({ parent: wrapper, title: 'Attendance Calendar', single_column: true });
  let cur = moment().startOf('month');
  const shifts = {};

  page.set_primary_action('Today', () => { cur = moment().startOf('month'); render(); });
  page.add_inner_button('‹ Prev', () => { cur.subtract(1, 'month'); render(); });
  page.add_inner_button('Next ›', () => { cur.add(1, 'month'); render(); });

  const C = {
    P: ['#2e9e57', 'rgba(46,158,87,.15)'],  AB: ['#d93a3a', 'rgba(217,58,58,.15)'],
    WO: ['#f0932b', 'rgba(240,147,43,.15)'], PH: ['#8a5cd1', 'rgba(138,92,209,.18)'],
    L: ['#2e9e57', 'rgba(46,158,87,.15)'],   HD: ['#f0932b', 'rgba(240,147,43,.15)'],
    WFH: ['#2f6fdb', 'rgba(47,111,219,.15)']
  };

  $(page.body).html(`<style>
    .ac-bar{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}
    .ac-bar span{border:1px solid var(--border-color);border-radius:14px;padding:2px 10px;font-size:12px}
    .ac-wrap{overflow-x:auto}
    .ac-g{display:grid;grid-template-columns:repeat(7,minmax(140px,1fr));min-width:980px;border:1px solid var(--border-color)}
    .ac-h{background:#4a9be0;color:#fff;text-align:center;padding:6px;font-weight:600;font-size:12px}
    .ac-c{min-height:130px;border-right:1px solid var(--border-color);border-bottom:1px solid var(--border-color);padding-bottom:6px;font-size:11px}
    .ac-c.out{opacity:.45}
    .ac-n{text-align:right;padding:2px 6px;border-bottom:1px solid var(--border-color)}
    .ac-c.today .ac-n{background:#2d6aa8;color:#fff;font-weight:700}
    .ac-e{margin:5px 4px 0;padding:4px 6px;border-left:3px solid;border-radius:3px}
    .ac-e b{display:block}
    .ac-r{display:flex;justify-content:space-between;color:var(--text-muted);margin-top:2px}
    .ac-r em{font-style:normal;color:var(--text-color)}
    .ac-tag{display:inline-block;background:#f0932b;color:#fff;border-radius:8px;padding:0 6px;font-size:10px;margin-top:2px}
    .ac-msg{padding:30px;text-align:center;color:var(--text-muted)}
    .ac-leg{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0;font-size:12px;color:var(--text-muted)}
    .ac-leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}
  </style>
  <div id="ac-emp" style="max-width:320px;margin:10px 0"></div>
  <h4 id="ac-t" class="text-center"></h4>
  <div class="ac-bar" id="ac-s"></div>
  <div class="ac-wrap"><div class="ac-g" id="ac-g"></div></div>
  <div class="ac-leg">
    <span><i style="background:#2e9e57"></i>P Present / Leave</span>
    <span><i style="background:#f0932b"></i>WO Week off / Half day</span>
    <span><i style="background:#d93a3a"></i>AB Absent</span>
    <span><i style="background:#8a5cd1"></i>PH Holiday</span>
    <span><i style="background:#2f6fdb"></i>WFH</span>
  </div>`);

  const emp = frappe.ui.form.make_control({
    parent: $('#ac-emp'),
    df: { fieldname: 'employee', label: 'Employee', fieldtype: 'Link', options: 'Employee', change: () => render() },
    render_input: true
  });
  emp.refresh();

  const hm = h => { const m = Math.round((h || 0) * 60); return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0'); };
  const t12 = t => moment(t, 'HH:mm:ss').format('h:mm A');
  const msg = (t, color) => $('#ac-g').html(`<div class="ac-msg" style="grid-column:1/-1;${color ? 'color:' + color : ''}">${t}</div>`);

  frappe.db.get_list('Shift Type', { fields: ['name', 'start_time', 'end_time'], limit: 100 })
    .then(r => (r || []).forEach(s => shifts[s.name] = s)).catch(() => {});

  frappe.db.get_value('Employee', { user_id: frappe.session.user }, 'name')
    .then(r => { if (r.message && r.message.name) emp.set_value(r.message.name); else render(); })
    .catch(() => render());

  async function render() {
    $('#ac-t').text(cur.format('MMMM YYYY'));
    const employee = emp.get_value();
    if (!employee) { $('#ac-s').html(''); msg('Select an Employee above to see attendance.'); return; }

    try {
      const from = cur.format('YYYY-MM-DD'), to = cur.clone().endOf('month').format('YYYY-MM-DD');

      // Attendance
      const rows = await frappe.db.get_list('Attendance', {
        filters: { employee, docstatus: ['<', 2], attendance_date: ['between', [from, to]] },
        fields: ['attendance_date', 'status', 'shift', 'in_time', 'out_time', 'working_hours', 'early_exit', 'late_entry', 'leave_type'],
        limit: 100
      });
      const att = {}; rows.forEach(r => att[r.attendance_date] = r);

      // Holidays / Week offs
      const hol = {};
      try {
        const e = (await frappe.db.get_value('Employee', employee, ['holiday_list', 'company'])).message || {};
        let hl = e.holiday_list;
        if (!hl && e.company) hl = (await frappe.db.get_value('Company', e.company, 'default_holiday_list')).message.default_holiday_list;
        if (hl) {
          const doc = await frappe.db.get_doc('Holiday List', hl);
          (doc.holidays || []).forEach(h => {
            if (h.holiday_date >= from && h.holiday_date <= to) hol[h.holiday_date] = h;
          });
        }
      } catch (err) { console.warn('Holiday list not loaded', err); }

      // Draw
      let html = ['SUN','MON','TUE','WED','THU','FRI','SAT'].map(d => `<div class="ac-h">${d}</div>`).join('');
      const first = cur.clone().subtract(cur.day(), 'days');
      const total = Math.ceil((cur.day() + cur.daysInMonth()) / 7) * 7;
      const count = {};

      for (let i = 0; i < total; i++) {
        const d = first.clone().add(i, 'days'), key = d.format('YYYY-MM-DD'), inM = d.month() === cur.month();
        let card = '';
        if (inM) {
          const a = att[key], h = hol[key];
          let code, label;
          if (a) {
            code = { 'Present': 'P', 'Absent': 'AB', 'On Leave': 'L', 'Half Day': 'HD', 'Work From Home': 'WFH' }[a.status] || 'P';
            label = a.status === 'On Leave' ? (a.leave_type || 'Leave') : code;
            if (h) label = (h.weekly_off ? 'WO' : 'PH') + '(' + label + ')';
          } else if (h) { code = h.weekly_off ? 'WO' : 'PH'; label = code; }

          if (code) {
            count[label] = (count[label] || 0) + 1;
            const [bc, bg] = C[code];
            let body = '', tag = '';
            if (a && a.in_time) {
              const sh = shifts[a.shift];
              if (sh) body += `<div class="ac-r"><span>${t12(sh.start_time)} to ${t12(sh.end_time)}</span></div>`;
              body += `<div class="ac-r"><span>In/Out</span><em>${moment(a.in_time).format('HH:mm')} - ${a.out_time ? moment(a.out_time).format('HH:mm') : '--'}</em></div>`;
              body += `<div class="ac-r"><span>Duration</span><em>${hm(a.working_hours)}</em></div>`;
              body += `<div class="ac-r"><span>Net Hrs</span><em>${hm(a.working_hours)}</em></div>`;
              if (a.early_exit && sh && a.out_time) {
                const diff = moment(key + ' ' + sh.end_time).diff(moment(a.out_time), 'minutes');
                if (diff > 0) {
                  tag = `<span class="ac-tag">${hm(diff / 60)}</span>`;
                  body += `<div class="ac-r"><span>Early By</span><em>${hm(diff / 60)}</em></div>`;
                }
              }
            }
            card = `<div class="ac-e" style="border-color:${bc};background:${bg}"><b>Status : ${label}</b>${tag}${body}</div>`;
          }
        }
        html += `<div class="ac-c ${inM ? '' : 'out'} ${d.isSame(moment(), 'day') ? 'today' : ''}"><div class="ac-n">${d.date()}</div>${card}</div>`;
      }
      $('#ac-g').html(html);
      $('#ac-s').html(Object.keys(count).length
        ? Object.entries(count).map(([k, v]) => `<span>${k}: <b>${v}</b></span>`).join('')
        : '<span>No attendance records for this month</span>');
    } catch (err) {
      console.error(err);
      msg('Could not load data: ' + (err.message || 'see browser console (F12)'), '#d93a3a');
    }
  }
};