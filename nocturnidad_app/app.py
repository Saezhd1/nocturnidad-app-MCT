from flask import Flask, render_template, request, send_file, redirect, url_for
import io
from src.parser import parse_pdf_file
from src.nocturnidad import calcular_nocturnidad_por_dia
from src.aggregator import agregar_por_mes_y_global
from src.pdf_export import exportar_pdf_informe

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB

# Memoria simple en sesión de proceso (puedes sustituir por DB si lo necesitas)
CACHE = {}

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('files')
    empleado = request.form.get('empleado', '').strip()
    nombre = request.form.get('nombre', '').strip()

    if not empleado or not nombre:
        return redirect(url_for('index'))

    resultados_por_pdf = []
    for f in files:
        if not f or f.filename == '':
            continue
        data = f.read()
        # Parse de un PDF individual
        registros = parse_pdf_file(io.BytesIO(data))
        # Cálculo de nocturnidad por día
        calculado = calcular_nocturnidad_por_dia(registros)
        resultados_por_pdf.append({
            'filename': f.filename,
            'dias': calculado
        })

    # Agregados mensual y global
    resumen = agregar_por_mes_y_global(resultados_por_pdf)

    key = f"{empleado}:{nombre}"
    CACHE[key] = {
        'empleado': empleado,
        'nombre': nombre,
        'resultados': resultados_por_pdf,
        'resumen': resumen
    }

    return render_template('result.html', key=key, resultados=resultados_por_pdf, resumen=resumen, empleado=empleado, nombre=nombre)

@app.route('/download/<key>', methods=['GET'])
def download(key):
    if key not in CACHE:
        return redirect(url_for('index'))

    payload = CACHE[key]
    buffer = exportar_pdf_informe(
        empleado=payload['empleado'],
        nombre=payload['nombre'],
        resultados=payload['resultados'],
        resumen=payload['resumen']
    )
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"informe_nocturnidad_{payload['empleado']}.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
    