# 💅 BeautyBook Bot

**Полноценная система записи для салона красоты через Telegram Mini App.**

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://t.me/Beautybook1_bot)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repo-black?logo=github)](https://github.com/VladislavBroPiton/BeautyBook)
[![Render Deploy](https://img.shields.io/badge/Deployed%20on-Render-46e3b7?logo=render)](https://render.com)

---


## 🚀 Ключевые возможности

- **📱 Telegram Mini App** – современный интерфейс записи прямо внутри Telegram (HTML/CSS/JS)
- **🤖 Telegram-бот** (aiogram 3.x, асинхронный) – обработка команд, управление записями
- **🔒 Защита от овербукинга** – двойная проверка: на клиенте (автообновление слотов) и на сервере (валидация перед сохранением)
- **📅 Интеграция с Google Calendar** – автоматическое создание событий для каждого визита
- **⏰ Напоминания** – клиенты получают уведомления за день и за час до записи
- **👩‍💼 Панель мастера** – просмотр и отмена записей внутри Mini App (с парольным доступом)
- **📊 Статистика** – администратор получает сводку по записям (общая, по дням, по услугам, по мастерам)
- **🌐 Webhook + Long Polling** – бот готов к продакшн-деплою
- **🗄️ PostgreSQL** (Neon) – надёжное хранение данных
- **🚀 Деплой на Render** – с настройкой вебхуков и переменных окружения

---

## 🛠️ Технологический стек

| Компонент            | Технология                                                          |
|----------------------|---------------------------------------------------------------------|
| Бэкенд               | Python 3.11, aiogram 3.x, aiohttp                                   |
| База данных          | PostgreSQL (asyncpg, Neon)                                           |
| Мини-приложение      | HTML, CSS, JavaScript, Telegram Web App API, Flatpickr               |
| Google Календарь     | Google Calendar API (Service Account)                                |
| Деплой               | Render, Webhook                                                      |
| Контейнеризация      | (планируется Docker)                                                 |

---

