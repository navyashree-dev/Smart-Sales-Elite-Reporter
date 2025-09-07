from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, session, jsonify, send_file
)
import os
import traceback
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend for servers
import matplotlib.pyplot as plt

# ---- Your existing project modules ----
from scripts.google_sheets_reader import read_sheet
from scripts.save_to_db import save_to_db
from scripts.generate_report import generate_report
from scripts.email_sender import send_email

# ---- New: dashboard data helpers ----
import sqlite3
import pandas as pd
from io import BytesIO

# ✅ NEW: Google Credentials Loading for Render Deployment
import json
from google.oauth2 import service_account

# Load Google Credentials from environment variable (Render-safe)
google_creds_json = os.getenv("GOOGLE_CREDENTIALS")
if google_creds_json:
    try:
        creds_dict = json.loads(google_creds_json)
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        # ✅ You can now import/use this credentials object in read_sheet() or anywhere needed
    except Exception as e:
        print("❌ Failed to load GOOGLE_CREDENTIALS:", e)
        credentials = None
else:
    print("⚠ GOOGLE_CREDENTIALS environment variable not set. Some features may fail.")
    credentials = None


app = Flask(__name__)
app.secret_key = 'simplekey123'  # Secret key for session

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------------ EXISTING ROUTES ------------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == "NAVYA" and password == "SHREE":
            session['logged_in'] = True
            return redirect(url_for('index'))  # ✅ Changed to index page
        else:
            flash("❌ Invalid username or password!", "error")
    return render_template('login.html')


# ✅ New Index Route
@app.route('/index')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if not start_date or not end_date:
            flash("⚠ Please enter both start and end dates!", "error")
            return redirect(url_for('index'))

        df = read_sheet()  # ✅ This function should now internally use the `credentials` object above
        if df.empty:
            flash("❌ Failed to load data from Google Sheet.", "error")
            return redirect(url_for('index'))

        save_to_db(df)  # saves into data/transactions.db

        # Generate report and PDF
        report_text, pdf_path = generate_report(start_date, end_date)
        if not report_text.strip():
            flash("❌ Report is empty!", "error")
            return redirect(url_for('index'))

        # Store the generated PDF path in session for sending email
        session['last_report_pdf'] = pdf_path

        flash(f"✅ Report generated successfully! Saved as {os.path.basename(pdf_path)}", "success")
        return render_template('index.html', report=report_text, start_date=start_date, end_date=end_date)

    except Exception as e:
        traceback.print_exc()
        flash(f"❌ An error occurred: {str(e)}", "error")
        return redirect(url_for('index'))


@app.route('/send-mail', methods=['POST'])
def send_mail():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    recipient_email = request.form.get('recipient_email')
    if not recipient_email:
        flash("Please enter a recipient email.", "error")
        return redirect(url_for('index'))

    pdf_path = session.get('last_report_pdf')
    if not pdf_path or not os.path.exists(pdf_path):
        flash("Report not found. Please generate it first.", "error")
        return redirect(url_for('index'))

    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    subject = f"Sales Report ({start_date} to {end_date})"
    body = "Dear User,\n\nPlease find the attached sales report.\n\nRegards,\nSmart Sales Elite Reporter\nNavyaShree"

    if send_email(recipient_email, subject, body, pdf_path):
        flash("✅ Email sent successfully!", "success")
    else:
        flash("❌ Failed to send email. Check logs.", "error")

    return redirect(url_for('index'))


@app.route('/history')
def history():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    files = sorted(os.listdir(REPORTS_DIR), reverse=True)
    pdf_files = [f for f in files if f.endswith('.pdf')]
    return render_template('history.html', files=pdf_files)


