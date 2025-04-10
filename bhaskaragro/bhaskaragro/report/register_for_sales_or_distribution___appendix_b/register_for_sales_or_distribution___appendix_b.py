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
				"width": 200
			},
			{
				"label": _("Item Name"),
				"fieldname": 'item_name',
				"fieldtype": "Read Only",
				"width": 200
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
				"width": 200
			},
			{
				"label": _("Purchase Receipt Date"),
				"fieldname": 'posting_date',
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Supplier"),
				"fieldname": 'supplier',
				"fieldtype": "Link",
				"options":"Supplier",
				"width": 200

			},
			{
				"label": _("Supplier Name"),
				"fieldname": 'supplier_name',
				"fieldtype": "Data",
				"width": 200

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
				"label": _("Purchase Invoice No"),
				"fieldname": 'invoice_no',
				"fieldtype": "Link",
				"options":"Purchase Invoice",
				"width": 200
			},
			{
				"label": _("Sold/Distributed"),
				"fieldname": 's_and_d',
				"fieldtype": "int",
				"width": 100
			},
			{
				"label": _("Stock Balance"),
				"fieldname": 'stock_balance',
				"fieldtype": "int",
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
	if filters.get("item_group"):
		conditions += "AND pi.item_group = '%s'" % filters.get('item_group')
	if filters.get("supplier"):
		conditions += "AND p.supplier = '%s'" % filters.get('supplier')	
	if filters.get("company"):
		conditions += "AND p.company = '%s'" % filters.get('company')		

	return conditions

def get_data(filters):
	
	conditions = get_condition(filters)
	doc = frappe.db.sql("""
						select p.name, pi.item_code, pi.item_group,pi.item_name, pi.warehouse,
						p.posting_date, pi.received_qty as qty,
						p.supplier, p.supplier_name, pi.batch_no,

						(select distinct pin.parent from `tabPurchase Invoice Item` pin 
							where  pin.purchase_receipt=p.name limit 1) as invoice_no,

						(select b.manufacturing_date from `tabBatch` b 
							where  b.name=pi.batch_no) as date_of_manufacturing, 

						(Select sum(qty) from `tabSales Invoice Item` sii
							where sii.item_code = pi.item_code
							group by item_code) as s_and_d,

						(Select actual_qty from `tabBin`
							where item_code = pi.item_code 
							and warehouse = pi.warehouse) as stock_balance,

						(select  b.expiry_date from `tabBatch` b where  b.name=pi.batch_no) 
							as date_of_expiry
						
						from `tabPurchase Receipt` p 

						inner join `tabPurchase Receipt Item` pi on p.name=pi.parent

						where p.docstatus=1 
		{conditions} """.format(conditions=conditions),filters, as_dict=1)
	return doc	
