"""Travel Claim Report: Excel download with a real hyperlink for every bill.

Layout follows TravelClaimReport.xlsx: title row, green header row, one row per
Expense Claim, one amount column per expense type, and "Open" hyperlinks.
"""

import html
import re
from datetime import date, datetime
from io import BytesIO
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import flt, get_url, getdate
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Expense Claim Type name -> column group. Change the names on the left
# if your Expense Claim Types are named differently.
TYPE_MAP = {
	"Conveyance (KM)": "KM",
	"Transport": "TRANSPORT",
	"Transport (Ticket)": "TRANSPORT",
	"Food": "FOOD",
	"Hotel": "HOTEL",
	"Hotel Lodging": "HOTEL",
	"Local Conveyance": "CONVEYANCE",
	"Other 1": "OTHER_A",
	"Other 2": "OTHER_B",
	"Other A": "OTHER_A",
	"Other B": "OTHER_B",
}
# Any Expense Claim Type that is not in TYPE_MAP is shown under this group.
FALLBACK_GROUP = "OTHER_A"

# (group key, amount header, remark header or None, bill link header)
GROUPS = [
	("KM", "TotalKMAmount", None, "TotalKMPath_Link"),
	("TRANSPORT", "Transport", None, "TransportPath_Link"),
	("FOOD", "Food", None, "FoodPath_Link"),
	("HOTEL", "Hotel", None, "HotelPath_Link"),
	("CONVEYANCE", "Conveyance", "ConveyanceRemark", "ConveyancePath_Link"),
	("OTHER_A", "OtherA", "OtherARemark", "OtherAPath_Link"),
	("OTHER_B", "OtherB", "OtherBRemark", "OtherBPath_Link"),
]

CLAIM_FIELDS = [
	"name",
	"company",
	"employee",
	"employee_name",
	"posting_date",
	"remark",
	"status",
	"approval_status",
	"expense_approver",
	"total_claimed_amount",
	"total_sanctioned_amount",
	"modified",
	"custom_travel_type",
	"custom_travel_purpose",
	"custom_per_km_rate",
	"custom_from_date",
	"custom_to_date",
	"custom_from_location",
	"custom_to_location",
	"custom_total_km",
	"custom_manager_remark",
]

DETAIL_FIELDS = ["parent", "idx", "expense_type", "amount", "description", "custom_bill"]


def _clean(text):
	"""Plain text from a field that may hold HTML (Text Editor fields do)."""
	if not text:
		return ""
	text = re.sub(r"<[^>]+>", " ", str(text))
	return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _file_url(file_url, base_url):
	if not file_url:
		return ""
	file_url = str(file_url).strip()
	if not file_url.lower().startswith("http"):
		file_url = base_url.rstrip("/") + "/" + file_url.lstrip("/")
	return quote(file_url, safe="/:%?=&#")


def _title(from_date, to_date):
	f, t = getdate(from_date), getdate(to_date)
	if (f.year, f.month) == (t.year, t.month):
		period = f.strftime("%b-%Y")
	else:
		period = f"{f.strftime('%d-%b-%Y')} to {t.strftime('%d-%b-%Y')}"
	return f"Travel Claim Report - ({period})"


