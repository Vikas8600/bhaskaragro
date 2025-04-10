// Copyright (c) 2016, Dexciss Technology and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Person Wise Summary"] = {
	"filters": [
		{
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options:"Sales Person",
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
