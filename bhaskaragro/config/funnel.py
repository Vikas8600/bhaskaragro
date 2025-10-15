# import frappe
# import base64
# from frappe.utils.file_manager import save_file, remove_file

# @frappe.whitelist()
# def attach_irn_pdf(doc):
#     """
#     Generate PDF of Sales Invoice and attach it to custom_attachment field.
#     """
#     try:
#         # Generate PDF
#         pdf_data = frappe.get_print(
#             doc.doctype,
#             doc.name,
#             print_format="New Sales Bhaskara Format",
#             as_pdf=True
#         )

#         # Encode PDF data
#         file_content = base64.b64encode(pdf_data).decode()

#         # Create File document
#         file_doc = frappe.get_doc({
#             "doctype": "File",
#             "file_name": f"{doc.name}-EInvoice.pdf",
#             "attached_to_doctype": doc.doctype,
#             "attached_to_name": doc.name,
#             "is_private": 0,
#             "content": file_content,
#             "decode": True
#         }).insert()

#         # Update custom_attachment field with file URL
#         doc.db_set("custom_attachment", file_doc.file_url)

#     except Exception as e:
#         frappe.log_error(message=str(e), title=f"Attach IRN PDF - {doc.name}")


# @frappe.whitelist()
# def attach_missing_irn_pdfs(batch_size=50):
#     """
#     Attach PDFs for all Sales Invoices with IRN but no attachment yet.
#     Processes in batches of 'batch_size', starting from latest.
#     """
#     while True:
#         invoices = frappe.get_all(
#             "Sales Invoice",
#             filters={"irn": ["is", "set"], "custom_attachment": ["is", "not set"]},
#             pluck="name",
#             limit=batch_size,
#             order_by="creation desc"
#         )

#         if not invoices:
#             break  # all done

#         for name in invoices:
#             doc = frappe.get_doc("Sales Invoice", name)
#             attach_irn_pdf(doc)
        
#         # Optional: Commit after each batch to avoid long transactions
#         frappe.db.commit()


import frappe
import base64
from frappe.utils.file_manager import save_file, remove_file

@frappe.whitelist()
def attach_irn_pdf(doc):
    """
    Generate PDF of Sales Invoice and attach it to custom_attachment field.
    """
    try:
        # Generate PDF
        pdf_data = frappe.get_print(
            doc.doctype,
            doc.name,
            print_format="New Sales Bhaskara Format",
            as_pdf=True
        )

        # Encode PDF data
        file_content = base64.b64encode(pdf_data).decode()

        # Create File document
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{doc.name}-EInvoice.pdf",
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "is_private": 0,
            "content": file_content,
            "decode": True
        }).insert()

        # Update custom_attachment field with file URL
        doc.db_set("custom_attachment", file_doc.file_url)

    except Exception as e:
        frappe.log_error(message=str(e), title=f"Attach IRN PDF - {doc.name}")

@frappe.whitelist()
def attach_missing_irn_pdfs():
    """
    Attach PDFs for all Sales Invoices with IRN but no attachment yet.
    """
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"irn": ["is", "set"], "custom_attachment": ["is", "not set"]},
        pluck="name",
        limit=50,
        order_by="creation desc"
    )

    for name in invoices:
        doc = frappe.get_doc("Sales Invoice", name)
        attach_irn_pdf(doc)

