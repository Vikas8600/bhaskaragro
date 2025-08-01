import base64
import frappe
from frappe.utils.pdf import get_pdf

@frappe.whitelist()
def attach_pdf_base64(doc, method=None):
    try:
        pdf_content = get_pdf(frappe.get_print("Sales Order", doc.name, print_format="Sales Order Confirmation Format"))

        # Encode to base64
        encoded_pdf = base64.b64encode(pdf_content).decode("utf-8")

        # Attach to custom fields
        doc.custom_pdf_base64 = encoded_pdf
        doc.custom_pdf_filename = f"{doc.name}.pdf"
        doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(f"Failed to generate PDF: {str(e)}", "Attach PDF Base64")
