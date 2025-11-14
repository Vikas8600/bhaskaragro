import frappe
from frappe import _
from frappe.utils import today, get_first_day, get_last_day, add_months, getdate
from frappe.utils.pdf import get_pdf
import calendar

@frappe.whitelist()
def generate_monthly_gl_reports():
    """
    Scheduled function to generate General Ledger reports for all customers
    Runs on the 1st day of every month for the previous month
    """
    try:
        # Get previous month's date range
        current_date = getdate(today())
        first_day_current_month = get_first_day(current_date)
        last_day_previous_month = add_months(first_day_current_month, -1)
        first_day_previous_month = get_first_day(last_day_previous_month)

        # Get month name and year
        month_name = calendar.month_name[last_day_previous_month.month]
        year = last_day_previous_month.year

        frappe.logger().info(f"Starting GL Report generation for {month_name} {year}")

        # Get all active customers
        customers = frappe.get_all(
            "Customer",
            filters={"disabled": 0},
            fields=["name", "customer_name"]
        )

        if not customers:
            frappe.logger().warning("No active customers found")
            return

        success_count = 0
        error_count = 0

        # Generate report for each customer
        for customer in customers:
            try:
                generate_and_store_gl_report(
                    customer=customer.name,
                    customer_name=customer.customer_name,
                    from_date=first_day_previous_month,
                    to_date=last_day_previous_month,
                    month=month_name,
                    year=year
                )
                success_count += 1
                frappe.db.commit()

            except Exception as e:
                error_count += 1
                frappe.logger().error(f"Error generating GL report for {customer.name}: {str(e)}")
                frappe.db.rollback()

        frappe.logger().info(
            f"GL Report generation completed. Success: {success_count}, Errors: {error_count}"
        )

    except Exception as e:
        frappe.logger().error(f"Error in generate_monthly_gl_reports: {str(e)}")
        frappe.db.rollback()


def generate_and_store_gl_report(customer, customer_name, from_date, to_date, month, year):
    """
    Generate General Ledger report for a specific customer and store it
    """

    # Check if report already exists for this customer and month
    existing_report = frappe.db.exists(
        "General Ledger Report List",
        {"customer": customer, "month": month, "name": f"{month}-{year}"}
    )

    if existing_report:
        frappe.logger().info(f"Report already exists for {customer} - {month} {year}")
        return

    company = frappe.defaults.get_user_default("Company")
    if not company:
        frappe.throw(_("No default Company found for user"))

    # Prepare filters for General Ledger report
    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "party_type": "Customer",
        "party": customer,
        "group_by": "Group by Voucher (Consolidated)",
        "include_dimensions": 1,
        "show_opening_entries": 1,
        "show_cancelled_entries": 0,
        "show_net_values_in_party_account": 0
    }

    # Generate the report HTML
    report_html = get_general_ledger_html(filters, customer_name, month, year)

    # Convert HTML to PDF
    pdf_data = get_pdf(report_html)

    # Create new General Ledger Report List document
    gl_report_doc = frappe.get_doc({
        "doctype": "General Ledger Report List",
        "customer": customer,
        "month": month
    })

    gl_report_doc.insert(ignore_permissions=True)

    # Attach the PDF file
    file_name = f"GL_Report_{customer}_{month}_{year}.pdf"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "attached_to_doctype": "General Ledger Report List",
        "attached_to_name": gl_report_doc.name,
        "attached_to_field": "general_ledger_report",
        "is_private": 1,
        "content": pdf_data
    })
    file_doc.save(ignore_permissions=True)

    # Update the document with file URL
    gl_report_doc.general_ledger_report = file_doc.file_url
    gl_report_doc.save(ignore_permissions=True)

    frappe.logger().info(f"Successfully generated GL report for {customer} - {month} {year}")


