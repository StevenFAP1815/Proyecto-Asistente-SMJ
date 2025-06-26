from sqlalchemy import text
from .db_connection import obtener_conexion
import logging

# Configurar logging simple para depuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockRepository:
    
    @staticmethod
    def get_current_stock(product_id: int) -> int:
        """Obtiene el stock actual de un producto."""
        with obtener_conexion() as session:
            try:
                result = session.execute(
                    text("SELECT stock FROM productos WHERE id_producto = :id"),
                    {"id": product_id}
                ).fetchone()
                return result['stock'] if result else 0
            except Exception as e:
                logger.error(f"Error al consultar stock: {e}")
                raise

    @staticmethod
    def update_stock(product_id: int, quantity: int, action: str = 'add'):
        """
        Actualiza el stock de un producto.
        
        Args:
            product_id (int): ID del producto.
            quantity (int): Cantidad a modificar.
            action (str): 'add', 'subtract' o 'set'.
        
        Raises:
            ValueError: Si los parámetros son inválidos.
        """
        if quantity < 0:
            raise ValueError("La cantidad no puede ser negativa.")
        
        valid_actions = {'add', 'subtract', 'set'}
        if action not in valid_actions:
            raise ValueError(f"Acción inválida. Usa {valid_actions}")

        with obtener_conexion() as session:
            try:
                if action == 'set':
                    sql = "UPDATE productos SET stock = :qty WHERE id_producto = :id"
                else:
                    operator = '+' if action == 'add' else '-'
                    sql = f"UPDATE productos SET stock = stock {operator} :qty WHERE id_producto = :id"
                
                session.execute(text(sql), {"id": product_id, "qty": quantity})
                session.commit()
                logger.info(f"Stock actualizado para producto {product_id} ({action} {quantity})")
            except Exception as e:
                session.rollback()
                logger.error(f"Error al actualizar stock: {e}")
                raise

    @staticmethod
    def get_low_stock_products(threshold: int = 5):
        """Obtiene productos con stock bajo (≤ threshold)."""
        with obtener_conexion() as session:
            try:
                results = session.execute(
                    text("SELECT * FROM productos WHERE stock <= :threshold ORDER BY stock ASC"),
                    {"threshold": threshold}
                ).fetchall()
                return [dict(r) for r in results]
            except Exception as e:
                logger.error(f"Error al obtener productos con bajo stock: {e}")
                raise
