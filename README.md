# Sistema Inteligente de Migración de Clientes Prepago a Postpago

Sistema backend en Django REST Framework que identifica clientes prepago con alto
potencial de migración, les envía ofertas automáticas vía WhatsApp/SMS usando Twilio,
y registra su intención de cambio para el equipo comercial.

---

## Tabla de contenidos

- [Requisitos previos](#requisitos-previos)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación local (sin Docker)](#instalación-local-sin-docker)
- [Instalación con Docker](#instalación-con-docker)
- [Variables de entorno](#variables-de-entorno)
- [Migraciones y base de datos](#migraciones-y-base-de-datos)
- [Correr el servidor](#correr-el-servidor)
- [Correr los tests](#correr-los-tests)
- [Frontend](#frontend)
- [Documentación de la API](#documentación-de-la-api)
- [Antes de hacer un commit](#antes-de-hacer-un-commit)
- [Flujo de trabajo Git](#flujo-de-trabajo-git)

---

## Requisitos previos

Tener instalado en tu máquina antes de clonar el proyecto:

| Herramienta | Versión mínima | Descarga |
|---|---|---|
| Python | 3.12 | https://www.python.org/downloads/ |
| pip | Incluido con Python | — |
| Git | Cualquier versión reciente | https://git-scm.com/ |
| Docker Desktop | Cualquier versión reciente | https://www.docker.com/products/docker-desktop/ (opcional) |

---

## Tecnologías utilizadas

**Backend**
- Django 5.1 — framework web
- Django REST Framework 3.15 — construcción de la API REST
- djangorestframework-simplejwt — autenticación JWT
- django-filter — filtros en endpoints
- django-cors-headers — manejo de CORS
- drf-spectacular — documentación automática Swagger / OpenAPI
- dj-database-url — configuración de base de datos por URL
- python-decouple — manejo de variables de entorno
- psycopg2-binary — driver PostgreSQL
- gunicorn — servidor WSGI para producción
- twilio — integración con WhatsApp y SMS
- python-dateutil — utilidades de fechas

**Base de datos**
- SQLite (desarrollo local)
- PostgreSQL 16 (Docker / producción)

**Calidad de código**
- black — formateador automático de código
- pre-commit — hooks que impiden commits sin formatear

**Frontend**
- HTML5 / CSS3 / JavaScript vanilla (sin framework)

**Infraestructura**
- Docker + Docker Compose (opcional para desarrollo)

---

## Estructura del proyecto

```
Proyecto-integrador-2/
├── apps/
│   ├── users/           # RF01–RF05 — Usuarios, login, roles, seguridad
│   ├── core_business/   # RF06–RF10 — Clientes prepago, filtros, exportación CSV
│   ├── analytics/       # RF11–RF13, RF18 — Recargas, elegibilidad, historial
│   ├── management/      # RF14, RF16, RF17 — Reglas de negocio, auditoría, dashboard
│   └── communications/  # RF15, RF20 — Twilio, notificaciones, webhook
├── config/
│   ├── settings/
│   │   ├── base.py      # Configuración compartida
│   │   ├── dev.py       # Configuración de desarrollo (SQLite)
│   │   └── prod.py      # Configuración de producción (PostgreSQL)
│   └── urls.py          # Rutas principales
├── frontend/            # Archivos HTML/CSS/JS del panel administrativo
├── .env.example         # Plantilla de variables de entorno
├── .pre-commit-config.yaml
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── requirements.txt
```

---

## Instalación local (sin Docker)

### 1. Clonar el repositorio

```bash
git clone https://github.com/juanda151005/Proyecto-integrador-2.git
cd Proyecto-integrador-2
```

### 2. Crear y activar el entorno virtual

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

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar la plantilla
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

Abrir el archivo `.env` y completar los valores. Para desarrollo local
el `DATABASE_URL` se puede dejar vacío — usará SQLite automáticamente.

### 5. Instalar pre-commit

```bash
pre-commit install
```

Esto configura el hook que ejecuta `black` automáticamente antes de cada commit.

### 6. Aplicar migraciones

```bash
python manage.py migrate
```

### 7. Crear superusuario

```bash
python manage.py createsuperuser
```

### 8. Levantar el servidor

```bash
python manage.py runserver
```

El servidor queda disponible en `http://127.0.0.1:8000`.

---

## Instalación con Docker

### 1. Clonar el repositorio

```bash
git clone https://github.com/juanda151005/Proyecto-integrador-2.git
cd Proyecto-integrador-2
```

### 2. Configurar variables de entorno

```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

En el `.env` el `DATABASE_URL` debe apuntar a PostgreSQL:

```
DATABASE_URL=postgres://postgres:postgres@db:5432/smart_migration_db
```

### 3. Levantar los contenedores

```bash
docker-compose up --build
```

### 4. Aplicar migraciones (en otra terminal)

```bash
docker-compose exec web python manage.py migrate
```

### 5. Crear superusuario

```bash
docker-compose exec web python manage.py createsuperuser
```

El servidor queda disponible en `http://127.0.0.1:8000`.

---

## Variables de entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django | Cambiar en producción |
| `DEBUG` | Modo debug | `True` |
| `ALLOWED_HOSTS` | Hosts permitidos | `localhost,127.0.0.1` |
| `DATABASE_URL` | URL de conexión a la base de datos | SQLite si está vacío |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | Duración del access token | `60` |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Duración del refresh token | `7` |
| `TWILIO_ACCOUNT_SID` | Account SID de Twilio | — |
| `TWILIO_AUTH_TOKEN` | Auth Token de Twilio | — |
| `TWILIO_PHONE_NUMBER` | Número de teléfono Twilio (SMS) | — |
| `TWILIO_WHATSAPP_NUMBER` | Número WhatsApp Twilio | — |
| `EXTERNAL_API_BASE_URL` | URL de la API CRM externa | — |
| `EXTERNAL_API_KEY` | API key del CRM externo | — |

---

## Migraciones y base de datos

```bash
# Aplicar migraciones pendientes
python manage.py migrate

# Crear nuevas migraciones después de cambiar un modelo
python manage.py makemigrations

# Ver migraciones pendientes
python manage.py showmigrations
```

---

## Correr el servidor

```bash
# Desarrollo
python manage.py runserver

# Desarrollo en puerto específico
python manage.py runserver 0.0.0.0:8000
```

---

## Correr los tests

```bash
# Correr todos los tests
python manage.py test

# Correr tests de una app específica
python manage.py test apps.analytics
python manage.py test apps.users
python manage.py test apps.core_business

# Correr con detalle de cada test
python manage.py test apps.analytics --verbosity=2

# Correr una capa específica de tests
python manage.py test apps.analytics.tests.test_models
python manage.py test apps.analytics.tests.test_serializers
python manage.py test apps.analytics.tests.test_views
```

---

## Frontend

El frontend es HTML/CSS/JS vanilla ubicado en la carpeta `frontend/`.
No requiere instalación ni build. Las páginas disponibles son:

| Archivo | Descripción |
|---|---|
| `login.html` | Pantalla de inicio de sesión |
| `dashboard.html` | Panel principal con métricas |
| `index.html` | Página de inicio |
| `usuarios.html` | Gestión de usuarios |
| `bitacora.html` | Bitácora de login |
| `acceso-denegado.html` | Página de error 403 |

Para usarlo basta con abrir los archivos directamente en el navegador
o servirlos con cualquier servidor estático mientras el backend corre.

---

## Documentación de la API

Con el servidor corriendo, la documentación interactiva está disponible en:

| URL | Descripción |
|---|---|
| `http://127.0.0.1:8000/api/docs/` | Swagger UI — probar endpoints |
| `http://127.0.0.1:8000/api/redoc/` | ReDoc — documentación legible |
| `http://127.0.0.1:8000/api/schema/` | Esquema OpenAPI en JSON |
| `http://127.0.0.1:8000/admin/` | Panel de administración de Django |

### Autenticación en Swagger

1. Ir a `POST /api/v1/auth/token/`
2. Enviar `username` y `password`
3. Copiar el valor del campo `access`
4. Hacer clic en el botón **Authorize** (arriba a la derecha)
5. Escribir `Bearer <token copiado>` y confirmar

---

## Antes de hacer un commit

Estos pasos son **obligatorios** antes de cualquier commit. El pre-commit
los ejecuta automáticamente, pero es buena práctica correrlos manualmente primero:

```bash
# 1. Formatear todo el código con black
black .

# 2. Correr los tests de la app que modificaste
python manage.py test apps.<nombre_app> --verbosity=2

# 3. Verificar que no haya archivos sin agregar
git status
```

Si algún test falla, **no hacer commit** hasta resolverlo.

---

## Flujo de trabajo Git

El proyecto usa el siguiente flujo. **Nunca hacer push directo a `dev` o `main`.**

### Tipos de commit permitidos

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
feat(analytics): implementar RF11 - registro de recargas

- Validaciones de negocio en TopUpSerializer
- IsAuthenticated en TopUpListCreateView
- Tests organizados en carpeta tests/ por capas
```

### Flujo completo

```bash
# 1. Crear rama desde dev
git checkout dev
git pull origin dev
git checkout -b feature/nombre-descriptivo

# 2. Trabajar en la rama, hacer commits
black .
git add <archivos>
git commit -m "feat(scope): descripción"

# 3. Sincronizar con dev antes de subir
git fetch origin
git merge origin/dev

# 4. Subir la rama
git push origin feature/nombre-descriptivo

# 5. Abrir Pull Request en GitHub: feature/... → dev
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

