import os
import json
import pymysql
from datetime import datetime
from data.models import Usuario, UsuarioInvitado, Corredor, Administrador, CalificacionTributaria

# Intentar importar la SDK de Azure Cosmos DB NoSQL
try:
    from azure.cosmos import CosmosClient
    COSMOS_AVAILABLE = True
except ImportError:
    COSMOS_AVAILABLE = False

class DataBase:
    def __init__(self):
        # Cargar variables de entorno desde .env manualmente si existe
        if os.path.exists(".env"):
            with open(".env") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        key, val = line.strip().split("=", 1)
                        os.environ.setdefault(key, val)

        # 1. Configuración de conexión MySQL / AWS RDS
        self.mysql_host = os.environ.get("MYSQL_HOST", "")
        self.mysql_user = os.environ.get("MYSQL_USER", "")
        self.mysql_password = os.environ.get("MYSQL_PASSWORD", "")
        self.mysql_db = os.environ.get("MYSQL_DB", "")
        self.mysql_port = int(os.environ.get("MYSQL_PORT", 3306))

        # 2. Configuración de Azure Cosmos DB
        self.cosmos_url = os.environ.get("COSMOS_URI", "")
        self.cosmos_key = os.environ.get("COSMOS_KEY", "")
        self.cosmos_db_name = os.environ.get("COSMOS_DB", "")
        self.cosmos_container_name = os.environ.get("COSMOS_CONTAINER", "")

        self.cosmos_container = None
        if COSMOS_AVAILABLE and self.cosmos_url and self.cosmos_key:
            try:
                self.cosmos_client = CosmosClient(self.cosmos_url, credential=self.cosmos_key)
                self.cosmos_database = self.cosmos_client.get_database_client(self.cosmos_db_name)
                self.cosmos_container = self.cosmos_database.get_container_client(self.cosmos_container_name)
                print("[INFO] Conexión inicializada con Azure Cosmos DB (Logs).")
            except Exception as e:
                print("[WARNING] No se pudo inicializar la conexión con Azure Cosmos DB:", e)

    def _get_connection(self):
        return pymysql.connect(
            host=self.mysql_host,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_db,
            port=self.mysql_port,
            autocommit=False
        )

#####################-LOG-#####################
    def registrar_log(self, accion, usuario, detalle):
        doc = {
            "id": f"log_{datetime.now().timestamp()}_{accion}",
            "accion": accion,
            "usuario": usuario,
            "fecha": datetime.now().isoformat(),
            "detalle": detalle
        }
        
        # Intentar guardar en Azure Cosmos DB
        success = False
        if COSMOS_AVAILABLE and self.cosmos_container:
            try:
                self.cosmos_container.create_item(body=doc)
                success = True
                print("[INFO] Log registrado en Azure Cosmos DB.")
            except Exception as e:
                print("Error escribiendo log en Cosmos DB:", e)

        # Fallback a MySQL local de respaldo en RDS
        if not success:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    sql = "INSERT INTO logs (accion, usuario, detalle) VALUES (%s, %s, %s)"
                    detalle_json = json.dumps(detalle) if detalle else None
                    cursor.execute(sql, (accion, usuario, detalle_json))
                conn.commit()
                success = True
                print("[INFO] Log registrado en base de datos MySQL (RDS) de respaldo.")
            except Exception as e:
                print("Error registrando log en MySQL:", e)
            finally:
                conn.close()
        return success

    def obtener_logs(self, limite=50):
        # Intentar leer desde Azure Cosmos DB
        if COSMOS_AVAILABLE and self.cosmos_container:
            try:
                # Query de ordenación en Cosmos DB SQL API
                query = f"SELECT * FROM c ORDER BY c.fecha DESC OFFSET 0 LIMIT {limite}"
                items = list(self.cosmos_container.query_items(
                    query=query,
                    enable_cross_partition_query=True
                ))
                return items
            except Exception as e:
                print("Error leyendo logs de Cosmos DB:", e)

        # Fallback a MySQL RDS
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT id, accion, usuario, fecha, detalle FROM logs ORDER BY fecha DESC LIMIT %s"
                cursor.execute(sql, (limite,))
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                results = []
                for r in rows:
                    doc = dict(zip(columns, r))
                    if doc.get("fecha"):
                        doc["fecha"] = doc["fecha"].isoformat() if hasattr(doc["fecha"], "isoformat") else str(doc["fecha"])
                    if isinstance(doc.get("detalle"), str):
                        doc["detalle"] = json.loads(doc["detalle"])
                    results.append(doc)
                return results
        except Exception as e:
            print("Error al obtener logs de MySQL:", e)
            return []
        finally:
            conn.close()