def get_general_ledger_html(filters, customer_name, month, year):
    """
    Generate HTML content for General Ledger report with guaranteed data retrieval
    """

    try:
        report = frappe.get_doc("Report", "General Ledger")

        # Try to execute the report directly (standard ERPNext method)
        execute_fn = frappe.get_attr(report.report_module + ".execute")
        columns, data = execute_fn(filters)

        frappe.logger().info(f"Fetched {len(data)} rows for {customer_name} ({month} {year})")

    except Exception as e:
        frappe.logger().error(f"Error fetching GL data: {str(e)}")
        columns, data = [], []

    if not data:
        return f"""
        <html><body>
        <h2>General Ledger Report</h2>
        <p>No data found for {customer_name} ({month} {year})</p>
        </body></html>
        """

    # Build HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                font-size: 10pt;
                margin: 20px;
            }}
            h1 {{
                text-align: center;
                color: #333;
                font-size: 18pt;
                margin-bottom: 5px;
            }}
            h2 {{
                text-align: center;
                color: #666;
                font-size: 14pt;
                margin-top: 5px;
                margin-bottom: 20px;
            }}
            table, th, td {{
                border: 1px solid #000;
                border-collapse: collapse;
                padding: 6px;
            }}
            th {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            .number {{
                text-align: right;
            }}
            .total-row {{
                font-weight: bold;
                background-color: #f9f9f9;
            }}
        </style>
    </head>
    <body>
        <h1>General Ledger Report</h1>
        <h2>{customer_name} - {month} {year}</h2>
        
        <table>
            <thead>
                <tr>
    """

    # Add column headers
    for col in columns:
        html += f"<th>{col.get('label', '')}</th>"

    html += "</tr></thead><tbody>"

    # Add data rows
    for row in data:
        is_total_row = isinstance(row, dict) and row.get('is_total_row', False)
        row_class = ' class="total-row"' if is_total_row else ''
        html += f"<tr{row_class}>"

        for i, col in enumerate(columns):
            fieldname = col.get('fieldname')
            cell_value = ""
            if isinstance(row, (list, tuple)):
                if i < len(row):
                    cell_value = row[i]
            elif isinstance(row, dict):
                cell_value = row.get(fieldname, '')

            cell_class = ' class="number"' if col.get('fieldtype') in ['Currency', 'Float', 'Int'] else ''

            if col.get('fieldtype') == 'Currency' and cell_value:
                try:
                    cell_value = f"{float(cell_value):,.2f}"
                except:
                    pass

            html += f"<td{cell_class}>{cell_value or ''}</td>"

        html += "</tr>"

    html += "</tbody></table></body></html>"
    return html


@frappe.whitelist()
def manual_generate_gl_report(customer, month, year):
    """
    Manually generate GL report for a specific customer and month
    """
    try:
        if not frappe.has_permission("General Ledger Report List", "create"):
            frappe.throw(_("Not permitted"), frappe.PermissionError)

        # Parse month and year
        month_num = list(calendar.month_name).index(month)
        year = int(year)

        from_date = getdate(f"{year}-{month_num:02d}-01")
        to_date = get_last_day(from_date)

        customer_name = frappe.db.get_value("Customer", customer, "customer_name")

        if not customer_name:
            frappe.throw(_("Customer {0} not found").format(customer))

        generate_and_store_gl_report(
            customer=customer,
            customer_name=customer_name,
            from_date=from_date,
            to_date=to_date,
            month=month,
            year=year
        )

        frappe.db.commit()

        return {
            "success": True,
            "message": _("General Ledger report generated successfully for {0}").format(customer_name),
            "report_name": f"{month}-{year}"
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error in manual_generate_gl_report: {str(e)}")
        frappe.throw(_("Error generating report: {0}").format(str(e)))


# import frappe
# from frappe import _
# from frappe.utils import today, get_first_day, get_last_day, add_months, getdate
# from frappe.utils.pdf import get_pdf
# import calendar

# @frappe.whitelist()
# def generate_monthly_gl_reports():
#     """
#     Scheduled function to generate General Ledger reports for all customers
#     Runs on the 1st day of every month for the CURRENT month
#     """
#     try:
#         # Get current month's date range
#         current_date = getdate(today())
#         first_day_current_month = get_first_day(current_date)
#         last_day_current_month = get_last_day(current_date)

#         # Get month name and year
#         month_name = calendar.month_name[current_date.month]
#         year = current_date.year

#         frappe.logger().info(f"Starting GL Report generation for {month_name} {year}")

#         # Get all active customers
#         customers = frappe.get_all(
#             "Customer",
#             filters={"disabled": 0},
#             fields=["name", "customer_name"]
#         )

#         if not customers:
#             frappe.logger().warning("No active customers found")
#             return

#         success_count = 0
#         error_count = 0

#         # Generate report for each customer
#         for customer in customers:
#             try:
#                 generate_and_store_gl_report(
#                     customer=customer.name,
#                     customer_name=customer.customer_name,
#                     from_date=first_day_current_month,
#                     to_date=last_day_current_month,
#                     month=month_name,
#                     year=year
#                 )
#                 success_count += 1
#                 frappe.db.commit()

#             except Exception as e:
#                 error_count += 1
#                 frappe.logger().error(f"Error generating GL report for {customer.name}: {str(e)}")
#                 frappe.db.rollback()

#         frappe.logger().info(
#             f"GL Report generation completed. Success: {success_count}, Errors: {error_count}"
#         )

#     except Exception as e:
#         frappe.logger().error(f"Error in generate_monthly_gl_reports: {str(e)}")
#         frappe.db.rollback()


# def generate_and_store_gl_report(customer, customer_name, from_date, to_date, month, year):
#     """
#     Generate General Ledger report for a specific customer and store it
#     """

#     # Check if report already exists for this customer and month
#     existing_report = frappe.db.exists(
#         "General Ledger Report List",
#         {"customer": customer, "month": month, "year": year}
#     )

#     if existing_report:
#         frappe.logger().info(f"Report already exists for {customer} - {month} {year}")
#         return

#     company = frappe.defaults.get_user_default("Company")
#     if not company:
#         frappe.throw(_("No default Company found for user"))

#     # Prepare filters for General Ledger report
#     filters = {
#         "company": company,
#         "from_date": from_date,
#         "to_date": to_date,
#         "party_type": "Customer",
#         "party": customer,
#         "group_by": "Group by Voucher (Consolidated)",
#         "include_dimensions": 1,
#         "show_opening_entries": 1,
#         "show_cancelled_entries": 0,
#         "show_net_values_in_party_account": 0
#     }

#     # Generate the report HTML
#     report_html = get_general_ledger_html(filters, customer, customer_name, month, year)

#     # Convert HTML to PDF
#     pdf_data = get_pdf(report_html)

#     # Create new General Ledger Report List document
#     gl_report_doc = frappe.get_doc({
#         "doctype": "General Ledger Report List",
#         "customer": customer,
#         "month": month,
#         "year": year
#     })

#     gl_report_doc.insert(ignore_permissions=True)

#     # Attach the PDF file
#     file_name = f"GL_Report_{customer}_{month}_{year}.pdf"
#     file_doc = frappe.get_doc({
#         "doctype": "File",
#         "file_name": file_name,
#         "attached_to_doctype": "General Ledger Report List",
#         "attached_to_name": gl_report_doc.name,
#         "attached_to_field": "general_ledger_report",
#         "is_private": 1,
#         "content": pdf_data
#     })
#     file_doc.save(ignore_permissions=True)

#     # Update the document with file URL
#     gl_report_doc.general_ledger_report = file_doc.file_url
#     gl_report_doc.save(ignore_permissions=True)

#     frappe.logger().info(f"Successfully generated GL report for {customer} - {month} {year}")


# def get_general_ledger_html(filters, customer, customer_name, month, year):
#     """
#     Generate HTML content for General Ledger report with guaranteed data retrieval
#     """

#     columns = []
#     data = []

#     try:
#         # First, try the standard report execution
#         report = frappe.get_doc("Report", "General Ledger")
#         execute_fn = frappe.get_attr(report.report_module + ".execute")
#         columns, data = execute_fn(filters)

#         frappe.logger().info(f"Standard method: Fetched {len(data)} rows for {customer_name} ({month} {year})")

#     except Exception as e:
#         frappe.logger().error(f"Error with standard method: {str(e)}")

#     # If no data found, try direct database query with quote handling
#     if not data:
#         frappe.logger().info(f"Trying direct query for customer: {customer}")
        
#         try:
#             # Query GL entries directly, handling potential quote issues
#             gl_entries = frappe.db.sql("""
#                 SELECT 
#                     posting_date,
#                     account,
#                     against_voucher_type as voucher_type,
#                     voucher_no,
#                     against_voucher,
#                     remarks,
#                     debit,
#                     credit,
#                     debit - credit as balance
#                 FROM `tabGL Entry`
#                 WHERE 
#                     company = %(company)s
#                     AND posting_date BETWEEN %(from_date)s AND %(to_date)s
#                     AND party_type = 'Customer'
#                     AND (party = %(party)s OR party = %(party_quoted)s)
#                     AND is_cancelled = 0
#                 ORDER BY posting_date, creation
#             """, {
#                 'company': filters['company'],
#                 'from_date': filters['from_date'],
#                 'to_date': filters['to_date'],
#                 'party': customer,
#                 'party_quoted': f'"{customer}"'
#             }, as_dict=1)

#             if gl_entries:
#                 frappe.logger().info(f"Direct query: Found {len(gl_entries)} entries for {customer}")
                
#                 # Create columns for direct query
#                 columns = [
#                     {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date"},
#                     {"label": "Account", "fieldname": "account", "fieldtype": "Data"},
#                     {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data"},
#                     {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Data"},
#                     {"label": "Against Voucher", "fieldname": "against_voucher", "fieldtype": "Data"},
#                     {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Text"},
#                     {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency"},
#                     {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency"},
#                     {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency"}
#                 ]
                
#                 data = gl_entries
                
#                 # Calculate running balance
#                 running_balance = 0
#                 for entry in data:
#                     running_balance += (entry.get('debit', 0) - entry.get('credit', 0))
#                     entry['balance'] = running_balance

#             else:
#                 frappe.logger().warning(f"No GL entries found for {customer} (tried both with and without quotes)")

#         except Exception as e:
#             frappe.logger().error(f"Error in direct query: {str(e)}")

#     if not data:
#         return f"""
#         <html><body>
#         <h2>General Ledger Report</h2>
#         <p>No data found for {customer_name} ({month} {year})</p>
#         <p>Customer ID searched: {customer}</p>
#         </body></html>
#         """

#     # Build HTML
#     html = f"""
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <meta charset="utf-8">
#         <style>
#             body {{
#                 font-family: Arial, sans-serif;
#                 font-size: 10pt;
#                 margin: 20px;
#             }}
#             h1 {{
#                 text-align: center;
#                 color: #333;
#                 font-size: 18pt;
#                 margin-bottom: 5px;
#             }}
#             h2 {{
#                 text-align: center;
#                 color: #666;
#                 font-size: 14pt;
#                 margin-top: 5px;
#                 margin-bottom: 20px;
#             }}
#             table {{
#                 width: 100%;
#                 border-collapse: collapse;
#                 margin-top: 20px;
#             }}
#             th, td {{
#                 border: 1px solid #000;
#                 padding: 6px;
#                 text-align: left;
#             }}
#             th {{
#                 background-color: #f0f0f0;
#                 font-weight: bold;
#             }}
#             .number {{
#                 text-align: right;
#             }}
#             .total-row {{
#                 font-weight: bold;
#                 background-color: #f9f9f9;
#             }}
#         </style>
#     </head>
#     <body>
#         <h1>General Ledger Report</h1>
#         <h2>{customer_name} - {month} {year}</h2>
        
#         <table>
#             <thead>
#                 <tr>
#     """

#     # Add column headers
#     for col in columns:
#         html += f"<th>{col.get('label', '')}</th>"

#     html += "</tr></thead><tbody>"

#     # Add data rows
#     for row in data:
#         is_total_row = isinstance(row, dict) and row.get('is_total_row', False)
#         row_class = ' class="total-row"' if is_total_row else ''
#         html += f"<tr{row_class}>"

#         for i, col in enumerate(columns):
#             fieldname = col.get('fieldname')
#             cell_value = ""
            
#             if isinstance(row, (list, tuple)):
#                 if i < len(row):
#                     cell_value = row[i]
#             elif isinstance(row, dict):
#                 cell_value = row.get(fieldname, '')

#             cell_class = ' class="number"' if col.get('fieldtype') in ['Currency', 'Float', 'Int'] else ''

#             if col.get('fieldtype') == 'Currency' and cell_value:
#                 try:
#                     cell_value = f"{float(cell_value):,.2f}"
#                 except:
#                     pass
#             elif col.get('fieldtype') == 'Date' and cell_value:
#                 try:
#                     cell_value = str(cell_value)
#                 except:
#                     pass

#             html += f"<td{cell_class}>{cell_value or ''}</td>"

#         html += "</tr>"

#     html += "</tbody></table></body></html>"
#     return html


# @frappe.whitelist()
# def manual_generate_gl_report(customer, month, year):
#     """
#     Manually generate GL report for a specific customer and month
#     """
#     try:
#         if not frappe.has_permission("General Ledger Report List", "create"):
#             frappe.throw(_("Not permitted"), frappe.PermissionError)

#         # Parse month and year
#         month_num = list(calendar.month_name).index(month)
#         year = int(year)

#         from_date = getdate(f"{year}-{month_num:02d}-01")
#         to_date = get_last_day(from_date)

#         customer_name = frappe.db.get_value("Customer", customer, "customer_name")

#         if not customer_name:
#             frappe.throw(_("Customer {0} not found").format(customer))

#         generate_and_store_gl_report(
#             customer=customer,
#             customer_name=customer_name,
#             from_date=from_date,
#             to_date=to_date,
#             month=month,
#             year=year
#         )

#         frappe.db.commit()

#         return {
#             "success": True,
#             "message": _("General Ledger report generated successfully for {0}").format(customer_name),
#             "report_name": f"{month}-{year}"
#         }

#     except Exception as e:
#         frappe.db.rollback()
#         frappe.log_error(f"Error in manual_generate_gl_report: {str(e)}")
#         frappe.throw(_("Error generating report: {0}").format(str(e)))