from app.database.create_customer import obtener_cliente_por_telefono, insertar_cliente
from database.order import insertar_pedido
from database.detail import insertar_detalle_pedido
from database.message import enviar_mensaje
from database.product import StockRepository
import logging

async def manejar_intencion(data_intencion, telefono, nombre):
    intencion = data_intencion.get("intencion")
    parametros = data_intencion.get("parametros", {})
    respuesta_gpt = data_intencion.get("respuesta_gpt", "No se pudo procesar la solicitud.")

    try:
        if intencion == "hacer_pedido":
            # Verificar si el cliente existe
            cliente = obtener_cliente_por_telefono(telefono)
            if not cliente:
                insertar_cliente(nombre, telefono, "Sin dirección")
                cliente = obtener_cliente_por_telefono(telefono)

            # Buscar producto por nombre
            producto_nombre = parametros.get("producto", "agua")
            producto_db = StockRepository.get_producto_por_nombre(producto_nombre)

            if not producto_db:
                return f"Lo siento, no tenemos el producto '{producto_nombre}'."

            cantidad = parametros.get("cantidad", 1)
            precio_unitario = float(producto_db['precio'])
            id_producto = producto_db['id_producto']

            # Crear el pedido
            pedido_id = insertar_pedido(cliente['id_cliente'])

            # Insertar el detalle del pedido
            insertar_detalle_pedido(pedido_id, id_producto, cantidad, precio_unitario)

            mensaje_respuesta = f"Pedido recibido: {cantidad}x {producto_nombre}."
            await enviar_mensaje(telefono, mensaje_respuesta)
            return mensaje_respuesta

        # Otras intenciones
        return respuesta_gpt

    except Exception as e:
        logging.error(f"Error al manejar intención: {e}")
        return "Hubo un error al procesar tu solicitud."
