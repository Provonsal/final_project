<div align="center">

# 🗂️ Control System

**REST API для управления командами, заданиями и встречами сотрудников**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Docs](https://img.shields.io/badge/docs-online-success)](https://provonsal.github.io/final_project/)

[📚 Документация](https://provonsal.github.io/final_project/) ·
[📦 Последний релиз](https://github.com/Provonsal/final_project/releases/latest) ·
[💻 Исходный код](https://github.com/Provonsal/final_project)

</div>

---

## 📖 О проекте

**Control System** — это backend-приложение для управления сотрудниками внутри
организации. Сервис позволяет менеджерам создавать команды, приглашать в них
участников по invite-коду, назначать задания и оценивать их выполнение, а также
планировать встречи команды.

Каждый сотрудник имеет одну из трёх ролей — **гость**, **участник** или
**менеджер** — и может одновременно состоять в нескольких командах. Гибкая
система встреч позволяет использовать их как для онлайн-, так и для офлайн-
формата без изменения схемы данных.

Авторизация построена на JWT access-токенах и refresh-токенах с механизмом
**token families** — при подозрении на компрометацию можно отозвать всё
«семейство» токенов пользователя разом.

---

## ✨ Возможности

| | |
|---|---|
| 👥 **Команды** | Менеджер создаёт команду и становится её владельцем |
| 🎟️ **Invite-коды** | Вступление в команду по уникальному коду; участник может быть в нескольких командах |
| ✅ **Задания** | Привязка задач к участникам команды, сроки, статусы |
| ⭐ **Оценки** | Менеджеры выставляют оценки по заданиям (плоская шкала) |
| 📅 **Встречи** | Гибкий формат: `max_members = 0` → офлайн, `> 0` → онлайн с лимитом участников |
| 🔐 **JWT + Refresh** | Access/refresh токены, отзыв по семейству |
| 🛡️ **Ролевой доступ** | Проверки доступа на уровне роутов и сервисов |
| 📚 **Автодокументация** | Swagger UI из FastAPI + Sphinx-документация API |

---

## 🎭 Роли и модель доступа

| Роль | Что может |
|------|-----------|
| 🚪 **Гость** (`GUEST`) | Регистрация, вход, просмотр своего профиля |
| 👤 **Участник** (`MEMBER`) | Просмотр задач и встреч своих команд, комментарии, оценки собственных задач, выход из команды |
| 🛡️ **Менеджер** (`MANAGER`) | Создание команд и встреч, приглашение участников, оценка задач, модерация комментариев, управление составом |

> При вступлении в команду гость автоматически повышается до участника. При
> выходе из последней команды роль снова понижается до гостя.

---

## 🏗️ Архитектура

Приложение разделено на четыре слоя с чётким разделением ответственности:
```
┌─────────────────────────────────────────────────┐
│ Routes (FastAPI routers)                        │
│ • приём HTTP-запроса                            │
│ • получение объектов из БД                      │
│ • проверка базового доступа                     │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│ Services (business logic)                       │
│ • бизнес-правила                                │
│ • сложные проверки прав                         │
│ • оркестрация нескольких репозиториев           │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│ Repositories                                    │
│ • изоляция SQLAlchemy-сессии                    │
│ • CRUD-операции, специфичные для домена         │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│ Dependencies (DI)                               │
│ • фабрика AsyncSession                          │
│ • текущий пользователь из JWT                   │
│ • инъекция сервисов в роуты                     │
└─────────────────────────────────────────────────┘
```

**Ключевые принципы:**
- Сервисы **не знают** про HTTP. Они кидают доменные исключения (`NotFoundError`, `AuthorizationError`, `BusinessRuleError`), которые перехватываются глобальными обработчиками FastAPI.
- Роуты **тонкие**: получают объекты из БД по id, вызывают метод сервиса, возвращают Pydantic-схему.
- Сессия БД создаётся в зависимости и передаётся через DI — сервисы и репозитории не открывают её самостоятельно.

---

## 🧰 Технологический стек

- **Язык:** Python 3.12
- **Веб-фреймворк:** FastAPI, Uvicorn
- **ORM:** SQLAlchemy 2.x (async) + asyncpg
- **Миграции:** Alembic
- **Валидация:** Pydantic v2
- **Аутентификация:** PyJWT, JWT + refresh tokens (token families)
- **Хэширование паролей:** собственный `PWDManager` (salt + SHA-256)
- **Шаблоны:** Jinja2
- **Документация:** Sphinx + Furo (публикуется на GitHub Pages)
- **Контейнеризация:** Docker, Docker Compose
- **CI/CD:** GitHub Actions (release workflow, docs workflow)

---

## 🚀 Быстрый старт (Docker)

Самый быстрый способ — использовать готовый стек из последнего релиза.

**1. Скачайте файлы релиза:**

Перейдите на [страницу последнего релиза](https://github.com/Provonsal/final_project/releases/latest) и скачайте архив с файлами или отдельно:
- `docker-compose.yml`
- `.env.example`

**2. Подготовьте переменные окружения:**

В папке где скачан `docker-compose.yml` и `.env.example`:

```bash
cp .env.example .env
```

Откройте .env и заполните значения:
```dotenv
POSTGRES_USER="your_username"
POSTGRES_PASSWORD="your_password"
POSTGRES_DB="your_database_name"
DATABASE_URL="postgresql+asyncpg://your_username:your_password@localhost:5432/your_database_name"
SECRET_KEY="your-secret-key-change-in-production"
VIEWS_SECRET="dev-secret-change-me"
TEST_DB_URL="postgresql+asyncpg://your_username:your_password@localhost:5432/your_database_name"
API_BASE_URL="http://localhost:8000"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
TOKEN_ALGORITHM="HS256"
ALGORITHM="sha256"  
SALT_SIZE=16        
HASH_SIZE=32        
ITERATIONS=600000  
```

**3. Запустите стек:**
```bash
docker compose up -d
```

**4. Проверьте:**

- API: http://localhost:8000

- Swagger UI: http://localhost:8000/docs

- Healthcheck: http://localhost:8000/health



## 🛠️ Локальная разработка

**Требования**: Docker, Docker Compose.

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/Provonsal/final_project.git
cd final_project

# 2. Подготовьте .env
cp .env.example .env
# отредактируйте .env

# 3. Запустите dev-стек (с hot-reload)
docker compose up --build
```

Dev-стек монтирует app/, utils/ и alembic/ с хоста — изменения в коде
подхватываются Uvicorn'ом автоматически, пересборка не требуется.

## Миграции

```bash
# Сгенерировать новую миграцию по изменениям моделей
docker compose run --rm backend alembic revision --autogenerate -m "описание изменений"

# Применить миграции
docker compose run --rm backend alembic upgrade head
```

Файлы миграций появятся на хосте в alembic/versions/ — их можно коммитить.

## Структура проекта

```
final_project/
├── app/                    # код приложения
│   ├── models/             # SQLAlchemy-модели
│   ├── schemas/            # Pydantic-схемы
│   ├── repositories/       # слой работы с БД
│   ├── services/           # бизнес-логика
│   ├── routers/            # FastAPI-роуты
│   ├── dependencies.py     # DI-зависимости
│   ├── database/           # настройка движка и сессии
│   ├── error_handlers/     # глобальные обработчики исключений
│   └── main.py             # точка входа
├── utils/                  # общие утилиты (PWDManager и др.)
├── alembic/                # миграции
├── alembic.ini
├── docs/                   # Sphinx-документация
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── requirements.txt
```

## 📚 Документация

Полная документация API (Sphinx, сгенерированная из докстрингов):

👉 https://provonsal.github.io/final_project/

## 📦 Релизы и публикация образов

Каждый релиз автоматически собирается GitHub Actions при пуше тега вида v*
и публикуется в GitHub Container Registry:

```bash
docker pull ghcr.io/provonsal/final_project:latest
```

## 📄 Лицензия

Проект распространяется под лицензией MIT — см. файл LICENSE,
если он добавлен в репозиторий.

<div align="center">

[⬆ Наверх](#top)

<sub>Сделано с ❤️ на FastAPI</sub>

</div>