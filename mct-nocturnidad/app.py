# app.py
# Aplicación Flask mínima para subir varios PDFs, extraer la primera tabla,
# calcular minutos nocturnos según reglas y generar un informe PDF descargable.

import io
import json
from datetime import datetime, time, timedelta
from collections import defaultdict, OrderedDict

from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import pdfplumber
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "cambia_esta_clave_por_una_segura"  # Cambia en producción

# Reglas y constantes
FECHA_MINIMA = datetime.strptime("30/03/2022", "%d/%m/%Y").date()
TARIFA_ANTERIOR_FIN = datetime.strptime("25/04/2025", "%d/%m/%Y").date()
TARIFA_ANTERIOR = 0.05
TARIFA_NUEVA = 0.062

# Tramos nocturnos base (en minutos desde 00:00)
TRAMOS = [
    (22 * 60, 24 * 60 + 59),  # 22:00 - 00:59 (00:59 tratado como 24:59)
    (4 * 60, 6 * 60)          # 04:00 - 06:00
]

def parse_time_str(tstr):
    """
    Intenta extraer una hora en formato HH:MM desde una cadena.
    Devuelve minutos desde 00:00 (int) o None si no se puede parsear.
    """
    if not tstr or not isinstance(tstr, str):
        return None
    tstr = tstr.strip()
    # Normalizar separadores
    tstr = tstr.replace('.', ':').replace(',', ':')
    # Buscar patrón HH:MM
    parts = tstr.split()
    # Tomar la primera parte que contenga ':'
    candidate = None
    for p in parts:
        if ':' in p:
            candidate = p
            break
    if candidate is None:
        candidate = tstr if ':' in tstr else None
    if candidate is None:
        return None
    try:
        hh, mm = candidate.split(':')[:2]
        hh = int(hh)
        mm = int(mm)
        # Si hora es 0-59 y queremos tratar 00:59 como 24:59, lo manejamos más tarde
        return hh * 60 + mm
    except Exception:
        return None

def normalize_hi_hf(hi_cell, hf_cell):
    """
    Según reglas:
    - En HI tomar la referencia de la línea superior (si hay saltos de línea)
    - En HF tomar la referencia de la línea inferior
    """
    hi = None
    hf = None
    if isinstance(hi_cell, str):
        lines = [l.strip() for l in hi_cell.splitlines() if l.strip()]
        if lines:
            hi = lines[0]  # línea superior
    if isinstance(hf_cell, str):
        lines = [l.strip() for l in hf_cell.splitlines() if l.strip()]
        if lines:
            hf = lines[-1]  # línea inferior
    # Si no son strings, intentar convertir a str
    if hi is None and hi_cell is not None:
        hi = str(hi_cell).strip()
    if hf is None and hf_cell is not None:
        hf = str(hf_cell).strip()
    return hi, hf

def minutes_overlap(a_start, a_end, b_start, b_end):
    """Devuelve minutos de solapamiento entre dos intervalos [start,end] en minutos."""
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    return max(0, end - start + 1)  # +1 para incluir minuto final como en 00:59=24:59

def compute_nocturnal_minutes(hi_min, hf_min):
    """
    hi_min, hf_min en minutos desde 00:00; si hf_min < hi_min asumimos cruce de medianoche y sumamos 1440 a hf.
    Consideramos tramos nocturnos en el mismo día y en el día siguiente (para cruce medianoche).
    """
    if hi_min is None or hf_min is None:
        return 0
    # Ajuste 00:59 como 24:59: si un tiempo está entre 0 y 59 (inclusive) y representa HF o similar,
    # lo manejaremos con la lógica de cruce de medianoche (añadiendo 1440 cuando corresponda).
    start = hi_min
    end = hf_min
    if end < start:
        end += 1440  # cruza medianoche

    total = 0
    # Comprobar tramos nocturnos en día base y día siguiente (sumando 1440)
    for base in (0, 1440):
        for tramo in TRAMOS:
            t_start = tramo[0] + base
            t_end = tramo[1] + base
            total += minutes_overlap(start, end, t_start, t_end)
    return total

def tarifa_por_fecha(fecha_obj):
    if fecha_obj <= TARIFA_ANTERIOR_FIN:
        return TARIFA_ANTERIOR
    else:
        return TARIFA_NUEVA

def extract_first_table_from_pdf(file_stream):
    """
    Extrae la primera tabla encontrada en el PDF usando pdfplumber.
    Devuelve un DataFrame (pandas) o None si no se encuentra tabla.
    """
    try:
        with pdfplumber.open(file_stream) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    # Tomamos la primera tabla encontrada
                    table = tables[0]
                    # Convertir a DataFrame: la primera fila puede ser cabecera
                    df = pd.DataFrame(table)
                    # Si la primera fila parece cabecera (contiene 'Fecha' o 'HI' o 'HF'), la usamos
                    header_candidates = df.iloc[0].astype(str).str.lower().tolist()
                    if any('fecha' in str(h) for h in header_candidates) or any('hi' in str(h) for h in header_candidates) or any('hf' in str(h) for h in header_candidates):
                        df.columns = df.iloc[0]
                        df = df[1:].reset_index(drop=True)
                    else:
                        # Si no hay cabecera clara, dejamos índices numéricos
                        df = df.reset_index(drop=True)
                    return df
    except Exception as e:
        print("Error leyendo PDF:", e)
    return None

