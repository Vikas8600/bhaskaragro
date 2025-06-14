# # Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# # License: GNU General Public License v3. See license.txt


import frappe

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe.utils import flt
from erpnext.accounts.utils import (
	cancel_exchange_gain_loss_journal,
	get_account_currency,
	update_voucher_outstanding,
)

class CustomSalesInvoice(SalesInvoice):
    def allow_write_off_only_on_pos(self):
        pass
    def make_write_off_gl_entry(self, gl_entries):
		# write off entries, applicable if only pos
        if (
            self.write_off_account
            and flt(self.write_off_amount, self.precision("write_off_amount"))
        ):
            write_off_account_currency = get_account_currency(self.write_off_account)
            default_cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": self.debit_to,
                        "party_type": "Customer",
                        "party": self.customer,
                        "against": self.write_off_account,
                        "credit": flt(self.base_write_off_amount, self.precision("base_write_off_amount")),
                        "credit_in_account_currency": (
                            flt(self.base_write_off_amount, self.precision("base_write_off_amount"))
                            if self.party_account_currency == self.company_currency
                            else flt(self.write_off_amount, self.precision("write_off_amount"))
                        ),
                        "credit_in_transaction_currency": flt(
                            self.write_off_amount, self.precision("write_off_amount")
                        ),
                        "against_voucher": self.return_against if cint(self.is_return) else self.name,
                        "against_voucher_type": self.doctype,
                        "cost_center": self.cost_center,
                        "project": self.project,
                    },
                    self.party_account_currency,
                    item=self,
                )
            )
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": self.write_off_account,
                        "against": self.customer,
                        "debit": flt(self.base_write_off_amount, self.precision("base_write_off_amount")),
                        "debit_in_account_currency": (
                            flt(self.base_write_off_amount, self.precision("base_write_off_amount"))
                            if write_off_account_currency == self.company_currency
                            else flt(self.write_off_amount, self.precision("write_off_amount"))
                        ),
                        "debit_in_transaction_currency": flt(
                            self.write_off_amount, self.precision("write_off_amount")
                        ),
                        "cost_center": self.cost_center or self.write_off_cost_center or default_cost_center,
                    },
                    write_off_account_currency,
                    item=self,
                )
            )


def batch_no(self,method):
    for j in self.entries:
        frappe.db.set_value("Sales Invoice Item",self.voucher_detail_no,"batch_no",j.batch_no)

