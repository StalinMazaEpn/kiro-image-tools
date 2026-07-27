# Requirements Document

## Introduction

Este feature tiene dos objetivos principales:

1. **Mejorar la documentación del proyecto** — Reestructurar el README y/o crear documentación adicional con secciones claras de arquitectura, tecnologías usadas, estructura del proyecto y guía de uso básica.

2. **Crear configuración de despliegue en AWS Free Tier** — Generar una carpeta `aws/` con opciones viables para desplegar el servicio como demo en servicios gratuitos de AWS, considerando las restricciones de recursos del modelo U2NET (~176MB, ~512Mi-2Gi RAM).

## Glossary

- **Image_Tools_API**: Servicio REST API basado en Flask para procesamiento de imágenes (remoción de fondo con U2NET/rembg).
- **Documentation_System**: Conjunto de archivos markdown (README.md y docs adicionales) que describen la arquitectura, tecnologías y uso del proyecto.
- **AWS_Deployment_Config**: Carpeta `aws/` con archivos de infraestructura como código (IaC) y guías para desplegar en AWS Free Tier.
- **U2NET_Model**: Modelo de deep learning (~176MB ONNX) usado por rembg para segmentación de imágenes.
- **Free_Tier**: Nivel gratuito de AWS que permite uso limitado de servicios sin costo durante 12 meses o permanentemente según el servicio.

## Requirements

### Requirement 1: Documentación de arquitectura del sistema

**User Story:** Como desarrollador que descubre el proyecto, quiero encontrar una sección clara de arquitectura en la documentación, para que pueda entender rápidamente cómo están organizados los componentes y el flujo de datos.

#### Acceptance Criteria

1. THE Documentation_System SHALL incluir una sección de arquitectura que contenga una descripción textual o diagrama del flujo completo de procesamiento de imágenes, enumerando cada etapa en orden: recepción del request, autenticación via X-API-KEY, descarga de imágenes desde URL, remoción de fondo con rembg/U2NET, composición del sujeto sobre el fondo, y generación de la respuesta con URL temporal.
2. THE Documentation_System SHALL describir cada componente principal del sistema indicando para cada uno: nombre, responsabilidad en una oración, y ruta del archivo fuente en el repositorio. Los componentes mínimos a documentar son: ModelManager (singleton), middleware de autenticación, rutas (blueprints), esquemas de validación, y almacenamiento temporal.
3. THE Documentation_System SHALL documentar el patrón de precarga del modelo explicando: el motivo de precargar en lugar de cargar bajo demanda, cómo el flag `--preload` de Gunicorn permite compartir el modelo entre workers mediante copy-on-write, y qué ocurre si la precarga falla durante el arranque del proceso.

### Requirement 2: Documentación de tecnologías y dependencias

**User Story:** Como desarrollador, quiero una sección de tecnologías usadas en la documentación, para que pueda evaluar rápidamente la stack técnica y compatibilidad con mi entorno.

#### Acceptance Criteria

1. THE Documentation_System SHALL incluir una tabla o lista de las tecnologías principales con versión: Python 3.11, Flask 2.3.3, flask-smorest 0.42.1, marshmallow 3.20.1, rembg 2.0.57, onnxruntime 1.20.1, Pillow 10.1.0, Gunicorn 21.2.0.
2. THE Documentation_System SHALL describir el propósito de cada tecnología principal en el contexto del proyecto en máximo una oración por tecnología.
3. THE Documentation_System SHALL documentar las herramientas de desarrollo: uv como gestor de paquetes, Docker para contenedorización, docker-compose para orquestación local, y pyproject.toml como formato de definición de dependencias.

### Requirement 3: Documentación de estructura del proyecto

**User Story:** Como desarrollador nuevo en el proyecto, quiero ver la estructura de carpetas documentada, para que pueda navegar el código fuente de forma eficiente.

#### Acceptance Criteria

1. THE Documentation_System SHALL incluir un árbol de directorios hasta 2 niveles de profundidad que cubra todas las carpetas del proyecto (app/, app/routes/, app/schemas/, app/middleware/, tests/, k8s/, scripts/) y los archivos de configuración raíz (Dockerfile, docker-compose.yml, pyproject.toml, app.py, wsgi.py), con una descripción de máximo 150 caracteres por entrada que indique su propósito funcional.
2. THE Documentation_System SHALL describir la responsabilidad de cada módulo dentro de `app/` (config, model_manager, routes, schemas, middleware) en 1 a 3 oraciones que indiquen qué entrada recibe, qué salida produce y con qué otros módulos interactúa.
3. WHILE la documentación de estructura del proyecto está marcada como completa, IF se agrega una nueva carpeta o módulo dentro de `app/`, THEN THE Documentation_System SHALL requerir actualización del árbol de directorios y la descripción de módulos para mantener la documentación precisa. La adición de una nueva carpeta no marcará automáticamente la documentación como incompleta; la actualización queda como tarea pendiente que no bloquea el estado de completitud existente.

