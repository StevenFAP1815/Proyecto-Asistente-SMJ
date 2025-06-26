import os
import time
import sys
import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import openai
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.database.db_connection import get_db_connection

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AssistantStatus(Enum):
    """Estados del asistente para mejor control"""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    FILES_MISSING = "files_missing"

@dataclass
class AssistantConfig:
    """Configuración del asistente centralizada"""
    openai_api_key: str
    assistant_id: Optional[str] = None
    model: str = "gpt-4o-mini"
    max_polling_attempts: int = 60  # 30 segundos con 0.5s interval
    polling_interval: float = 0.5
    prompts_file_path: Optional[str] = None
    assistant_name: str = "Asistente_FOBO"

class AssistantManager:
    def __init__(self, config: Optional[AssistantConfig] = None):
        """Inicializa el AssistantManager con configuración opcional"""
        self.status = AssistantStatus.NOT_INITIALIZED
        self.client = None
        self.assistant_id = None
        self.config = config or self._load_config_from_env()
        
        # Configurar encoding solo en Windows si es necesario
        self._setup_system_encoding()
        
        # Inicializar cliente OpenAI
        self._initialize_openai_client()
        
        # Verificar y configurar asistente
        self._setup_assistant()

    def _load_config_from_env(self) -> AssistantConfig:
        """Carga configuración desde variables de entorno"""
        load_dotenv()
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada en el entorno")
        
        return AssistantConfig(
            openai_api_key=api_key,
            assistant_id=os.getenv("OPENAI_ASSISTANT_ID"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            prompts_file_path=os.getenv("PROMPTS_FILE_PATH")
        )

    def _setup_system_encoding(self):
        """Configura encoding del sistema si es necesario"""
        try:
            if sys.platform == "win32":
                # Verificar si ya está configurado correctamente
                import codecs
                if sys.stdout.encoding.lower() != 'utf-8':
                    os.system("chcp 65001 >nul 2>&1")  # Silenciar salida
                    logging.info("Configurado encoding UTF-8 en Windows")
        except Exception as e:
            logging.warning(f"No se pudo configurar encoding: {e}")

    def _initialize_openai_client(self):
        """Inicializa cliente OpenAI con manejo de errores"""
        try:
            self.client = openai.OpenAI(api_key=self.config.openai_api_key)
            # Verificar conectividad básica
            self.client.models.list()
            logging.info("Cliente OpenAI inicializado correctamente")
        except openai.AuthenticationError:
            raise ValueError("API Key de OpenAI inválida")
        except openai.APIConnectionError:
            raise ConnectionError("No se pudo conectar a la API de OpenAI")
        except Exception as e:
            raise RuntimeError(f"Error inicializando cliente OpenAI: {e}")

    def _setup_assistant(self):
        """Configura el asistente verificando o creando uno nuevo"""
        self.status = AssistantStatus.INITIALIZING
        
        try:
            if self.config.assistant_id and self._verify_existing_assistant():
                self.assistant_id = self.config.assistant_id
                self.status = AssistantStatus.READY
                logging.info(f"Asistente existente configurado: {self.assistant_id}")
            else:
                if self._create_new_assistant():
                    self.status = AssistantStatus.READY
                    logging.info(f"Nuevo asistente creado: {self.assistant_id}")
                else:
                    self.status = AssistantStatus.ERROR
                    logging.error("No se pudo configurar el asistente")
        except Exception as e:
            self.status = AssistantStatus.ERROR
            logging.error(f"Error configurando asistente: {e}")

    def _verify_existing_assistant(self) -> bool:
        """Verifica si el asistente existente es válido"""
        try:
            assistant = self.client.beta.assistants.retrieve(self.config.assistant_id)
            logging.info(f"Asistente válido: {assistant.name}")
            
            # Verificar si tiene herramientas de búsqueda de archivos
            has_file_search = any(
                tool.type == "file_search" 
                for tool in assistant.tools
            )
            
            if not has_file_search:
                logging.warning("Asistente no tiene herramientas de búsqueda de archivos")
                return False
                
            return True
        except openai.NotFoundError:
            logging.warning(f"Asistente {self.config.assistant_id} no encontrado")
            return False
        except Exception as e:
            logging.error(f"Error verificando asistente: {e}")
            return False

    def _create_new_assistant(self) -> bool:
        """Crea un nuevo asistente con archivos"""
        try:
            # Cargar archivo de prompts
            file_id = self._upload_prompts_file()
            if not file_id:
                self.status = AssistantStatus.FILES_MISSING
                return False

            # Crear vector store y añadir archivo
            vector_store = self.client.beta.vector_stores.create(
                name=f"{self.config.assistant_name}_knowledge"
            )
            
            self.client.beta.vector_stores.files.create(
                vector_store_id=vector_store.id,
                file_id=file_id
            )

            # Crear asistente con nueva API
            assistant = self.client.beta.assistants.create(
                name=self.config.assistant_name,
                instructions=self._get_assistant_instructions(),
                tools=[{"type": "file_search"}],  # Nueva API
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [vector_store.id]
                    }
                },
                model=self.config.model
            )

            self.assistant_id = assistant.id
            
            logging.info(f"IMPORTANTE: Nuevo asistente creado con ID: {assistant.id}")
            logging.info("Guarda este ID en tu configuración OPENAI_ASSISTANT_ID")
            
            return True
            
        except Exception as e:
            logging.error(f"Error creando asistente: {e}")
            return False

    def _get_assistant_instructions(self) -> str:
        """Retorna las instrucciones del asistente"""
        return (
            "Eres un asistente especializado en ayudar a emprendimientos. "
            "Debes responder preguntas sobre productos, precios, stock y políticas "
            "de la empresa. Usa EXCLUSIVAMENTE la información proporcionada en los archivos cargados. "
            "Si no encuentras información específica, indica claramente que no tienes esa información "
            "y sugiere contactar directamente con el equipo de soporte."
        )

    def _get_prompts_file_path(self) -> Optional[str]:
        """Obtiene la ruta del archivo de prompts"""
        if self.config.prompts_file_path:
            return self.config.prompts_file_path
            
        # Ruta por defecto
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        default_path = os.path.join(base_dir, "app", "services", "prompts", "prompts.md")
        
        return default_path if os.path.exists(default_path) else None

    def _upload_prompts_file(self) -> Optional[str]:
        """Sube el archivo de prompts y retorna el file_id"""
        try:
            file_path = self._get_prompts_file_path()
            if not file_path or not os.path.exists(file_path):
                logging.error("Archivo de prompts no encontrado")
                logging.error("Crea el archivo con:")
                logging.error("- Preguntas frecuentes (FAQ)")
                logging.error("- Información sobre productos y servicios")
                logging.error("- Políticas de envío, pago y devoluciones")
                return None

            with open(file_path, 'rb') as f:
                file = self.client.files.create(file=f, purpose="assistants")
                logging.info(f"Archivo de conocimiento cargado: {file.id}")
                return file.id
                
        except Exception as e:
            logging.error(f"Error cargando archivo de prompts: {e}")
            return None

    def _get_or_create_thread(self, wa_id: str) -> Optional[str]:
        """Obtiene thread existente o crea uno nuevo"""
        try:
            # Verificar thread existente
            thread_id = self._get_thread_from_db(wa_id)
            if thread_id:
                try:
                    # Verificar que el thread existe en OpenAI
                    self.client.beta.threads.retrieve(thread_id)
                    return thread_id
                except openai.NotFoundError:
                    logging.warning(f"Thread {thread_id} no existe en OpenAI, creando nuevo")
                    self._delete_thread_from_db(wa_id)

            # Crear nuevo thread
            thread = self.client.beta.threads.create()
            self._store_thread_in_db(wa_id, thread.id)
            logging.info(f"Nuevo thread creado: {thread.id}")
            return thread.id
            
        except Exception as e:
            logging.error(f"Error manejando thread: {e}")
            return None

    def _get_thread_from_db(self, wa_id: str) -> Optional[str]:
        """Obtiene thread_id desde la base de datos"""
        try:
            with get_db_connection() as session:
                result = session.execute(
                    text("SELECT thread_id FROM threads WHERE wa_id = :wa_id"),
                    {"wa_id": wa_id}
                ).fetchone()
                return result[0] if result else None
        except SQLAlchemyError as e:
            logging.error(f"Error consultando thread en DB: {e}")
            return None

    def _store_thread_in_db(self, wa_id: str, thread_id: str) -> bool:
        """Almacena thread en la base de datos - optimizado para MySQL"""
        try:
            with get_db_connection() as session:
                # Sintaxis específica para MySQL
                session.execute(
                    text("""
                        INSERT INTO threads (wa_id, thread_id)
                        VALUES (:wa_id, :thread_id)
                        ON DUPLICATE KEY UPDATE thread_id = VALUES(thread_id)
                    """),
                    {"wa_id": wa_id, "thread_id": thread_id}
                )
                session.commit()
                return True
        except SQLAlchemyError as e:
            logging.error(f"Error guardando thread en DB: {e}")
            return False

    def _delete_thread_from_db(self, wa_id: str) -> bool:
        """Elimina thread de la base de datos"""
        try:
            with get_db_connection() as session:
                session.execute(
                    text("DELETE FROM threads WHERE wa_id = :wa_id"),
                    {"wa_id": wa_id}
                )
                session.commit()
                return True
        except SQLAlchemyError as e:
            logging.error(f"Error eliminando thread de DB: {e}")
            return False

    def _run_assistant_with_timeout(self, thread_id: str, user_name: str) -> Optional[str]:
        """Ejecuta el asistente con timeout configurable"""
        try:
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                instructions=f"Estás conversando con {user_name}, cliente de un emprendimiento."
            )

            # Polling con timeout configurable
            for attempt in range(self.config.max_polling_attempts):
                time.sleep(self.config.polling_interval)
                
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id, 
                    run_id=run.id
                )
                
                logging.debug(f"Estado del run: {run.status} (intento {attempt + 1})")
                
                if run.status == "completed":
                    messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                    return messages.data[0].content[0].text.value
                elif run.status == "failed":
                    logging.error(f"Run falló: {run.last_error}")
                    return "Ocurrió un error al procesar tu mensaje. Por favor intenta nuevamente."
                elif run.status in ["cancelled", "expired"]:
                    return "La solicitud fue cancelada o expiró. Por favor intenta nuevamente."

            # Timeout alcanzado
            logging.warning(f"Timeout ejecutando asistente después de {self.config.max_polling_attempts} intentos")
            return "La solicitud tardó demasiado tiempo. Por favor intenta más tarde."
            
        except Exception as e:
            logging.error(f"Error ejecutando asistente: {e}")
            return "Hubo un problema técnico. Por favor intenta nuevamente."

    def is_ready(self) -> bool:
        """Verifica si el asistente está listo para procesar mensajes"""
        return self.status == AssistantStatus.READY and self.assistant_id is not None

    def get_status(self) -> AssistantStatus:
        """Retorna el estado actual del asistente"""
        return self.status

    def generate_response(self, message_body: str, wa_id: str, name: str) -> str:
        """Genera respuesta del asistente con manejo robusto de errores"""
        if not self.is_ready():
            error_msg = self._get_error_message_for_status()
            logging.error(f"Asistente no está listo: {self.status}")
            return error_msg

        if not message_body.strip():
            return "Por favor envía un mensaje con contenido."

        try:
            # Obtener o crear thread
            thread_id = self._get_or_create_thread(wa_id)
            if not thread_id:
                return "Error técnico creando conversación. Por favor intenta nuevamente."

            # Añadir mensaje del usuario
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message_body
            )

            # Ejecutar asistente
            response = self._run_assistant_with_timeout(thread_id, name)
            return response or "No pude generar una respuesta. Por favor intenta nuevamente."

        except openai.RateLimitError:
            return "Estoy procesando muchas solicitudes. Por favor espera un momento e intenta nuevamente."
        except openai.APIConnectionError:
            return "Problemas de conexión con el servicio. Por favor intenta más tarde."
        except Exception as e:
            logging.error(f"Error en generate_response: {e}")
            return "Ocurrió un error inesperado. Por favor intenta nuevamente."

    def _get_error_message_for_status(self) -> str:
        """Retorna mensaje de error apropiado según el estado"""
        status_messages = {
            AssistantStatus.NOT_INITIALIZED: "El asistente no está inicializado.",
            AssistantStatus.INITIALIZING: "El asistente se está inicializando. Por favor espera.",
            AssistantStatus.ERROR: "Error en la configuración del asistente.",
            AssistantStatus.FILES_MISSING: "Faltan archivos de configuración del asistente."
        }
        
        return status_messages.get(
            self.status, 
            "El asistente no está disponible en este momento."
        )

    def health_check(self) -> Dict[str, Any]:
        """Verifica el estado de salud del asistente"""
        return {
            "status": self.status.value,
            "ready": self.is_ready(),
            "assistant_id": self.assistant_id,
            "client_initialized": self.client is not None,
            "timestamp": time.time()
        }


# Instancia global del manager (para compatibilidad con código existente)
assistant_manager_instance = None

def initialize_assistant_manager(config: Optional[AssistantConfig] = None) -> AssistantManager:
    """Inicializa la instancia global del assistant manager"""
    global assistant_manager_instance
    assistant_manager_instance = AssistantManager(config)
    return assistant_manager_instance

def get_assistant_manager() -> AssistantManager:
    """Obtiene la instancia del assistant manager, inicializándola si es necesario"""
    global assistant_manager_instance
    if assistant_manager_instance is None:
        assistant_manager_instance = AssistantManager()
    return assistant_manager_instance

# Para compatibilidad con el código existente
if assistant_manager_instance is None:
    try:
        assistant_manager_instance = AssistantManager()
    except Exception as e:
        logging.error(f"Error inicializando assistant manager: {e}")
        assistant_manager_instance = None