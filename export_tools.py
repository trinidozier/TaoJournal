import pandas as pd
from fpdf import FPDF
from tkinter import filedialog

def export_to_excel(trades):
    df = pd.DataFrame(trades)
    save_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel Files", "*.xlsx")])
    if save_path:
        df.to_excel(save_path, index=False)

def export_to_pdf(trades):
    save_path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                             filetypes=[("PDF Files", "*.pdf")])
    if not save_path:
        return

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

    pdf.output(save_path)
