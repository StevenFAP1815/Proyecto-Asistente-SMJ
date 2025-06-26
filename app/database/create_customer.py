from .db_connection import obtener_conexion
from sqlalchemy import text

def insertar_cliente(nombre, telefono, direccion):
    session = obtener_conexion()
    try:
        sql = """
        INSERT INTO clientes (nombre, telefono, direccion)
        VALUES (:nombre, :telefono, :direccion)
        """
        session.execute(text(sql), {"nombre": nombre, "telefono": telefono, "direccion": direccion})
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def obtener_cliente_por_telefono(telefono):
    session = obtener_conexion()
    try:
        sql = "SELECT * FROM clientes WHERE telefono = :telefono"
        resultado = session.execute(text(sql), {"telefono": telefono}).fetchone()
        return resultado
    except Exception as e:
        raise e
    finally:
        session.close()