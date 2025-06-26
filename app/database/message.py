from .db_connection import obtener_conexion
from sqlalchemy import text

def insertar_mensaje(id_cliente, contenido, tipo):
    session = obtener_conexion()
    try:
        sql = """
        INSERT INTO mensajes (id_cliente, contenido, tipo)
        VALUES (:id_cliente, :contenido, :tipo)
        """
        session.execute(text(sql), {"id_cliente": id_cliente, "contenido": contenido, "tipo": tipo})
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def obtener_mensajes_cliente(id_cliente):
    session = obtener_conexion()
    try:
        sql = "SELECT * FROM mensajes WHERE id_cliente = :id_cliente ORDER BY fecha DESC"
        resultado = session.execute(text(sql), {"id_cliente": id_cliente}).fetchall()
        return resultado
    except Exception as e:
        raise e
    finally:
        session.close()
