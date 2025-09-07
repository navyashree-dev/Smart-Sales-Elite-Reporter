import os
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
import matplotlib.pyplot as plt
from fpdf import FPDF  # <-- New: PDF generation

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_report(start_date_str, end_date_str):
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        if end_date < start_date:
            return "Error: End date cannot be before start date.", None
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD.", None

    start_date_sql = start_date.strftime("%Y-%m-%d")
    end_date_sql = end_date.strftime("%Y-%m-%d")
    heading = f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"

    # Load data from SQLite
    conn = sqlite3.connect("data/transactions.db")
    query = "SELECT * FROM transactions WHERE date BETWEEN ? AND ?"
    df = pd.read_sql(query, conn, params=(start_date_sql, end_date_sql))
    conn.close()

    if df.empty:
        return f"No transactions found between {start_date_sql} and {end_date_sql}.", None

    sales_data = df.to_string(index=False)

    prompt = f"""
You are a financial analyst. Given the following sales data for {heading}, generate a professional report.

Make sure the report is in plain text only. Do not use markdown (no *, **, |, -, etc.). Just simple paragraph text.

Structure:
1. Sales Performance: Summary of total revenue, number of transactions, and top-selling products/customers.
2. Insights: Identify notable patterns, issues, or opportunities based on the data.
3. Recommendations: Offer data-driven suggestions for improvement or next steps.
4. Overall: Provide a brief executive summary of the sales during this period.

Sales Data:
{sales_data}
"""

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    full_report = f"Sales Summary: {heading}\n\n{response.text.strip()}"

    # Save text report (old logic)
    os.makedirs("reports", exist_ok=True)
    report_txt_path = os.path.join("reports", f"report_{start_date_sql}_to_{end_date_sql}.txt")
    with open(report_txt_path, "w", encoding="utf-8") as f:
        f.write(full_report)

    # Create chart
    possible_sales_cols = ["Sales", "Amount", "Total", "Revenue"]
    sales_col = next((col for col in df.columns if col.strip().lower() in [c.lower() for c in possible_sales_cols]), None)
    if sales_col is None:
        raise ValueError(f"No sales column found. Expected one of: {possible_sales_cols}")
    chart_data = df.groupby("Product")[sales_col].sum().to_dict()
    chart_path = create_sales_chart(chart_data, start_date_sql, end_date_sql)

    # ----- NEW: generate PDF from text + chart -----
    pdf_path = os.path.join("reports", f"report_{start_date_sql}_to_{end_date_sql}.pdf")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 8, full_report)
    pdf.ln(10)
    if os.path.exists(chart_path):
        pdf.image(chart_path, w=180)
    pdf.output(pdf_path)

    return full_report, pdf_path  # <-- return PDF path for send-mail

def create_sales_chart(data, start_date_sql, end_date_sql):
    plt.figure(figsize=(10, 6))
    products = list(data.keys())
    sales = list(data.values())
    bars = plt.barh(products, sales, color='skyblue', edgecolor='black')
    title = f"Sales Chart - {start_date_sql} to {end_date_sql}"
    plt.title(title, fontsize=16, fontweight='bold')
    plt.xlabel("Units Sold", fontsize=14)
    plt.ylabel("Product", fontsize=14)
    plt.yticks(fontsize=10)
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.5, bar.get_y() + bar.get_height() / 2, f'{width:.0f}', ha='left', va='center', fontsize=9)
    plt.tight_layout()
    os.makedirs("reports", exist_ok=True)
    chart_path = os.path.join("reports", f"chart_{start_date_sql}_to_{end_date_sql}.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    return chart_path
