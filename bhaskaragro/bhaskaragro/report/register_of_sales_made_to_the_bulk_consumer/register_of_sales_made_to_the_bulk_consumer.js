// Copyright (c) 2016, Dexciss Technology and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Register Of Sales Made To The Bulk Consumer"] = {
	"filters": [
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
        }

	]
};