def find_columns(df):
    """
    Busca columnas Fecha, HI, HF (insensible a mayúsculas).
    Devuelve nombres de columnas encontrados o None si no se encuentran.
    """
    cols = list(df.columns)
    lower = [str(c).lower() for c in cols]
    fecha_col = None
    hi_col = None
    hf_col = None
    for i, name in enumerate(lower):
        if 'fecha' in name:
            fecha_col = cols[i]
        if name.strip() in ('hi', 'h.i', 'hora inicio', 'hora_inicio', 'hora inicio'):
            hi_col = cols[i]
        if name.strip() in ('hf', 'h.f', 'hora fin', 'hora_final', 'hora final', 'hora_fin'):
            hf_col = cols[i]
    # Si no detecta por nombres exactos, intentar heurística
    if fecha_col is None:
        for i, name in enumerate(lower):
            if 'date' in name or 'fecha' in name:
                fecha_col = cols[i]
                break
    if hi_col is None:
        for i, name in enumerate(lower):
            if 'hi' in name or 'inicio' in name or 'hora' in name and 'in' in name:
                hi_col = cols[i]
                break
    if hf_col is None:
        for i, name in enumerate(lower):
            if 'hf' in name or 'fin' in name or 'hora' in name and 'fi' in name:
                hf_col = cols[i]
                break
    return fecha_col, hi_col, hf_col

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        employee_name = request.form.get("employee_name", "").strip()
        employee_code = request.form.get("employee_code", "").strip()
        files = request.files.getlist("pdfs")
        if not employee_name or not employee_code:
            flash("Indica Nombre completo y Código de empleado.", "danger")
            return redirect(url_for("index"))
        if not files or len(files) == 0:
            flash("Adjunta al menos un PDF.", "danger")
            return redirect(url_for("index"))

        rows = []
        # Procesar cada PDF
        for f in files:
            try:
                df = extract_first_table_from_pdf(f)
                if df is None:
                    continue
                fecha_col, hi_col, hf_col = find_columns(df)
                if not fecha_col or not hi_col or not hf_col:
                    # intentar columnas por posición si hay al menos 3 columnas
                    if df.shape[1] >= 3:
                        fecha_col = df.columns[0]
                        hi_col = df.columns[1]
                        hf_col = df.columns[2]
                    else:
                        continue
                for _, r in df.iterrows():
                    raw_fecha = r.get(fecha_col)
                    raw_hi = r.get(hi_col)
                    raw_hf = r.get(hf_col)
                    # Normalizar strings
                    fecha_str = str(raw_fecha).strip() if raw_fecha is not None else ""
                    # Intentar parsear fecha en varios formatos
                    fecha_obj = None
                    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
                        try:
                            fecha_obj = datetime.strptime(fecha_str, fmt).date()
                            break
                        except Exception:
                            continue
                    if fecha_obj is None:
                        # Si no se puede parsear, saltar fila
                        continue
                    if fecha_obj < FECHA_MINIMA:
                        continue  # no analizamos fechas anteriores

                    hi_text, hf_text = normalize_hi_hf(raw_hi, raw_hf)
                    hi_min = parse_time_str(hi_text) if hi_text else None
                    hf_min = parse_time_str(hf_text) if hf_text else None

                    if hi_min is None or hf_min is None:
                        # Si alguna está vacía, pasamos al día siguiente (omitimos)
                        continue

                    minutos_nocturnos = compute_nocturnal_minutes(hi_min, hf_min)
                    if minutos_nocturnos <= 0:
                        continue  # omitimos línea si no hay minutos nocturnos

                    tarifa = tarifa_por_fecha(fecha_obj)
                    importe = minutos_nocturnos * tarifa

                    # Formatear horas para mostrar (mantener las cadenas originales si existen)
                    hi_display = hi_text if hi_text else ""
                    hf_display = hf_text if hf_text else ""

                    rows.append({
                        "fecha": fecha_obj.strftime("%d/%m/%Y"),
                        "fecha_obj": fecha_obj.isoformat(),
                        "hi": hi_display,
                        "hf": hf_display,
                        "minutos": int(minutos_nocturnos),
                        "importe": round(float(importe), 2)
                    })
            except Exception as e:
                print("Error procesando archivo:", e)
                continue

        # Resumen mensual, anual y global
        monthly = OrderedDict()
        annual = OrderedDict()
        global_min = 0
        global_imp = 0.0
        for r in rows:
            d = datetime.strptime(r["fecha"], "%d/%m/%Y")
            mes_key = d.strftime("%Y-%m")
            anio_key = d.strftime("%Y")
            monthly.setdefault(mes_key, {"mes": mes_key, "minutos": 0, "importe": 0.0})
            annual.setdefault(anio_key, {"anio": anio_key, "minutos": 0, "importe": 0.0})
            monthly[mes_key]["minutos"] += r["minutos"]
            monthly[mes_key]["importe"] += r["importe"]
            annual[anio_key]["minutos"] += r["minutos"]
            annual[anio_key]["importe"] += r["importe"]
            global_min += r["minutos"]
            global_imp += r["importe"]

        # Convertir dicts a listas ordenadas
        monthly_list = [ {"mes": k, "minutos": v["minutos"], "importe": round(v["importe"],2)} for k,v in monthly.items() ]
        annual_list = [ {"anio": k, "minutos": v["minutos"], "importe": round(v["importe"],2)} for k,v in annual.items() ]

        summary = {
            "monthly": monthly_list,
            "annual": annual_list,
            "global": {"minutos": int(global_min), "importe": round(global_imp, 2)}
        }

        # Pasar los datos serializados al template para vista previa y para descarga
        payload = {
            "employee_name": employee_name,
            "employee_code": employee_code,
            "rows": rows,
            "summary": summary
        }

        return render_template("preview.html", employee_name=employee_name,
                               employee_code=employee_code, rows=rows, summary=summary,
                               payload_json=json.dumps(payload))
    return render_template("index.html")

