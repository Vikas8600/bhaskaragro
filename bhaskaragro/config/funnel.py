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
import hashlib
import string
import random
from urllib.parse import urlencode

@frappe.whitelist(allow_guest=True)
def send_pdf_url(variables=None):
    try:
        if not variables or not variables.get("name"):
            frappe.throw("Document reference not provided in variables")
        
        so_name = frappe.get_doc("Sales Order", variables["name"])
        
        if not so_name:
            return {"error": "Missing Sales Order name"}
        
        # Base site URL
        base_url = frappe.utils.get_url()
        
        # Create or get existing short link
        short_code = get_or_create_short_link(so_name.name)
        
        # Short URL
        short_url = f"{base_url}/s/{short_code}"
        
        variables["pdf_url"] = short_url
        variables["full_pdf_url"] = get_full_pdf_url(base_url, so_name.name) 
        
        return variables
    
    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="Error in send_pdf_url"
        )
        return {"error": "Failed to generate PDF URL"}

def get_or_create_short_link(so_name):
    """Create or retrieve existing short link for Sales Order"""
    
    # Check if short link already exists
    existing_link = frappe.db.get_value("Short Link", 
                                      filters={"reference_doctype": "Sales Order", 
                                              "reference_name": so_name},
                                      fieldname="short_code")
    
    if existing_link:
        return existing_link
    
    # Generate new short code
    short_code = generate_short_code()
    
    # Ensure uniqueness
    while frappe.db.exists("Short Link", {"short_code": short_code}):
        short_code = generate_short_code()
    
    # Create Short Link document
    short_link_doc = frappe.get_doc({
        "doctype": "Short Link",
        "short_code": short_code,
        "reference_doctype": "Sales Order",
        "reference_name": so_name,
        "created_by": frappe.session.user
    })
    short_link_doc.insert(ignore_permissions=True)
    
    return short_code

def generate_short_code(length=6):
    """Generate random short code"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_full_pdf_url(base_url, so_name):
    """Generate the full PDF URL"""
    params = urlencode({
        "doctype": "Sales Order",
        "name": so_name,
        "format": "Sales Order Confirmation Format",
        "no_letterhead": 0
    })
    return f"{base_url}/print?{params}"

@frappe.whitelist(allow_guest=True)
def redirect_short_link(short_code):
    """Handle short link redirection"""
    
    short_link = frappe.get_doc("Short Link", {"short_code": short_code})
    
    if not short_link:
        frappe.throw("Invalid short link")
    
    # Get the Sales Order
    so_name = short_link.reference_name
    base_url = frappe.utils.get_url()
    
    # Generate full PDF URL
    full_url = get_full_pdf_url(base_url, so_name)
    
    # Redirect to the PDF
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = full_url
