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
        
        # Calculate previous month
        if current_date.month == 1:
            prev_month = 12
            prev_year = current_date.year - 1
        else:
            prev_month = current_date.month -1
            prev_year = current_date.year
        
        # Get first and last day of previous month
        first_day_previous_month = getdate(f"{prev_year}-{prev_month:02d}-01")
        last_day_num = calendar.monthrange(prev_year, prev_month)[1]
        last_day_previous_month = getdate(f"{prev_year}-{prev_month:02d}-{last_day_num}")

        # Get month name and year
        month_name = calendar.month_name[prev_month]
        year = prev_year

        frappe.logger().info(f"Starting GL Report generation for {month_name} {year}")
        frappe.logger().info(f"Date Range: {first_day_previous_month} to {last_day_previous_month}")

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
    
    frappe.logger().info(f"Generating report for {customer_name} ({customer})")
    frappe.logger().info(f"Date Range: {from_date} to {to_date}")

    # Check if report already exists for this customer and month - FIXED
    existing_report = frappe.db.exists(
        "General Ledger Report List",
        {"customer": customer, "month": month}
    )

    if existing_report:
        frappe.logger().info(f"Report already exists for {customer} - {month} {year}")
        return

    company = frappe.defaults.get_user_default("Company")
    if not company:
        # Try to get first active company
        company = frappe.get_all("Company", filters={"disabled": 0}, limit=1, pluck="name")
        if company:
            company = company[0]
        else:
            frappe.throw(_("No active Company found"))

    frappe.logger().info(f"Using company: {company}")

    # Prepare filters for General Ledger report
    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "party_type": "Customer",
        "party": [customer],  # Note: Some ERPNext versions expect a list
        "group_by": "Group by Voucher (Consolidated)",
        "include_dimensions": 1,
        "show_opening_entries": 1,
        "show_cancelled_entries": 0,
        "show_net_values_in_party_account": 0
    }

    # Generate the report HTML
    report_html = get_general_ledger_html(filters, customer, customer_name, month, year)

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


# def get_general_ledger_html(filters, customer, customer_name, month, year):
#     """
#     Generate HTML content for General Ledger report with guaranteed data retrieval
#     """

#     columns = []
#     data = []
#     method_used = "none"

#     frappe.logger().info(f"=== Fetching GL data for {customer_name} ===")
#     frappe.logger().info(f"Filters: {filters}")

#     # Method 1: Try standard report execution
#     try:
#         report = frappe.get_doc("Report", "General Ledger")
#         execute_fn = frappe.get_attr(report.report_module + ".execute")
        
#         # Try with party as list first
#         columns, data = execute_fn(filters)
#         method_used = "standard_list"
#         frappe.logger().info(f"✓ Standard method (list): Fetched {len(data)} rows")

#     except Exception as e:
#         frappe.logger().error(f"✗ Error with standard method (list): {str(e)}")
        
#         # Try with party as string
#         try:
#             filters_copy = filters.copy()
#             filters_copy["party"] = customer  # Try as string instead of list
#             columns, data = execute_fn(filters_copy)
#             method_used = "standard_string"
#             frappe.logger().info(f"✓ Standard method (string): Fetched {len(data)} rows")
#         except Exception as e2:
#             frappe.logger().error(f"✗ Error with standard method (string): {str(e2)}")

#     # Method 2: Direct database query if no data found
#     if not data:
#         frappe.logger().info(f"Attempting direct database query for customer: {customer}")
        
#         try:
#             # First check if any entries exist
#             check_query = """
#                 SELECT COUNT(*) as count
#                 FROM `tabGL Entry`
#                 WHERE party_type = 'Customer' 
#                 AND party = %(party)s
#             """
#             total_count = frappe.db.sql(check_query, {'party': customer}, as_dict=1)
#             frappe.logger().info(f"Total GL entries for {customer}: {total_count[0].get('count', 0)}")
            
#             # Check entries in date range
#             date_check = """
#                 SELECT COUNT(*) as count
#                 FROM `tabGL Entry`
#                 WHERE party_type = 'Customer' 
#                 AND party = %(party)s
#                 AND posting_date BETWEEN %(from_date)s AND %(to_date)s
#             """
#             range_count = frappe.db.sql(date_check, {
#                 'party': customer,
#                 'from_date': filters['from_date'],
#                 'to_date': filters['to_date']
#             }, as_dict=1)
#             frappe.logger().info(f"GL entries in date range: {range_count[0].get('count', 0)}")
            
