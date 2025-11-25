import re
import pdfplumber

FECHA_REGEX = re.compile(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b")
HORA_REGEX = re.compile(r"\b\d{1,2}[:.]\d{2}\b")

def normalizar_hora(h):
    # '5:00', '05.00' -> '05:00'
    partes = h.replace(".", ":").split(":")
    return f"{int(partes[0]):02d}:{partes[1]}"

def parse_pdf(file):
    registros = []

    with pdfplumber.open(file) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(use_text_flow=True) or []
            if not words:
                continue

            # Agrupar por línea con tolerancia vertical
            lines = []
            current = []
            last_top = None
            tol = 2.0  # tolerancia de y (ajustable según el PDF)

            for w in words:
                top = float(w.get("top", 0))
                text = w.get("text", "").strip()

                if last_top is None or abs(top - last_top) <= tol:
                    current.append(text)
                    last_top = top
                else:
                    if current:
                        lines.append(" ".join(current))
                    current = [text]
                    last_top = top

            if current:
                lines.append(" ".join(current))

            # Buscar fecha y horas en cada línea reconstruida
            for line in lines:
                fecha_m = FECHA_REGEX.search(line)
                if not fecha_m:
                    continue
                fecha = fecha_m.group(0).replace("-", "/")

                horas = HORA_REGEX.findall(line)
                if len(horas) >= 2:
                    hi = normalizar_hora(horas[0])
                    hf = normalizar_hora(horas[1])
                    registros.append({
                        "fecha": fecha,
                        "hi": hi,
                        "hf": hf,
                        "principal": line
                    })

    print("[parser] Registros extraídos:", len(registros))
    return registros
