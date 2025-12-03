from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from io import BytesIO

def _tabla_dias(resultados_por_pdf):
    rows = [["Archivo", "Fecha", "HI", "HF", "Minutos nocturnos", "Importe (€)"]]
    for doc in resultados_por_pdf:
        fn = doc['filename']
        for d in doc['dias']:
            if d['minutos_nocturnos'] > 0:
                rows.append([fn, d['fecha'], d['hi'], d['hf'],
                             str(d['minutos_nocturnos']), d['importe']])
    return rows

def _tabla_mes(resumen):
    rows = [["Mes/Año", "Minutos", "Importe (€)", "Días"]]
    for k, v in sorted(resumen['por_mes'].items()):
        rows.append([k, str(v['minutos']), f"{v['importe']:.2f}", str(v['dias'])])
    return rows

def _tabla_global(resumen):
    t = resumen['global']
    return [["Total minutos", "Total importe (€)", "Total días"],
            [str(t['minutos']), f"{t['importe']:.2f}", str(t['dias'])]]

def exportar_pdf_informe(empleado, nombre, resultados, resumen):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=36, rightMargin=36,
                            topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Cabecera
    story += [Paragraph("Informe de nocturnidad", styles['Title']),
              Spacer(1, 12),
              Paragraph(f"Empleado: {empleado} | Nombre: {nombre}", styles['Normal']),
              Spacer(1, 24)]

    # Tabla detalle
    dias_tbl = Table(_tabla_dias(resultados))
    dias_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eeeeee')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.gray),
        ('ALIGN', (4,1), (5,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ]))
    story += [Paragraph("Detalle por tramos", styles['Heading2']),
              Spacer(1, 6), dias_tbl, Spacer(1, 18)]

    # Tabla mensual
    mes_tbl = Table(_tabla_mes(resumen))
    mes_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eeeeee')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.gray),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ]))
    story += [Paragraph("Resumen mensual", styles['Heading2']),
              Spacer(1, 6), mes_tbl, Spacer(1, 18)]

    # Tabla global
    global_tbl = Table(_tabla_global(resumen))
    global_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eeeeee')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.gray),
        ('ALIGN', (0,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ]))
    story += [Paragraph("Resumen global", styles['Heading2']),
              Spacer(1, 6), global_tbl]

    # Construir PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
