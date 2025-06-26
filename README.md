# Proyecto-Asistente-SMJ
Asistente de ventas personalizable

# Virtual-Assistant
Prototipo chatbot 

## Limitaciones
Actualemente el bot esta diseñado sobre el freamwork "Flask" por lo que la respuestas a peticiones moderadas (peticiones entre 200-300) no es la más óptima pues hay un retardo para responder cada solicitud. 

El código no puede responder a otra petición sin terminar una tarea previa.

## Funcionalidades extra
Se planea implementar:
- Filtros para discriminar entre compradores potenciales y "mirones". Con el fin de ahorrar tokens.
- Feedback interactivo para entrenamiento del asistente para que sea más preciso con sus respuestas.

## Errores a manejar
### Generales
    - Caídas de las API's.
    - Errores en las rutas de archivos pdf (prompts).
    - Asegurar que el archivo de texto plano este cargado correctamente.
    - Ventana sobrepasa las 24hrs y no hay respuesta del cliente (gasto extra).
### Técnicos
- Validación más estricta en los mensajes de whatsapp (campos vacíos).
- Evitar inyecciones SQL.
- Timeouts y reintentos mas elaborados para depuración

## Siguientes pasos a futuro
- Cambiar de freamwork. Flask ----> FastAPI (Para poder recibir hasta mil solicitudes que puedan responderse al mismo tiempo).
- Adquirir un dominio y servicio de hosting.
