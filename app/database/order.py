from .db_connection import obtener_conexion
from sqlalchemy import text

def insertar_pedido(id_cliente):
    session = obtener_conexion()
    try:
        sql = """
        INSERT INTO pedidos (id_cliente, estado)
        VALUES (:id_cliente, 'pendiente')
        """
        session.execute(text(sql), {"id_cliente": id_cliente})
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def obtener_ultimo_pedido(id_cliente):
    session = obtener_conexion()
    try:
        sql = "SELECT id_pedido FROM pedidos WHERE id_cliente = :id_cliente ORDER BY fecha_pedido DESC LIMIT 1"
        resultado = session.execute(text(sql), {"id_cliente": id_cliente}).fetchone()
        return resultado['id_pedido'] if resultado else None
    except Exception as e:
        raise e
    finally:
        session.close()

def consultar_estado_pedido(id_pedido):
    """Consulta el estado de un pedido dado su id."""
    session = obtener_conexion()
    try:
        sql = "SELECT estado FROM pedidos WHERE id_pedido = :id_pedido"
        resultado = session.execute(text(sql), {"id_pedido": id_pedido}).fetchone()
        if resultado:
            return resultado['estado']
        return "Pedido no encontrado"
    except Exception as e:
        raise e
    finally:
        session.close()