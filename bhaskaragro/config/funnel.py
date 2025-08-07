import frappe
import requests
from urllib.parse import urlencode

@frappe.whitelist(allow_guest=True)
def send_pdf_url(variables=None):
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
        "letterhead": "Bhaskar Agro Bellary New",
    })

    pdf_url = f"{base_url}/api/method/frappe.utils.print_format.download_pdf?{params}"

    # Use TinyURL to shorten the link
    tinyurl_api = "https://tinyurl.com/api-create.php"
    response = requests.get(tinyurl_api, params={"url": pdf_url})

    short_url = response.text if response.status_code == 200 else pdf_url

    variables["pdf_url"] = short_url




@frappe.whitelist(allow_guest=True)
def send_pdf_url(variables=None):
    doc = variables.get("doc")

    si_name = frappe.get_doc("Sales Invoice", doc.name)
    if not si_name:
        return {"error": "Missing Sales Invoice name"}

    base_url = frappe.utils.get_url()

    params = urlencode({
        "doctype": "Sales Invoice",
        "name": si_name.name,
        "format": "Sales Order Confirmation Format",
        "no_letterhead": 0
        "letterhead": "Bhaskar Agro Bellary New",
    })

    pdf_url = f"{base_url}/api/method/frappe.utils.print_format.download_pdf?{params}"

    # Use TinyURL to shorten the link
    tinyurl_api = "https://tinyurl.com/api-create.php"
    response = requests.get(tinyurl_api, params={"url": pdf_url})

    short_url = response.text if response.status_code == 200 else pdf_url

    variables["pdf_url"] = short_url
