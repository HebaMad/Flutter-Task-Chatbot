# Flutter Task Chatbot

## Overview
Flutter Task Chatbot is an MVP plan for a task manager that combines a Flutter UI with a backend proxy that calls Gemini (via LangChain) and executes tool-based CRUD actions. The agent must return **structured JSON only** according to the schema below so the backend can deterministically execute task operations.

## Deliverables
### A) Flutter App
**Screens**
- **Tasks**
  - Tabs: Today / All / Done
  - Task list with search + filters (priority/status)
  - Add task button
- **Task Details**
  - Edit title/description/due date/priority
  - Delete
  - Mark as done / undo
- **Chat**
  - Conversation thread + quick suggestion chips
  - Confirmation message after each action (“تم تنفيذ”)

### B) Backend Proxy (protects API key)
- `POST /chat`
- Optional: `GET /health`
- Responsibilities
  - Call Gemini Developer API (via LangChain)
  - Execute tool actions (CRUD) through LangChain tools
  - Read/write tasks (Firestore or local DB)

### C) Agent Spec (Gemini + Tools)
- System/developer prompt rules
- Tool-calling JSON schema
- Disambiguation logic

## Proposed Stack (Google + Gemini Free)
- **LLM/Agent**: Gemini Developer API (Gemini Flash recommended for MVP) orchestrated by LangChain
- **Backend**
  - Option 1: Firebase Cloud Functions + Firestore
  - Option 2: FastAPI or Node proxy (local or hosted)
- **Agent Orchestration**: LangChain (tool calling + routing)
- **Database**
  - Cloud: Firestore
  - Local-first: Hive or SQLite
- **Flutter State**: Riverpod or Bloc
- **Auth (optional)**: Firebase Auth

## MVP Scope
**CRUD**
- Create task
- Update task (partial)
- Delete task
- List tasks (filters: date range / today / status)
- Mark done / undo

**Chat Intents**
- `create_task`
- `update_task`
- `delete_task`
- `list_tasks`
- `complete_task`
- `clarify` (for ambiguity)

## Data Model (Firestore)
Collection: `users/{userId}/tasks/{taskId}`

Task document fields:
- `title`: string (required)
- `description`: string (optional)
- `dueAt`: timestamp | null
- `priority`: "low" | "medium" | "high" (default: "medium")
- `status`: "todo" | "done" (default: "todo")
- `createdAt`: timestamp
- `updatedAt`: timestamp
- `source`: "ui" | "chat" (optional)

Optional indexes:
- `dueAt + status`
- `status + updatedAt`

## API Contract
### `POST /chat`
Request:
```json
{
  "userId": "u123",
  "message": "ضيف مهمة اسمها اشتري حليب بكرة 6",
  "timezone": "Africa/Cairo"
}
```

Response:
```json
{
  "reply": "تمام، أضفت مهمة (اشتري حليب) لبكرة الساعة 6 مساءً.",
  "actions": [
    {
      "type": "create_task",
      "task": {
        "id": "t_abc",
        "title": "اشتري حليب",
        "dueAt": "2026-01-14T18:00:00+02:00",
        "priority": "medium",
        "status": "todo"
      }
    }
  ],
  "needsClarification": false
}
```

Errors:
- `400`: invalid payload
- `401/403`: unauthorized (if auth enabled)
- `429`: rate limit
- `500`: internal

## Agent Tool Calling Schema
Gemini must output **JSON only** with this format:
```json
{
  "intent": "create_task",
  "confidence": 0.86,
  "entities": {
    "title": "اشتري حليب",
    "due": {
      "date": "tomorrow",
      "time": "18:00"
    },
    "priority": "medium"
  },
  "clarification": null
}
```

### Intents + Entities
**create_task**
- `title` (required)
- `due` (optional)
- `priority` (optional)
- `description` (optional)

**update_task**
- `taskRef`: `{ id?, title? }`
- `patch`: `{ title?, due?, priority?, description?, status? }`

**delete_task**
- `taskRef`: `{ id?, title? }`

**list_tasks**
- `filter`: `{ when: today|tomorrow|this_week|range|null, status: todo|done|all, priority?, query? }`

**complete_task**
- `taskRef`

**clarify**
- `question`: string
- `candidates`: array of tasks (ids + titles)

## Disambiguation Rules
For update/delete/complete without ID:
1. Backend searches tasks by fuzzy/contains on title.
2. If 0 results → reply: “مش لاقي مهمة بهذا الاسم… بدك تنشئها؟”
3. If 1 result → execute directly.
4. If >1 results → ask clarification and include 3–5 candidates.

For create without a clear title:
- Ask: “شو عنوان المهمة؟”

## Gemini Prompt (System/Developer)
**System (short):**
- You are a Task Manager Agent.
- Output JSON only following the schema.
- Do not execute actions; only classify intent/entities.
- If ambiguity > 1, use `intent=clarify` with a clear question.
- Understand relative time (tomorrow/next week) using the provided timezone.

**Language support:**
- Arabic dialects: Palestinian, Egyptian, Gulf

**Few-shot examples:**
- “ورجيني مهام اليوم” → `list_tasks` (today + todo)
- “احذف مهمة الاجتماع” → `delete_task` (`taskRef.title`)
- “خلّي الدراسة high” → `update_task` (`priority=high`)