#             # Query GL entries directly
#             gl_entries = frappe.db.sql("""
#                 SELECT 
#                     posting_date,
#                     account,
#                     against_voucher_type as voucher_type,
#                     voucher_no,
#                     against_voucher,
#                     remarks,
#                     debit,
#                     credit
#                 FROM `tabGL Entry`
#                 WHERE 
#                     company = %(company)s
#                     AND posting_date BETWEEN %(from_date)s AND %(to_date)s
#                     AND party_type = 'Customer'
#                     AND party = %(party)s
#                     AND is_cancelled = 0
#                 ORDER BY posting_date, creation
#             """, {
#                 'company': filters['company'],
#                 'from_date': filters['from_date'],
#                 'to_date': filters['to_date'],
#                 'party': customer
#             }, as_dict=1)

#             if gl_entries:
#                 frappe.logger().info(f"✓ Direct query: Found {len(gl_entries)} entries")
#                 method_used = "direct_query"
                
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
#                 frappe.logger().warning(f"✗ No GL entries found in direct query")

#         except Exception as e:
#             frappe.logger().error(f"✗ Error in direct query: {str(e)}")
#             import traceback
#             frappe.logger().error(traceback.format_exc())

#     if not data:
#         frappe.logger().warning(f"No data available for {customer_name} in {month} {year}")
#         return f"""
#         <html>
#         <head>
#             <style>
#                 body {{
#                     font-family: Arial, sans-serif;
#                     padding: 20px;
#                 }}
#                 .info-box {{
#                     background: #f8f9fa;
#                     border: 1px solid #dee2e6;
#                     padding: 15px;
#                     margin: 10px 0;
#                 }}
#             </style>
#         </head>
#         <body>
#             <h2>General Ledger Report</h2>
#             <h3>{customer_name} - {month} {year}</h3>
            
#             <div class="info-box">
#                 <p><strong>Status:</strong> No data found</p>
#                 <p><strong>Customer ID:</strong> {customer}</p>
#                 <p><strong>Date Range:</strong> {filters['from_date']} to {filters['to_date']}</p>
#                 <p><strong>Company:</strong> {filters['company']}</p>
#             </div>
            
#             <p><em>Note: No General Ledger entries found for this customer in the specified period.</em></p>
#             <p><em>Please verify that transactions exist for this customer during {month} {year}.</em></p>
#         </body>
#         </html>
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
#                 margin-bottom: 10px;
#             }}
#             .info-line {{
#                 text-align: center;
#                 font-size: 9pt;
#                 color: #999;
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
#             .footer {{
#                 margin-top: 10px;
#                 font-size: 8pt;
#                 color: #999;
#             }}
#         </style>
#     </head>
#     <body>
#         <h1>General Ledger Report</h1>
#         <h2>{customer_name}</h2>
#         <div class="info-line">{month} {year} | {filters['from_date']} to {filters['to_date']}</div>
        
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

#     html += f"""
#             </tbody>
#         </table>
#         <div class="footer">
#             Generated on {today()} | Method: {method_used} | Records: {len(data)} | Company: {filters['company']}
#         </div>
#     </body></html>
#     """
    
#     frappe.logger().info(f"✓ HTML generated successfully with {len(data)} rows using method: {method_used}")
#     return html


