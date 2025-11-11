# Copyright (c) 2025, Dexciss Technology and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GeneralLedgerReport(Document):
	pass


import frappe
from frappe.utils import now_datetime, get_first_day, get_last_day, today
import calendar

def create_general_ledger_reports():
    """
    Scheduled task to create General Ledger Report for all customers
    Creates one document per customer with their GL report attached
    """
    try:
        # Get current month and year
        current_date = now_datetime()
        month_name = calendar.month_name[current_date.month]
        
        # Get all active customers
        customers = frappe.get_all("Customer", filters={"disabled": 0}, fields=["name"])
        
        if not customers:
            frappe.log_error("No active customers found", "General Ledger Report Scheduler")
            return
        
        created_count = 0
        error_count = 0
        
        for customer in customers:
            try:
                # Check if report already exists for this customer and month
                existing = frappe.db.exists("General Ledger Report", {
                    "customer": customer.name,
                    "month": month_name
                })
                
                if existing:
                    frappe.logger().info(f"Report already exists for {customer.name} - {month_name}")
                    continue
                
                # Generate the General Ledger Report
                report_file = generate_gl_report_for_customer(customer.name, month_name)
                
                if report_file:
                    # Create the General Ledger Report document
                    doc = frappe.get_doc({
                        "doctype": "General Ledger Report",
                        "customer": customer.name,
                        "month": month_name,
                        "general_ledger_report": report_file
                    })
                    doc.insert(ignore_permissions=True)
                    frappe.db.commit()
                    
                    created_count += 1
                    frappe.logger().info(f"Created GL Report for {customer.name}")
                else:
                    error_count += 1
                    frappe.log_error(f"Failed to generate report for {customer.name}", 
                                   "General Ledger Report Generation")
                    
            except Exception as e:
                error_count += 1
                frappe.log_error(f"Error creating report for {customer.name}: {str(e)}", 
                               "General Ledger Report Scheduler")
                continue
        
        # Log summary
        summary = f"General Ledger Reports Created: {created_count}, Errors: {error_count}"
        frappe.logger().info(summary)
        
    except Exception as e:
        frappe.log_error(str(e), "General Ledger Report Scheduler - Main")


def generate_gl_report_for_customer(customer_name, month_name):
    """
    Generate General Ledger report for a specific customer
    Returns the file URL/path to attach to the document
    """
    try:
        # Get month number from month name
        month_num = list(calendar.month_name).index(month_name)
        current_year = now_datetime().year
        
        # Get date range for the month
        from_date = get_first_day(f"{current_year}-{month_num:02d}-01")
        to_date = get_last_day(f"{current_year}-{month_num:02d}-01")
        
        # Prepare filters for General Ledger report
        filters = {
            "company": frappe.defaults.get_user_default("Company"),
            "from_date": from_date,
            "to_date": to_date,
            "party_type": "Customer",
            "party": [customer_name],
            "group_by": "Group by Voucher (Consolidated)",
        }
        
        # Generate the report
        report = frappe.get_doc("Report", "General Ledger")
        columns, data = report.get_data(
            filters=filters,
            as_dict=False
        )
        
        if not data:
            frappe.logger().info(f"No data found for customer {customer_name}")
            return None
        
        # Create Excel/PDF file
        file_name = f"GL_Report_{customer_name}_{month_name}_{current_year}.xlsx"
        file_path = create_report_file(columns, data, file_name)
        
        return file_path
        
    except Exception as e:
        frappe.log_error(f"Error generating GL report for {customer_name}: {str(e)}", 
                        "GL Report Generation")
        return None


def create_report_file(columns, data, file_name):
    """
    Create an Excel file from report data and save it
    """
    try:
        from frappe.utils.xlsxutils import make_xlsx
        import io
        
        # Prepare data for Excel
        xlsx_data = []
        
        # Add headers
        headers = [col.get("label") or col.get("fieldname") for col in columns]
        xlsx_data.append(headers)
        
        # Add data rows
        for row in data:
            xlsx_data.append(list(row))
        
        # Create Excel file
        xlsx_file = make_xlsx(xlsx_data, "General Ledger")
        
        # Save file
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "content": xlsx_file.getvalue(),
            "is_private": 1,
            "folder": "Home/Attachments"
        })
        file_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return file_doc.file_url
        
    except Exception as e:
        frappe.log_error(f"Error creating report file: {str(e)}", "Report File Creation")
        return None