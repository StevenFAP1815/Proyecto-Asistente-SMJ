from .db_connection import obtener_conexion
from sqlalchemy import text
import logging

def crear_promocion(titulo, descripcion, fecha_inicio, fecha_fin):
    session = obtener_conexion()
    try:
        sql = """
        INSERT INTO promociones (titulo, descripcion, fecha_inicio, fecha_fin)
        VALUES (:titulo, :descripcion, :fecha_inicio, :fecha_fin)
        """
        session.execute(text(sql), {"titulo": titulo, "descripcion": descripcion, "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin})
        session.commit()
        logging.info("✅ Promoción creada exitosamente.")
    except Exception as e:
        session.rollback()
        logging.error(f"❌ Error al crear la promoción: {e}")
    finally:
        session.close()

def obtener_todos_los_clientes():
    session = obtener_conexion()
    try:
        sql = "SELECT id_cliente, telefono FROM clientes"
        clientes = session.execute(text(sql)).fetchall()
        return clientes
    except Exception as e:
        logging.error(f"❌ Error al obtener los clientes: {e}")
        return []
    finally:
        session.close()

def registrar_envio_promocion(id_cliente, id_promocion):
    session = obtener_conexion()
    try:
        sql = """
        INSERT INTO clientes_promociones (id_cliente, id_promocion)
        VALUES (:id_cliente, :id_promocion)
        """
        session.execute(text(sql), {"id_cliente": id_cliente, "id_promocion": id_promocion})
        session.commit()
        logging.info(f"✅ Promoción {id_promocion} registrada para cliente {id_cliente}.")
    except Exception as e:
        session.rollback()
        logging.error(f"❌ Error al registrar promoción enviada: {e}")
    finally:
        session.close()