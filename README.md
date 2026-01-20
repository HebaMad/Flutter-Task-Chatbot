# Flutter-Task-Chatbot
Week 1 
# 🧠 AI Tasks Chatbot – Backend MVP

Backend MVP for an AI-powered task management chatbot.
The system interprets user intents and performs task operations through a conversational interface.

---

## ✨ Features

* **Conversational Task Management**

  * Create, list, update, delete, and complete tasks via chat
* **Intent-based Execution**

  * Clean separation between intent interpretation and business logic
* **Disambiguation Support**

  * Handles ambiguous task references by asking follow-up questions
* **Multi-dialect Responses**

  * Supports Palestinian (`pal`) and Egyptian (`egy`) Arabic
  * Architecture ready for additional dialects
* **Fully Tested**

  * Comprehensive pytest coverage (CRUD, disambiguation, edge cases)

---

## 🏗️ Architecture Overview

* **FastAPI** for HTTP API
* **Single entrypoint**: `POST /v1/chat`
* Clear separation of concerns:

  * `routes` – API endpoints
  * `domain` – business logic & intent execution
  * `tasks` – in-memory task store
  * `i18n` – localized responses
  * `tests` – isolated and deterministic tests

---

## 📦 Task Model

Each task contains:

* `id`
* `title`
* `due_text`
* `completed`

Tasks are scoped per `userId`.

---

## 🔁 Supported Intents

* `create_task`
* `list_tasks`
* `update_task`
* `delete_task`
* `complete_task`
* `clarify`
* `not_implemented`

---




## 📌 Status

✅ Backend MVP complete
🧩 Ready for frontend integration or further backend expansion

