
frappe.ui.form.on("Journal Entry", {

    

	refresh: function(frm) {
		

        
		frm.set_query("party_type", "accounts", function(doc, cdt, cdn) {
			const row = locals[cdt][cdn];

			return {
                query:"bhaskaragro.custom_journal_entry.get_party_type",
				filters: {
					'account': row.account,
                    
				}
			}
		});
    }
})

    
