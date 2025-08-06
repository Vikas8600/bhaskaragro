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
import requests
from urllib.parse import urlencode

@frappe.whitelist(allow_guest=True)
def send_pdf_url(variables):
    doc = variables.get("doc")

    so_name = frappe.get_doc("Sales Order", doc.name)
    if not so_name:
        return {"error": "Missing Sales Order name"}

    base_url = frappe.utils.get_url()

    params = urlencode({
        "doctype": "Sales Order",
        "name": so_name.name,
        "format": "Sales Order Confirmation Format",
        "no_letterhead": 0
    })

    pdf_url = f"{base_url}/print?{params}"

    # Use TinyURL to shorten the link
    tinyurl_api = "https://tinyurl.com/api-create.php"
    response = requests.get(tinyurl_api, params={"url": pdf_url})

    short_url = response.text if response.status_code == 200 else pdf_url

    variables["pdf_url"] = short_url
