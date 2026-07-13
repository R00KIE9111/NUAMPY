class Usuario:
    def __init__(self, nombre, contraseña, rol, correo, rut, _id=None):
        self._id = _id
        self.nombre = nombre
        self.contraseña = contraseña
        self.rol = rol
        self.correo = correo
        self.rut = rut

class UsuarioInvitado(Usuario):
    def __init__(self, nombre, contraseña, correo, rut, _id=None):
        super().__init__(nombre, contraseña, "INVITADO", correo, rut, _id)

class Administrador(Usuario):
    def __init__(self, nombre, contraseña, correo, rut, _id=None):
        super().__init__(nombre, contraseña, "ADMIN", correo, rut, _id)

class Corredor(Usuario):
    def __init__(self, nombre, contraseña, correo, rut, empresa_corredora, mercado, _id=None):
        super().__init__(nombre, contraseña, "CORREDOR", correo, rut, _id)
        self.empresa_corredora = empresa_corredora
        self.mercado = mercado

class CalificacionTributaria:
    def __init__(self, mercado, instrumento, anio, fecha_pago, secuencia_evento, dividendo, valor_historico, descripcion, isfut, factor_actualizacion, tipo_sociedad, factores, corredor, monto_total=None, calificacion_valor=None):
        self.mercado = mercado #Peru Chile Colombia
        self.instrumento = instrumento #Nombre de la empresa es el instrumento financiero type String max 50 no se debe enviar en blanco, Restriccion, no debe de guardar cosas nulas 
        self.anio = anio #Se necesita rescatar el año en los filtros y que automaticamente se coloque en ingresar calificacion, cambiar a periodo comercial el nombre, "Restricciones, nada de numeros negativos, año minimo 1900 y maximo finito"
        self.fecha_pago = fecha_pago #Se guarda la fecha donde se hizo el pago(ingreso de calificacion), Restriccion, no debe de permitir fechas menor a 1900, capturar tambien la hora, todosl os datos posibles
        self.secuencia_evento = secuencia_evento #Int, Guarda numeros del mil para arriba.
        self.dividendo = dividendo #DecimalField, Guarda 8 decimales, siempre son 8, Restricciones, nada de negativos ni tampoco enteros "tip:Precicion 8"
        self.valor_historico = valor_historico #DecimalField, Guarda 8 decimales, siempre son 8, Restricciones, nada de negativos ni tampoco enteros "tip:Precicion 8"
        self.descripcion = descripcion #String; Nada de dejar en blanco
        self.isfut = isfut #Boolean, es un Si o No
        self.factor_actualizacion = factor_actualizacion #DecimalField, Guarda 8 decimales, siempre son 8, Restricciones, nada de negativos ni tampoco enteros "tip:Precicion 8"
        self.tipo_sociedad = tipo_sociedad #Abierta o Cerrada actualmente preguntar a la profesora, ademas no puede estar en blanco
        self.factores = factores  #DecimalField, nada de numeros negativos, Guarda un entero y 8 decimales se rellena los decimales con 0 para que sea 8
        self.corredor = corredor #String, Como se subio, si por csv monto o factor, o por una persona corredor, cambiar de nombre a origen
        self.monto_total = monto_total
        self.calificacion_valor = calificacion_valor

#Si se pueden guardar duplicados, la direncia es el id; y no se pueden guardar archivos iguales
#uso de hash para csv
#Implementar OWASP utilizar errores, 400 etc evitar mostrar contenido, 

#Filtro en Html estamos dejando determinado peru pero en caso de eliminar Perú debería ser desde la base de datos
#El admin debe de ser capaz de añadir, eliminar o actualizar mercados