@app.route('/download/<filename>')
def download_report(filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("✅ You have been logged out.", "success")
    return redirect(url_for('login'))


# ------------------------ UPLOAD -----------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    if not session.get('logged_in'):
        return jsonify({"error": "unauthorized"}), 401
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    try:
        filename = file.filename.replace(" ", "_")
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        return jsonify({"filepath": save_path})
    except Exception as e:
        print("Upload error:", e)
        return jsonify({"error": str(e)}), 500


# ------------------------ DASHBOARD & ANALYTICS -----------------------------
DB_PATH = "data/transactions.db"
TABLE = "transactions"

def _normalize_df(df):
    """
    Normalize incoming dataframe columns and preserve region & payment_mode if present.
    Returns columns: date, product, customer, region, payment_mode, quantity, amount
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "product", "customer", "region", "payment_mode", "quantity", "amount"])

    # map lowercase header -> original header name
    cmap = {c.lower().strip(): c for c in df.columns}

    def pick(*cands):
        for c in cands:
            key = c.lower().strip()
            if key in cmap:
                return cmap[key]
        return None

    # detect columns (expanded to include region/payment)
    date_c = pick("date", "order date", "order_date", "created_at")
    prod_c = pick("product", "item", "sku", "product name", "product_name")
    cust_c = pick("customer", "client", "buyer", "customer name", "customer_name")
    region_c = pick("region", "region name", "area", "zone")
    payment_c = pick("payment mode", "payment_mode", "paymentmethod", "payment method", "payment")
    qty_c  = pick("quantity", "qty", "units")
    amt_c  = pick("amount", "sales", "total", "revenue", "price", "grand total", "grand_total")

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_c], errors="coerce").dt.strftime("%Y-%m-%d") if date_c else ""
    out["product"] = df[prod_c].astype(str) if prod_c else ""
    out["customer"] = df[cust_c].astype(str) if cust_c else ""
    # preserve region and payment_mode (if present) otherwise empty string
    out["region"] = df[region_c].astype(str) if region_c else ""
    out["payment_mode"] = df[payment_c].astype(str) if payment_c else ""
    out["quantity"] = pd.to_numeric(df[qty_c], errors="coerce").fillna(1).astype(int) if qty_c else 1
    out["amount"] = pd.to_numeric(df[amt_c], errors="coerce").fillna(0.0) if amt_c else 0.0

    return out[["date", "product", "customer", "region", "payment_mode", "quantity", "amount"]]


def _load_filtered_df(start=None, end=None, product=None, customer=None):
    """
    Load data from DB and apply filters. Returns dataframe with columns:
    date, product, customer, region, payment_mode, quantity, amount
    """
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(columns=["date", "product", "customer", "region", "payment_mode", "quantity", "amount"])
    conn = sqlite3.connect(DB_PATH)
    try:
        raw = pd.read_sql_query(f"SELECT * FROM {TABLE}", conn)
    finally:
        conn.close()
    df = _normalize_df(raw)
    if start:
        df = df[pd.to_datetime(df["date"], errors="coerce") >= pd.to_datetime(start)]
    if end:
        df = df[pd.to_datetime(df["date"], errors="coerce") <= pd.to_datetime(end)]
    if product:
        df = df[df["product"].str.lower().str.contains(product.lower(), na=False)]
    if customer:
        df = df[df["customer"].str.lower().str.contains(customer.lower(), na=False)]
    # ensure numeric types and consistent formatting
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["date"] = df["date"].astype(str)
    # ensure region & payment_mode exist as strings
    df["region"] = df.get("region", "").astype(str)
    df["payment_mode"] = df.get("payment_mode", "").astype(str)
    return df


# ----- LIVE DASHBOARD ROUTE -----
@app.route('/live-dashboard')
def live_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    return render_template("dashboard.html", start_date=start_date, end_date=end_date)


# ----- API endpoint for charts -----
@app.route("/api/sales-data")
def api_sales_data():
    if not session.get('logged_in'):
        return jsonify({"error": "unauthorized"}), 401
    start = request.args.get("start_date") or None
    end = request.args.get("end_date") or None
    product = request.args.get("product") or None
    customer = request.args.get("customer") or None
    df = _load_filtered_df(start, end, product, customer)
    # return records with region & payment_mode included
    return jsonify(df.to_dict(orient="records"))


# ----- Export live dashboard data -----
@app.route("/live-dashboard-export/<filetype>")
def live_dashboard_export(filetype):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    start = request.args.get("start_date") or None
    end = request.args.get("end_date") or None
    product = request.args.get("product") or None
    customer = request.args.get("customer") or None
    df = _load_filtered_df(start, end, product, customer)

    if filetype.lower() == "excel":
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="DashboardData")
        bio.seek(0)
        fname = f"live_dashboard_{start or 'all'}_to_{end or 'all'}.xlsx"
        return send_file(bio, as_attachment=True, download_name=fname,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    if filetype.lower() == "pdf":
        plt.figure(figsize=(7, 4))
        if not df.empty:
            by_prod = df.groupby("product")["amount"].sum().sort_values(ascending=False).head(15)
            by_prod.plot(kind="bar")
            plt.ylabel("Amount")
            plt.title("Revenue by Product")
            plt.tight_layout()
        else:
            plt.text(0.5, 0.5, "No data for selected filters", ha="center", va="center")
            plt.axis("off")
        bio = BytesIO()
        plt.savefig(bio, format="pdf")
        plt.close()
        bio.seek(0)
        fname = f"live_dashboard_{start or 'all'}_to_{end or 'all'}.pdf"
        return send_file(bio, as_attachment=True, download_name=fname, mimetype="application/pdf")

    return "Invalid file type", 400


if __name__ == '__main__':
    app.run(debug=True)
