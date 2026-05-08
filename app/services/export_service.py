import pandas as pd
from fpdf import FPDF
import io
from datetime import datetime

async def generate_excel(data, filename_prefix="report"):
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return output.getvalue(), filename

async def generate_pdf(data, title="Report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    
    if not data:
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, "No data available", ln=True)
        return pdf.output(), f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    # Headers
    pdf.set_font("Arial", "B", 10)
    cols = list(data[0].keys())
    col_width = pdf.epw / len(cols)
    
    for col in cols:
        pdf.cell(col_width, 10, str(col), border=1)
    pdf.ln()
    
    # Data
    pdf.set_font("Arial", "", 9)
    for row in data:
        for col in cols:
            val = str(row.get(col, ""))
            pdf.cell(col_width, 8, val[:20], border=1) # Truncate for simplicity
        pdf.ln()
        
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return bytes(pdf.output()), filename
