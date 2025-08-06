# import frappe

# @frappe.whitelist(allow_guest=True)
# def send_pdf_url(variables=None):
#     try:
#         if not variables or not variables.get("name"):
#             frappe.throw("Document reference not provided in variables")

#         so_name = frappe.get_doc("Sales Order", variables["name"])

#         if not so_name:
#             return {"error": "Missing Sales Order name"}

#         # Base site URL
#         base_url = frappe.utils.get_url()

#         # Proper query parameters for the print URL
#         params = urlencode({
#             "doctype": "Sales Order",
#             "name": so_name.name,
#             "format": "Sales Order Confirmation Format",
#             "no_letterhead": 0
#         })

#         # Full PDF link
#         pdf_url = f"{base_url}/print?{params}"

#         variables["pdf_url"] = pdf_url

#         return variables

#     except Exception:
#         frappe.log_error(
#             message=frappe.get_traceback(),
#             title="Error in send_pdf_url"
#         )
#         return {"error": "Failed to generate PDF URL"}



import frappe
from urllib.parse import urlencode
from werkzeug.utils import redirect

@frappe.whitelist(allow_guest=True)
def send_pdf_url(variables=None):
    """
    Return a short PDF URL in variables["pdf_url"].
    """
    try:
        if not variables or not variables.get("name"):
            frappe.throw("Document reference not provided in variables")

        so_name = frappe.get_doc("Sales Order", variables["name"])
        if not so_name:
            return {"error": "Missing Sales Order name"}

        # Base site URL
        base_url = frappe.utils.get_url()


        # Short link that calls our own API
        short_link = f"{base_url}/api/method/bhaskaragro.config.funnel.get_pdf?name={so_name.name}"

        variables["pdf_url"] = short_link
        return variables

    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="Error in send_pdf_url"
        )
        return {"error": "Failed to generate PDF URL"}


@frappe.whitelist(allow_guest=True)
def get_pdf(name):
   
    if not name:
        frappe.throw("Sales Order name is required")

    params = urlencode({
        "doctype": "Sales Order",
        "name": name,
        "format": "Sales Order Confirmation Format",
        "no_letterhead": 0,
        "letterhead": "Hind Header",
        "settings": "{}",
        "_lang": "en"
    })

    long_url = f"/api/method/frappe.utils.print_format.download_pdf?{params}"
    return redirect(long_url)  # Werkzeug redirect