@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    """
    Recibe JSON con los datos (desde la vista previa) y genera un PDF con reportlab.
    """
    data_json = request.form.get("payload")
    if not data_json:
        flash("No hay datos para generar el PDF.", "danger")
        return redirect(url_for("index"))
    data = json.loads(data_json)
    employee_name = data.get("employee_name", "")
    employee_code = data.get("employee_code", "")
    rows = data.get("rows", [])
    summary = data.get("summary", {})

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    title_style = styles["Heading1"]

    # Header: logo y título
    logo_path = "static/logo.png"
    try:
        c.drawImage(logo_path, 15*mm, height - 30*mm, width=30*mm, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50*mm, height - 20*mm, "MCT cálculo complemento de nocturnidad")
    c.setFont("Helvetica", 10)
    c.drawString(50*mm, height - 26*mm, f"Código de empleado: {employee_code}")
    c.drawString(50*mm, height - 32*mm, f"Nombre completo: {employee_name}")

    y = height - 42*mm

    # Tabla de detalle
    if rows:
        data_table = [["Fecha", "Hora Inicio", "Hora Fin", "Minutos nocturnos", "Importe (€)"]]
        for r in rows:
            data_table.append([r["fecha"], r["hi"], r["hf"], str(r["minutos"]), f"{r['importe']:.2f}"])
        table = Table(data_table, colWidths=[40*mm, 30*mm, 30*mm, 40*mm, 30*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f0f4ff")),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (3,1), (4,-1), 'RIGHT'),
        ]))
        w, h = table.wrapOn(c, width-30*mm, y)
        table.drawOn(c, 15*mm, y - h)
        y = y - h - 8*mm
    else:
        c.setFont("Helvetica", 10)
        c.drawString(15*mm, y, "No se han detectado días con minutos nocturnos según los PDFs subidos y las reglas aplicadas.")
        y -= 10*mm

    # Resumen mensual
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15*mm, y, "Resumen mensual")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    monthly = summary.get("monthly", [])
    for m in monthly:
        c.drawString(18*mm, y, f"{m['mes']} — {m['minutos']} min — {m['importe']:.2f} €")
        y -= 5*mm
        if y < 40*mm:
            c.showPage()
            y = height - 30*mm

    # Resumen anual
    y -= 4*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15*mm, y, "Resumen anual")
    y -= 6*mm
    c.setFont("Helvetica", 10)
    annual = summary.get("annual", [])
    for a in annual:
        c.drawString(18*mm, y, f"{a['anio']} — {a['minutos']} min — {a['importe']:.2f} €")
        y -= 5*mm
        if y < 40*mm:
            c.showPage()
            y = height - 30*mm

    # Resumen global
    y -= 6*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15*mm, y, "Total global")
    y -= 6*mm
    global_s = summary.get("global", {})
    c.setFont("Helvetica", 10)
    c.drawString(18*mm, y, f"{global_s.get('minutos',0)} min — {global_s.get('importe',0.0):.2f} €")
    y -= 12*mm

    # Nota legal
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y, "Nota legal")
    y -= 6*mm
    c.setFont("Helvetica", 9)
    c.drawString(15*mm, y, "Cálculo según ACTA JUZGADO DE LO SOCIAL Nº4 Procedimiento Nº0000055/2025")
    y -= 5*mm
    c.drawString(15*mm, y, "Importes desde 30/03/2022 hasta 25/04/2025 1h=3€ 0,05€min")
    y -= 5*mm
    c.drawString(15*mm, y, "Importes desde 26/04/2025 1h=3,72€ 0,062€min")
    y -= 12*mm

    # Footer
    c.setFont("Helvetica", 9)
    c.drawString(15*mm, 12*mm, "Movimiento Social Laboral de Conductores de TITSA")
    # Número de página
    c.drawRightString(width - 15*mm, 12*mm, "Página 1")

    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="informe_nocturnidad.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)