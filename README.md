# Smart Migration System

Sistema backend para la gestión inteligente de migración de clientes prepago a postpago en una empresa de telecomunicaciones. Identifica automáticamente clientes con perfil de migración, les envía ofertas personalizadas vía WhatsApp o SMS usando Twilio, y pone a disposición del equipo comercial un panel de seguimiento con historial completo de cada cliente.

---

## Tabla de contenidos

- [¿Qué hace el sistema?](#qué-hace-el-sistema)
- [Arquitectura y estructura del proyecto](#arquitectura-y-estructura-del-proyecto)
- [Módulos y responsabilidades](#módulos-y-responsabilidades)
- [Flujo principal del negocio](#flujo-principal-del-negocio)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Requisitos previos](#requisitos-previos)
- [Instalación local paso a paso](#instalación-local-paso-a-paso)
- [Instalación con Docker paso a paso](#instalación-con-docker-paso-a-paso)
- [Variables de entorno](#variables-de-entorno)
- [Endpoints de la API](#endpoints-de-la-api)
- [Documentación interactiva](#documentación-interactiva)
- [Frontend](#frontend)
- [Correr los tests](#correr-los-tests)
- [Antes de hacer un commit](#antes-de-hacer-un-commit)
- [Flujo de trabajo Git](#flujo-de-trabajo-git)
- [Equipo](#equipo)

---

## ¿Qué hace el sistema?

El sistema resuelve un problema concreto de negocio: una empresa de telecomunicaciones tiene clientes en planes prepago que podrían migrar a postpago, pero no tiene una forma automatizada de identificarlos, contactarlos y darles seguimiento.

El flujo completo es:

1. **Registro de clientes prepago** — se ingresan manualmente o se importan desde CSV/Excel.
2. **Registro de recargas** — cada recarga que hace un cliente queda registrada en el sistema.
3. **Motor de elegibilidad** — automáticamente evalúa si un cliente cumple los criterios para recibir una oferta (antigüedad mínima de la línea, configurable).
4. **Envío automático de oferta** — cuando un cliente pasa a ser elegible, el sistema le envía un mensaje de WhatsApp o SMS con la oferta de migración.
5. **Captura de respuesta** — el cliente responde "SI" o "NO" y el webhook de Twilio actualiza el estado en el sistema.
6. **Seguimiento por asesores** — el equipo comercial ve las conversaciones abiertas, las gestiona y cierra el proceso.
7. **Trazabilidad completa** — cada cambio que sufre un cliente (manual o automático) queda registrado en un historial consultable por el analista.

---

## Arquitectura y estructura del proyecto

El proyecto sigue una arquitectura de **Django por dominio de negocio**: cada módulo (`app`) agrupa todo lo relacionado con un área funcional específica (modelos, vistas, serializers, servicios, tests), en lugar de agrupar por tipo de archivo.

```
Proyecto-integrador-2/
│
├── apps/                          # Módulos de negocio
│   ├── users/                     # Gestión de usuarios, autenticación y roles
│   │   ├── models.py              # CustomUser (ADMIN, ANALYST, AGENT) + LoginAttempt
│   │   ├── serializers.py         # Serializers de usuario, login, perfil, contraseña
│   │   ├── views.py               # CRUD usuarios, JWT, perfil, recuperación contraseña
│   │   ├── services.py            # Lógica de creación, hashing, emails, tokens
│   │   ├── permissions.py         # IsAdmin, IsAnalyst, IsAgent, IsAdminOrAnalyst
│   │   ├── middleware.py          # RBACMiddleware — control de acceso por rol
│   │   └── urls.py
│   │
│   ├── core_business/             # Clientes prepago y planes
│   │   ├── models.py              # Client, Plan
│   │   ├── serializers.py         # CRUD clientes, importación CSV/Excel
│   │   ├── views.py               # CRUD clientes, exportación CSV, importación
│   │   ├── filters.py             # ClientFilter — filtros de negocio (RF07)
│   │   ├── signals.py             # Dispara evaluación de elegibilidad y envío de oferta
│   │   └── urls.py
│   │
│   ├── analytics/                 # Recargas, elegibilidad e historial
│   │   ├── models.py              # TopUp (recargas), ClientChangeLog (historial)
│   │   ├── serializers.py         # TopUp, elegibilidad, gasto promedio, historial
│   │   ├── views.py               # Endpoints de recargas, elegibilidad, historial
│   │   ├── services.py            # EligibilityEngine — motor de elegibilidad (RF13)
│   │   ├── history.py             # record_client_changes — trazabilidad RF18
│   │   ├── signals.py             # Recalcula gasto y elegibilidad al registrar recarga
│   │   └── urls.py
│   │
│   ├── management/                # Configuración del sistema y auditoría
│   │   ├── models.py              # BusinessRule, AuditLog (inmutable), GlobalSystemSettings
│   │   ├── views.py               # Reglas de negocio, bitácora, dashboard RF17
│   │   ├── audit.py               # log_critical_action — escritura centralizada RF14
│   │   ├── runtime_settings.py    # Lectura en caliente de configuración global
│   │   └── urls.py
│   │
│   └── communications/            # Twilio, notificaciones y conversaciones
│       ├── models.py              # NotificationLog, Conversation
│       ├── views.py               # Envío individual, masivo, webhook Twilio, conversaciones
│       ├── services.py            # TwilioService, ExternalAPIService
│       └── urls.py
│
├── config/                        # Configuración de Django
│   ├── settings/
│   │   ├── base.py                # Configuración compartida (todas las apps, JWT, DRF)
│   │   ├── dev.py                 # Desarrollo: SQLite, CORS abierto, DEBUG=True
│   │   └── prod.py                # Producción: PostgreSQL, CORS restringido
│   ├── urls.py                    # Rutas raíz del proyecto
│   ├── wsgi.py
│   └── asgi.py
│
├── frontend/                      # Panel web HTML/CSS/JS vanilla
│   ├── login.html
│   ├── dashboard.html
│   ├── clientes.html
│   ├── recargas.html
│   ├── planes.html
│   ├── usuarios.html
│   ├── conversaciones.html
│   ├── configuracion.html
│   ├── auditoria.html
│   ├── bitacora.html
│   ├── perfil.html
│   ├── css/style.css
│   └── js/api.js
│
├── tests/                         # Tests de integración por sprint
│   └── sprint2/
│
├── .env.example                   # Plantilla de variables de entorno
├── .pre-commit-config.yaml        # Hooks de black
├── .python-version                # Versión de Python del proyecto
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── requirements.txt
```

---

## Módulos y responsabilidades

### `apps/users` — Usuarios y seguridad
Gestiona todo lo relacionado con las personas que operan el sistema. Implementa tres roles: **ADMIN** (gestiona usuarios y configuración), **ANALYST** (consulta y analiza clientes) y **AGENT** (gestiona conversaciones). La autenticación es con JWT. Incluye recuperación de contraseña por email con token HMAC y bitácora de intentos de login.

### `apps/core_business` — Clientes y planes
Es el núcleo del negocio. Contiene el modelo `Client` (el cliente prepago con todos sus datos) y `Plan` (los planes de migración configurables con plantillas de mensajes y precios). Permite registrar clientes individualmente o importarlos masivamente desde CSV o Excel. Soporta exportación a CSV con los mismos filtros del listado.

### `apps/analytics` — Motor de elegibilidad e historial
Contiene el motor (`EligibilityEngine`) que decide si un cliente es candidato a migrar, basándose en la antigüedad de su línea (parámetro configurable). También gestiona las recargas (`TopUp`) y calcula el gasto promedio mensual. El módulo `history.py` implementa la trazabilidad completa de cambios sobre cada cliente (RF18).

### `apps/management` — Configuración y auditoría
Centraliza las reglas de negocio (parámetros configurables como días mínimos de antigüedad), la bitácora de auditoría (`AuditLog`, inmutable por diseño), la configuración global del sistema y el dashboard de métricas de conversión.

### `apps/communications` — Twilio y seguimiento
Maneja el envío de mensajes (WhatsApp y SMS) a través de Twilio, el webhook que recibe las respuestas de los clientes, y las conversaciones que se generan cuando un cliente responde "SI". Los asesores gestionan las conversaciones abiertas desde este módulo.

---

## Flujo principal del negocio

```
Cliente creado / actualizado
        │
        ▼
  [signal post_save]
  EligibilityEngine.evaluate_client()
        │
        ├── antigüedad < mínimo → is_eligible = False  ──────────────┐
        │                                                             │
        └── antigüedad >= mínimo → is_eligible = True                │
                  │                                                   │
                  ▼                                                   │
        [signal pre_save]                                             │
        TwilioService.send_offer()                                    │
                  │                                                   │
                  ▼                                                   │
        NotificationLog creado (SENT)                                 │
        Conversation creada (OPEN)                                    │
                  │                                                   │
                  ▼                                                   │
        Cliente responde por WhatsApp/SMS                             │
                  │                                                   │
        [webhook /api/v1/communications/webhook/]                     │
                  │                                                   │
                  ├── "SI" → NotificationLog=ACCEPTED                 │
                  │          Conversation=OPEN (para asesor)          │
                  │                                                   │
                  └── "NO" → NotificationLog=REJECTED   ◄────────────┘
                             Conversation=CLOSED
```

Cada paso que cambia el estado del cliente queda registrado en `ClientChangeLog` con quién lo hizo y cuándo.

---

## Tecnologías utilizadas

**Backend**
- Python 3.12
- Django 5.1
- Django REST Framework 3.15
- djangorestframework-simplejwt — autenticación JWT
- django-filter — filtros declarativos en endpoints
- django-cors-headers — manejo de CORS
- drf-spectacular — documentación automática Swagger / OpenAPI
- dj-database-url — configuración de BD por URL
- python-decouple — variables de entorno tipadas
- gunicorn — servidor WSGI para producción
- twilio — integración WhatsApp y SMS
- openpyxl — lectura de archivos Excel
- Pillow — manejo de imágenes (fotos de perfil)
- python-dateutil — utilidades de fechas

**Base de datos**
- SQLite — desarrollo local (sin configuración adicional)
- MySQL 8.0 — Docker y producción

**Calidad de código**
- black — formateador automático
- pre-commit — hooks que impiden commits sin formatear

**Frontend**
- HTML5 / CSS3 / JavaScript vanilla (sin framework, sin build)

**Infraestructura**
- Docker + Docker Compose

---

## Requisitos previos

Instalar en la máquina antes de clonar:

| Herramienta | Versión recomendada | Notas |
|---|---|---|
| Python | 3.12 | No usar 3.14+, tiene bug con Django Admin 5.1.x |
| pip | Incluido con Python | — |
| Git | Cualquier versión reciente | — |
| Docker Desktop | Cualquier versión reciente | Solo si usas Docker |

---

## Instalación local paso a paso

Esta es la forma más rápida para desarrollo. Usa SQLite, no necesita Docker ni MySQL.

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/juanda151005/Proyecto-integrador-2.git
cd Proyecto-integrador-2
```

### Paso 2 — Crear el entorno virtual

El entorno virtual aísla las dependencias del proyecto del resto del sistema.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

Cuando el entorno está activo, el prompt del terminal muestra `(venv)` al inicio.

### Paso 3 — Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 4 — Crear el archivo de variables de entorno

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Abrir el archivo `.env` y revisar los valores. Para desarrollo local **no es necesario cambiar nada** — el sistema usará SQLite automáticamente si `DATABASE_URL` está vacío. Los valores de Twilio y email solo son necesarios si se quieren probar esas funcionalidades.

### Paso 5 — Instalar pre-commit

```bash
pre-commit install
```

Esto configura el hook que corre `black` automáticamente antes de cada `git commit`. Solo se hace una vez por clon del repositorio.

### Paso 6 — Aplicar migraciones

```bash
python manage.py migrate
```

Esto crea todas las tablas en la base de datos SQLite local.

### Paso 7 — Crear el superusuario administrador

```bash
python manage.py createsuperuser
```

El sistema pedirá username, email y contraseña. Este usuario tendrá rol ADMIN y acceso completo.

### Paso 8 — Levantar el servidor

```bash
python manage.py runserver
```

El servidor queda disponible en `http://127.0.0.1:8000`.

Para verificar que todo funciona, abrir `http://127.0.0.1:8000/api/docs/` en el navegador — debe mostrar el Swagger con todos los endpoints.

---

## Instalación con Docker paso a paso

Esta opción levanta el backend junto con una base de datos MySQL en contenedores. Ideal para simular el entorno de producción.

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/juanda151005/Proyecto-integrador-2.git
cd Proyecto-integrador-2
```

### Paso 2 — Crear el archivo de variables de entorno

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Editar el `.env` y asegurarse de que `DATABASE_URL` apunte a MySQL:

```
DATABASE_URL=mysql://root:root@db:3306/smart_migration_db
```

### Paso 3 — Construir y levantar los contenedores

```bash
docker-compose up --build
```

La primera vez descarga las imágenes de Python y MySQL, lo que puede tardar unos minutos. Las siguientes veces es más rápido.

### Paso 4 — Aplicar migraciones (en otra terminal)

Con los contenedores corriendo, abrir una nueva terminal y ejecutar:

```bash
docker-compose exec web python manage.py migrate
```

### Paso 5 — Crear el superusuario

```bash
docker-compose exec web python manage.py createsuperuser
```

### Paso 6 — Verificar

El servidor queda disponible en `http://127.0.0.1:8000`.

Para detener los contenedores:
```bash
docker-compose down
```

Para detenerlos y eliminar los volúmenes (borra los datos de la BD):
```bash
docker-compose down -v
```

---

## Variables de entorno

| Variable | Descripción | Requerida en dev |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django. Cambiar en producción | No (hay default inseguro) |
| `DEBUG` | Modo debug | No (default `True`) |
| `ALLOWED_HOSTS` | Hosts permitidos separados por coma | No |
| `DATABASE_URL` | URL de conexión a la BD | No (SQLite si está vacío) |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | Duración del access token en minutos | No (default `60`) |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Duración del refresh token en días | No (default `7`) |
| `EMAIL_HOST_USER` | Correo Gmail para envío de emails | Solo para probar RF06 |
| `EMAIL_HOST_PASSWORD` | App Password de Gmail | Solo para probar RF06 |
| `FRONTEND_URL` | URL base del frontend para links en emails | No (default localhost) |
| `TWILIO_ACCOUNT_SID` | Account SID de Twilio | Solo para probar RF15 |
| `TWILIO_AUTH_TOKEN` | Auth Token de Twilio | Solo para probar RF15 |
| `TWILIO_PHONE_NUMBER` | Número Twilio para SMS | Solo para probar RF15 |
| `TWILIO_WHATSAPP_NUMBER` | Número Twilio para WhatsApp | Solo para probar RF15 |
| `EXTERNAL_API_BASE_URL` | URL de la API CRM externa | Solo para probar RF20 |
| `EXTERNAL_API_KEY` | API key del CRM externo | Solo para probar RF20 |

---

## Endpoints de la API

Todos los endpoints requieren el header `Authorization: Bearer <token>` salvo los marcados como públicos.

### Autenticación

| Método | URL | Descripción | Acceso |
|---|---|---|---|
| POST | `/api/v1/auth/token/` | Login — obtener access y refresh token | Público |
| POST | `/api/v1/auth/token/refresh/` | Renovar access token | Público |
| POST | `/api/v1/auth/password-reset/` | Solicitar email de recuperación | Público |
| POST | `/api/v1/auth/password-reset/confirm/` | Confirmar nuevo password | Público |

### Usuarios

| Método | URL | Descripción | Acceso |
|---|---|---|---|
| GET / POST | `/api/v1/users/` | Listar / crear usuarios | ADMIN |
| GET / PUT / DELETE | `/api/v1/users/<id>/` | Detalle de usuario | ADMIN |
| GET | `/api/v1/users/me/` | Datos del usuario autenticado | Autenticado |
| GET / PATCH | `/api/v1/users/profile/` | Ver / actualizar perfil propio | Autenticado |
| POST | `/api/v1/users/change-password/` | Cambiar contraseña propia | Autenticado |
| GET | `/api/v1/users/login-attempts/` | Bitácora de intentos de login | ADMIN |

### Clientes

| Método | URL | Descripción | Acceso |
|---|---|---|---|
| GET / POST | `/api/v1/clients/` | Listar / crear clientes | Autenticado |
| GET / PATCH / DELETE | `/api/v1/clients/<id>/` | Detalle de cliente | Autenticado |
| GET | `/api/v1/clients/export/` | Exportar clientes a CSV | Autenticado |
| POST | `/api/v1/clients/import/` | Importar clientes desde CSV/Excel | ADMIN / ANALYST |
| GET / POST | `/api/v1/clients/plans/` | Listar / crear planes | Autenticado / ADMIN |
| GET / PATCH / DELETE | `/api/v1/clients/plans/<id>/` | Detalle de plan | Autenticado / ADMIN |

### Analytics

| Método | URL | Descripción | Acceso |
|---|---|---|---|
| GET / POST | `/api/v1/analytics/topups/` | Listar / registrar recargas | Autenticado |
| GET / PATCH | `/api/v1/analytics/topups/<id>/` | Detalle de recarga | Autenticado |
| POST | `/api/v1/analytics/average-spending/` | Calcular gasto promedio de un cliente | Autenticado |
| POST | `/api/v1/analytics/eligibility/` | Evaluar elegibilidad (uno o todos) | Autenticado |
| GET | `/api/v1/analytics/change-logs/` | Historial de cambios de un cliente | Autenticado |

**Parámetros del historial de cambios:**
- `?client_id=<int>` — filtra por cliente (recomendado siempre)
- `?field_name=<str>` — filtra por nombre del campo (ej: `?field_name=Estado`)
- `?changed_by=<int>` — filtra por usuario que hizo el cambio

### Gestión

| Método | URL | Descripción | Acceso |
|---|---|---|---|
| GET / PATCH | `/api/v1/management/system-settings/` | Configuración global del sistema | ADMIN |
| GET / POST | `/api/v1/management/rules/` | Reglas de negocio | Autenticado / ADMIN |
| GET / PATCH / DELETE | `/api/v1/management/rules/<id>/` | Detalle de regla | ADMIN |
| GET | `/api/v1/management/audit-logs/` | Bitácora de auditoría | ADMIN |
| GET | `/api/v1/management/conversion-report/` | Dashboard de métricas | ADMIN / ANALYST |

### Comunicaciones

| Método | URL | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/v1/communications/notifications/` | Logs de notificaciones | Autenticado |
| POST | `/api/v1/communications/send/` | Enviar mensaje a un cliente | ADMIN / ANALYST |
| POST | `/api/v1/communications/send-offer/` | Enviar oferta personalizada | ADMIN / ANALYST |
| POST | `/api/v1/communications/bulk-notify/` | Envío masivo a elegibles | ADMIN |
| POST | `/api/v1/communications/webhook/` | Webhook Twilio (respuestas) | Público |
| GET | `/api/v1/communications/conversations/` | Listar conversaciones | ADMIN / ANALYST |
| GET / PATCH | `/api/v1/communications/conversations/<id>/` | Gestionar conversación | ADMIN / ANALYST |
| GET | `/api/v1/communications/external-api/` | Consulta CRM externo | Autenticado |

---

## Documentación interactiva

Con el servidor corriendo, la documentación está disponible en:

| URL | Descripción |
|---|---|
| `http://127.0.0.1:8000/api/docs/` | Swagger UI — probar endpoints directamente |
| `http://127.0.0.1:8000/api/redoc/` | ReDoc — documentación legible |
| `http://127.0.0.1:8000/api/schema/` | Esquema OpenAPI en JSON |
| `http://127.0.0.1:8000/admin/` | Panel de administración de Django |

### Cómo autenticarse en Swagger

1. Ir a `POST /api/v1/auth/token/` y expandirlo.
2. Hacer clic en **Try it out**.
3. Ingresar `username` y `password` del superusuario creado.
4. Ejecutar. Copiar el valor del campo `access` de la respuesta.
5. Hacer clic en el botón **Authorize** (arriba a la derecha, ícono de candado).
6. Escribir `Bearer <token copiado>` y confirmar.
7. Todos los endpoints siguientes ya estarán autenticados.

---

## Frontend

El panel web está en la carpeta `frontend/` como archivos HTML/CSS/JS estáticos. No requiere instalación, npm ni ningún proceso de build.

| Archivo | Descripción |
|---|---|
| `login.html` | Pantalla de inicio de sesión |
| `dashboard.html` | Panel principal con métricas de conversión |
| `clientes.html` | Listado, filtros y gestión de clientes |
| `recargas.html` | Registro y consulta de recargas |
| `planes.html` | Gestión de planes de migración |
| `usuarios.html` | Gestión de usuarios del sistema |
| `conversaciones.html` | Seguimiento de conversaciones con clientes |
| `configuracion.html` | Configuración global y reglas de negocio |
| `auditoria.html` | Bitácora de auditoría |
| `bitacora.html` | Bitácora de intentos de login |
| `perfil.html` | Perfil del usuario autenticado |

Para usarlo: abrir los archivos directamente en el navegador con el backend corriendo en `http://127.0.0.1:8000`.

---

## Correr los tests

```bash
# Correr todos los tests del proyecto
python manage.py test

# Correr tests de una app específica
python manage.py test apps.analytics
python manage.py test apps.users
python manage.py test apps.core_business
python manage.py test apps.management

# Correr con detalle de cada test
python manage.py test apps.analytics --verbosity=2

# Correr una capa específica de tests
python manage.py test apps.analytics.tests.test_models
python manage.py test apps.analytics.tests.test_serializers
python manage.py test apps.analytics.tests.test_services
python manage.py test apps.analytics.tests.test_views
```

Los tests usan una base de datos temporal separada que se crea y destruye automáticamente en cada ejecución.

---

## Antes de hacer un commit

Estos pasos son **obligatorios** antes de cualquier commit. El hook de pre-commit corre `black` automáticamente, pero es buena práctica hacerlo manual primero:

```bash
# 1. Formatear todo el código
black .

# 2. Correr los tests de la app que modificaste
python manage.py test apps.<nombre_app> --verbosity=2

# 3. Verificar que no haya archivos sin agregar
git status
```

Si algún test falla, **no hacer commit** hasta resolverlo.

---

## Flujo de trabajo Git

**Nunca hacer push directo a `dev` o `main`.**

### Tipos de commit

| Tipo | Cuándo usarlo |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `refactor` | Cambio de código sin nueva funcionalidad |
| `test` | Agregar o modificar tests |
| `docs` | Cambios en documentación |
| `chore` | Tareas de mantenimiento |

### Formato del mensaje de commit

```
tipo(scope): descripción corta en presente

- Detalle opcional del cambio 1
- Detalle opcional del cambio 2
```

Ejemplo:
```
feat(analytics): implementar RF18 - historial de cambios del cliente

- Crear history.py con record_client_changes y snapshot_for_history
- Integrar captura de cambios manuales en ClientDetailView.perform_update
- Integrar captura de cambios automáticos en signals de core_business y analytics
- Mejorar ClientChangeLogSerializer con source_label
```

### Flujo completo

```bash
# 1. Partir siempre desde dev actualizado
git checkout dev
git pull origin dev
git checkout -b feature/nombre-descriptivo

# 2. Desarrollar, formatear y testear
black .
python manage.py test apps.<app_modificada> --verbosity=2

# 3. Hacer commit
git add <archivos>
git commit -m "feat(scope): descripción"

# 4. Sincronizar con dev antes de subir
git fetch origin
git merge origin/dev

# 5. Subir la rama y abrir Pull Request
git push origin feature/nombre-descriptivo
# Abrir PR en GitHub: feature/... → dev
# NUNCA abrir PR directamente a main
```

---

## Equipo

| Nombre | Rol |
|---|---|
| Santiago Sabogal Lozano | Líder / Analista |
| Juan David Velásquez Restrepo | Desarrollador backend |
| Esteban Salazar Orozco | Diseñador / UX |
| Emmanuel Castañeda Cano | Analista de negocio |
