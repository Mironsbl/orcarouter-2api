# OrcaRouter 2API Gateway

Автономный локальный 2API-шлюз для платформы **OrcaRouter** (`orcarouter.ai`), предоставляющий OpenAI-совместимый доступ к тяжелым флагманским моделям с нулевой стоимостью ($0.00).

## Поддерживаемые бесплатные модели
- 🇨🇳 **`tencent/hy4-preview-free`**: Флагманский MoE-гигант от Tencent Hunyuan на **770B параметров** (49B активных, 78 слоёв, 256 экспертов) с окном **1 000 000 токенов (1M)** и нативной спекулятивной MTP-генерацией.
- ⚡️ **`z-ai/glm-5.3-flash-free`**: Свежий **GLM 5.3 Flash** от Z.ai (320B параметров, 1M контекст, нативная мультимодальность).
- 💎 **`deepseek/deepseek-v4.1-flash-free`**: **DeepSeek V4.1 Flash** (1M контекст, вывод до 384k токенов).
- 🔄 **`orcarouter/free`**: Автоматический балансировщик запросов по свободным мощностям.

---

## Быстрый старт

### 1. Установка зависимостей
```bash
pip install fastapi uvicorn httpx pydantic
```

### 2. Привязка ключа (1 клик)
Запустите скрипт авторизации:
```bash
py -3.12 auth_device.py
```
Скрипт откроет браузер, подтвердит привязку через PKCE Loopback и сохранит ключ в `keys_pool.json`.

### 3. Запуск шлюза
```bash
# Windows
start.bat

# Linux / macOS
python server.py
```
Шлюз поднимется на: `http://127.0.0.1:8095/v1`

---

## Настройка в IDE и агентах

### OpenCode
- **Provider ID**: `orcarouter`
- **Name**: `Tencent Hy4 770B (OrcaRouter)`
- **Base URL**: `http://127.0.0.1:8095/v1`
- **API Key**: `dummy`
- **Model ID**: `tencent/hy4-preview-free`

### Cursor / VS Code / Claude Code
- **Base URL**: `http://127.0.0.1:8095/v1`
- **Model**: `tencent/hy4-preview-free`
