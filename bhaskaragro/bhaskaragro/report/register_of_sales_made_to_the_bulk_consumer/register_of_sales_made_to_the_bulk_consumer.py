# Copyright (c) 2013, Dexciss Technology and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns=get_columns(filters)
	data = get_data(filters)
	return columns, data




def get_columns(filters):
	columns=[
			{
				"label": _("Item Code"),
				"fieldname": 'item_code',
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},
			{
				"label": _("Item Name"),
				"fieldname": 'item_name',
				"fieldtype": "Read Only",
				"width": 100
			},

			{
				"label": _("Item Group"),
				"fieldname": 'item_group',
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 100
			},
			{
				"label": _("Warehouse"),
				"fieldname": 'warehouse',
				"fieldtype": "Link",
				"options":"Warehouse",
				"width": 100
			},
			{
				"label": _("Purchase Receipt No"),
				"fieldname": 'name',
				"fieldtype": "Link",
				"options":"Purchase Receipt",
				"width": 100
			},
			{
				"label": _("Purchase Receipt Date"),
				"fieldname": 'posting_date',
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Batch No"),
				"fieldname": 'batch_no',
				"fieldtype": "Link",
				"options":"Batch",
				"width": 100
			},
			{
				"label": _("Date Of Manufacturing"),
				"fieldname": 'date_of_manufacturing',
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Date Of Expiry"),
				"fieldname": 'date_of_expiry',
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Quantity Received"),
				"fieldname": 'qty',
				"fieldtype": "Float",
				"width": 100
			},
			{
				"label": _("Name Of The Purchaser"),
				"fieldname": 'supplier_name',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Purchase Invoice No"),
				"fieldname": 'invoice_no',
				"fieldtype": "Link",
				"options":"Purchase Invoice",
				"width": 100
			},
			{
				"label": _("Purchaser Address"),
				"fieldname": 'address',
				"fieldtype": "Small Text",
				"width": 100
			},
			{
				"label": _("Licence No of Purchaser"),
				"fieldname": 'license_of_purchaser',
				"fieldtype": "Data",
				"width": 100
			},
	]
	return columns

def get_condition(filters):

	conditions=" "
	if filters.get("from_date"):
		conditions += "AND p.posting_date >='%s'" % filters.get('from_date')
	if filters.get("to_date"):
		conditions += "AND p.posting_date <='%s'" % filters.get('to_date')
	if filters.get("item_code"):
		conditions += "AND pi.item_code = '%s'" % filters.get('item_code')
	if filters.get("purchase_receipt"):
		conditions += "AND p.name = '%s'" % filters.get('purchase_receipt')
	if filters.get("batch_no"):
		conditions += "AND pi.batch_no = '%s'" % filters.get('batch_no')
	return conditions


def get_data(filters):
	
	conditions = get_condition(filters)
	doc = frappe.db.sql("""select p.name,pi.item_code,pi.item_name,pi.item_group,pi.warehouse,p.posting_date,pi.received_qty as qty,pi.batch_no,
	p.supplier_name,(select concat(a.address_title,a.address_line1,a.address_line2,a.city,a.state,a.country,a.pincode) 
	from `tabAddress` a where a.name=p.supplier_address) as address,
	(select a.pl_no from `tabAddress` a where a.name=p.supplier_address) as license_of_purchaser ,
	(select distinct pin.parent from `tabPurchase Invoice Item` pin where  pin.purchase_receipt=p.name limit 1) as invoice_no,
	(select b.manufacturing_date from `tabBatch` b where  b.name=pi.batch_no) as date_of_manufacturing, 
	(select  b.expiry_date from `tabBatch` b where  b.name=pi.batch_no) 
	as date_of_expiry from `tabPurchase Receipt` p inner join `tabPurchase Receipt Item` pi on p.name=pi.parent
	where p.docstatus=1 
		{conditions} """.format(conditions=conditions),filters, as_dict=1)
	return doc
	
