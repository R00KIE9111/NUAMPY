###################-IMPORTS-###################
import hashlib as h
from datetime import datetime
from data.dataBase import DataBase
from data.models import UsuarioInvitado, Corredor, Administrador, CalificacionTributaria

class GestionUsuarios:
    def __init__(self):
        self.db = DataBase()

    def cifrar_contraseña(self, password):
        return h.sha256(str(password).encode()).hexdigest()

    def verificar_contraseña(self, password_ingresada, password_guardada):
        return self.cifrar_contraseña(password_ingresada) == password_guardada

    def verificar_usuario(self, nombre, contraseña):
        usuario = self.db.obtener_usuario(nombre)
        if usuario and self.verificar_contraseña(contraseña, usuario.contraseña):
            return usuario
        return None

    def crear_usuario(self, nombre, contraseña, rol, correo, empresa=None, mercado=None, rut=None):
        contraseña_cifrada = self.cifrar_contraseña(contraseña)
        if rol == "INVITADO":
            nuevo = UsuarioInvitado(nombre, contraseña_cifrada, correo, rut)
        elif rol == "CORREDOR":
            nuevo = Corredor(nombre, contraseña_cifrada, correo, rut, empresa, mercado)
        elif rol == "ADMIN":
            nuevo = Administrador(nombre, contraseña_cifrada, correo, rut)
        else:
            return False
        ok = self.db.crear_usuario(nuevo)
        if ok:
            self.db.registrar_log("CREAR_USUARIO", nombre, {"rol": rol, "correo": correo})
        return ok

    def actualizar_usuario(self, nombre, nuevos_datos):
        if "contraseña" in nuevos_datos:
            nuevos_datos["contraseña"] = self.cifrar_contraseña(nuevos_datos["contraseña"])
        ok = self.db.actualizar_usuario(nombre, nuevos_datos)
        if ok:
            self.db.registrar_log("ACTUALIZAR_USUARIO", nombre, {"datos": nuevos_datos})
        return ok

    def eliminar_usuario(self, nombre):
        ok = self.db.eliminar_usuario_por_nombre(nombre)
        if ok:
            self.db.registrar_log("ELIMINAR_USUARIO", "admin", {"usuario": nombre})
        return ok

    def listar_usuarios(self):
        return self.db.obtener_todos_los_usuarios()

    def factores_desde_montos(self, montos: dict):
        total = sum(montos.values())
        if total <= 0:
            return None
        factores = {}
        for i in range(8, 38):
            factores[f"factor_{i}"] = round(montos.get(f"monto_{i}", 0.0) / total, 8)
        residuo = 1.0 - sum(factores.values())
        if "factor_37" not in factores:
            factores["factor_37"] = 0.0
        factores["factor_37"] = round(factores["factor_37"] + residuo, 8)
        return factores

    def insertar_calificacion(self, mercado, instrumento, anio, fecha_pago, secuencia_evento, dividendo, valor_historico, descripcion, isfut, factor_actualizacion, tipo_sociedad, factores, corredor):
        nueva = CalificacionTributaria(mercado, instrumento, anio, fecha_pago, secuencia_evento, dividendo, valor_historico, descripcion, isfut, factor_actualizacion, tipo_sociedad, factores, corredor)
        res = self.db.insertar_calificacion(nueva)
        if res:
            self.db.registrar_log("CREAR_CALIFICACION", corredor, {"calificacion_id": res})
        return res

    def insertar_calificacion_desde_montos(self, mercado, instrumento, anio, fecha_pago, secuencia_evento, dividendo, valor_historico, descripcion, isfut, factor_actualizacion, tipo_sociedad, montos, corredor):
        factores = self.factores_desde_montos(montos)
        if not factores:
            return None
        monto_total = sum(montos.values())
        calificacion_valor = float(dividendo) * float(factor_actualizacion)
        nueva = CalificacionTributaria(mercado, instrumento, anio, fecha_pago, secuencia_evento, dividendo, valor_historico, descripcion, isfut, factor_actualizacion, tipo_sociedad, factores, corredor, monto_total=monto_total, calificacion_valor=calificacion_valor)
        res = self.db.insertar_calificacion_con_montos(nueva, montos)
        if res:
            self.db.registrar_log("CREAR_CALIFICACION", corredor, {
                "calificacion_id": res,
                "monto_total": monto_total,
                "calificacion_valor": calificacion_valor
            })
        return res

    def obtener_todas_las_calificaciones(self):
        docs = self.db.obtener_todas_las_calificaciones()
        objetos = []
        for d in docs:
            objetos.append(CalificacionTributaria(
                d.get("mercado"),
                d.get("instrumento"),
                d.get("anio"),
                d.get("fecha_pago"),
                d.get("secuencia_evento"),
                d.get("dividendo"),
                d.get("valor_historico"),
                d.get("descripcion"),
                d.get("isfut"),
                d.get("factor_actualizacion"),
                d.get("tipo_sociedad"),
                d.get("factores", {}),
                d.get("corredor"),
                d.get("monto_total"),
                d.get("calificacion_valor")
            ))
        return objetos
    
    def filtro_calificaciones(self, mercado, instrumento, anio, corredor, tipo_sociedad): 
        lista = self.obtener_todas_las_calificaciones()  
        resultados = []  

        for li in lista:
            if all([    
                (not mercado or getattr(li, "mercado", None) == mercado),  
                (not instrumento or getattr(li, "instrumento", None) == instrumento),
                (not anio or getattr(li, "anio", None) == anio),  
                (not corredor or getattr(li, "corredor", None) == corredor),
                (not tipo_sociedad or getattr(li, "tipo_sociedad", None) == tipo_sociedad)
            ]):
                resultados.append(li)

        return resultados 

    def obtener_mercados(self):
        lista = self.obtener_todas_las_calificaciones()
        mercados = []  
        
        for li in lista:
            mercado = getattr(li, "mercado", None)   
            if mercado and mercado not in mercados: 
                mercados.append(mercado)
            
        return mercados 
    
    def eliminar_calificacion(self, _id):
        ok = self.db.eliminar_calificacion_por_id(_id)
        if ok:
            self.db.registrar_log("ELIMINAR_CALIFICACION", "admin", {"calificacion_id": _id})
        return ok

    def obtener_calificacion_por_id(self, _id):
        return self.db.obtener_calificacion_por_id(_id)

    def solicitar_eliminacion(self, calificacion_id, solicitante, motivo=""):
        cal = self.db.obtener_calificacion_por_id(calificacion_id)
        if not cal:
            return None
        owner = cal.get("corredor")
        if owner != solicitante:
            return None
        res = self.db.crear_solicitud_eliminacion(calificacion_id, solicitante, motivo)
        if res:
            self.db.registrar_log("SOLICITAR_ELIMINACION", solicitante, {
                "calificacion_id": calificacion_id,
                "motivo": motivo
            })
        return res

    def listar_solicitudes(self, estado=None):
        return self.db.obtener_solicitudes_eliminacion(estado)

    def actualizar_estado_solicitud(self, solicitud_id, nuevo_estado):
        ok = self.db.actualizar_estado_solicitud(solicitud_id, nuevo_estado)
        if ok:
            self.db.registrar_log("CAMBIO_ESTADO_SOLICITUD", "admin", {
                "solicitud_id": solicitud_id,
                "nuevo_estado": nuevo_estado
            })
        return ok

    def eliminar_solicitud(self, solicitud_id):
        ok = self.db.eliminar_solicitud_por_id(solicitud_id)
        if ok:
            self.db.registrar_log("ELIMINAR_SOLICITUD", "admin", {"solicitud_id": solicitud_id})
        return ok
    
    def registrar_log(self, accion, usuario=None, detalle=None):
        return self.db.registrar_log(accion, usuario, detalle)

    def obtener_logs(self):
        return self.db.obtener_logs()

    def procesar_fila_csv(self, row, tipo_carga):
        # Normalizar claves
        norm = {}
        for k, v in row.items():
            if k is None:
                continue
            nk = k.lower().strip()
            nk = nk.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            nk = nk.replace("ñ", "n").replace(" ", "_")
            norm[nk] = v
            
        mercado = norm.get("mercado", "")
        instrumento = norm.get("instrumento", "")
        
        anio_val = norm.get("anio") or norm.get("periodo_comercial") or norm.get("periodo") or "0"
        try:
            anio = int(float(anio_val))
        except ValueError:
            anio = 0
            
        fecha_pago = norm.get("fecha_de_pago") or norm.get("fecha_pago") or norm.get("fecha", "")
        
        sec_val = norm.get("secuencia_evento") or norm.get("secuencia") or "0"
        try:
            secuencia_evento = int(float(sec_val))
        except ValueError:
            secuencia_evento = 0
            
        div_val = norm.get("dividendo", "0")
        try:
            dividendo = float(div_val)
        except ValueError:
            dividendo = 0.0
            
        val_hist = norm.get("valor_historico") or norm.get("valor_historico") or "0"
        try:
            valor_historico = float(val_hist)
        except ValueError:
            valor_historico = 0.0
            
        descripcion = norm.get("descripcion") or norm.get("descripcion_evento") or ""
        
        isfut_val = norm.get("isfut", "no")
        isfut = str(isfut_val).lower() in ("si", "yes", "true", "1")
        
        fact_act = norm.get("factor_actualizacion") or norm.get("factor") or "0"
        try:
            factor_actualizacion = float(fact_act)
        except ValueError:
            factor_actualizacion = 0.0
            
        tipo_sociedad = norm.get("tipo_sociedad") or norm.get("sociedad", "")
        corredor = norm.get("corredor") or norm.get("origen", "")
        
        # Extraer factores o montos del 8 al 37
        factores = {}
        montos = {}
        
        if tipo_carga == "factores":
            for i in range(8, 38):
                key = f"factor_{i}"
                val = norm.get(key) or norm.get(f"factor{i}") or "0"
                try:
                    factores[key] = float(val)
                except ValueError:
                    factores[key] = 0.0
            # Guardar calificacion usando insertar_calificacion
            return self.insertar_calificacion(
                mercado, instrumento, anio, fecha_pago, secuencia_evento,
                dividendo, valor_historico, descripcion, isfut,
                factor_actualizacion, tipo_sociedad, factores, corredor
            )
            
        elif tipo_carga == "montos":
            for i in range(8, 38):
                key = f"monto_{i}"
                val = norm.get(key) or norm.get(f"monto{i}") or "0"
                try:
                    montos[key] = float(val)
                except ValueError:
                    montos[key] = 0.0
            # Guardar calificacion usando insertar_calificacion_desde_montos
            return self.insertar_calificacion_desde_montos(
                mercado, instrumento, anio, fecha_pago, secuencia_evento,
                dividendo, valor_historico, descripcion, isfut,
                factor_actualizacion, tipo_sociedad, montos, corredor
            )
        return None