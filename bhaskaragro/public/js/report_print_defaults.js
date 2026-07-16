// Preselect print settings in the Print / PDF dialog of query reports,
// so users don't have to pick them on every print.
(function () {
	const REPORT_PRINT_DEFAULTS = {
		"General Ledger": {
			print_format: "Statement of Account",
			orientation: "Landscape",
			with_letter_head: 1,
			letter_head: "Bhaskar Office Letter Head",
		},
	};

	const original_get_print_settings = frappe.ui.get_print_settings;

	frappe.ui.get_print_settings = function (...args) {
		const dialog = original_get_print_settings.apply(this, args);

		const route = frappe.get_route();
		const defaults = route && route[0] === "query-report" && REPORT_PRINT_DEFAULTS[route[1]];

		if (defaults && dialog && dialog.set_value) {
			Object.entries(defaults).forEach(([fieldname, value]) => {
				dialog.set_value(fieldname, value);
			});
		}

		return dialog;
	};
})();
