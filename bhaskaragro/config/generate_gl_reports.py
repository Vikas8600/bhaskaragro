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
    Creates document even if no GL entries exist
    """
    
    frappe.logger().info(f"Generating report for {customer_name} ({customer})")
    frappe.logger().info(f"Date Range: {from_date} to {to_date}")

    # Check if report already exists for this customer and month
    existing_report = frappe.db.exists(
        "General Ledger Report List",
        {"customer": customer, "month": month}
    )

    if existing_report:
        frappe.logger().info(f"Report already exists for {customer} - {month} {year}")
        return

    company = frappe.defaults.get_user_default("Company")
    if not company:
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
        "party": [customer],
        "group_by": "Group by Voucher (Consolidated)",
        "include_dimensions": 1,
        "show_opening_entries": 1,
        "show_cancelled_entries": 0,
        "show_net_values_in_party_account": 0
    }

    # Generate the report HTML (even if no data)
    report_html = get_general_ledger_html(filters, customer, customer_name, month, year)

    # Convert HTML to PDF
    pdf_data = get_pdf(report_html)

    # CREATE THE DOCUMENT REGARDLESS OF WHETHER THERE'S DATA
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
#     Generate HTML content for General Ledger report
#     Returns HTML with message if no data found
#     """
    
#     # Fetch GL Data
#     try:
#         report = frappe.get_doc("Report", "General Ledger")
#         execute_fn = frappe.get_attr(report.report_module + ".execute")
#         columns, data = execute_fn(filters)
#     except:
#         columns, data = [], []

#     # If no data, use direct SQL query
#     if not data:
#         opening_row = frappe.db.sql("""
#             SELECT 
#                 SUM(debit) AS opening_debit,
#                 SUM(credit) AS opening_credit
#             FROM `tabGL Entry`
#             WHERE 
#                 company = %(company)s
#                 AND posting_date < %(from_date)s
#                 AND party_type = 'Customer'
#                 AND party = %(party)s
#                 AND is_cancelled = 0
#         """, {
#             "company": filters["company"],
#             "from_date": filters["from_date"],
#             "party": customer
#         }, as_dict=True)

#         opening_balance = 0
#         if opening_row and opening_row[0]:
#             opening_balance = (opening_row[0].opening_debit or 0) - (opening_row[0].opening_credit or 0)

#         gl_entries = frappe.db.sql("""
#             SELECT 
#                 posting_date,
#                 CONCAT(voucher_type, ' - ', voucher_no) as reference,
#                 remarks,
#                 debit,
#                 credit
#             FROM `tabGL Entry`
#             WHERE 
#                 company = %(company)s
#                 AND posting_date BETWEEN %(from_date)s AND %(to_date)s
#                 AND party_type = 'Customer'
#                 AND party = %(party)s
#                 AND is_cancelled = 0
#             ORDER BY posting_date
#         """, {
#             "company": filters["company"],
#             "from_date": filters["from_date"],
#             "to_date": filters["to_date"],
#             "party": customer
#         }, as_dict=True)

#         columns = [
#             {"label": "Date", "fieldname": "posting_date"},
#             {"label": "Reference", "fieldname": "reference"},
#             {"label": "Remarks", "fieldname": "remarks"},
#             {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency"},
#             {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency"},
#             {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency"}
#         ]

#         data = []
#         balance = opening_balance

#         for d in gl_entries:
#             balance += (d.debit or 0) - (d.credit or 0)
#             d.balance = balance
#             data.append(d)

#         total_debit = sum(d.debit or 0 for d in gl_entries)
#         total_credit = sum(d.credit or 0 for d in gl_entries)
#         total_balance = total_debit - total_credit
#         closing_balance = opening_balance + total_balance
#     else:
#         # Use data from report
#         opening_balance = 0
#         total_debit = 0
#         total_credit = 0
#         for row in data:
#             if isinstance(row, (list, tuple)):
#                 # Find debit/credit indices
#                 for i, col in enumerate(columns):
#                     if col.get('fieldname') == 'debit':
#                         total_debit += row[i] or 0
#                     elif col.get('fieldname') == 'credit':
#                         total_credit += row[i] or 0
#         total_balance = total_debit - total_credit
#         closing_balance = opening_balance + total_balance

#     # BUILD HTML - REGARDLESS OF WHETHER DATA EXISTS