### Requirement 4: Mejora de la documentación existente

**User Story:** Como mantenedor del proyecto, quiero que la documentación existente sea coherente y bien organizada, para que la información no esté dispersa o duplicada.

#### Acceptance Criteria

1. THE Documentation_System SHALL reorganizar el README.md existente utilizando una jerarquía de encabezados de máximo 3 niveles (H1 para el título del proyecto, H2 para secciones principales, H3 para subsecciones), donde cada sección principal está separada por una línea en blanco antes de su encabezado H2.
2. THE Documentation_System SHALL mantener en el README reorganizado todas las secciones de contenido presentes en el README original: descripción del proyecto, arquitectura, instrucciones de ejecución local/Docker/Docker Compose/Kubernetes, tabla de endpoints, ejemplos de uso (curl, .http, Swagger), documentación del endpoint image-process con sus parámetros, y ejecución de tests.
3. THE Documentation_System SHALL eliminar las secciones que contengan únicamente texto placeholder (secciones cuyo cuerpo sea exclusivamente "TODO:" seguido de texto genérico sin información específica del proyecto) y el bloque de enlaces de referencia externos no relacionados con el proyecto (enlaces a ASP.NET Core, VS Code, Chakra Core).
4. IF una sección del README original contiene información duplicada en otra sección, THEN THE Documentation_System SHALL consolidar el contenido duplicado en una única sección, preservando la versión más completa y eliminando la repetición. WHEN no existen secciones duplicadas en el README original, THE Documentation_System SHALL omitir el paso de consolidación.
5. IF la consolidación de contenido duplicado falla durante la reorganización, THEN THE Documentation_System SHALL continuar con la reorganización dejando las secciones duplicadas en su lugar original en vez de detener el proceso.

### Requirement 5: Evaluación de opciones de despliegue AWS Free Tier

**User Story:** Como desarrollador, quiero un documento que compare opciones viables de AWS Free Tier para este servicio, para que pueda elegir la mejor alternativa para una demo.

#### Acceptance Criteria

1. THE AWS_Deployment_Config SHALL incluir un documento comparativo de al menos 3 opciones de despliegue en AWS Free Tier, evaluando cada una contra las restricciones del servicio: imagen Docker de 600MB, modelo de 176MB, y consumo de RAM entre 512MB y 2GB en runtime.
2. WHEN una opción de AWS no sea viable por restricciones de memoria (menos de 512MB disponible para la aplicación), almacenamiento (menos de 600MB para la imagen), o tiempo de cold start superior a 120 segundos, THE AWS_Deployment_Config SHALL documentar la opción excluida indicando: nombre del servicio, restricción específica que la descalifica, y el valor límite del servicio comparado con el valor requerido.
3. THE AWS_Deployment_Config SHALL incluir para cada opción viable: estimación de costo mensual en USD dentro del Free Tier (12 meses) y después del Free Tier, límite de horas o invocaciones mensuales gratuitas, RAM asignable en MB, almacenamiento disponible en GB, tiempo estimado de cold start en segundos, y comando o archivo de configuración de referencia para el despliegue.
4. THE AWS_Deployment_Config SHALL incluir una tabla resumen que clasifique las opciones viables por orden de recomendación, indicando para cada una: puntuación de viabilidad (alta, media, baja) basada en compatibilidad con las restricciones, y la limitación principal para uso en demo.
5. IF ninguna opción de AWS Free Tier cumple simultáneamente con las restricciones de RAM mínima de 512MB y almacenamiento mínimo de 600MB, THEN THE AWS_Deployment_Config SHALL documentar la opción de menor costo fuera del Free Tier que sí cumpla las restricciones, incluyendo el costo mensual estimado en USD.

### Requirement 6: Configuración de despliegue AWS recomendada

**User Story:** Como desarrollador, quiero archivos de infraestructura listos para desplegar en la opción AWS recomendada, para que pueda levantar una demo funcional sin configuración manual extensa.

#### Acceptance Criteria

