import frappe
import requests
from urllib.parse import urlencode
from erpnext.accounts.utils import get_balance_on
import datetime


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
        "no_letterhead": 0,
        "letterhead": "Bhaskar Agro Bellary New",
    })

    pdf_url = f"{base_url}/api/method/frappe.utils.print_format.download_pdf?{params}"

    # Use TinyURL to shorten the link
    tinyurl_api = "https://tinyurl.com/api-create.php"
    response = requests.get(tinyurl_api, params={"url": pdf_url})

    short_url = response.text if response.status_code == 200 else pdf_url

    variables["pdf_url"] = short_url


    

@frappe.whitelist(allow_guest=True)
def unpaid_amount(variables):
   
    si = frappe.get_doc("Sales Invoice", variables['doc']['name'])

    unpaid_total = flt(get_balance_on(
        party_type="Customer",
        party=si.customer,
        company=si.company
    ))

    variables["total_unpaid"] = unpaid_total
    return variables


@frappe.whitelist(allow_guest=True)
def send_pdf_url_invoice(variables=None):
    doc = variables.get("doc")

    si_name = frappe.get_doc("Sales Invoice", doc.name)
    if not si_name:
        return {"error": "Missing Sales Invoice name"}

    base_url = frappe.utils.get_url()

    params = urlencode({
        "doctype": "Sales Invoice",
        "name": si_name.name,
        "format": "New Sales Bhaskara Format",
        "no_letterhead": 0,
        "letterhead": "Bhaskar Agro Bellary New",
    })

    pdf_url = f"{base_url}/api/method/frappe.utils.print_format.download_pdf?{params}"

    # Use TinyURL to shorten the link
    tinyurl_api = "https://tinyurl.com/api-create.php"
    response = requests.get(tinyurl_api, params={"url": pdf_url})

    short_url = response.text if response.status_code == 200 else pdf_url

    variables["pdf_url"] = short_url



@frappe.whitelist(allow_guest=True)
def send_pdf_url_po(variables=None):
    doc = variables.get("doc")

    po_name = frappe.get_doc("Purchase Order", doc.name)
    if not po_name:
        return {"error": "Missing Purchase Order name"}

    base_url = frappe.utils.get_url()

    params = urlencode({
        "doctype": "Purchase Order",
        "name": po_name.name,
        "format": "Bhaskar PO",
        "no_letterhead": 0,
        "letterhead": "Bhaskar Agro Bellary New",
    })

    pdf_url = f"{base_url}/api/method/frappe.utils.print_format.download_pdf?{params}"

    # Use TinyURL to shorten the link
    tinyurl_api = "https://tinyurl.com/api-create.php"
    response = requests.get(tinyurl_api, params={"url": pdf_url})

    short_url = response.text if response.status_code == 200 else pdf_url

    variables["pdf_url"] = short_url




@frappe.whitelist(allow_guest=True)
def send_pdf_url_pi(variables=None):
    doc = variables.get("doc")

    pi_name = frappe.get_doc("Purchase Invoice", doc.name)
    if not pi_name:
        return {"error": "Missing Purchase Invoice name"}

    base_url = frappe.utils.get_url()

    params = urlencode({
        "doctype": "Purchase Invoice",
        "name": pi_name.name,
        "format": "Bhaskar Purchase Invoice Format",
        "no_letterhead": 0,
        "letterhead": "Bhaskar Agro Bellary New",
    })

    pdf_url = f"{base_url}/api/method/frappe.utils.print_format.download_pdf?{params}"

    # Use TinyURL to shorten the link
    tinyurl_api = "https://tinyurl.com/api-create.php"
    response = requests.get(tinyurl_api, params={"url": pdf_url})

    short_url = response.text if response.status_code == 200 else pdf_url

    variables["pdf_url"] = short_url






@frappe.whitelist(allow_guest=True)
def send_pdf_url_ss(variables=None):
    doc = variables.get("doc")

    pi_name = frappe.get_doc("Salary Slip", doc.name)
    if not pi_name:
        return {"error": "Missing Salary Slip name"}

    base_url = frappe.utils.get_url()

    params = urlencode({
        "doctype": "Salary Slip",
        "name": pi_name.name,
        "format": "New Bhaskara Salary Slip",
        "no_letterhead": 0,
        "letterhead": "Bhaskar Agro Bellary New",
    })

    pdf_url = f"{base_url}/api/method/frappe.utils.print_format.download_pdf?{params}"

    # Use TinyURL to shorten the link
    tinyurl_api = "https://tinyurl.com/api-create.php"
    response = requests.get(tinyurl_api, params={"url": pdf_url})

    short_url = response.text if response.status_code == 200 else pdf_url

    variables["pdf_url"] = short_url


