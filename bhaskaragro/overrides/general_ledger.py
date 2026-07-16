import frappe
from erpnext.accounts.report.general_ledger import general_ledger

_get_gl_entries = general_ledger.get_gl_entries


def get_gl_entries(filters, accounting_dimensions):
	gl_entries = _get_gl_entries(filters, accounting_dimensions)

	if filters.get("show_remarks"):
		set_journal_entry_user_remark(gl_entries)

	return gl_entries


def set_journal_entry_user_remark(gl_entries):
	"""Show Journal Entry's user_remark instead of GL Entry remarks in General Ledger."""
	je_names = {gle.voucher_no for gle in gl_entries if gle.voucher_type == "Journal Entry"}
	if not je_names:
		return

	user_remarks = frappe._dict(
		frappe.get_all(
			"Journal Entry",
			filters={"name": ("in", je_names), "user_remark": ("is", "set")},
			fields=["name", "user_remark"],
			as_list=1,
		)
	)

	for gle in gl_entries:
		if gle.voucher_type == "Journal Entry" and gle.voucher_no in user_remarks:
			gle.remarks = user_remarks[gle.voucher_no]


general_ledger.get_gl_entries = get_gl_entries