def make_workbook(title, claims, details, branches, base_url):
	"""Build the workbook and return it as bytes. Pure python, no database access."""
	details_by_claim = {}
	for d in details:
		details_by_claim.setdefault(d.get("parent"), []).append(d)

	rows = []
	max_links = {g[0]: 1 for g in GROUPS}

	for c in claims:
		data = {g[0]: {"amount": 0.0, "remarks": [], "links": []} for g in GROUPS}
		for d in details_by_claim.get(c.get("name"), []):
			expense_type = d.get("expense_type")
			key = TYPE_MAP.get(expense_type, FALLBACK_GROUP)
			slot = data[key]
			slot["amount"] += flt(d.get("amount"))

			remark = _clean(d.get("description"))
			if expense_type not in TYPE_MAP:
				remark = f"{expense_type}: {remark}" if remark else str(expense_type)
			if remark:
				slot["remarks"].append(remark)

			url = _file_url(d.get("custom_bill"), base_url)
			if url:
				slot["links"].append(url)

		# No "Conveyance (KM)" row: show Total KM x Per KM Rate, as in the old portal
		if not data["KM"]["amount"]:
			data["KM"]["amount"] = round(
				flt(c.get("custom_total_km")) * flt(c.get("custom_per_km_rate")), 2
			)

		for key, slot in data.items():
			max_links[key] = max(max_links[key], len(slot["links"]))
		rows.append((c, data))

	headers = [
		"SrNo",
		"CompanyName",
		"BranchName",
		"VoucherNo",
		"VoucherDate",
		"TravelEmployeeName",
		"VehicleType",
		"TravelPurpose",
		"PerKMRate",
		"FromDate",
		"Todate",
		"FromLocation",
		"ToLocation",
		"Description",
		"TotalKM",
	]
	for key, amount_header, remark_header, link_header in GROUPS:
		headers.append(amount_header)
		if remark_header:
			headers.append(remark_header)
		for i in range(max_links[key]):
			headers.append(link_header if i == 0 else f"{link_header}{i + 1}")
	headers += [
		"TotalAmount",
		"ApprovedAmount",
		"Status",
		"ApprovalStatus",
		"ApproveRejectBy",
		"ApproveRejectDate",
		"ManagerRemark",
	]

	wb = Workbook()
	ws = wb.active
	ws.title = "TravelClaim Report"

	thin = Side(style="thin", color="000000")
	border = Border(left=thin, right=thin, top=thin, bottom=thin)
	header_fill = PatternFill("solid", fgColor="CDDEAC")
	header_font = Font(name="Calibri", size=10, bold=True)
	body_font = Font(name="Calibri", size=10)
	link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")

	ws.cell(row=1, column=1, value=title).font = Font(name="Calibri", size=11, bold=True)
	ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(21, len(headers)))
	ws.cell(row=1, column=1).alignment = Alignment(horizontal="left")

	for col, header in enumerate(headers, start=1):
		cell = ws.cell(row=2, column=col, value=header)
		cell.font = header_font
		cell.fill = header_fill
		cell.border = border

	widths = [len(h) + 2 for h in headers]

	for sr, (c, data) in enumerate(rows, start=1):
		values = [
			sr,
			c.get("company"),
			branches.get(c.get("employee")) or "",
			c.get("name"),
			c.get("posting_date"),  # Voucher Date = Posting Date
			c.get("employee_name"),
			c.get("custom_travel_type") or "",
			c.get("custom_travel_purpose") or "",
			flt(c.get("custom_per_km_rate")),
			c.get("custom_from_date"),
			c.get("custom_to_date"),
			c.get("custom_from_location") or "",
			c.get("custom_to_location") or "",
			_clean(c.get("custom_description") or c.get("remark")),
			flt(c.get("custom_total_km")),
		]
		for key, _amount_header, remark_header, _link_header in GROUPS:
			slot = data[key]
			values.append(slot["amount"])
			if remark_header:
				values.append("; ".join(slot["remarks"]))
			for i in range(max_links[key]):
				values.append(("LINK", slot["links"][i]) if i < len(slot["links"]) else "")
		values += [
			flt(c.get("total_claimed_amount")),
			flt(c.get("total_sanctioned_amount")),
			c.get("workflow_state") or c.get("status") or "",
			c.get("approval_status") or "",
			c.get("expense_approver") or "",
			c.get("modified"),
			_clean(c.get("custom_manager_remark")),
		]

		for col, value in enumerate(values, start=1):
			cell = ws.cell(row=sr + 2, column=col)
			cell.font = body_font
			cell.border = border
			if isinstance(value, tuple):
				cell.value = "Open"
				cell.hyperlink = value[1]
				cell.font = link_font
			elif isinstance(value, datetime):
				cell.value = value.replace(tzinfo=None)
				cell.number_format = "DD/MMM/YYYY HH:MM"
			elif isinstance(value, date):
				cell.value = value
				cell.number_format = "DD/MMM/YYYY"
			else:
				cell.value = value
				widths[col - 1] = max(widths[col - 1], min(len(str(value)) + 2, 45))

	for col, width in enumerate(widths, start=1):
		ws.column_dimensions[get_column_letter(col)].width = max(10, min(width, 45))
	ws.freeze_panes = "A3"

	out = BytesIO()
	wb.save(out)
	return out.getvalue()


def _get_claims(company, from_date, to_date):
	fields = list(CLAIM_FIELDS)
	meta = frappe.get_meta("Expense Claim")
	for optional in ("workflow_state", "custom_description"):
		if meta.has_field(optional):
			fields.append(optional)
	# get_list applies the user's permissions, so people see only claims they may read
	return frappe.get_list(
		"Expense Claim",
		filters={
			"company": company,
			"posting_date": ["between", [from_date, to_date]],
			"docstatus": ["<", 2],
		},
		fields=fields,
		order_by="posting_date desc, name desc",
		limit_page_length=0,
	)


@frappe.whitelist()
def count_claims(company, from_date, to_date):
	return len(_get_claims(company, from_date, to_date))


@frappe.whitelist()
def download(company, from_date, to_date):
	claims = _get_claims(company, from_date, to_date)
	if not claims:
		frappe.throw(_("No claims found for the selected dates."))

	details = frappe.get_all(
		"Expense Claim Detail",
		filters={"parent": ["in", [c.name for c in claims]], "parenttype": "Expense Claim"},
		fields=DETAIL_FIELDS,
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)
	employees = list({c.employee for c in claims if c.employee})
	branches = {
		e.name: e.branch
		for e in frappe.get_all(
			"Employee", filters={"name": ["in", employees]}, fields=["name", "branch"]
		)
	}

	frappe.response["filename"] = f"Travel_Claim_Report_{from_date}_to_{to_date}.xlsx"
	frappe.response["filecontent"] = make_workbook(
		_title(from_date, to_date), claims, details, branches, get_url()
	)
	frappe.response["type"] = "binary"