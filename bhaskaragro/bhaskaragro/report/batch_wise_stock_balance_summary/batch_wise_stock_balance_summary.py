# # # Copyright (c) 2022, Dexciss Technology and contributors
# # # For license information, please see license.txt


from asyncio import DatagramTransport
from re import A
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate
from frappe.utils import date_diff
from datetime import date, datetime



def execute(filters=None):
	if not filters: filters = {}

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)
	get_qty= get_stock_ledger_entries(filters)

	
	data = []
	
	for item in sorted(iwb_map):
		if not filters.get("item") or filters.get("item") == item:
			for wh in sorted(iwb_map[item]):
				for batch in sorted(iwb_map[item][wh]):
					qty_dict = iwb_map[item][wh][batch]
					if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
						data.append([item, item_map[item]["item_name"], item_map[item]["description"], wh, batch,
							flt(qty_dict.opening_qty, float_precision), flt(qty_dict.in_qty, float_precision),
							flt(qty_dict.out_qty, float_precision), flt(qty_dict.bal_qty, float_precision),
							item_map[item]["stock_uom"],
							item_map[item]["manufacturing_date"],
							item_map[item]["expiry_date"]
						])

	for i in data:
		

		if filters.get("date_of_generating_report") and i[-1] != None:
			i.append(date_diff(i[-1],i[-2]))															#shelf life
			i.append(date_diff(filters.get("date_of_generating_report"),i[-3]))  						#lapsed life
			i.append(date_diff(i[-3],filters.get("date_of_generating_report")))  						#balanced life
		
		else:
			i.append(None)
			i.append(date_diff(filters.get("date_of_generating_report"),i[-3]))
			i.append(None)


	
	a = []
	for d in data:
		a.append(d[14])
		for x in get_qty:
			
			
			if d[0] == x.get("item_code") and d[4]== x.get("batch_no") and d[3] == x.get("warehouse"):
				
				abc=frappe.db.sql("""select stock_value
					from `tabStock Ledger Entry` 
					where item_code=%(item_code)s
					 and batch_no=%(batch_no)s
					 and warehouse=%(warehouse)s
					 and is_cancelled = 0
					 and docstatus < 2  and ifnull(batch_no, '') != ''
					order by creation desc limit 1"""
					,{'item_code':x.get("item_code"),'batch_no':x.get("batch_no"),'warehouse':x.get("warehouse")},as_dict=1)
					
				for i in abc:
						d.append(i.get("stock_value"))


	for d in data:
		if d[14] in range(0,30):
			d.append(d[15])
		else:
			d.insert(16,0)
		
		if d[14] in range(filters.get("range1"),filters.get("range2")+1):
			d.insert(17,d[15])
		else:
			d.insert(17,0)

		if d[14] in range(filters.get("range2"),filters.get("range3")+1):
			d.insert(18,d[15])
		else:
			d.insert(18,0)
		
		if d[14] in range(filters.get("range3"),filters.get("range4")+1):
			d.insert(19,d[15])
		else:
			d.insert(19,0)

		if d[14] in range(filters.get("range4"),2000):
			d.insert(20,d[15])
		else:
			d.insert(20,0)
			
	return columns, data


def get_columns(filters):
	"""return columns based on filters"""
	

	columns = [_("Item") + ":Link/Item:100"] + [_("Item Name") + "::150"] + [_("Description") + "::150"] + \
		[_("Warehouse") + ":Link/Warehouse:100"] + [_("Batch") + ":Link/Batch:100"] + [_("Opening Qty") + ":Float:90"] + \
		[_("In Qty") + ":Float:80"] + [_("Out Qty") + ":Float:80"] + [_("Balance Qty") + ":Float:90"] + \
		[_("UOM") + "::90"] + [_("Manufacturing Date") + ":Date:110"] +[_("Expiry Date") + ":Date:110"] +\
		[_("Shelf Life") + ":Int:100"] + [_("Lapsed Life") + ":Int:100"] + [_("Balanced Life") + ":Int:100"]+[_("Stock Value") + ":Currency:100"]+\
		[_("0 - 30") + ":Currency:100"]
	
	if filters.get("range1") and filters.get("range2") and filters.get("range3") and filters.get("range4"):
		columns.extend([_("{0} - {1}".format(filters.get("range1")+1,filters.get("range2"))) + ":Currency:100"])
		columns.extend([_("{0} - {1}".format(filters.get("range2")+1,filters.get("range3"))) + ":Currency:100"])
		columns.extend([_("{0} - {1}".format(filters.get("range3")+1,filters.get("range4"))) + ":Currency:100"])
		columns.extend([_(" Above {0}".format(filters.get("range4")+1)) + ":Currency:100"])


	
	return columns


def get_conditions(filters):
	
	conditions = ""
	
	
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))

	for field in ["item_code", "warehouse", "batch_no", "company"]:
		if filters.get(field):
			conditions += " and {0} = {1}".format(field, frappe.db.escape(filters.get(field)))

	return conditions


# get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select item_code, batch_no, warehouse, posting_date,stock_value, sum(actual_qty) as actual_qty
		from `tabStock Ledger Entry` 
		where is_cancelled = 0 and docstatus < 2  and ifnull(batch_no, '') != '' %s
		group by voucher_no, batch_no, item_code, warehouse
		order by item_code, warehouse""" %
		conditions, as_dict=1)


def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	for s in sle:	
		s.update({
		"manufacturing_date": (frappe.db.get_value("Batch", s.get('batch_no'), "manufacturing_date")),})
		
	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:	
	
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
			}))
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]

		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) \
				+ flt(d.actual_qty, float_precision)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) \
					+ abs(flt(d.actual_qty, float_precision))

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)
	
	
	return iwb_map


def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("""select t1.name, t1.item_name, t1.description,t1.stock_uom,t2.batch_id,t2.manufacturing_date,t2.expiry_date from `tabItem` as t1 join `tabBatch` as t2 on t1.name=t2.item""", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map




