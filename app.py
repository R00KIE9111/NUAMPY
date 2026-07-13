###############################################################
# Importación de librerías                                    #
#-------------------------------------------------------------#
# Flask: framework principal                                  #
from flask import *
# Protección contra ataques CSRF (Cross-Site Request Forgery) #
from flask_wtf.csrf import CSRFProtect as token
# Gestión de todo: lógica definida en control/gestion.py      #
from control.gestion import GestionUsuarios
# Librerías adicionales utilizadas en el proyecto:            #
# Para leer y procesar archivos CSV                           #
import csv
# Para encriptar datos y evitar duplicados                    #
import hashlib as h
# Para depurar nombres de archivos subidos (viene de Flask)   #
from werkzeug.utils import secure_filename as sf
###############################################################



###############################################################
# Configuracion Inicial de la App                             #
#-------------------------------------------------------------#
# Creación de la aplicación Flask                             #
app = Flask(
#### Nombre del módulo actual                                 #
    __name__,
#### Rutas de plantillas y archivos estáticos                 #
    template_folder="ui/templates",
    static_folder="ui/static"
)
# Configuración de la clave secreta para sesiones y CSRF      #
app.secret_key = "clave-secreta-super-segura"
csrf = token(app)
# Clase de gestión de usuarios y calificaciones               #
gestion = GestionUsuarios()
###############################################################



###############################################################
# Seguridad y Autenticación de Usuarios                       #
#-------------------------------------------------------------#
@app.before_request
def verificar_login():
#### Definición de rutas públicas (sin autenticación)         #
    rutas_publicas = ['login', 'static']
#### Redirección a login si no está autenticado               #
    if "usuario" not in session and request.endpoint not in rutas_publicas:
        return redirect(url_for("login"))
#-------------------------------------------------------------#
@app.route("/login", methods=["GET", "POST"])
def login():
#### Manejo de formulario de login                            #
    if request.method == "POST":
######## Obtención de datos del formulario                    #
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
######## Verificación de usuario y contraseña                 #
        user_obj = gestion.verificar_usuario(usuario, contraseña)
######## Manejo de sesión y redirección                       #
        if user_obj:
            session["usuario"] = user_obj.nombre
            session["rol"] = user_obj.rol
            return redirect(url_for("dashboard"))
######## Manejo de error en login                             #
        else:
            return render_template("login.html", error="Usuario o contraseña incorrectos")
#### Redireccion a la página de login
    return render_template("login.html")
#-------------------------------------------------------------#
@app.route("/logout")
def logout():
# Limpieza de la sesión y redirección al login                #
    session.clear()
    return redirect(url_for("login"))
###############################################################



###############################################################
# Rutas Principales de la Aplicación                          #
#-------------------------------------------------------------#
# Por defecto redirige al login                               #
@app.route("/")
def home():
    return render_template("login.html")
#-------------------------------------------------------------#
# Dashboard es pagina principal una vez logueado              #
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    
    # Filtro automático para Corredores
    if session.get("rol") == "CORREDOR":
        calificaciones = gestion.filtro_calificaciones(None, None, None, session["usuario"], None)
    else:
        calificaciones = gestion.obtener_todas_las_calificaciones()
        
    mercados = gestion.obtener_mercados()
    return render_template("dashboard.html", usuario=session["usuario"], calificaciones=calificaciones, mercados=mercados)
###############################################################



###############################################################
# Administración de Usuarios                                  #
#-------------------------------------------------------------#
@app.route("/administracion")
def administracion():
#### Lista todos los usuarios para la administración          #
    usuarios = gestion.listar_usuarios()
    return render_template("administracion.html", usuarios=usuarios)
#-------------------------------------------------------------#
@app.route("/configuracion_perfil", methods=["GET", "POST"])
def configuracion_perfil():
    if "usuario" not in session:
        return redirect(url_for("login"))
    usuario = session["usuario"]
    user_obj = gestion.db.obtener_usuario(usuario)
    if request.method == "POST":
        nuevo_correo = request.form.get("correo")
        nueva_contraseña = request.form.get("contraseña")
        gestion.actualizar_usuario(usuario, {"correo": nuevo_correo, "contraseña": nueva_contraseña})
        return redirect(url_for("dashboard"))
    return render_template("configuracion_perfil.html", usuario=user_obj)

###############################################################
@app.route("/crear_user", methods=["GET", "POST"])
def crear_user():
    if request.method == "POST":
        nombre = request.form["nombre"]
        correo = request.form["correo"]
        contraseña = request.form["contraseña"]
        rol = request.form["rol"]
        gestion.crear_usuario(nombre, contraseña, rol, correo)
        return redirect(url_for("administracion"))
    return render_template("crear_user.html")