1. THE AWS_Deployment_Config SHALL proporcionar archivos de infraestructura como código usando una única herramienta de IaC (CloudFormation, CDK, o Terraform) para desplegar el contenedor en un servicio AWS compatible con Free Tier que soporte contenedores Docker (por ejemplo, App Runner, ECS con Fargate, o EC2).
2. THE AWS_Deployment_Config SHALL incluir un README con instrucciones paso a paso para desplegar desde cero, incluyendo: prerrequisitos de software (CLI de AWS, herramienta IaC), configuración de credenciales AWS, comandos de despliegue en orden, y comando para verificar que el servicio responde en el endpoint /health.
3. THE AWS_Deployment_Config SHALL configurar el contenedor con mínimo 512Mi de RAM, mínimo 0.25 vCPU, almacenamiento suficiente para el modelo U2NET (176MB incluido en la imagen Docker), puerto 8070 expuesto, timeout de request de al menos 300 segundos, y un health check configurado contra el endpoint /health con un start period de al menos 120 segundos.
4. IF el servicio de AWS requiere configuración de red (VPC, subnets, security groups), THEN THE AWS_Deployment_Config SHALL incluir la configuración de red necesaria en los archivos IaC o documentar en el README los pasos exactos para usar la configuración de red por defecto de la cuenta AWS.
5. THE AWS_Deployment_Config SHALL incluir la configuración de un repositorio de imágenes (ECR) y las variables de entorno requeridas por el servicio (ENVIRONMENT, IMAGE_TOOLS_API_TOKENS, IMAGE_TOOLS_API_GLOBAL_PREFIX, MAX_UPLOAD_MB) como parámetros configurables en los archivos IaC.
6. WHEN el desarrollador ejecuta los comandos de despliegue documentados en el README con credenciales AWS válidas, THE AWS_Deployment_Config SHALL resultar en un servicio que cumple ambas condiciones: el health check interno del contenedor responde con estado exitoso en el endpoint /health, Y el servicio es accesible públicamente via HTTPS o HTTP, dentro de los 5 minutos posteriores al inicio del despliegue.

### Requirement 7: Variables de entorno y seguridad en AWS

**User Story:** Como desarrollador, quiero que la configuración AWS maneje correctamente las variables de entorno y secretos, para que pueda desplegar de forma segura sin exponer tokens.

#### Acceptance Criteria

1. THE AWS_Deployment_Config SHALL definir las variables de entorno requeridas por la Image_Tools_API: ENVIRONMENT, IMAGE_TOOLS_API_TOKENS, IMAGE_TOOLS_API_GLOBAL_PREFIX, MAX_UPLOAD_MB, IMAGE_PROCESS_VALIDATE_HTTPS_URL, y LOG_LEVEL, asignando valores por defecto documentados para las variables no sensibles (IMAGE_TOOLS_API_GLOBAL_PREFIX=/api/v1, MAX_UPLOAD_MB=10, IMAGE_PROCESS_VALIDATE_HTTPS_URL=false, LOG_LEVEL=INFO).
2. THE AWS_Deployment_Config SHALL clasificar IMAGE_TOOLS_API_TOKENS como secreto y almacenarlo mediante AWS Secrets Manager o SSM Parameter Store (tipo SecureString), mientras que las variables no sensibles (ENVIRONMENT, IMAGE_TOOLS_API_GLOBAL_PREFIX, MAX_UPLOAD_MB, IMAGE_PROCESS_VALIDATE_HTTPS_URL, LOG_LEVEL) SHALL ser definidas como variables de entorno en texto plano en la configuración del servicio.
3. THE AWS_Deployment_Config SHALL incluir un archivo de ejemplo para secrets (sin valores reales) que liste cada variable sensible con un valor placeholder y contenga comentarios indicando el mecanismo de almacenamiento utilizado (Secrets Manager o SSM SecureString) y los pasos para configurar cada secreto.
4. IF una variable de entorno requerida (ENVIRONMENT, IMAGE_TOOLS_API_TOKENS, IMAGE_TOOLS_API_GLOBAL_PREFIX, MAX_UPLOAD_MB, IMAGE_PROCESS_VALIDATE_HTTPS_URL, LOG_LEVEL) no está definida o está vacía al momento del despliegue, THEN THE AWS_Deployment_Config SHALL impedir el inicio del contenedor sin aplicar valores por defecto para ninguna variable de la lista requerida, y registrar un mensaje de error indicando el nombre de la variable faltante. WHEN todas las variables requeridas están presentes y el contenedor inicia correctamente, THE AWS_Deployment_Config SHALL omitir el registro de errores relacionados con variables de entorno.
5. IF el secreto IMAGE_TOOLS_API_TOKENS no puede ser recuperado del almacén de secretos (Secrets Manager o SSM Parameter Store) debido a permisos insuficientes o recurso inexistente, THEN THE AWS_Deployment_Config SHALL impedir el inicio del contenedor y registrar un mensaje de error indicando la falla de acceso al secreto sin exponer el valor del mismo.
