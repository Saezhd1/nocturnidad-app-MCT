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

def parse_pdf(file):
    registros = []
    try:
        with pdfplumber.open(file) as pdf:
            last_fecha = None
            for page in pdf.pages:
                cols = _find_columns(page)
                # Palabras con tolerancias pequeñas para que se agrupen por línea
                words = page.extract_words(x_tolerance=2, y_tolerance=2, use_text_flow=False)

                # Agrupar por línea (clave: y redondeada)
                lines = {}
                for w in words:
                    if w["top"] <= cols["header_bottom"]:
                        continue
                    y_key = round(w["top"], 1)
                    lines.setdefault(y_key, []).append(w)

                # Ordenar por vertical
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

                    # Consolidar
                    fecha_val = " ".join(fecha_tokens).strip()
                    hi_raw = " ".join(hi_tokens).strip()
                    hf_raw = " ".join(hf_tokens).strip()

                    # Heredar fecha en filas partida (rowspan visual)
                    if not fecha_val and last_fecha:
                        fecha_val = last_fecha
                    elif fecha_val:
                        last_fecha = fecha_val

                    # Filtrar si no hay horas en ninguna columna
                    if not (hi_raw or hf_raw): 
                        continue

                    # Extraer horas HH:MM y descartar ruidos (00, números sueltos)
                    hi_list = [x for x in hi_raw.split() if ":" in x and x.count(":") == 1]
                    hf_list = [x for x in hf_raw.split() if ":" in x and x.count(":") == 1]

                    if not hi_list or not hf_list:
                        continue

                    # Regla Daniel:
                    # - Principal: HI arriba (índice 0) con HF abajo (último)
                    # - Secundario: si hay dos, HI abajo (índice 1) con HF arriba (índice 0)
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
        print("[parser] Error al leer PDF:", e)

    print(f"[parser] Registros extraídos: {len(registros)}")
    for r in registros[:6]:
        print("[parser] Ej:", r)
    return registros
