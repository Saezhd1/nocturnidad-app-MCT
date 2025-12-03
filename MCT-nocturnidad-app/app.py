from flask import Flask, render_template, request, session, send_file
from io import BytesIO
from src.parser import parse_pdf
from src.nocturnidad import calcular_nocturnidad_por_dia
from src.aggregator import agregar_resumen
from src.pdf_export import exportar_pdf_informe

app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("pdfs")
    empleado = request.form.get("empleado") or ""
    nombre = request.form.get("nombre") or ""

    resultados = []
    for f in files:
        regs = parse_pdf(f)
        dias = calcular_nocturnidad_por_dia(regs)
        resultados.append({"filename": f.filename, "dias": dias})

    resumen = agregar_resumen(resultados)

    session["payload"] = {
        "empleado": empleado,
        "nombre": nombre,
        "resultados": resultados,
        "resumen": resumen,
    }
    return render_template("result.html", empleado=empleado, nombre=nombre,
                           resultados=resultados, resumen=resumen)

@app.route("/download")
def download():
    payload = session.get("payload")
    if not payload:
        return "No hay datos para exportar"
    buffer = exportar_pdf_informe(payload["empleado"], payload["nombre"],
                                  payload["resultados"], payload["resumen"])
    return send_file(buffer, as_attachment=True,
                     download_name="informe_nocturnidad.pdf",
                     mimetype="application/pdf")
