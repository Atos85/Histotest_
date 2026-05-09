from flask import Flask, request, redirect, url_for, session, render_template
import os
import random

app = Flask(__name__)
app.secret_key = "clave_temporal"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_FOLDER = os.path.join(BASE_DIR, "test")

ADMIN_PASSWORD = "admin123"


def listar_tests():
    return [
        f for f in os.listdir(TEST_FOLDER)
        if f.lower().endswith(".txt")
    ]


def cargar_preguntas(nombre_archivo):

    ruta = os.path.join(TEST_FOLDER, nombre_archivo)

    with open(ruta, "r", encoding="utf-8") as f:
        lineas = [linea.strip() for linea in f.readlines()]

    preguntas = []
    pregunta_actual = None

    for linea in lineas:

        if not linea:
            continue

        if linea.lower().startswith("pregunta"):

            if pregunta_actual:
                preguntas.append(pregunta_actual)

            pregunta_actual = {
                "pregunta": "",
                "opciones": {},
                "correcta": ""
            }

        elif pregunta_actual and not linea.lower().startswith(
            ("a)", "b)", "c)", "d)", "correcta:")
        ):
            pregunta_actual["pregunta"] += " " + linea

        elif linea.lower().startswith("a)"):
            pregunta_actual["opciones"]["A"] = linea[2:].strip()

        elif linea.lower().startswith("b)"):
            pregunta_actual["opciones"]["B"] = linea[2:].strip()

        elif linea.lower().startswith("c)"):
            pregunta_actual["opciones"]["C"] = linea[2:].strip()

        elif linea.lower().startswith("d)"):
            pregunta_actual["opciones"]["D"] = linea[2:].strip()

        elif linea.lower().startswith("correcta:"):
            pregunta_actual["correcta"] = (
                linea.split(":", 1)[1]
                .strip()
                .upper()
            )

    if pregunta_actual:
        preguntas.append(pregunta_actual)

    return preguntas


@app.route("/", methods=["GET", "POST"])
def inicio():

    if request.method == "POST":

        archivo = request.form.get("archivo")

        preguntas = cargar_preguntas(archivo)

        orden = list(range(len(preguntas)))
        random.shuffle(orden)

        session["archivo"] = archivo
        session["orden"] = orden
        session["indice"] = 0
        session["aciertos"] = 0
        session["fallos"] = []
        session["total"] = len(preguntas)

        return redirect(url_for("pregunta"))

    html = """
    <html>
    <head>
        <title>Histotest</title>
    </head>
    <body>

    <h1>Selecciona un test</h1>

    <form method="POST">

        <select name="archivo">
    """

    for test in listar_tests():
        html += f'<option value="{test}">{test}</option>'

    html += """
        </select>

        <button type="submit">
            Cargar test
        </button>

    </form>

    <p>
        <a href="/admin">
            Panel administrador
        </a>
    </p>

    </body>
    </html>
    """

    return html


@app.route("/pregunta", methods=["GET", "POST"])
def pregunta():

    archivo = session.get("archivo")
    orden = session.get("orden", [])
    indice = session.get("indice", 0)

    if not archivo or not orden:
        return redirect(url_for("inicio"))

    preguntas = cargar_preguntas(archivo)

    if indice >= len(orden):
        return redirect(url_for("resultado"))

    posicion_real = orden[indice]

    pregunta_actual = preguntas[posicion_real]

    if request.method == "POST":

        respuesta = request.form.get("respuesta")

        correcta = pregunta_actual["correcta"]

        es_correcta = respuesta == correcta

        if es_correcta:

            session["aciertos"] = (
                session.get("aciertos", 0) + 1
            )

        else:

            fallos = session.get("fallos", [])

            fallos.append({
                "pregunta": pregunta_actual["pregunta"],
                "tu": respuesta,
                "correcta": correcta
            })

            session["fallos"] = fallos

        session["ultimo_resultado"] = {
            "correcta": es_correcta,
            "respuesta_correcta": correcta,
            "numero": indice + 1,
            "total": len(orden)
        }

        return redirect(url_for("feedback"))

    return render_template(
        "pregunta.html",
        pregunta=pregunta_actual,
        numero=indice + 1,
        total=len(orden)
    )


@app.route("/feedback")
def feedback():

    resultado = session.get("ultimo_resultado")

    if not resultado:
        return redirect(url_for("pregunta"))

    return render_template(
        "feedback.html",
        correcta=resultado["correcta"],
        respuesta_correcta=resultado["respuesta_correcta"],
        numero=resultado["numero"],
        total=resultado["total"]
    )


@app.route("/siguiente")
def siguiente():

    session["indice"] = (
        session.get("indice", 0) + 1
    )

    return redirect(url_for("pregunta"))


@app.route("/resultado")
def resultado():

    return render_template(
        "resultado.html",
        aciertos=session.get("aciertos", 0),
        total=session.get("total", 0),
        fallos=session.get("fallos", [])
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    mensaje = ""

    if request.method == "POST":

        archivo = request.files.get("archivo")

        if archivo and archivo.filename.lower().endswith(".txt"):

            ruta_destino = os.path.join(
                TEST_FOLDER,
                archivo.filename
            )

            archivo.save(ruta_destino)

            mensaje = "Test subido correctamente."

        else:
            mensaje = "Solo se permiten archivos .txt."

    tests = listar_tests()

    return render_template(
        "admin.html",
        tests=tests,
        mensaje=mensaje
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    error = ""

    if request.method == "POST":

        password = request.form.get("password")

        if password == ADMIN_PASSWORD:

            session["admin"] = True

            return redirect(url_for("admin"))

        else:
            error = "Contraseña incorrecta."

    return render_template(
        "admin_login.html",
        error=error
    )


@app.route("/admin/logout")
def admin_logout():

    session.pop("admin", None)

    return redirect(url_for("inicio"))


@app.route("/admin/borrar/<nombre>")
def borrar_test(nombre):

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    ruta = os.path.join(TEST_FOLDER, nombre)

    if (
        os.path.exists(ruta)
        and nombre.lower().endswith(".txt")
    ):
        os.remove(ruta)

    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True)