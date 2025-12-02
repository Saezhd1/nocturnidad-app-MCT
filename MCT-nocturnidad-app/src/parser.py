import pdfplumber

def _in_range(xmid, xr, tol=2):
    return xr[0] - tol <= xmid <= xr[1] + tol

def _find_columns(page):
    """
    Encuentra rangos X para columnas clave. Prioriza cabeceras reales; si falla, usa rangos fijos
    ajustados a este modelo de TITSA.
    """
    words = page.extract_words(use_text_flow=True)
    fecha_x = hi_x = hf_x = None
    header_bottom = page.bbox[1] + 40  # altura aproximada bajo cabecera

    for w in words:
        t = (w.get("text") or "").strip().lower()
        if t == "fecha":
            fecha_x = (w["x0"], w["x1"]); header_bottom = max(header_bottom, w["bottom"])
        elif t == "hi":
            hi_x = (w["x0"], w["x1"]); header_bottom = max(header_bottom, w["bottom"])
        elif t == "hf":
            hf_x = (w["x0"], w["x1"]); header_bottom = max(header_bottom, w["bottom"])

    # Fallback “hardcodeado” para este modelo si no encuentra cabeceras
    if not (fecha_x and hi_x and hf_x):
        x0_page, x1_page = page.bbox[0], page.bbox[2]
        width = x1_page - x0_page
        fecha_x = (x0_page + 0.06 * width, x0_page + 0.22 * width)
        hi_x    = (x0_page + 0.69 * width, x0_page + 0.81 * width)
        hf_x    = (x0_page + 0.81 * width, x0_page + 0.95 * width)

    return {"fecha": fecha_x, "hi": hi_x, "hf": hf_x, "header_bottom": header_bottom}

def _normalize_hour(h):
    """
    Normaliza horas especiales:
    - '00:59' se interpreta como '24:59'
    - Cualquier hora >= 24:XX se convierte a 00:XX (manteniendo la fecha)
    """
    h = h.strip()
    if not h or ":" not in h:
        return h
    try:
        hh, mm = h.split(":")
        hh = int(hh)
        mm = int(mm)
    except ValueError:
        return h

    # Caso especial: 00:59 → 24:59
    if hh == 0 and mm == 59:
        return "24:59"

    # Caso general: si hora >= 24, restamos 24
    if hh >= 24:
        hh = hh - 24
        return f"{hh:02d}:{mm:02d}"

    return f"{hh:02d}:{mm:02d}"

def parse_pdf(file):
    registros = []
    try:
        with pdfplumber.open(file) as pdf:
            last_fecha = None
            for page in pdf.pages:
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

                    if not fecha_val and last_fecha:
                        fecha_val = last_fecha
                    elif fecha_val:
                        last_fecha = fecha_val

                    if not (hi_raw or hf_raw):
                        continue

                    hi_list = [_normalize_hour(x) for x in hi_raw.split() if ":" in x and x.count(":") == 1]
                    hf_list = [_normalize_hour(x) for x in hf_raw.split() if ":" in x and x.count(":") == 1]

                    if not hi_list or not hf_list:
                        continue

                    principal_hi = hi_list[0]
                    principal_hf = hf_list[-1]
                    registros.append({
                        "fecha": fecha_val,
                        "hi": principal_hi,
                        "hf": principal_hf,
                        "principal": True
                    })

                    if len(hi_list) >= 2 and len(hf_list) >= 2:
                        registros.append({
                            "fecha": fecha_val,
                            "hi": hi_list[1],
                            "hf": hf_list[0],
                            "principal": False
                        })
    except Exception as e:
        print(f"[parser] Error al leer PDF {file}:", e)

    print(f"[parser] Registros extraídos de {file}: {len(registros)}")
    for r in registros[:6]:
        print("[parser] Ej:", r)
    return registros

def parse_multiple_pdfs(files):
    """
    Analiza varios PDFs y devuelve un diccionario con resultados por archivo.
    """
    all_results = {}
    for f in files:
        print(f"\n[parser] Procesando {f}...")
        all_results[f] = parse_pdf(f)
    return all_results
