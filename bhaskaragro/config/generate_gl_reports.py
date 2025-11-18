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
            prev_month = current_date.month - 1
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


def get_general_ledger_html(filters, customer, customer_name, month, year):
    """
    Generate HTML content for General Ledger report with guaranteed data retrieval
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
            
            # Query GL entries directly
            gl_entries = frappe.db.sql("""
                SELECT 
                    posting_date,
                    account,
                    against_voucher_type as voucher_type,
                    voucher_no,
                    against_voucher,
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

            if gl_entries:
                frappe.logger().info(f"✓ Direct query: Found {len(gl_entries)} entries")
                method_used = "direct_query"
                
                # Create columns for direct query
                columns = [
                    {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date"},
                    {"label": "Account", "fieldname": "account", "fieldtype": "Data"},
                    {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data"},
                    {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Data"},
                    {"label": "Against Voucher", "fieldname": "against_voucher", "fieldtype": "Data"},
                    {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Text"},
                    {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency"},
                    {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency"},
                    {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency"}
                ]
                
                data = gl_entries
                
                # Calculate running balance
                running_balance = 0
                for entry in data:
                    running_balance += (entry.get('debit', 0) - entry.get('credit', 0))
                    entry['balance'] = running_balance

            else:
                frappe.logger().warning(f"✗ No GL entries found in direct query")

        except Exception as e:
            frappe.logger().error(f"✗ Error in direct query: {str(e)}")
            import traceback
            frappe.logger().error(traceback.format_exc())

    if not data:
        frappe.logger().warning(f"No data available for {customer_name} in {month} {year}")
        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                }}
                .info-box {{
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    padding: 15px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <h2>General Ledger Report</h2>
            <h3>{customer_name} - {month} {year}</h3>
            
            <div class="info-box">
                <p><strong>Status:</strong> No data found</p>
                <p><strong>Customer ID:</strong> {customer}</p>
                <p><strong>Date Range:</strong> {filters['from_date']} to {filters['to_date']}</p>
                <p><strong>Company:</strong> {filters['company']}</p>
            </div>
            
            <p><em>Note: No General Ledger entries found for this customer in the specified period.</em></p>
            <p><em>Please verify that transactions exist for this customer during {month} {year}.</em></p>
        </body>
        </html>
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
                margin-bottom: 10px;
            }}
            .info-line {{
                text-align: center;
                font-size: 9pt;
                color: #999;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #000;
                padding: 6px;
                text-align: left;
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
            .footer {{
                margin-top: 10px;
                font-size: 8pt;
                color: #999;
            }}
        </style>
    </head>
    <body>
        <h1>General Ledger Report</h1>
        <h2>{customer_name}</h2>
        <div class="info-line">{month} {year} | {filters['from_date']} to {filters['to_date']}</div>
        
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
            elif col.get('fieldtype') == 'Date' and cell_value:
                try:
                    cell_value = str(cell_value)
                except:
                    pass

            html += f"<td{cell_class}>{cell_value or ''}</td>"

        html += "</tr>"

    html += f"""
            </tbody>
        </table>
        <div class="footer">
            Generated on {today()} | Method: {method_used} | Records: {len(data)} | Company: {filters['company']}
        </div>
    </body></html>
    """
    
    frappe.logger().info(f"✓ HTML generated successfully with {len(data)} rows using method: {method_used}")
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