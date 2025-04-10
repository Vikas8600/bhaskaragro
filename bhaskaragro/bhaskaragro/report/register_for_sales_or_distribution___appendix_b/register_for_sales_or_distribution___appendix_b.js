// Copyright (c) 2016, Dexciss Technology and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Register for Sales or Distribution - Appendix B"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options:"Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_global_default("year_start_date"),
			reqd: 0
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_global_default("year_end_date"),
			reqd: 0
        },
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options:"Item Group",
			default: "",
			reqd: 0
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options:"Item",
			default: "",
			reqd: 0
		},
		{
			fieldname: "batch_no",
			label: __("Batch Number"),
			fieldtype: "Link",
			options:"Batch",
			default: "",
			reqd: 0
		},
		{
			fieldname: "purchase_receipt",
			label: __("Purchase Receipt"),
			fieldtype: "Link",
			options:"Purchase Receipt",
			default: "",
			reqd: 0
		},
		
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options:"Supplier",
			default: "",
			reqd: 0
		},
	]
};
