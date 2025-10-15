


# import frappe
# from frappe.core.doctype.file.file import create_new_file

# def attach_irn_pdf(doc):
#     pdf_data = frappe.get_print(doc.doctype, doc.name, print_format="New Sales Bhaskara Format", as_pdf=True)
#     file = create_new_file(
#         content=pdf_data,
#         doctype=doc.doctype,
#         docname=doc.name,
#         is_private=1,
#         df="custom_attachment",
#         filename=f"{doc.name}-EInvoice.pdf"
#     )
#     doc.db_set("custom_attachment", file.file_url)
#     frappe.db.commit()

# def attach_missing_irn_pdfs():
#     invoices = frappe.get_all(
#         "Sales Invoice",
#         filters={"irn": ["is", "set"], "custom_attachment": ["is", "not set"]},
#         pluck="name"
#     )
#     for name in invoices:
#         doc = frappe.get_doc("Sales Invoice", name)
#         attach_irn_pdf(doc)


import frappe
import base64
from frappe.utils.file_manager import save_file, remove_file

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
            "is_private": 1,
            "content": file_content,
            "decode": True
        }).insert()

        # Update custom_attachment field with file URL
        doc.db_set("custom_attachment", file_doc.file_url)

    except Exception as e:
        frappe.log_error(message=str(e), title=f"Attach IRN PDF - {doc.name}")

def attach_missing_irn_pdfs():
    """
    Attach PDFs for all Sales Invoices with IRN but no attachment yet.
    """
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"irn": ["is", "set"], "custom_attachment": ["is", "not set"]},
        pluck="name"
    )

    for name in invoices:
        doc = frappe.get_doc("Sales Invoice", name)
        attach_irn_pdf(doc)
