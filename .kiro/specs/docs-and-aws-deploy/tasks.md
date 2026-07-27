# Implementation Plan: docs-and-aws-deploy

## Overview

Este plan implementa la reestructuración de documentación del proyecto y la configuración de despliegue AWS Free Tier. Las tareas están ordenadas para que la documentación base se complete primero, seguida del documento comparativo de AWS, los archivos de infraestructura, y finalmente la validación.

## Tasks

- [ ] 1. Reestructurar README.md y agregar documentación del proyecto
  - [ ] 1.1 Reorganizar README.md con jerarquía de encabezados correcta
    - Reestructurar el README.md existente usando H1 para título, H2 para secciones principales, H3 para subsecciones
    - Eliminar secciones placeholder ("Build and Test TODO:", "Contribute TODO:") y el bloque de enlaces externos (ASP.NET Core, VS Code, Chakra Core)
    - Consolidar contenido duplicado si existe, preservando la versión más completa
    - Mantener todas las secciones de contenido existentes: descripción, arquitectura, ejecución local/Docker/Compose/K8s, endpoints, ejemplos de uso, endpoint image-process, tests
    - Separar cada sección H2 con línea en blanco antes del encabezado
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 1.2 Agregar sección de Arquitectura del sistema
    - Crear sección H2 "Arquitectura" con descripción del flujo completo de procesamiento: recepción request → autenticación X-API-KEY → descarga imágenes desde URL → remoción de fondo con rembg/U2NET → composición sujeto sobre fondo → respuesta con URL temporal
    - Documentar cada componente principal: ModelManager (singleton, `app/model_manager.py`), middleware de autenticación (`app/middleware/auth.py`), rutas/blueprints (`app/routes/`), esquemas de validación (`app/schemas/`), almacenamiento temporal
    - Documentar patrón de precarga del modelo: motivo (evitar latencia en primer request), flag `--preload` de Gunicorn para copy-on-write entre workers, comportamiento si precarga falla
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ] 1.3 Agregar sección de Tecnologías y dependencias
    - Crear sección H2 "Tecnologías" con tabla de tecnologías principales y versiones: Python 3.11, Flask 2.3.3, flask-smorest 0.42.1, marshmallow 3.20.1, rembg 2.0.57, onnxruntime 1.20.1, Pillow 10.1.0, Gunicorn 21.2.0
    - Incluir propósito de cada tecnología en una oración (contexto del proyecto)
    - Documentar herramientas de desarrollo: uv (gestor de paquetes), Docker (contenedorización), docker-compose (orquestación local), pyproject.toml (definición de dependencias)
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 1.4 Agregar sección de Estructura del proyecto
    - Crear sección H2 "Estructura del proyecto" con árbol de directorios hasta 2 niveles de profundidad
    - Cubrir carpetas: app/, app/routes/, app/schemas/, app/middleware/, tests/, k8s/, scripts/ y archivos raíz: Dockerfile, docker-compose.yml, pyproject.toml, app.py, wsgi.py
    - Descripción de máximo 150 caracteres por entrada indicando propósito funcional
    - Describir responsabilidad de cada módulo dentro de `app/` (config, model_manager, routes, schemas, middleware) en 1-3 oraciones: entrada, salida, interacciones
    - _Requirements: 3.1, 3.2_

- [ ] 2. Checkpoint - Verificar documentación del README
  - Ensure all content is correct and well-structured, ask the user if questions arise.

