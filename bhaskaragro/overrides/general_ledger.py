import frappe
from frappe import _

import erpnext.accounts.report.general_ledger.general_ledger as original_gl

_original_execute = original_gl.execute


def custom_execute(filters=None):
	columns, data = _original_execute(filters)

	if data:
		for row in data:
			if isinstance(row, dict) and row.get("account") == f"'{_('Total')}'":
				row["voucher_type"] = _("Total")

	return columns, data
