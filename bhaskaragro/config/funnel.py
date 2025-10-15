


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
            "is_private": 1,
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
        limit=50 
    )

    for name in invoices:
        doc = frappe.get_doc("Sales Invoice", name)
        attach_irn_pdf(doc)


import frappe
from frappe.utils import now_datetime, add_to_date

@frappe.whitelist()
def attach_sales_invoice_pdf_later(doc_name):
    """
    Enqueue a job to attach PDF 5 minutes later.
    """
    frappe.enqueue_in(
        minutes=5,
        queue="long",
        job_name=f"attach_pdf_{doc_name}",
        method="bhaskaragro.config.funnel._attach_sales_invoice_pdf",
        doc_name=doc_name
    )

def _attach_sales_invoice_pdf(doc_name):
    """
    Actual function to generate PDF and attach to Sales Invoice.
    """
    doc = frappe.get_doc("Sales Invoice", doc_name)
    
    # Generate PDF
    pdf_data = frappe.get_print(
        "Sales Invoice",
        doc.name,
        print_format="New Sales Bhaskara Format",
        as_pdf=True
    )
    
    # Save file and attach
    file_name = f"{doc.name}-confirmation.pdf"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "attached_to_doctype": "Sales Invoice",
        "attached_to_name": doc.name,
        "content": pdf_data
    })
    file_doc.save(ignore_permissions=True)
    
    # Update custom_attachment field
    doc.db_set("custom_attachment", file_doc.file_url)
    frappe.logger().info(f"PDF attached for Sales Invoice {doc_name}")
