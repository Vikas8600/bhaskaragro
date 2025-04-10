// Copyright (c) 2022, Dexciss Technology and contributors
// For license information, please see license.txt
/* eslint-disable */



frappe.query_reports["Batch Wise Stock Balance Summary"] = {
	"filters": [
		
		
				{
					"fieldname":"date_of_generating_report",
					"label": __("Date of Generating Report"),
					"fieldtype": "Date",
					"default":frappe.datetime.get_today()
				},
		
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.sys_defaults.year_start_date,
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function() {
				return {
					filters: {
						"has_batch_no": 1
					}
				};
			},
			// "reqd":1
		},
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"get_query": function() {
				let company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						"company": company
					}
				};
			}
		},
		{
			"fieldname":"batch_no",
			"label": __("Batch No"),
			"fieldtype": "Link",
			"options": "Batch",
			"get_query": function() {
				let item_code = frappe.query_report.get_filter_value('item_code');
				return {
					filters: {
						"item": item_code
					}
				};
			}
		},
		{
			"fieldname":"range1",
			"label": __("Range1"),
			"fieldtype": "Int",
			"default":30
		},
			{
			"fieldname":"range2",
			"label": __("Range2"),
			"fieldtype": "Int",
			"default":60

		},
		{
			"fieldname":"range3",
			"label": __("Range3"),
			"fieldtype": "Int",
			"default":90
		},
		{
			"fieldname":"range4",
			"label": __("Range4"),
			"fieldtype": "Int",
			"default":120
		},
	],
	"formatter": function (value, row, column, data, default_formatter) {
		if (column.fieldname == "Batch" && data && !!data["Batch"]) {
			value = data["Batch"];
			column.link_onclick = "frappe.query_reports['Batch Wise Stock Balance Summary'].set_batch_route_to_stock_ledger(" + JSON.stringify(data) + ")";
		}

		value = default_formatter(value, row, column, data);
		return value;
	},
	"set_batch_route_to_stock_ledger": function (data) {
		frappe.route_options = {
			"batch_no": data["Batch"]
		};

		frappe.set_route("query-report", "Stock Ledger");
	},

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "balanced_life" && data && data.balanced_life < 0) {
			value = "<span style='color:red'>" + value + "</span>";
		}
		else if (column.fieldname == "balanced_life" && data && data.balanced_life > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}

		return value;
	},
	
}