- [ ] 3. Crear documento comparativo de opciones AWS
  - [ ] 3.1 Crear `aws/COMPARISON.md` con evaluación de opciones AWS Free Tier
    - Crear carpeta `aws/` y archivo `COMPARISON.md`
    - Documentar restricciones del servicio: imagen Docker 600MB, modelo U2NET 176MB, RAM runtime 512MB-2GB
    - Evaluar al menos 5 opciones: EC2 t2.micro, Lambda (container), App Runner, ECS Fargate, Lightsail
    - Para cada opción viable: costo mensual USD (Free Tier y post-Free Tier), horas/invocaciones gratuitas, RAM asignable MB, almacenamiento GB, cold start estimado, referencia de configuración
    - Para opciones no viables: nombre, restricción específica que descalifica, valor límite vs valor requerido
    - Tabla resumen con clasificación por viabilidad (alta/media/baja) y limitación principal
    - Si ninguna opción cumple restricciones, documentar opción de menor costo fuera de Free Tier
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 4. Implementar archivos de infraestructura AWS
  - [ ] 4.1 Crear `aws/scripts/entrypoint.sh` para validación de variables de entorno
    - Crear script shell que valide variables requeridas antes de iniciar Gunicorn
    - Variables a validar: ENVIRONMENT, IMAGE_TOOLS_API_TOKENS, IMAGE_TOOLS_API_GLOBAL_PREFIX, MAX_UPLOAD_MB, IMAGE_PROCESS_VALIDATE_HTTPS_URL, LOG_LEVEL
    - Verificar que cada variable existe Y no está vacía
    - Formato de error: `[ENTRYPOINT] ERROR: Required environment variable '<NAME>' is not set or empty`
    - Si falta alguna: salir con código 1 sin iniciar Gunicorn
    - Si todas presentes: ejecutar `exec gunicorn ...` (reemplazar proceso shell)
    - Nunca imprimir valores de secretos, solo nombres de variables
    - Errores a stderr para captura por Docker/CloudWatch
    - _Requirements: 7.4, 7.5_

  - [ ] 4.2 Crear `aws/cloudformation/template.yaml` con stack de infraestructura
    - Crear template CloudFormation con recursos: ECR Repository, EC2 Security Group (puertos 8070 + 22), IAM Role + Instance Profile (ECR pull + SSM read), EC2 Instance t2.micro con Amazon Linux 2023
    - Parámetros de entrada: Environment, ApiGlobalPrefix, MaxUploadMb, ValidateHttpsUrl, LogLevel, KeyPairName, ApiTokensParameterName
    - UserData: instalar Docker en la instancia
    - Outputs: InstancePublicIp, EcrRepositoryUri, ServiceUrl
    - Configurar mínimo 512Mi RAM (t2.micro = 1GB), puerto 8070, timeout 300s
    - Health check contra /health con start period de 120s
    - _Requirements: 6.1, 6.3, 6.4, 6.5_

  - [ ] 4.3 Crear `aws/env.example` con ejemplo de variables de entorno
    - Listar cada variable con valor placeholder
    - Clasificar IMAGE_TOOLS_API_TOKENS como secreto (SSM SecureString)
    - Variables no sensibles con valores por defecto documentados: IMAGE_TOOLS_API_GLOBAL_PREFIX=/api/v1, MAX_UPLOAD_MB=10, IMAGE_PROCESS_VALIDATE_HTTPS_URL=false, LOG_LEVEL=INFO
    - Incluir comentarios indicando mecanismo de almacenamiento (SSM SecureString) y pasos para configurar secreto
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ] 4.4 Crear `aws/README.md` con guía de despliegue paso a paso
    - Documentar prerrequisitos: AWS CLI, credenciales configuradas
    - Instrucciones paso a paso: crear parámetro SSM SecureString, desplegar stack CloudFormation, build y push imagen Docker a ECR, SSH a instancia para docker pull y run
    - Comando para verificar servicio responde en /health
    - Documentar flujo completo desde cero hasta health check exitoso
    - Notas sobre VPC default y troubleshooting
    - _Requirements: 6.2, 6.6_

- [ ] 5. Checkpoint - Verificar archivos AWS
  - Ensure all files are created correctly, CloudFormation template is syntactically valid, ask the user if questions arise.

- [ ] 6. Agregar sección AWS al README principal y validación final
  - [ ] 6.1 Agregar sección de despliegue AWS al README.md principal
    - Agregar subsección H3 "AWS (EC2 Free Tier)" dentro de la sección "Construir y ejecutar" del README
    - Referenciar `aws/README.md` para instrucciones detalladas
    - Incluir resumen breve: EC2 t2.micro, CloudFormation, SSM Parameter Store
    - _Requirements: 4.2, 6.2_

  - [ ]* 6.2 Validar CloudFormation template con AWS CLI
    - Ejecutar `aws cloudformation validate-template --template-body file://aws/cloudformation/template.yaml`
    - Corregir errores de sintaxis o referencias inválidas
    - _Requirements: 6.1_

  - [ ]* 6.3 Crear tests para entrypoint.sh
    - Escribir script de test que valide: todas variables presentes → éxito, variable faltante → exit 1 con mensaje, variable vacía → exit 1 con mensaje, múltiples faltantes → mensajes para cada una
    - Ubicar en `tests/test_entrypoint.sh` o usar bats-core si disponible
    - _Requirements: 7.4, 7.5_

- [ ] 7. Final checkpoint - Verificar integración completa
  - Ensure all documentation is consistent, README restructured correctly, AWS files complete, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- No property-based testing needed — this feature is documentation + IaC (static content and declarative configuration)
- The entrypoint.sh script is the only executable code; example-based tests are sufficient
- CloudFormation validation via `aws cloudformation validate-template` is the primary automated check

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["3.1", "4.1"] },
    { "id": 3, "tasks": ["4.2", "4.3"] },
    { "id": 4, "tasks": ["4.4"] },
    { "id": 5, "tasks": ["6.1", "6.2", "6.3"] }
  ]
}
```