#     letter_head_html = frappe.db.get_value(
#         "Letter Head",
#         "Bhaskar Office Letter Head",
#         "content"
#     ) or ""
#     html = f"""
#     <html>
#     <head>
#         <style>
#             body {{
#                 font-family: Arial, sans-serif;
#                 font-size: 10pt;
#                 margin: 20px;
#             }}
#             h1, h2 {{
#                 text-align: center;
#                 margin: 0;
#                 padding: 0;
#             }}
#             .info {{
#                 text-align: center;
#                 font-size: 9pt;
#                 margin-bottom: 15px;
#             }}
#             table {{
#                 width: 100%;
#                 border-collapse: collapse;
#                 margin-top: 15px;
#             }}
#             th {{
#                 background: #f0f0f0;
#                 border: 1px solid #000;
#                 padding: 6px;
#                 text-align: left;
#                 font-weight: bold;
#             }}
#             td {{
#                 border: 1px solid #000;
#                 padding: 6px;
#                 vertical-align: top;
#             }}
#             .num {{
#                 text-align: right;
#             }}
#             .total-row {{
#                 font-weight: bold;
#                 background: #fafafa;
#             }}
#             .no-data {{
#                 text-align: center;
#                 padding: 30px;
#                 color: #999;
#                 font-style: italic;
#             }}
#         </style>
#     </head>
#     <body>
#     <div style="text-align: center; margin-bottom: 20px;">
#     <div style="display: inline-block; text-align: center; width: 100%;">
#         {letter_head_html}
#     </div>
# </div>

    
#         <h2>STATEMENTS OF ACCOUNTS</h2>
#         <d>
#     <strong>Customer:</strong> {customer} | 
#     <strong>Customer Name:</strong> {customer_name} | 
#     <strong>Date Range:</strong> {filters['from_date']} to {filters['to_date']}
# </d>

       
#         <table>
#             <tr>
#                 <th>Opening Balance</th>
#                 <td class="num">{opening_balance:,.2f}</td>
#             </tr>
#         </table>
#     """

#     # If no data, show message
#     if not data:
#         html += """
#         <div class="no-data">
#             No transactions found for this customer in the specified period.
#         </div>
#         """
#     else:
#         # Show data table
#         html += "<table><thead><tr>"
#         for col in columns:
#             html += f"<th>{col['label']}</th>"
#         html += "</tr></thead><tbody>"

#         for row in data:
#             html += "<tr>"
#             for col in columns:
#                 val = row.get(col["fieldname"], "") if isinstance(row, dict) else ""
#                 if col.get("fieldtype") == "Currency":
#                     val = f"{float(val or 0):,.2f}"
#                     html += f"<td class='num'>{val}</td>"
#                 else:
#                     html += f"<td>{val}</td>"
#             html += "</tr>"

#         html += f"""
#             <tr class="total-row">
#                 <td colspan="{len(columns)-3}">Totals</td>
#                 <td class="num">{total_debit:,.2f}</td>
#                 <td class="num">{total_credit:,.2f}</td>
#                 <td class="num">{total_balance:,.2f}</td>
#             </tr>
#         </tbody></table>
#         """

#     # Closing balance table
#     html += f"""
#         <table>
#             <tr class="total-row">
#                 <th>Closing Balance</th>
#                 <td class="num">{closing_balance:,.2f}</td>
#             </tr>
#         </table>
#     </body>
#     </html>
#     """

