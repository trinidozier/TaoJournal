import pandas as pd
from fpdf import FPDF
import os
from datetime import datetime

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

def export_to_excel(trades, filename=None):
    df = pd.DataFrame(trades)
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{EXPORT_DIR}/trades_{timestamp}.xlsx"
    df.to_excel(filename, index=False)
    return filename

def export_to_pdf(trades, filename=None):
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{EXPORT_DIR}/trades_{timestamp}.pdf"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    for trade in trades:
        pdf.set_font("Arial", 'B', size=10)
        pdf.cell(200, 10, txt=f"Trade ID: {trade.get('ID', 'N/A')}", ln=True)
        pdf.set_font("Arial", size=10)
        for key, value in trade.items():
            if key != 'ID':
                pdf.cell(200, 8, txt=f"{key}: {value}", ln=True)
        pdf.ln(5)

    pdf.output(filename)
    return filename
