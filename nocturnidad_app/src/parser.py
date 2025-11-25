import pdfplumber

def parse_pdf(file):
    registros = []
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if not table:
                    continue
                for row in table[1:]:
                    try:
                        fecha = row[0]
                        hi = row[15] if len(row) > 15 else None
                        hf = row[16] if len(row) > 16 else None
                        if hi and hf:
                            registros.append({
                                "fecha": fecha,
                                "hi": hi,
                                "hf": hf
                            })
                    except Exception:
                        continue
    except Exception as e:
        print("Error al leer PDF:", e)

    return registros
