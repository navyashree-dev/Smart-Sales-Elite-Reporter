from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
import os
import textwrap

def generate_pdf_with_chart(report_text, chart_path, report_date, filename=None):
    # Ensure the reports directory exists
    os.makedirs("reports", exist_ok=True)

    if filename is None:
        filename = f"reports/report_{report_date}.pdf"

    # Initialize canvas
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4  # A4 size: 595x842 points

    # Margins and layout settings
    left_margin = 40
    right_margin = 40
    max_width = width - left_margin - right_margin
    line_height = 15
    wrap_width = 90  # Adjust depending on font & margins

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, f"Daily Sales Report - {report_date}")
    
    # Start text below title
    y = height - 80

    # Set font for body text
    c.setFont("Helvetica", 12)

    # Split input text by lines and wrap them nicely
    for line in report_text.split("\n"):
        wrapped_lines = textwrap.wrap(line, width=wrap_width)
        for wrap_line in wrapped_lines:
            if y < 100:  # Keep enough space for chart at bottom
                c.showPage()
                c.setFont("Helvetica", 12)
                y = height - 50
            c.drawString(left_margin, y, wrap_line)
            y -= line_height

    # Insert chart image at bottom of last page
    if chart_path and os.path.exists(chart_path):
        # Calculate position for image (centered horizontally)
        img_width = 400  # desired width in points
        img_height = 200  # approximate height
        img_x = (width - img_width) / 2
        img_y = 40  # margin from bottom

        c.drawImage(chart_path, img_x, img_y, width=img_width, height=img_height)

    c.save()

    return filename