@app.route("/eliminar_user", methods=["GET", "POST"])
def eliminar_user():
    if request.method == "POST":
        nombre = request.form.get("nombre") or request.args.get("nombre")
        if nombre:
            gestion.eliminar_usuario(nombre)
        return redirect(url_for("administracion"))

    usuarios = gestion.listar_usuarios()
    return render_template("eliminar_user.html", usuarios=usuarios)

@app.route("/modificar_usuario/<nombre>", methods=["GET", "POST"])
def modificar_usuario(nombre):
    user_obj = gestion.db.obtener_usuario(nombre)
    if not user_obj:
        return "Usuario no encontrado", 404

    if request.method == "POST":
        nuevos_datos = {
            "contraseña": request.form.get("contraseña"),
            "rol": request.form.get("rol"),
            "correo": request.form.get("correo")
        }
        gestion.actualizar_usuario(nombre, nuevos_datos)
        return redirect(url_for("administracion"))  

    return render_template("modificar_usuario.html", usuario=user_obj)

###############################################################
@app.route("/crear_calificacion", methods=["GET", "POST"])
def crear_calificacion():
    factores = []
    for i in range (8,38):
        factor_i =  "factor_" + str(i)
        factores.append(factor_i)
    montos = []
    for x in range(8,38):
        monto_x = "monto_"+ str(x)
        montos.append(monto_x)

    if request.method == "POST":
        modo = request.form.get("modo")

        mercado = request.form.get("Mercado")
        instrumento = request.form.get("Instrumento")
        anio = request.form.get("anio")
        fecha_pago = request.form.get("Fecha_de_pago")
        secuencia_evento = request.form.get("secuencia_evento")

        dividendo_raw = request.form.get("Dividendo", "0")
        factor_actualizacion_raw = request.form.get("factor_actualizacion", "0")

        try:
            dividendo = float(dividendo_raw) if dividendo_raw != "" else 0.0
        except ValueError:
            dividendo = 0.0

        try:
            factor_actualizacion = float(factor_actualizacion_raw) if factor_actualizacion_raw != "" else 0.0
        except ValueError:
            factor_actualizacion = 0.0
            
        valor_historico = request.form.get("valor_historico")
        descripcion = request.form.get("Descripcion")
        isfut = request.form.get("ISFUT")
        tipo_sociedad = request.form.get("tipo_sociedad")
        corredor = request.form.get("Corredor")
        
        res = None

        if modo == "montos":
            montos_valores = {}

            for monto in montos:
                datos_monto = request.form.get(monto)
                if datos_monto is not None and datos_monto != "":
                    datos_numero_montos = float(datos_monto)
                else:
                    datos_numero_montos = 0.0
                montos_valores[monto] = datos_numero_montos
            res = gestion.insertar_calificacion_desde_montos(
                mercado, instrumento, anio, fecha_pago, secuencia_evento,
                dividendo, valor_historico, descripcion, isfut,
                factor_actualizacion, tipo_sociedad, montos_valores, corredor
            )
        
        elif modo == "factores":
            factores_valores = {}

            for factor in factores:
                datos = request.form.get(factor)
                if datos is not None and datos != "":
                    datos_numero = float(datos)
                else:
                    datos_numero = 0.0
                factores_valores[factor] = datos_numero
            res = gestion.insertar_calificacion(mercado, instrumento, anio, fecha_pago, secuencia_evento, dividendo,valor_historico, descripcion, isfut, factor_actualizacion, tipo_sociedad,factores_valores, corredor)

        if res:
            return redirect(url_for("dashboard"))   
        else:
            return "Error al crear la calificación", 500                                   
    return render_template("crear_calificacion.html", factores=factores, montos=montos)

@app.route("/modificar_calificacion", methods=["GET", "POST"])
def modificar_calificacion():
    return render_template("modificar_calificacion.html")

@app.route("/eliminar_calificacion", methods=["GET", "POST"])
def eliminar_calificacion():
    return render_template("eliminar_calificacion.html")

