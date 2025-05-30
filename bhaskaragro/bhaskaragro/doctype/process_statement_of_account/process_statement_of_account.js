// Copyright (c) 2022, Dexciss Technology and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Statement of Account', {
	view_properties: function(frm) {
		frappe.route_options = {doc_type: 'Customer'};
		frappe.set_route("Form", "Customize Form");
	},
	refresh: function(frm){
		if(!frm.doc.__islocal) {
			frm.add_custom_button('Send Emails',function(){
				frappe.call({
					method: "bhaskaragro.bhaskaragro.doctype.process_statement_of_account.process_statement_of_account.send_emails",
					args: {
						"document_name": frm.doc.name,
					},
					callback: function(r) {
						if(r && r.message) {
							frappe.show_alert({message: __('Emails Queued'), indicator: 'blue'});
						}
						else{
							frappe.msgprint(__('No Records for these settings.'))
						}
					}
				});
			});
			if (frm.doc.check==0){
			frm.add_custom_button('Download',function(){
				frm.set_value('check',1);
				frm.save()
				frappe.msgprint(__('Download started Please Wait Until Download'));
				var url = frappe.urllib.get_full_url(
					'/api/method/bhaskaragro.bhaskaragro.doctype.process_statement_of_account.process_statement_of_account.download_statements?'
					+ 'document_name='+encodeURIComponent(frm.doc.name))
				$.ajax({
					url: url,
					type: 'GET',
					success: function(result) {
						if(jQuery.isEmptyObject(result)){
							
							frappe.msgprint(__('No Records for these settings.'));
						}
						else{
							window.location = url;
						}
					}
				});
			
			});
		}
		
		}
	
	},
	onload: function(frm) {
		frm.set_query('currency', function(){
			return {
				filters: {
					'enabled': 1
				}
			}
		});
		if(frm.doc.__islocal){
			frm.set_value('from_date', frappe.datetime.add_months(frappe.datetime.get_today(), -1));
			frm.set_value('to_date', frappe.datetime.get_today());
		}
	},
	customer_collection: function(frm){
		frm.set_value('collection_name', '');
		if(frm.doc.customer_collection){
			frm.get_field('collection_name').set_label(frm.doc.customer_collection);
		}
	},
	frequency: function(frm){
		if(frm.doc.frequency != ''){
			frm.set_value('start_date', frappe.datetime.get_today());
		}
		else{
			frm.set_value('start_date', '');
		}
	},
	fetch_customers: function(frm){
		if(frm.doc.collection_name){
			frappe.call({
				method: "bhaskaragro.bhaskaragro.doctype.process_statement_of_account.process_statement_of_account.fetch_customers",
				args: {
					'customer_collection': frm.doc.customer_collection,
					'collection_name': frm.doc.collection_name,
					'primary_mandatory': frm.doc.primary_mandatory
				},
				callback: function(r) {
					if(!r.exc) {
						if(r.message.length){
							frm.clear_table('customers');
							for (const customer of r.message){
								var row = frm.add_child('customers');
								row.customer = customer.name;
								row.primary_email = customer.primary_email;
								row.billing_email = customer.billing_email;
							}
							frm.refresh_field('customers');
						}
						else{
							frappe.throw(__('No Customers found with selected options.'));
						}
					}
				}
			});
		}
		else {
			frappe.throw('Enter ' + frm.doc.customer_collection + ' name.');
		}
	}
});

frappe.ui.form.on('Process Statement Of Accounts Customer', {
	customer: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		if (!row.customer){
			return;
		}
		frappe.call({
			method: 'bhaskaragro.bhaskaragro.doctype.process_statement_of_account.process_statement_of_account.get_customer_emails',
			args: {
				'customer_name': row.customer,
				'primary_mandatory': frm.doc.primary_mandatory
			},
			callback: function(r){
				if(!r.exe){
					if(r.message.length){
						frappe.model.set_value(cdt, cdn, "primary_email", r.message[0])
						frappe.model.set_value(cdt, cdn, "billing_email", r.message[1])
					}
					else {
						return
					}
				}
			}
		})
	}
});
