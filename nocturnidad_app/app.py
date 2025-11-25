from flask import Flask, render_template, request
from src.parser import parse_pdf
from src.nocturnidad import calcular_nocturnidad_global
from src.aggregator import agregar_resumen

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    # Comprobaciones defensivas
    if "file" not in request.files:
        return "No se ha enviado ningún archivo", 400

    file = request.files["file"]
    if file.filename == "":
        return "Archivo vacío", 400

    empleado = request.form.get("empleado", "")
    nombre = request.form.get("nombre", "")

    # 1. Parsear PDF
    registros = parse_pdf(file)

    # 2. Calcular nocturnidad
    calc = calcular_nocturnidad_global(registros)
    resultados = calc["detalle"]  # lista de dicts con fecha, hi, hf, minutos, importe

    # 3. Resumen mensual y global
    resumen_mensual, resumen_global = agregar_resumen(resultados)

    # 4. Renderizar plantilla
    return render_template(
        "result.html",
        empleado=empleado,
        nombre=nombre,
        resultados=resultados,
        resumen_mensual=resumen_mensual,
        resumen_global=resumen_global
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
