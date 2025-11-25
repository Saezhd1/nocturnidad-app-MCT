import pdfplumber
import re

# Regex estricta para horas válidas HH:MM (00–23)
HHMM = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")

def _in_range(xmid, xr, tol=2):
    return xr[0] - tol <= xmid <= xr[1] + tol

def _find_columns(page):
    """
    Encuentra rangos X para columnas clave. Si no detecta cabeceras,
    usa rangos fijos calibrados para el modelo TITSA.
    """
    words = page.extract_words(use_text_flow=True)
    fecha_x = hi_x = hf_x = None
    header_bottom = page.bbox[1] + 40

    for w in words:
        t = (w.get("text") or "").strip().lower()
        if t == "fecha":
            fecha_x = (w["x0"], w["x1"]); header_bottom = max(header_bottom, w["bottom"])
        elif t == "hi":
            hi_x = (w["x0"], w["x1"]); header_bottom = max(header_bottom, w["bottom"])
        elif t == "hf":
            hf_x = (w["x0"], w["x1"]); header_bottom = max(header_bottom, w["bottom"])

    # Fallback si no encuentra cabeceras
    if not (fecha_x and hi_x and hf_x):
        x0_page, x1_page = page.bbox[0], page.bbox[2]
        width = x1_page - x0_page
        fecha_x = (x0_page + 0.06 * width, x0_page + 0.22 * width)
        hi_x    = (x0_page + 0.69 * width, x0_page + 0.81 * width)
        hf_x    = (x0_page + 0.81 * width, x0_page + 0.95 * width)

    return {"fecha": fecha_x, "hi": hi_x, "hf": hf_x, "header_bottom": header_bottom}

def parse_pdf(file):
    registros = []
    try:
        with pdfplumber.open(file) as pdf:
            last_fecha = None
            for page in pdf.pages:
                text_probe = (page.extract_text() or "").lower()
                # Saltar páginas de totales
                if "tabla de totalizados" in text_probe and "fecha" not in text_probe:
                    continue

                cols = _find_columns(page)
                words = page.extract_words(x_tolerance=2, y_tolerance=2, use_text_flow=False)

                # Agrupar por línea
                lines = {}
                for w in words:
                    if w["top"] <= cols["header_bottom"]:
                        continue
                    y_key = round(w["top"], 1)
                    lines.setdefault(y_key, []).append(w)

                for y in sorted(lines.keys()):
                    row_words = sorted(lines[y], key=lambda k: k["x0"])

                    fecha_tokens, hi_tokens, hf_tokens = [], [], []
                    for w in row_words:
                        t = (w.get("text") or "").strip()
                        xmid = (w["x0"] + w["x1"]) / 2.0
                        if _in_range(xmid, cols["fecha"]):
                            fecha_tokens.append(t)
                        elif _in_range(xmid, cols["hi"]):
                            hi_tokens.append(t)
                        elif _in_range(xmid, cols["hf"]):
                            hf_tokens.append(t)

                    fecha_val = " ".join(fecha_tokens).strip()
                    hi_raw = " ".join(hi_tokens).strip()
                    hf_raw = " ".join(hf_tokens).strip()

                    # Herencia de fecha en filas partidas
                    if not fecha_val and (hi_raw or hf_raw) and last_fecha:
                        fecha_val = last_fecha
                    elif fecha_val:
                        last_fecha = fecha_val

                    # Filtrar registros sin fecha
                    if not fecha_val.strip():
                        continue

                    # Extraer horas completas con finditer
                    hi_list = [m.group(0) for m in HHMM.finditer(hi_raw)]
                    hf_list = [m.group(0) for m in HHMM.finditer(hf_raw)]

                    if not hi_list or not hf_list:
                        continue

                    # Tramo principal
                    registros.append({
                        "fecha": fecha_val,
                        "hi": hi_list[0],
                        "hf": hf_list[-1],
                        "principal": True
                    })

                    # Tramo secundario
                    if len(hi_list) >= 2 and len(hf_list) >= 2:
                        registros.append({
                            "fecha": fecha_val,
                            "hi": hi_list[1],
                            "hf": hf_list[0],
                            "principal": False
                        })
    except Exception as e:
        print("[parser] Error al leer PDF:", e)

    print(f"[parser] Registros extraídos: {len(registros)}")
    for r in registros[:6]:
        print("[parser] Ej:", r)
    return registros
