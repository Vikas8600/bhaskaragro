# Copyright (c) 2013, Dexciss Technology and contributors
# For license information, please see license.txt

from heapq import merge
import frappe
from frappe import _

def execute(filters=None):
	columns=get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns=[
			{
				"label": _("Sales Person"),
				"fieldname": 'sales_person',
				"fieldtype": "Link",
				"options": "Sales Person",
				"width": 300
			},

			{
				"label": _("Customer"),
				"fieldname": 'customer',
				"fieldtype": "Link",
				"options": "Customer",
				"width": 100
			},
			{
				"label": _("Customer Name"),
				"fieldname": 'customer_name',
				"fieldtype": "Read Only",
				"width": 250
			},
			{
				"label": _("Total"),
				"fieldname": 'allocated_amount',
				"fieldtype": "Currency",
				"width": 100
			}
	]
	return columns

def get_condition(filters):

	conditions=" "
	if filters.get("sales_person"):
		conditions += "AND so.name = '%s'" % filters.get('sales_person')
	return conditions



def filters_list(filters):
	conditions=" "
	if filters.get("from_date"):
		conditions += "AND si.posting_date >='%s'" % filters.get('from_date')
	if filters.get("to_date"):
		conditions += "AND si.posting_date <='%s'" % filters.get('to_date')
	return conditions
def get_data(filters):
	list=[]
	conditions = get_condition(filters)
	filter=filters_list(filters)
	s_person=frappe.db.sql("""select so.name as sales_person from `tabSales Person` so where so.enabled=1 {conditions}""".format(conditions=conditions),as_dict=1)
	for f in s_person:
		R={"sales_person":""}
		R["sales_person"]="<b>"+str(f.get("sales_person"))+"</b>"
		list.append(R)
		doc = frappe.db.sql("""select c.name as customer,c.customer_name from `tabCustomer` c where c.disabled=0 
		and c.sales_person='{0}'""".format(f.get("sales_person")),as_dict=1)
		var=[]
		amount=[]
		for i in doc:
			K={"customer":"","customer_name":"","allocated_amount":""}
			doc1=frappe.db.sql("""select if(sum(st.allocated_amount),sum(st.allocated_amount),0) as allocated_amount 
			from `tabSales Invoice` si join `tabSales Team` st 
			on si.name=st.parent and st.sales_person ='{0}' where si.docstatus=1 and si.customer ='{1}' {conditions} group by si.customer""".format(f.get("sales_person"),i.get("customer"),conditions=filter),as_dict=1)
			if len(doc1)==0:
				doc1.append({"allocated_amount":0})
			for k in doc1:
				if k.get("allocated_amount") > 0:
					var.append(1)
					amount.append(k.get("allocated_amount"))
				K["customer"]=i.get("customer")
				K["customer_name"]=i.get("customer_name")
				K["allocated_amount"]=k.get("allocated_amount") if k else 0
				list.append(K)
		P={"sales_person":"","customer":"","customer_name":"","allocated_amount":""}
		P["sales_person"]="<b>Total</b>"
		P["customer"]="<b>"+str(len(doc))+"</b>"
		P["customer_name"]="<b>"+str(len(var))+"</b>"
		P["allocated_amount"]=sum(amount)
		list.append(P)

	return list
	
