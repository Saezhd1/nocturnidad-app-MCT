import os
from flask import Flask, render_template, request, redirect, url_for, send_file, session
from src.parser import parse_pdf
from src.nocturnidad import calcular_nocturnidad_por_dia
from src.pdf_export import exportar_pdf_informe

app = Flask(__name__)
app.secret_key = "supersecretkey"  # cámbialo por algo seguro en producción

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("pdfs")
    empleado = request.form.get("empleado")
    nombre = request.form.get("nombre")

    resultados = []
    resumen = {"por_mes": {}, "global": {"minutos": 0, "importe": 0, "dias": 0}}

    for f in files:
        registros = parse_pdf(f)
        calculado = calcular_nocturnidad_por_dia(registros)
        resultados.append({"filename": f.filename, "dias": calculado})

        # actualizar resumen global
        for d in calculado:
            minutos = d["minutos_nocturnos"]
            importe = float(d["importe"])
            if minutos > 0:
                resumen["global"]["minutos"] += minutos
                resumen["global"]["importe"] += importe
                resumen["global"]["dias"] += 1

    # guardar en sesión para descargar después
    session["payload"] = {
        "empleado": empleado,
        "nombre": nombre,
        "resultados": resultados,
        "resumen": resumen,
    }

    return render_template("result.html", empleado=empleado, nombre=nombre,
                           resultados=resultados, resumen=resumen)

# ✅ Ruta simple y estable
@app.route("/download")
def download():
    payload = session.get("payload")
    if not payload:
        return redirect(url_for("index"))

    buffer = exportar_pdf_informe(
        empleado=payload["empleado"],
        nombre=payload["nombre"],
        resultados=payload["resultados"],
        resumen=payload["resumen"]
    )
    buffer.seek(0)

    return send_file(buffer,
                     mimetype="application/pdf",
                     as_attachment=True,
                     download_name=f"informe_{payload['empleado']}.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
