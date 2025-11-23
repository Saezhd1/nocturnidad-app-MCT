import pdfplumber
import re
from .utils import parse_date_ddmmyyyy

# Este parser asume el patrón de tabla del documento adjunto:
# Filas con Fecha y columnas HI / HF que contienen DOS tramos "HH:MM HH:MM"

ROW_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4}$")
H_PAIR_REGEX = re.compile(r"\b\d{2}:\d{2}\s+\d{2}:\d{2}\b")

def extract_text_tables(pdf_file_obj):
    with pdfplumber.open(pdf_file_obj) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text(x_tolerance=2, y_tolerance=2) or ""
        return full_text

def parse_pdf_file(pdf_file_obj):
    with pdfplumber.open(pdf_file_obj) as pdf:
        registros = []
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue
            for row in table:
                if not row or not row[0]:
                    continue
                try:
                    fecha = parse_date_ddmmyyyy(row[0])
                except:
                    continue
                hi = row[15] if len(row) > 15 else None
                hf = row[16] if len(row) > 16 else None
                registros.append({
                    'fecha': fecha,
                    'hi': hi,
                    'hf': hf
                })
    return registros
