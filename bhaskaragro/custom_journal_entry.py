import frappe
from frappe.model.document import Document

class PartyType(Document):
	pass


@frappe.whitelist()
def get_party_type(doctype, txt, searchfield, start, page_len, filters):
    
    cond = ''
    if filters and filters.get('account'):
        account_type = frappe.db.get_value('Account', filters.get('account'), 'account_type')
        account = frappe.db.get_value('Account', filters.get('account'), 'allow_party_type_in_journal_entry')
        cond = "and account_type = '%s'" % account_type 
        cond = "and '%s' = 1"%account
        

    return frappe.db.sql("""select name from `tabParty Type`
            where `{key}` LIKE %(txt)s {cond}
            order by name limit %(start)s, %(page_len)s"""
            .format(key=searchfield, cond=cond), {
                'txt': '%' + txt + '%',
                'start': start, 'page_len': page_len
            })