###################-USUARIO-###################
    def obtener_usuario(self, nombre):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT id, nombre, contrasena, rol, correo, rut, empresa_corredora, mercado FROM usuarios WHERE nombre = %s"
                cursor.execute(sql, (nombre,))
                row = cursor.fetchone()
                if not row:
                    return None
                
                _id, nombre_db, contraseña, rol, correo, rut, empresa_corredora, mercado = row
                if rol == "CORREDOR":
                    return Corredor(nombre_db, contraseña, correo, rut, empresa_corredora, mercado, _id)
                if rol == "INVITADO":
                    return UsuarioInvitado(nombre_db, contraseña, correo, rut, _id)
                if rol == "ADMIN":
                    return Administrador(nombre_db, contraseña, correo, rut, _id)
                return Usuario(nombre_db, contraseña, rol, correo, rut, _id)
        except Exception as e:
            print("Error obtener_usuario:", e)
            return None
        finally:
            conn.close()

    def crear_usuario(self, usuario: Usuario):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO usuarios (nombre, contrasena, rol, correo, rut, empresa_corredora, mercado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                empresa = getattr(usuario, 'empresa_corredora', None)
                mercado = getattr(usuario, 'mercado', None)
                cursor.execute(sql, (usuario.nombre, usuario.contraseña, usuario.rol, usuario.correo, usuario.rut, empresa, mercado))
            conn.commit()
            return True
        except Exception as e:
            print("Error crear_usuario:", e)
            return False
        finally:
            conn.close()

    def actualizar_usuario(self, nombre, nuevos_datos):
        if not nuevos_datos:
            return False
        conn = self._get_connection()
        try:
            fields = []
            values = []
            for k, v in nuevos_datos.items():
                db_key = "contrasena" if k == "contraseña" else k
                fields.append(f"{db_key} = %s")
                values.append(v)
            values.append(nombre)
            
            sql = f"UPDATE usuarios SET {', '.join(fields)} WHERE nombre = %s"
            with conn.cursor() as cursor:
                res = cursor.execute(sql, values)
            conn.commit()
            return res > 0
        except Exception as e:
            print("Error actualizar_usuario:", e)
            return False
        finally:
            conn.close()

    def eliminar_usuario_por_nombre(self, nombre):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM usuarios WHERE nombre = %s"
                res = cursor.execute(sql, (nombre,))
            conn.commit()
            return res > 0
        except Exception as e:
            print("Error eliminar_usuario_por_nombre:", e)
            return False
        finally:
            conn.close()

    def obtener_todos_los_usuarios(self):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT id, nombre, contrasena, rol, correo, rut, empresa_corredora, mercado FROM usuarios"
                cursor.execute(sql)
                rows = cursor.fetchall()
                usuarios = []
                for r in rows:
                    _id, nombre, contraseña, rol, correo, rut, empresa_corredora, mercado = r
                    usuarios.append({
                        "_id": _id,
                        "nombre": nombre,
                        "contraseña": contraseña,
                        "rol": rol,
                        "correo": correo,
                        "rut": rut,
                        "empresa_corredora": empresa_corredora,
                        "mercado": mercado
                    })
                return usuarios
        except Exception as e:
            print("Error obtener_todos_los_usuarios:", e)
            return []
        finally:
            conn.close()

################-CALIFICACIONS-################
    def obtener_calificacion_por_id(self, _id):
        try:
            sql_id = int(_id)
        except (ValueError, TypeError):
            return None
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM calificaciones_tributarias WHERE id = %s"
                cursor.execute(sql, (sql_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                
                columns = [desc[0] for desc in cursor.description]
                doc = dict(zip(columns, row))
                doc["_id"] = doc["id"]
                if isinstance(doc.get("factores"), str):
                    doc["factores"] = json.loads(doc["factores"])
                if isinstance(doc.get("montos"), str):
                    doc["montos"] = json.loads(doc["montos"])
                return doc
        except Exception as e:
            print("Error obtener_calificacion_por_id:", e)
            return None
        finally:
            conn.close()

    def _execute_insert(self, calificacion: CalificacionTributaria, montos: dict = None):
        factores_json = json.dumps(calificacion.factores) if calificacion.factores else None
        montos_json = json.dumps(montos) if montos else (json.dumps(calificacion.montos) if getattr(calificacion, 'montos', None) else None)
        
        # Generar hash si no está presente para evitar duplicados
        cal_hash = getattr(calificacion, 'hash', None)
        if not cal_hash:
            raw_str = f"{calificacion.mercado}-{calificacion.instrumento}-{calificacion.anio}-{calificacion.fecha_pago}-{calificacion.secuencia_evento}-{calificacion.dividendo}"
            import hashlib
            cal_hash = hashlib.sha256(raw_str.encode()).hexdigest()
            
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Convertir isfut a bool/tinyint
                isfut_val = 1 if str(calificacion.isfut).lower() in ('si', 'true', '1') else 0
                
                sql = """
                    INSERT INTO calificaciones_tributarias (
                        mercado, instrumento, anio, fecha_pago, secuencia_evento,
                        dividendo, valor_historico, descripcion, isfut, factor_actualizacion,
                        tipo_sociedad, corredor, monto_total, calificacion_valor, factores, montos, hash
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    calificacion.mercado, calificacion.instrumento, int(calificacion.anio),
                    calificacion.fecha_pago, int(calificacion.secuencia_evento),
                    calificacion.dividendo, calificacion.valor_historico, calificacion.descripcion,
                    isfut_val, calificacion.factor_actualizacion, calificacion.tipo_sociedad,
                    calificacion.corredor, calificacion.monto_total, calificacion.calificacion_valor,
                    factores_json, montos_json, cal_hash
                ))
                inserted_id = cursor.lastrowid
            conn.commit()
            return str(inserted_id)
        except Exception as e:
            print("Error inserting calificacion:", e)
            return None
        finally:
            conn.close()

    def insertar_calificacion(self, calificacion: CalificacionTributaria):
        return self._execute_insert(calificacion)

    def insertar_calificacion_con_montos(self, calificacion: CalificacionTributaria, montos: dict):
        return self._execute_insert(calificacion, montos)

    def obtener_todas_las_calificaciones(self):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM calificaciones_tributarias"
                cursor.execute(sql)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                results = []
                for r in rows:
                    doc = dict(zip(columns, r))
                    doc["_id"] = doc["id"]
                    if isinstance(doc.get("factores"), str):
                        doc["factores"] = json.loads(doc["factores"])
                    if isinstance(doc.get("montos"), str):
                        doc["montos"] = json.loads(doc["montos"])
                    results.append(doc)
                return results
        except Exception as e:
            print("Error obtener_todas_las_calificaciones:", e)
            return []
        finally:
            conn.close()

    def eliminar_calificacion_por_id(self, _id):
        try:
            sql_id = int(_id)
        except (ValueError, TypeError):
            return False
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM calificaciones_tributarias WHERE id = %s"
                res = cursor.execute(sql, (sql_id,))
            conn.commit()
            return res > 0
        except Exception as e:
            print("Error eliminar calificacion:", e)
            return False
        finally:
            conn.close()

    def crear_solicitud_eliminacion(self, calificacion_id, solicitante, motivo=""):
        try:
            sql_cal_id = int(calificacion_id)
        except (ValueError, TypeError):
            return None
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO solicitudes_eliminacion (calificacion_id, solicitante, motivo, estado)
                    VALUES (%s, %s, %s, 'PENDIENTE')
                """
                cursor.execute(sql, (sql_cal_id, solicitante, motivo))
                inserted_id = cursor.lastrowid
            conn.commit()
            return str(inserted_id)
        except Exception as e:
            print("Error crear solicitud eliminacion:", e)
            return None
        finally:
            conn.close()

    def obtener_solicitudes_eliminacion(self, estado=None):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                if estado:
                    sql = "SELECT id, calificacion_id, solicitante, motivo, estado FROM solicitudes_eliminacion WHERE estado = %s"
                    cursor.execute(sql, (estado,))
                else:
                    sql = "SELECT id, calificacion_id, solicitante, motivo, estado FROM solicitudes_eliminacion"
                    cursor.execute(sql)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                results = []
                for r in rows:
                    doc = dict(zip(columns, r))
                    doc["_id"] = doc["id"]
                    results.append(doc)
                return results
        except Exception as e:
            print("Error obtener_solicitudes_eliminacion:", e)
            return []
        finally:
            conn.close()

    def actualizar_estado_solicitud(self, solicitud_id, nuevo_estado):
        try:
            sql_id = int(solicitud_id)
        except (ValueError, TypeError):
            return False
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "UPDATE solicitudes_eliminacion SET estado = %s WHERE id = %s"
                res = cursor.execute(sql, (nuevo_estado, sql_id))
            conn.commit()
            return res > 0
        except Exception as e:
            print("Error actualizar estado solicitud:", e)
            return False
        finally:
            conn.close()

    def eliminar_solicitud_por_id(self, solicitud_id):
        try:
            sql_id = int(solicitud_id)
        except (ValueError, TypeError):
            return False
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM solicitudes_eliminacion WHERE id = %s"
                res = cursor.execute(sql, (sql_id,))
            conn.commit()
            return res > 0
        except Exception as e:
            print("Error eliminar solicitud:", e)
            return False
        finally:
            conn.close()