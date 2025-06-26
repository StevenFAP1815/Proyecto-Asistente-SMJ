from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def obtener_conexion():
    DATABASE_URL = "mysql+pymysql://root:8136127STEVEN@localhost/bdfobo"  # Ajusta tus datos
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()

def test_db_connection():
    try:
        session = obtener_conexion()
        result = session.execute(text("SELECT 1")).fetchone()  # Aquí el cambio
        if result and result[0] == 1:
            print("✅ Conexión a la base de datos exitosa.")
        else:
            print("❌ Conexión a la base de datos fallida.")
        session.close()
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")

if __name__ == "__main__":
    test_db_connection()
