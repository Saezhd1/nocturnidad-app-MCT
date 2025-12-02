from flask import Flask, render_template, send_file
from parser import parse_multiple_pdfs
import pdfkit

app = Flask(__name__)

FILES = ["turnos1.pdf", "turnos2.pdf"]

@app.route("/")
def index():
    resultados = parse_multiple_pdfs(FILES)
    return render_template("result.html", resultados=resultados)

@app.route("/download")
def download_pdf():
    resultados = parse_multiple_pdfs(FILES)
    # Renderizamos el HTML con Jinja
    from flask import render_template_string
    html = render_template("result.html", resultados=resultados)
    pdfkit.from_string(html, "resultados.pdf")
    return send_file("resultados.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
