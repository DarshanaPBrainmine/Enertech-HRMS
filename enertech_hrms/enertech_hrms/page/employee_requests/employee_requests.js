// Frappe Page script – "Employee Requests" (Leave, Missed Punch, Gate Pass ...)
// Paste in: Page > Script box (Standard = No).
// IMPORTANT: 'employee-requests' below must match the "Page Name" field exactly.

frappe.pages['employee-requests'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Employee Requests',
		single_column: true,
	});

	// ---- EDIT THIS LIST: one line per request type -------------------------
	// label = what HR sees, doctype = exact DocType name in Enertech
	const TYPES = [
		// Standard HRMS doctypes
		{ label: 'Leave Request', doctype: 'Leave Application' },
		{ label: 'Attendance Request', doctype: 'Attendance Request' },
		{ label: 'Compensatory Leave', doctype: 'Compensatory Leave Request' },
		{ label: 'Shift Request', doctype: 'Shift Request' },
		{ label: 'Expense Claim', doctype: 'Expense Claim' },
		// Custom Enertech doctypes: confirm the exact names (Awesomebar > "DocType List")
		{ label: 'Gate Pass', doctype: 'Gate Pass' },
		{ label: 'Missed Punch Out', doctype: 'Missed Punch Out Request' },
		{ label: 'WFH Check In/Out', doctype: 'Work From Home Check IN - OUT' },
		{ label: 'Client Side Attendance', doctype: 'Client Side Attendance' },
	];
	// ------------------------------------------------------------------------

	let rows = [], failed = [], fType = 'All', fStat = 'All', q = '', shown = [];
	const esc = frappe.utils.escape_html;

	const status = d => d.workflow_state || d.approval_status || d.status ||
		({ 0: 'Draft', 1: 'Submitted', 2: 'Cancelled' }[d.docstatus]) || '';
	const group = s =>
		/approv|submitted|accept|complete|closed/i.test(s) ? 'Approved' :
		/reject|cancel/i.test(s) ? 'Rejected' : 'Pending';
	const color = { Approved: 'green', Rejected: 'red', Pending: 'orange' };

	page.add_field({
		fieldname: 'q', label: 'Search', fieldtype: 'Data',
		change() { q = (this.get_value() || '').toLowerCase(); render(); },
	});
	page.set_secondary_action('Refresh', () => load(), 'refresh');

	const $chips = $('<div style="margin-bottom:8px"></div>').appendTo(page.main);
	const $stats = $('<div style="margin-bottom:12px"></div>').appendTo(page.main);
	const $note = $('<div class="text-danger small" style="margin-bottom:8px"></div>').appendTo(page.main);
	const $tbl = $('<div></div>').appendTo(page.main);

	async function load() {
		$tbl.html('<p class="text-muted">Loading requests…</p>');
		const out = []; failed = [];
		await Promise.all(TYPES.map(async t => {
			try {
				// get_list respects permissions: managers only get their own team's records
				const res = await frappe.call({
					method: 'frappe.client.get_list',
					args: {
						doctype: t.doctype, fields: ['*'],
						order_by: 'creation desc', limit_page_length: 200,
					},
					silent: true, // no popup if a doctype is missing; shown in the red note instead
				});
				(res.message || []).forEach(d => out.push({ type: t.label, doctype: t.doctype, d }));
			} catch (e) { failed.push(t.doctype); }
		}));
		rows = out.sort((a, b) => (b.d.creation || '').localeCompare(a.d.creation || ''));
		render();
	}

	function render() {
		const typeCount = t => t === 'All' ? rows.length : rows.filter(r => r.type === t).length;
		$chips.html(['All', ...TYPES.map(t => t.label)].map(t =>
			`<button class="btn btn-xs ${fType === t ? 'btn-primary' : 'btn-default'}" data-type="${esc(t)}">
				${esc(t === 'All' ? 'All types' : t)} (${typeCount(t)})</button>`).join(' '));

		const base = rows.filter(r => fType === 'All' || r.type === fType);
		$stats.html(['All', 'Pending', 'Approved', 'Rejected'].map(s => {
			const n = base.filter(r => s === 'All' || group(status(r.d)) === s).length;
			return `<button class="btn btn-xs ${fStat === s ? 'btn-primary' : 'btn-default'}" data-stat="${s}">${s} (${n})</button>`;
		}).join(' '));

		$note.text(failed.length
			? `Could not load: ${failed.join(', ')}. Check the DocType name in TYPES and your read permission.` : '');

		shown = base.filter(r =>
			(fStat === 'All' || group(status(r.d)) === fStat) &&
			JSON.stringify(r.d).toLowerCase().includes(q));

		if (!shown.length) {
			$tbl.html('<p class="text-muted" style="padding:24px 0">No requests match these filters.</p>');
			return;
		}
		const body = shown.map((r, i) => {
			const d = r.d, s = status(d), g = group(s);
			const from = d.from_date || d.work_from_date, to = d.to_date || d.work_end_date;
			let when = from
				? from + (to && to !== from ? ' → ' + to : '')
				: String(d.date || d.attendance_date || d.posting_date || d.out_time || d.check_in || d.creation || '').slice(0, 16);
			if (d.total_claimed_amount) when += ' · ₹' + d.total_claimed_amount;
			const why = d.description || d.reason || d.explanation || d.purpose || d.remarks ||
				d.shift_type || d.shirt_size || d.location || d.client_name || '';
			const wf = d.workflow_state && g === 'Pending';
			return `<tr>
				<td><b>${esc(d.employee_name || d.employee || d.owner || '')}</b><br>
					<span class="text-muted small">${esc(d.department || '')}</span></td>
				<td>${esc(r.type)}</td>
				<td>${esc(when)}<br><span class="text-muted small">${esc(why)}</span></td>
				<td>${esc(String(d.creation || '').slice(0, 10))}</td>
				<td><span class="indicator-pill ${color[g]}">${esc(s)}</span></td>
				<td style="white-space:nowrap">
					${wf ? `<button class="btn btn-xs btn-success" data-act="approve" data-i="${i}">Approve</button>
					<button class="btn btn-xs btn-danger" data-act="reject" data-i="${i}">Reject</button>` : ''}
					<button class="btn btn-xs btn-default" data-act="open" data-i="${i}">Open</button>
				</td></tr>`;
		}).join('');
		$tbl.html(`<div style="overflow-x:auto"><table class="table table-bordered">
			<thead><tr><th>Employee</th><th>Request</th><th>Details</th><th>Submitted</th><th>Status</th><th>Action</th></tr></thead>
			<tbody>${body}</tbody></table></div>`);
	}

	async function act(r, kind) {
		const doc = await frappe.xcall('frappe.client.get', { doctype: r.doctype, name: r.d.name });
		const trans = await frappe.xcall('frappe.model.workflow.get_transitions', { doc });
		const re = kind === 'approve' ? /approv/i : /reject/i;
		const t = trans.find(x => re.test(x.action));
		if (!t) return frappe.msgprint(`No "${kind}" action is available to you on this request. Use Open to see the options.`);
		await frappe.xcall('frappe.model.workflow.apply_workflow', { doc, action: t.action });
		frappe.show_alert({ message: `${t.action}: ${r.d.name}`, indicator: 'green' });
		load();
	}

	$(wrapper).on('click', 'button[data-type]', function () { fType = $(this).data('type'); render(); });
	$(wrapper).on('click', 'button[data-stat]', function () { fStat = $(this).data('stat'); render(); });
	$(wrapper).on('click', 'button[data-act]', function () {
		const r = shown[$(this).data('i')], a = $(this).data('act');
		if (a === 'open') frappe.set_route('Form', r.doctype, r.d.name);
		else act(r, a);
	});

	load();
};