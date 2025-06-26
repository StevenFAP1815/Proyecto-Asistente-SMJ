from .db_connection import obtener_conexion
from sqlalchemy import text

def insertar_detalle_pedido(id_pedido, id_producto, cantidad, precio_unitario):
    session = obtener_conexion()
    try:
        sql = """
        INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, precio_unitario)
        VALUES (:id_pedido, :id_producto, :cantidad, :precio_unitario)
        """
        session.execute(text(sql), {"id_pedido": id_pedido, "id_producto": id_producto, "cantidad": cantidad, "precio_unitario": precio_unitario})
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def obtener_detalles_pedido(id_pedido):
    session = obtener_conexion()
    try:
        sql = "SELECT * FROM detalle_pedido WHERE id_pedido = :id_pedido"
        resultado = session.execute(text(sql), {"id_pedido": id_pedido}).fetchall()
        return resultado
    except Exception as e:
        raise e
    finally:
        session.close()