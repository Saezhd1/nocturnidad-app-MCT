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
    text = extract_text_tables(pdf_file_obj)

    # Extraemos filas por día: buscamos líneas con fecha y las HI / HF posteriores
    registros = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if ROW_REGEX.match(line):
            fecha = parse_date_ddmmyyyy(line)
            # en las siguientes ~10 líneas buscamos las columnas HI y HF (cada una con dos horas)
            hi, hf = None, None
            ventana = lines[i:i+18]  # acotamos
            for cand in ventana:
                m = H_PAIR_REGEX.search(cand)
                if m and hi is None:
                    hi = m.group(0)  # e.g. "15:42 18:54"
                elif m and hf is None and cand != hi:
                    hf = m.group(0)
                if hi and hf:
                    break

            registros.append({
                'fecha': fecha,
                'hi': hi,   # puede ser None si día sin trabajo
                'hf': hf
            })
        i += 1

    return registros