#     return html
def get_general_ledger_html(filters, customer, customer_name, month, year):
    """
    Generate HTML content for General Ledger report
    Returns HTML with message if no data found
    """
    
    # Fetch GL Data
    try:
        report = frappe.get_doc("Report", "General Ledger")
        execute_fn = frappe.get_attr(report.report_module + ".execute")
        columns, data = execute_fn(filters)
    except:
        columns, data = [], []

    # If no data, use direct SQL query
    if not data:
        opening_row = frappe.db.sql("""
            SELECT 
                SUM(debit) AS opening_debit,
                SUM(credit) AS opening_credit
            FROM `tabGL Entry`
            WHERE 
                company = %(company)s
                AND posting_date < %(from_date)s
                AND party_type = 'Customer'
                AND party = %(party)s
                AND is_cancelled = 0
        """, {
            "company": filters["company"],
            "from_date": filters["from_date"],
            "party": customer
        }, as_dict=True)

        opening_balance = 0
        if opening_row and opening_row[0]:
            opening_balance = (opening_row[0].opening_debit or 0) - (opening_row[0].opening_credit or 0)

        gl_entries = frappe.db.sql("""
            SELECT 
                posting_date,
                CONCAT(voucher_type, ' - ', voucher_no) as reference,
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
            ORDER BY posting_date
        """, {
            "company": filters["company"],
            "from_date": filters["from_date"],
            "to_date": filters["to_date"],
            "party": customer
        }, as_dict=True)

        columns = [
            {"label": "Date", "fieldname": "posting_date"},
            {"label": "Reference", "fieldname": "reference"},
            {"label": "Remarks", "fieldname": "remarks"},
            {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency"},
            {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency"},
            {"label": "Balance", "fieldname": "balance", "fieldtype": "Currency"}
        ]

        data = []
        balance = opening_balance

        for d in gl_entries:
            balance += (d.debit or 0) - (d.credit or 0)
            d.balance = balance
            data.append(d)

        total_debit = sum(d.debit or 0 for d in gl_entries)
        total_credit = sum(d.credit or 0 for d in gl_entries)
        total_balance = total_debit - total_credit
        closing_balance = opening_balance + total_balance
    else:
        # Use data from report
        opening_balance = 0
        total_debit = 0
        total_credit = 0
        for row in data:
            if isinstance(row, (list, tuple)):
                for i, col in enumerate(columns):
                    if col.get('fieldname') == 'debit':
                        total_debit += row[i] or 0
                    elif col.get('fieldname') == 'credit':
                        total_credit += row[i] or 0
        total_balance = total_debit - total_credit
        closing_balance = opening_balance + total_balance

    # BUILD HTML WITH FIXED COLUMN WIDTHS

    letter_head_html = frappe.db.get_value(
        "Letter Head",
        "Bhaskar Office Letter Head",
        "content"
    ) or ""
    
    html = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 15mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 9pt;
                margin: 0;
                padding: 0;
            }}
            h1, h2 {{
                text-align: center;
                margin: 5px 0;
                padding: 0;
                font-size: 14pt;
            }}
            .info {{
                text-align: center;
                font-size: 8pt;
                margin-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                table-layout: fixed; /* CRITICAL: Fixed layout prevents overflow */
            }}
            th {{
                background: #f0f0f0;
                border: 1px solid #000;
                padding: 5px;
                text-align: left;
                font-weight: bold;
                font-size: 8pt;
                word-wrap: break-word;
            }}
            td {{
                border: 1px solid #000;
                padding: 5px;
                vertical-align: top;
                font-size: 8pt;
                word-wrap: break-word; /* Allow text to wrap */
                overflow-wrap: break-word; /* Break long words */
            }}
            /* Fixed column widths to prevent overflow */
            table.data-table {{
                width: 100%;
            }}
            table.data-table th:nth-child(1),
            table.data-table td:nth-child(1) {{ width: 10%; }} /* Date */
            table.data-table th:nth-child(2),
            table.data-table td:nth-child(2) {{ width: 20%; }} /* Reference */
            table.data-table th:nth-child(3),
            table.data-table td:nth-child(3) {{ width: 30%; }} /* Remarks */
            table.data-table th:nth-child(4),
            table.data-table td:nth-child(4) {{ width: 13%; }} /* Debit */
            table.data-table th:nth-child(5),
            table.data-table td:nth-child(5) {{ width: 13%; }} /* Credit */
            table.data-table th:nth-child(6),
            table.data-table td:nth-child(6) {{ width: 14%; }} /* Balance */
            
            .num {{
                text-align: right;
            }}
            .total-row {{
                font-weight: bold;
                background: #fafafa;
            }}
            .no-data {{
                text-align: center;
                padding: 30px;
                color: #999;
                font-style: italic;
            }}
            /* Balance tables */
            table.balance-table {{
                width: 50%;
                margin-left: auto;
                margin-right: auto;
            }}
            table.balance-table th {{
                width: 60%;
            }}
            table.balance-table td {{
                width: 40%;
            }}
        </style>
    </head>
    <body>
        <div style="text-align: center; margin-bottom: 15px;">
            <div style="display: inline-block; text-align: center; width: 100%;">
                {letter_head_html}
            </div>
        </div>
        
        <h2>STATEMENTS OF ACCOUNTS</h2>
        <div class="info">
            <strong>Customer:</strong> {customer} | 
            <strong>Customer Name:</strong> {customer_name} | 
            <strong>Date Range:</strong> {filters['from_date']} to {filters['to_date']}
        </div>
       
        <table class="balance-table">
            <tr>
                <th>Opening Balance</th>
                <td class="num">{opening_balance:,.2f}</td>
            </tr>
        </table>
    """

    # If no data, show message
    if not data:
        html += """
        <div class="no-data">
            No transactions found for this customer in the specified period.
        </div>
        """
    else:
        # Show data table with fixed widths
        html += '<table class="data-table"><thead><tr>'
        for col in columns:
            html += f"<th>{col['label']}</th>"
        html += "</tr></thead><tbody>"

        for row in data:
            html += "<tr>"
            for col in columns:
                val = row.get(col["fieldname"], "") if isinstance(row, dict) else ""
                if col.get("fieldtype") == "Currency":
                    val = f"{float(val or 0):,.2f}"
                    html += f"<td class='num'>{val}</td>"
                else:
                    # Truncate very long text to prevent overflow
                    val_str = str(val) if val else ""
                    html += f"<td>{val_str}</td>"
            html += "</tr>"

        # Calculate colspan for totals row
        colspan = len(columns) - 3
        
        html += f"""
            <tr class="total-row">
                <td colspan="{colspan}">Totals</td>
                <td class="num">{total_debit:,.2f}</td>
                <td class="num">{total_credit:,.2f}</td>
                <td class="num">{total_balance:,.2f}</td>
            </tr>
        </tbody></table>
        """

    # Closing balance table
    html += f"""
        <table class="balance-table">
            <tr class="total-row">
                <th>Closing Balance</th>
                <td class="num">{closing_balance:,.2f}</td>
            </tr>
        </table>
    </body>
    </html>
    """

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