@frappe.whitelist()
def get_sales_invoice_context(invoice_name):
    variables = {}

    si = frappe.get_doc("Sales Invoice", invoice_name)

    # Format important date fields as strings
    variables["customer_name"] = si.customer_name
    variables["name"] = si.name
    variables["total"] = si.rounded_total
    variables["due_date"] = variables["due_date"] or datetime.date.today().strftime("%Y-%m-%d")
    variables["posting_date"] = variables["posting_date"] or datetime.date.today().strftime("%Y-%m-%d")
    variables["company"] = si.company

    # Defaults
    variables.update({
        "sales_person_1": "N/A",
        "whatsapp_no_1": "N/A",
        "sales_person_2": "N/A",
        "whatsapp_no_2": "N/A",
        "parent_sales_person": "N/A",
        "parent_sales_person_whatsapp_no": "N/A"
    })

    sales_team = si.get("sales_team", [])

    # Sales Person 1
    if len(sales_team) > 0 and sales_team[0].sales_person:
        sp1_name = sales_team[0].sales_person
        try:
            sp1_doc = frappe.get_doc("Sales Person", sp1_name)
            emp1 = frappe.get_doc("Employee", sp1_doc.employee) if sp1_doc.employee else None

            variables["sales_person_1"] = sp1_doc.name
            variables["whatsapp_no_1"] = (
                (emp1.cell_number or emp1.phone) if emp1 and (emp1.cell_number or emp1.phone) else "N/A"
            )

            # Parent Sales Person
            if sp1_doc.parent_sales_person:
                try:
                    parent_doc = frappe.get_doc("Sales Person", sp1_doc.parent_sales_person)
                    parent_emp = frappe.get_doc("Employee", parent_doc.employee) if parent_doc.employee else None

                    variables["parent_sales_person"] = parent_doc.name
                    variables["parent_sales_person_whatsapp_no"] = (
                        (parent_emp.cell_number or parent_emp.phone)
                        if parent_emp and (parent_emp.cell_number or parent_emp.phone)
                        else "N/A"
                    )

                except Exception as e:
                    frappe.log_error(f"Error fetching parent of {sp1_name}: {str(e)}", "Funnel Task")

        except Exception as e:
            frappe.log_error(f"Error processing Sales Person 1 ({sp1_name}): {str(e)}", "Funnel Task")

    # Sales Person 2
    if len(sales_team) > 1 and sales_team[1].sales_person:
        sp2_name = sales_team[1].sales_person
        try:
            sp2_doc = frappe.get_doc("Sales Person", sp2_name)
            emp2 = frappe.get_doc("Employee", sp2_doc.employee) if sp2_doc.employee else None

            variables["sales_person_2"] = sp2_doc.name
            variables["whatsapp_no_2"] = (
                (emp2.cell_number or emp2.phone) if emp2 and (emp2.cell_number or emp2.phone) else "N/A"
            )

        except Exception as e:
            frappe.log_error(f"Error processing Sales Person 2 ({sp2_name}): {str(e)}", "Funnel Task")

    # Total unpaid (all invoices for the same customer that are unpaid)
    unpaid_total = frappe.db.sql(
        """
        SELECT SUM(outstanding_amount)
        FROM `tabSales Invoice`
        WHERE customer = %s
          AND docstatus = 1
          AND outstanding_amount > 0
          AND status = 'Unpaid'
        """,
        (si.customer,),
        as_list=True,
    )[0][0] or 0

    variables["total_unpaid"] = unpaid_total

    return variables



def safe_date_format(date_val):
    """Return date as YYYY-MM-DD string, or None if invalid"""
    if not date_val:
        return None

    # If already a datetime.date object
    if isinstance(date_val, (datetime.date, datetime.datetime)):
        return date_val.strftime("%Y-%m-%d")

    # If string, try to parse
    if isinstance(date_val, str):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(date_val, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        # If no format matched
        frappe.log_error(f"Invalid date format: {date_val}", "Funnel Task")
        return None

    return None
