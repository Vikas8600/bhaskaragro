

# File: your_custom_app/your_custom_app/overrides/sales_invoice.py

import frappe
from frappe import _

def generate_and_attach_invoice_pdf(doc):
    """Generate and attach PDF of Sales Invoice after IRN generation."""
    if not doc.irn:
        return
    
    try:
        # Generate PDF with e-Invoice print format
        pdf_data = frappe.get_print(
            "Sales Invoice",
            doc.name,
            print_format="New Sales Bhaskara Format",
            as_pdf=True
        )
        
        file_name = f"{doc.name}-einvoice.pdf"
        
        # Delete old file if exists
        existing_files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Sales Invoice",
                "attached_to_name": doc.name,
                "file_name": file_name
            },
            pluck="name"
        )
        
        for existing_file in existing_files:
            frappe.delete_doc("File", existing_file, ignore_permissions=True)
        
        # Create new file
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": doc.name,
            "content": pdf_data,
            "is_private": 0
        })
        file_doc.save(ignore_permissions=True)
        
        # Update custom_attachment field
        frappe.db.set_value(
            "Sales Invoice",
            doc.name,
            "custom_attachment",
            file_doc.file_url,
            update_modified=False
        )
        
        frappe.logger().info(f"✅ Generated e-Invoice PDF for {doc.name}")
        
    except Exception as e:
        frappe.log_error(
            title=_("Failed to generate e-Invoice PDF for {0}").format(doc.name),
            message=frappe.get_traceback()
        )


def after_irn_generated(doc, method=None):
    """
    Called after IRN is generated and saved to database.
    This runs in the background via queue.
    """
    # Reload doc to get latest IRN value
    doc.reload()
    
    if not doc.irn:
        return
    
    # Generate PDF in background
    frappe.enqueue(
        generate_and_attach_invoice_pdf,
        queue="short",
        timeout=120,
        doc=doc
    )
    
# import frappe
# from frappe import _


# def generate_and_attach_invoice_pdf(doc):
#     """
#     Generate PDF of Sales Invoice with custom format and attach it to the document.
#     This function is called after IRN generation.
#     """
#     # Only proceed if IRN exists
#     if not doc.irn:
#         return
    
#     try:
#         # Generate PDF of Sales Invoice with custom format
#         pdf_data = frappe.get_print(
#             "Sales Invoice",
#             doc.name,
#             print_format="New Sales Bhaskara Format",
#             as_pdf=True
#         )
        
#         # Save file and attach to Sales Invoice
#         file_name = f"{doc.name}-einvoice.pdf"
        
#         # Check if file already exists and delete it
#         existing_files = frappe.get_all(
#             "File",
#             filters={
#                 "attached_to_doctype": "Sales Invoice",
#                 "attached_to_name": doc.name,
#                 "file_name": file_name
#             },
#             pluck="name"
#         )
        
#         for existing_file in existing_files:
#             frappe.delete_doc("File", existing_file, ignore_permissions=True)
        
#         # Create new file
#         file_doc = frappe.get_doc({
#             "doctype": "File",
#             "file_name": file_name,
#             "attached_to_doctype": "Sales Invoice",
#             "attached_to_name": doc.name,
#             "content": pdf_data,
#             "is_private": 0  # Set to 1 if you want it private
#         })
#         file_doc.save(ignore_permissions=True)
        
#         # Update custom_attachment field with file url
#         doc.db_set("custom_attachment", file_doc.file_url, update_modified=False)
        
#         frappe.logger().info(f"PDF generated and attached for Sales Invoice {doc.name}")
        
#     except Exception as e:
#         frappe.logger().error(f"Error generating PDF for Sales Invoice {doc.name}: {str(e)}")
#         # Don't raise - we don't want to break the e-invoice flow
#         frappe.log_error(
#             title=_("Failed to generate PDF for Sales Invoice {0}").format(doc.name),
#             message=frappe.get_traceback()
#         )


# def on_update_after_submit(doc, method):
#     """
#     Hook function that triggers when Sales Invoice is updated after submit.
#     This includes when IRN is set.
#     """
#     # Check if IRN was just added (comparing with DB value)
#     db_irn = frappe.db.get_value("Sales Invoice", doc.name, "irn")
    
#     # If IRN exists in current doc but process hasn't run yet
#     if doc.irn and doc.irn == db_irn:
#         # Check if attachment already exists
#         existing_attachment = frappe.db.get_value(
#             "Sales Invoice", 
#             doc.name, 
#             "custom_attachment"
#         )
        
#         # Only generate if attachment doesn't exist
#         if not existing_attachment:
#             generate_and_attach_invoice_pdf(doc)