@app.route("/filtro_calificaciones", methods=["GET", "POST"])
def filtro_calificaciones():
    if "usuario" not in session:
        return redirect(url_for("login"))
    resultados = []
    mercados = gestion.obtener_mercados()
    if request.method == "POST": 
        mercado = request.form.get("mercado") or None
        instrumento = request.form.get("instrumento") or None
        anio_original = request.form.get("anio")
        
        # Seguridad: Si es corredor, forzar su nombre en el filtro, ignorando lo que envíe
        if session.get("rol") == "CORREDOR":
            corredor = session["usuario"]
        else:
            corredor = request.form.get("corredor") or None
            
        tipo_sociedad = request.form.get("tipo_sociedad") or None
        try:
            anio = int(anio_original) if anio_original else None
        except:
            anio = None
        resultados = gestion.filtro_calificaciones(
            mercado=mercado,
            instrumento=instrumento,
            anio=anio,
            corredor=corredor,
            tipo_sociedad=tipo_sociedad
        )
        return render_template(
            "dashboard.html",
            calificaciones=resultados,
            usuario=session["usuario"],
            filtro_mercado=mercado,
            filtro_instrumento=instrumento,
            filtro_anio=anio_original,
            filtro_corredor=corredor,
            filtro_tipo_sociedad=tipo_sociedad,
            mercados=mercados
        )
    return render_template(
        "dashboard.html",
        calificaciones=resultados,
        usuario=session["usuario"],
        mercados=mercados
    )

@app.route("/leer_calificacion/<id>")
def leer_calificacion(id):
    return render_template("leer_calificacion.html", id=id)

@app.route("/leer_calificacion")
def leer_calificacion_sin_id():
    return render_template("leer_calificacion_sin_id.html")
###############################################################



###############################################################
# Carga Masiva de Calificaciones                              #
#-------------------------------------------------------------#
def procesar_csv(file, tipo_carga):
    if file and file.filename.endswith(".csv"):
######## Lectura del archivo CSV                              #
        contenido = file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(contenido)
######## Procesamiento de cada fila del CSV                   #
        for row in reader:
            gestion.procesar_fila_csv(row, tipo_carga)
#-------------------------------------------------------------#
@app.route("/cargar_montos", methods=["GET", "POST"])
def cargar_montos():
    if request.method == "POST":
        file = request.files["csv_file"]
        procesar_csv(file, "montos")
        return redirect(url_for("dashboard"))
    return render_template("cargar_montos.html")
#-------------------------------------------------------------#
@app.route("/cargar_factores", methods=["GET", "POST"])
def cargar_factores():
    if request.method == "POST":
        file = request.files["csv_file"]
        procesar_csv(file, "factores")
        return redirect(url_for("dashboard"))
    return render_template("cargar_factores.html")
###############################################################



###############################################################
# Visualización de Logs                                       #
#-------------------------------------------------------------#
@app.route("/logs")
def logs():
    if "usuario" not in session or session.get("rol") != "ADMIN":
        return redirect(url_for("dashboard"))
#### Obtención de registros de logs                           #
#### Si la función no existe, retorna una lista vacía         #
    registros = gestion.obtener_logs() if hasattr(gestion, "obtener_logs") else []
    return render_template("logs.html", logs=registros)
###############################################################



###############################################################
# Manejo de Errores Comunes                                   #
#-------------------------------------------------------------#
# Errores de Cliente                                          #
#-------------------------------------------------------------#
@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", mensaje="Solicitud incorrecta"), 400
#-------------------------------------------------------------#
@app.errorhandler(401)
def unauthorized(e):
    return render_template("error.html", mensaje="No autorizado"), 401
#-------------------------------------------------------------#
@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", mensaje="Prohibido el acceso"), 403
#-------------------------------------------------------------#
@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", mensaje="Página no encontrada"), 404
#-------------------------------------------------------------#
@app.errorhandler(405)
def method_not_allowed(e):
    return render_template("error.html", mensaje="Método no permitido"), 405
#-------------------------------------------------------------#
@app.errorhandler(408)
def request_timeout(e):
    return render_template("error.html", mensaje="Tiempo de solicitud agotado"), 408
#-------------------------------------------------------------#
@app.errorhandler(429)
def too_many_requests(e):
    return render_template("error.html", mensaje="Demasiadas solicitudes"), 429
#-------------------------------------------------------------#
# Errores de Servidor                                         #
#-------------------------------------------------------------#
@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", mensaje="Error interno del servidor"), 500
#-------------------------------------------------------------#
@app.errorhandler(502)
def bad_gateway(e):
    return render_template("error.html", mensaje="Puerta de enlace incorrecta"), 502
#-------------------------------------------------------------#
@app.errorhandler(503)
def service_unavailable(e):
    return render_template("error.html", mensaje="Servicio no disponible"), 503
#-------------------------------------------------------------#
@app.errorhandler(504)
def gateway_timeout(e):
    return render_template("error.html", mensaje="Tiempo de espera agotado"), 504
###############################################################



###############################################################
# Ejecución de la Aplicación                                  #
#-------------------------------------------------------------#
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=443, ssl_context="adhoc", debug=True)
###############################################################