def get_general_ledger_html(filters, customer, customer_name, month, year):
    """
    Generate HTML content for General Ledger report with enhanced formatting
    """

    columns = []
    data = []
    method_used = "none"

    frappe.logger().info(f"=== Fetching GL data for {customer_name} ===")
    frappe.logger().info(f"Filters: {filters}")

    # Method 1: Try standard report execution
    try:
        report = frappe.get_doc("Report", "General Ledger")
        execute_fn = frappe.get_attr(report.report_module + ".execute")
        
        # Try with party as list first
        columns, data = execute_fn(filters)
        method_used = "standard_list"
        frappe.logger().info(f"✓ Standard method (list): Fetched {len(data)} rows")

    except Exception as e:
        frappe.logger().error(f"✗ Error with standard method (list): {str(e)}")
        
        # Try with party as string
        try:
            filters_copy = filters.copy()
            filters_copy["party"] = customer  # Try as string instead of list
            columns, data = execute_fn(filters_copy)
            method_used = "standard_string"
            frappe.logger().info(f"✓ Standard method (string): Fetched {len(data)} rows")
        except Exception as e2:
            frappe.logger().error(f"✗ Error with standard method (string): {str(e2)}")

    # Method 2: Direct database query if no data found
    if not data:
        frappe.logger().info(f"Attempting direct database query for customer: {customer}")
        
        try:
            # First check if any entries exist
            check_query = """
                SELECT COUNT(*) as count
                FROM `tabGL Entry`
                WHERE party_type = 'Customer' 
                AND party = %(party)s
            """
            total_count = frappe.db.sql(check_query, {'party': customer}, as_dict=1)
            frappe.logger().info(f"Total GL entries for {customer}: {total_count[0].get('count', 0)}")
            
            # Check entries in date range
            date_check = """
                SELECT COUNT(*) as count
                FROM `tabGL Entry`
                WHERE party_type = 'Customer' 
                AND party = %(party)s
                AND posting_date BETWEEN %(from_date)s AND %(to_date)s
            """
            range_count = frappe.db.sql(date_check, {
                'party': customer,
                'from_date': filters['from_date'],
                'to_date': filters['to_date']
            }, as_dict=1)
            frappe.logger().info(f"GL entries in date range: {range_count[0].get('count', 0)}")
            
            # First, get opening balance (all entries before from_date)
            opening_balance_data = frappe.db.sql("""
                SELECT 
                    SUM(debit) as opening_debit,
                    SUM(credit) as opening_credit
                FROM `tabGL Entry`
                WHERE 
                    company = %(company)s
                    AND posting_date < %(from_date)s
                    AND party_type = 'Customer'
                    AND party = %(party)s
                    AND is_cancelled = 0
            """, {
                'company': filters['company'],
                'from_date': filters['from_date'],
                'party': customer
            }, as_dict=1)
            
            opening_debit = opening_balance_data[0].get('opening_debit', 0) or 0
            opening_credit = opening_balance_data[0].get('opening_credit', 0) or 0
            opening_balance = opening_debit - opening_credit
            
            frappe.logger().info(f"Opening Balance: Debit={opening_debit}, Credit={opening_credit}, Balance={opening_balance}")
            
            # Query GL entries directly
            gl_entries = frappe.db.sql("""
                SELECT 
                    posting_date,
                    voucher_type,
                    voucher_no,
                    remarks,
                    debit,
                    credit
                FROM `tabGL Entry`
                WHERE 
                    company = %(company)s
                    AND posting_date BETWEEN %(from_date)s AND %(to_date)s
                    AND party_type = 'Customer'
                    AND party = %(party)s
                    AND is_cancelled = 0
                ORDER BY posting_date, creation
            """, {
                'company': filters['company'],
                'from_date': filters['from_date'],
                'to_date': filters['to_date'],
                'party': customer
            }, as_dict=1)

            if gl_entries or opening_balance != 0:
                frappe.logger().info(f"✓ Direct query: Found {len(gl_entries)} entries")
                method_used = "direct_query"
                
                # Create columns for direct query - simplified columns
                columns = [
                    {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": "100px"},
                    {"label": "Reference", "fieldname": "voucher_no", "fieldtype": "Data", "width": "150px"},
                    {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Text", "width": "250px"},
                    {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": "120px"},
                    {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": "120px"},
                    {"label": "Balance (Dr - Cr)", "fieldname": "balance", "fieldtype": "Currency", "width": "120px"}
                ]
                
                data = []
                
                # Add opening balance row
                data.append({
                    'posting_date': '',
                    'voucher_no': '',
                    'remarks': 'Opening Balance',
                    'debit': '',
                    'credit': opening_credit if opening_credit > 0 else '',
                    'balance': opening_balance,
                    'is_opening': True
                })
                
                # Add GL entries with running balance
                running_balance = opening_balance
                for entry in gl_entries:
                    running_balance += (entry.get('debit', 0) - entry.get('credit', 0))
                    entry['balance'] = running_balance
                    data.append(entry)

            else:
                frappe.logger().warning(f"✗ No GL entries found in direct query")

        except Exception as e:
            frappe.logger().error(f"✗ Error in direct query: {str(e)}")
            import traceback
            frappe.logger().error(traceback.format_exc())

    if not data:
        frappe.logger().warning(f"No data available for {customer_name} in {month} {year}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    padding: 40px;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 3px solid #2c3e50;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                h1 {{
                    font-size: 24pt;
                    color: #2c3e50;
                    margin: 0 0 10px 0;
                }}
                h2 {{
                    font-size: 16pt;
                    color: #34495e;
                    margin: 5px 0;
                    font-weight: normal;
                }}
                .info-box {{
                    background: #f8f9fa;
                    border: 2px solid #dee2e6;
                    border-radius: 5px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .info-row {{
                    padding: 5px 0;
                    font-size: 11pt;
                }}
                .label {{
                    font-weight: bold;
                    color: #555;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>General Ledger Report</h1>
                <h2>{customer_name}</h2>
                <p style="color: #7f8c8d; font-size: 11pt; margin: 10px 0 0 0;">
                    Period: {month} {year} ({filters['from_date']} to {filters['to_date']})
                </p>
            </div>
            
            <div class="info-box">
                <div class="info-row"><span class="label">Status:</span> No transactions found</div>
                <div class="info-row"><span class="label">Customer ID:</span> {customer}</div>
                <div class="info-row"><span class="label">Company:</span> {filters['company']}</div>
                <div class="info-row"><span class="label">Date Range:</span> {filters['from_date']} to {filters['to_date']}</div>
            </div>
            
            <p style="text-align: center; color: #7f8c8d; font-style: italic; margin-top: 30px;">
                No General Ledger entries found for this customer in the specified period.
            </p>
        </body>
        </html>
        """

    # Calculate totals
    total_debit = 0
    total_credit = 0
    opening_balance = 0
    closing_balance = 0
    
    for row in data:
        if isinstance(row, dict):
            if row.get('is_opening'):
                opening_balance = float(row.get('balance', 0) or 0)
            else:
                total_debit += float(row.get('debit', 0) or 0)
                total_credit += float(row.get('credit', 0) or 0)
                closing_balance = float(row.get('balance', 0) or 0)

    # Build Enhanced HTML with professional styling
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4 landscape;
                margin: 15mm;
            }}
            
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 9pt;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            
            .header {{
                text-align: center;
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            
            .report-title {{
                font-size: 20pt;
                font-weight: bold;
                color: #2c3e50;
                margin: 0 0 8px 0;
            }}
            
            .customer-name {{
                font-size: 14pt;
                color: #34495e;
                margin: 5px 0;
                font-weight: 600;
            }}
            
            .period-info {{
                font-size: 10pt;
                color: #7f8c8d;
                margin-top: 8px;
            }}
            
            .report-info {{
                background: #f8f9fa;
                padding: 10px 15px;
                margin-bottom: 15px;
                border-left: 4px solid #3498db;
                font-size: 9pt;
            }}
            
            .report-info-row {{
                display: inline-block;
                margin-right: 30px;
            }}
            
            .report-info-label {{
                font-weight: bold;
                color: #555;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 9pt;
            }}
            
            thead {{
                background: linear-gradient(to bottom, #34495e 0%, #2c3e50 100%);
                color: white;
            }}
            
            th {{
                padding: 10px 8px;
                text-align: left;
                font-weight: 600;
                border: 1px solid #2c3e50;
                font-size: 9pt;
                white-space: nowrap;
            }}
            
            th.col-date {{
                width: 100px;
            }}
            
            th.col-reference {{
                width: 150px;
            }}
            
            th.col-remarks {{
                width: auto;
                min-width: 200px;
            }}
            
            th.col-debit,
            th.col-credit,
            th.col-balance {{
                width: 120px;
                text-align: right;
            }}
            
            td {{
                padding: 8px;
                border: 1px solid #ddd;
                vertical-align: top;
            }}
            
            tbody tr:nth-child(odd) {{
                background-color: #ffffff;
            }}
            
            tbody tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            
            tbody tr:hover {{
                background-color: #e8f4f8;
            }}
            
            .number {{
                text-align: right;
                font-family: 'Courier New', monospace;
                font-weight: 500;
            }}
            
            .date {{
                white-space: nowrap;
                font-weight: 500;
            }}
            
            .opening-row {{
                background: #fff3cd !important;
                font-weight: bold;
                border-bottom: 2px solid #ffc107 !important;
            }}
            
            .opening-row td {{
                padding: 10px 8px;
                font-style: italic;
            }}
            
            .total-row {{
                background: #ecf0f1 !important;
                font-weight: bold;
                border-top: 2px solid #2c3e50 !important;
                border-bottom: 2px solid #2c3e50 !important;
            }}
            
            .total-row td {{
                padding: 10px 8px;
                font-size: 10pt;
            }}
            
            .closing-row {{
                background: #d4edda !important;
                font-weight: bold;
                border-top: 2px solid #28a745 !important;
            }}
            
            .closing-row td {{
                padding: 10px 8px;
                font-size: 10pt;
            }}
            
            .footer {{
                margin-top: 20px;
                padding-top: 15px;
                border-top: 2px solid #ecf0f1;
                font-size: 8pt;
                color: #95a5a6;
                display: flex;
                justify-content: space-between;
            }}
            
            .footer-left, .footer-right {{
                display: inline-block;
            }}
            
            .no-data {{
                text-align: center;
                padding: 30px;
                color: #7f8c8d;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="report-title">General Ledger Report</div>
            <div class="customer-name">{customer_name}</div>
            <div class="period-info">{month} {year} | {filters['from_date']} to {filters['to_date']}</div>
        </div>
        
        <div class="report-info">
            <span class="report-info-row">
                <span class="report-info-label">Company:</span> {filters['company']}
            </span>
            <span class="report-info-row">
                <span class="report-info-label">Customer ID:</span> {customer}
            </span>
            <span class="report-info-row">
                <span class="report-info-label">Report Date:</span> {today()}
            </span>
        </div>
        
        <table>
            <thead>
                <tr>
    """

    # Add column headers with specific classes
    col_class_map = {
        'Date': 'col-date',
        'Reference': 'col-reference', 
        'Remarks': 'col-remarks',
        'Debit': 'col-debit',
        'Credit': 'col-credit',
        'Balance (Dr - Cr)': 'col-balance'
    }
    
    for col in columns:
        col_label = col.get('label', '')
        col_class = col_class_map.get(col_label, '')
        align_class = 'style="text-align: right;"' if col.get('fieldtype') in ['Currency', 'Float', 'Int'] else ''
        html += f"<th class='{col_class}' {align_class}>{col_label}</th>"

    html += "</tr></thead><tbody>"

    # Add data rows
    for row in data:
        is_total_row = isinstance(row, dict) and row.get('is_total_row', False)
        is_opening_row = isinstance(row, dict) and row.get('is_opening', False)
        
        row_class = ''
        if is_total_row:
            row_class = ' class="total-row"'
        elif is_opening_row:
            row_class = ' class="opening-row"'
            
        html += f"<tr{row_class}>"

        for i, col in enumerate(columns):
            fieldname = col.get('fieldname')
            fieldtype = col.get('fieldtype')
            cell_value = ""
            
            if isinstance(row, (list, tuple)):
                if i < len(row):
                    cell_value = row[i]
            elif isinstance(row, dict):
                cell_value = row.get(fieldname, '')

            # Determine cell class
            cell_classes = []
            if fieldtype in ['Currency', 'Float', 'Int']:
                cell_classes.append('number')
            if fieldtype == 'Date':
                cell_classes.append('date')
            
            cell_class = f' class="{" ".join(cell_classes)}"' if cell_classes else ''

            # Format cell value
            if fieldtype == 'Currency' and cell_value not in ['', None]:
                try:
                    cell_value = f"{float(cell_value):,.2f}"
                except:
                    cell_value = ""
            elif fieldtype in ['Float', 'Int'] and cell_value:
                try:
                    cell_value = f"{float(cell_value):,.2f}"
                except:
                    pass
            elif fieldtype == 'Date' and cell_value:
                try:
                    from frappe.utils import formatdate
                    cell_value = formatdate(cell_value)
                except:
                    cell_value = str(cell_value)

            # Handle empty values
            display_value = cell_value if cell_value not in ['', None] else ''
            html += f"<td{cell_class}>{display_value}</td>"

        html += "</tr>"

    # Add total row
    html += f"""
                <tr class="total-row">
                    <td colspan="3" style="text-align: right; font-weight: bold;">TOTAL</td>
                    <td class="number">{total_debit:,.2f}</td>
                    <td class="number">{total_credit:,.2f}</td>
                    <td class="number"></td>
                </tr>
                <tr class="closing-row">
                    <td colspan="3" style="text-align: right; font-weight: bold;">CLOSING BALANCE</td>
                    <td class="number"></td>
                    <td class="number"></td>
                    <td class="number">{closing_balance:,.2f}</td>
                </tr>
    """

    html += f"""
            </tbody>
        </table>
        
        <div class="footer">
            <div class="footer-left">
                Generated on {today()} | Method: {method_used} | Total Records: {len(data)}
            </div>
            <div class="footer-right">
                Page 1 of 1
            </div>
        </div>
    </body>
    </html>
    """
    
    frappe.logger().info(f"✓ Enhanced HTML generated successfully with {len(data)} rows using method: {method_used}")
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

        # CRITICAL: Get the FULL month date range
        # Calculate last day of month properly
        last_day_of_month = calendar.monthrange(year, month_num)[1]
        from_date = getdate(f"{year}-{month_num:02d}-01")
        to_date = getdate(f"{year}-{month_num:02d}-{last_day_of_month}")

        frappe.logger().info(f"Manual GL Report Generation")
        frappe.logger().info(f"Customer: {customer}")
        frappe.logger().info(f"Month: {month} {year} (Month #{month_num})")
        frappe.logger().info(f"Date Range: {from_date} to {to_date}")

        # Clean customer ID - remove any surrounding quotes
        customer = customer.strip().strip('"').strip("'")
        frappe.logger().info(f"Cleaned Customer ID: {customer}")

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
            "report_name": f"{month}-{year}",
            "date_range": f"{from_date} to {to_date}"
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error in manual_generate_gl_report: {str(e)}")
        frappe.throw(_("Error generating report: {0}").format(str(e)))


@frappe.whitelist()
def debug_customer_gl_entries(customer, month=None, year=None):
    """
    Debug function to check GL entries for a customer
    """
    company = frappe.defaults.get_user_default("Company")
    if not company:
        company = frappe.get_all("Company", filters={"disabled": 0}, limit=1, pluck="name")
        if company:
            company = company[0]
    
    results = {
        "customer": customer,
        "company": company
    }
    
    # If month and year provided, calculate date range
    if month and year:
        month_num = list(calendar.month_name).index(month)
        from_date = getdate(f"{year}-{month_num:02d}-01")
        to_date = get_last_day(from_date)
        results["from_date"] = str(from_date)
        results["to_date"] = str(to_date)
    else:
        from_date = None
        to_date = None
    
    # Check 1: Any GL entries for this customer?
    total_entries = frappe.db.sql("""
        SELECT COUNT(*) as count 
        FROM `tabGL Entry` 
        WHERE party_type = 'Customer' AND party = %s
    """, customer, as_dict=1)
    results["total_entries"] = total_entries[0].get('count', 0) if total_entries else 0
    
    # Check 2: Entries in date range?
    if from_date and to_date:
        date_range_entries = frappe.db.sql("""
            SELECT COUNT(*) as count 
            FROM `tabGL Entry` 
            WHERE party_type = 'Customer' 
            AND party = %s 
            AND posting_date BETWEEN %s AND %s
        """, (customer, from_date, to_date), as_dict=1)
        results["date_range_entries"] = date_range_entries[0].get('count', 0) if date_range_entries else 0
    
    # Check 3: Sample entries
    sample_entries = frappe.db.sql("""
        SELECT posting_date, voucher_type, voucher_no, debit, credit, company
        FROM `tabGL Entry` 
        WHERE party_type = 'Customer' AND party = %s 
        ORDER BY posting_date DESC
        LIMIT 5
    """, customer, as_dict=1)
    results["sample_entries"] = sample_entries
    
    # Check 4: Date range of entries
    date_range = frappe.db.sql("""
        SELECT 
            MIN(posting_date) as earliest_date,
            MAX(posting_date) as latest_date
        FROM `tabGL Entry`
        WHERE party_type = 'Customer' AND party = %s
    """, customer, as_dict=1)
    if date_range:
        results["earliest_entry"] = str(date_range[0].get('earliest_date', 'N/A'))
        results["latest_entry"] = str(date_range[0].get('latest_date', 'N/A'))
    
    return results