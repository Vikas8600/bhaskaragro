import frappe
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file

def attach_sales_order_pdf(so_name):
    so = frappe.get_doc("Sales Order", so_name)

    pdf_content = get_pdf(
        frappe.get_print(
            "Sales Order",
            so.name,
            "Sales Order Confirmation Format",  
            as_pdf=True
        )
    )

    # Save PDF file to the Sales Order's attachments
    filename = f"{so.name}-Sales-Order-Confirmation.pdf"
    save_file(filename, pdf_content, "Sales Order", so.name, is_private=0)

    return filename
