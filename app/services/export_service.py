import io
import pandas as pd
from fpdf import FPDF
from datetime import datetime

async def generate_excel(data, filename_prefix="report"):
    """
    Generates an Excel file from a list of dictionaries.
    """
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    output.seek(0)
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return output.getvalue(), filename

async def generate_pdf(data, title="Report"):
    """
    Generates a PDF file from a list of dictionaries.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    
    if not data:
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "No data available", ln=True)
        return pdf.output(dest='S'), f"{title.lower()}_report.pdf"

    # Header
    pdf.set_font("Arial", "B", 10)
    columns = list(data[0].keys())
    col_width = pdf.epw / len(columns)
    
    for col in columns:
        pdf.cell(col_width, 10, str(col).capitalize(), border=1)
    pdf.ln()
    
    # Data
    pdf.set_font("Arial", size=9)
    for row in data:
        for col in columns:
            val = str(row.get(col, ""))
            # Handle long text
            if len(val) > 20:
                val = val[:17] + "..."
            pdf.cell(col_width, 10, val, border=1)
        pdf.ln()
    
    filename = f"{title.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return pdf.output(dest='S'), filename
