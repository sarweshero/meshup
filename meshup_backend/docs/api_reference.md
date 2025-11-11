# Meshup API Reference (v1)

This document describes every publicly exposed REST endpoint under `https://<host>/api/v1/`. All endpoints return JSON and require HTTPS in production deployments.

---

## Conventions

- **Authentication**: Unless noted, endpoints require a valid JWT access token issued by `/auth/login/`. Supply it via `Authorization: Bearer <token>`.
- **Content Type**: Send request bodies as `application/json` unless a file upload is explicitly required.
- **Pagination**: List endpoints follow Django REST Framework pagination when `page` and `page_size` query parameters are provided. When pagination is active, responses return a `count`, `next`, `previous`, and `results` payload.
- **Timestamps**: All datetimes use ISO 8601 with timezone offsets (UTC by default).
- **Errors**: Validation failures return `400` with a JSON object of field errors. Permission issues return `403`, missing resources return `404`, and unauthenticated requests return `401`.

---

## Authentication

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register/` | Create a new user account. |
| POST | `/auth/login/` | Exchange credentials for JWT access/refresh tokens. |
| POST | `/auth/logout/` | Blacklist a refresh token. |
| POST | `/auth/token/refresh/` | Refresh an access token. |
| POST | `/auth/password-reset/` | Initiate password reset flow. |
| POST | `/auth/password-reset-confirm/` | Complete password reset with token. |

### `POST /auth/register/`
- **Auth**: None
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "username": "meshup_user",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
  }
  ```
- **Response** `201`:
  ```json
  {
    "message": "User registered successfully",
    "user": {
      "id": "<uuid>",
      "email": "user@example.com",
      "username": "meshup_user"
    },
    "tokens": {
      "refresh": "<token>",
      "access": "<token>"
    }
  }
  ```

### `POST /auth/login/`
- **Auth**: None
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePass123!"
  }
  ```
- **Response** `200`:
  ```json
  {
    "refresh": "<token>",
    "access": "<token>",
    "user": {
      "id": "<uuid>",
      "email": "user@example.com",
      "username": "meshup_user",
      "discriminator": "0001",
      "avatar": null,
      "status": "online"
    }
  }
  ```

### `POST /auth/logout/`
- **Auth**: Required
- **Body**:
  ```json
  {
    "refresh": "<token>"
  }
  ```
- **Response** `200`: `{ "message": "Successfully logged out" }`

### `POST /auth/token/refresh/`
- **Auth**: None
- **Body**: `{ "refresh": "<token>" }`
- **Response** `200`: `{ "access": "<token>" }`

### `POST /auth/password-reset/`
- **Auth**: None
- **Body**: `{ "email": "user@example.com" }`
- **Response** `200`: `{ "message": "Password reset email sent" }`

### `POST /auth/password-reset-confirm/`
- **Auth**: None
- **Body**:
  ```json
  {
    "token": "<reset-token>",
    "password": "NewSecurePass123!",
    "password_confirm": "NewSecurePass123!"
  }
  ```
- **Response** `200`: `{ "message": "Password has been reset successfully" }`

---

## Users

| Method | Path | Description |
| --- | --- | --- |
| GET | `/users/` | List users (non-admins receive only themselves). |
| GET | `/users/{user_id}/` | Retrieve a user (self or admin). |
| PATCH | `/users/{user_id}/` | Update a user (self or admin). |
| GET | `/users/me/` | Get the authenticated profile. |
| PATCH | `/users/me/` | Update the authenticated profile. |

**Model Highlights**
- Status choices: `online`, `away`, `dnd`, `offline`.
- Immutable fields via API: `email`, `username`, `discriminator`, `is_verified`.

### Query Parameters
- `search`: match username or email.
- Ordering: `?ordering=username` or `?ordering=-date_joined`.

### User Representation (`UserDetailSerializer`)
```json
{
  "id": "<uuid>",
  "email": "user@example.com",
  "username": "meshup_user",
  "discriminator": "1234",
  "avatar": "https://...",
  "bio": "About me",
  "status": "online",
  "custom_status": "Heads down",
  "is_verified": false,
  "date_joined": "2025-10-01T12:00:00Z",
  "last_login": "2025-11-07T08:45:00Z"
}
```

Partial updates accept any mutable field (e.g., `bio`, `status`, `custom_status`).

---

## Servers

| Method | Path | Description |
| --- | --- | --- |
| GET | `/servers/` | List servers visible to the user (public, owned, or member). |
| POST | `/servers/` | Create a new server. |
| GET | `/servers/{server_id}/` | Retrieve server details. |
| PUT/PATCH | `/servers/{server_id}/` | Update server metadata (owner/admin only). |
| DELETE | `/servers/{server_id}/` | Delete server (owner/admin). |
| POST | `/servers/{server_id}/join/` | Join a public server. |
| POST | `/servers/{server_id}/leave/` | Leave a server (non-owners). |
| GET | `/servers/{server_id}/roles/` | View roles (owner/admin or non-banned member). |
| POST | `/servers/{server_id}/members/{member_id}/roles/` | Assign roles to a member (MANAGE_ROLES permission required). |
| GET | `/servers/{server_id}/invites/` | List invites (MANAGE_MEMBERS). |
| POST | `/servers/{server_id}/invites/` | Create an invite (body below). |
| DELETE | `/servers/{server_id}/invites/{code}/` | Revoke an invite by code. |
| POST | `/servers/invites/accept/` | Redeem an invite code to join. |

### Server Schema (`ServerSerializer`)
```json
{
  "id": "<uuid>",
  "name": "Project Alpha",
  "description": "Planning workspace",
  "icon": "https://...",
  "banner": null,
  "region": "us-east",
  "is_public": true,
  "verification_level": 0,
  "owner": { "id": "<uuid>", "username": "owner", "discriminator": "0001", "status": "online", "avatar": null },
  "created_at": "2025-10-01T12:00:00Z",
  "updated_at": "2025-11-01T09:30:00Z",
  "member_count": 12
}
```

**Creation Fields**: `name` (required), `description`, `region` (`us-east`, `us-west`, `eu-central`, `asia-pacific`), `is_public`, `verification_level`, `icon`, `banner`.

Joining automatically assigns the default member role. Owners cannot leave their own server.

### Create Invite (`POST /servers/{server_id}/invites/`)
- **Body**:
  ```json
  {
    "label": "Design Sprint",
    "invitee_email": "guest@example.com",
    "max_uses": 5,
    "expires_at": "2025-11-15T23:59:00Z"
  }
  ```
- **Response** `201`:
  ```json
  {
    "id": "<uuid>",
    "code": "ABCD1234EF",
    "label": "Design Sprint",
    "invitee_email": "guest@example.com",
    "max_uses": 5,
    "uses": 0,
    "expires_at": "2025-11-15T23:59:00Z",
    "revoked_at": null,
    "created_at": "2025-11-07T14:00:00Z",
    "is_active": true,
    "server": { ... },
    "inviter": { ... }
  }
  ```

### Accept Invite (`POST /servers/invites/accept/`)
- **Body**: `{ "code": "ABCD1234EF" }`
- **Response** `200`:
  ```json
  {
    "message": "Joined server successfully",
    "server": { ... },
    "invite": { ... updated usage ... }
  }
  ```


---

## Channels

| Method | Path | Description |
| --- | --- | --- |
| GET | `/channels/{server_id}/` | List channels in a server (member access required). |
| POST | `/channels/{server_id}/` | Create a channel (MANAGE_CHANNELS). |
| GET | `/channels/{server_id}/{channel_id}/` | Retrieve a channel. |
| PUT/PATCH | `/channels/{server_id}/{channel_id}/` | Update channel (MANAGE_CHANNELS). |
| DELETE | `/channels/{server_id}/{channel_id}/` | Delete channel. |

### Channel Schema
```json
{
  "id": "<uuid>",
  "server": "<server_uuid>",
  "name": "general",
  "description": "Team chat",
  "channel_type": "text",           // text, voice, announcement, stage
  "position": 1,
  "is_private": false,
  "is_nsfw": false,
  "slowmode_delay": 0,
  "parent_category": null,
  "created_by": "<user_uuid>",
  "created_at": "2025-10-02T14:00:00Z",
  "updated_at": "2025-10-15T09:10:00Z"
}
```

---

## Messages

### Channel Messages

| Method | Path | Description |
| --- | --- | --- |
| GET | `/messages/channels/{channel_id}/` | List channel messages (filters: `author`, `is_pinned`, `thread_id`). |
| POST | `/messages/channels/{channel_id}/` | Create a message in the channel. |
| GET | `/messages/channels/{channel_id}/{message_id}/` | Retrieve single message. |
| PUT/PATCH | `/messages/channels/{channel_id}/{message_id}/` | Update own message (sets `is_edited`). |
| DELETE | `/messages/channels/{channel_id}/{message_id}/` | Soft-delete own message. |
| POST | `/messages/channels/{channel_id}/{message_id}/react/` | Add a reaction (`emoji`). |
| DELETE | `/messages/channels/{channel_id}/{message_id}/unreact/?emoji=...` | Remove own reaction. |
| POST | `/messages/channels/{channel_id}/{message_id}/pin/` | Pin message (MANAGE_CHANNELS). |
| DELETE | `/messages/channels/{channel_id}/{message_id}/unpin/` | Unpin message. |

**Create Body**
```json
{
  "content": "Standup in 10 minutes",
  "reply_to": "<message_uuid>",
  "thread_id": "<thread_uuid>",
  "attachments": ["<binary file upload field>"]
}
```

**Message Response** (`MessageSerializer`)
```json
{
  "id": "<uuid>",
  "channel": "<channel_uuid>",
  "author": { "id": "<uuid>", "username": "alice", "discriminator": "0001", "status": "online", "avatar": null },
  "content": "Standup in 10 minutes",
  "message_type": "default",
  "reply_to": {
    "id": "<uuid>",
    "author": { ... },
    "content": "Yesterday's summary...",
    "created_at": "2025-11-07T08:00:00Z"
  },
  "thread_id": null,
  "is_pinned": false,
  "is_edited": true,
  "attachments": [],
  "reactions": [{ "id": "<uuid>", "emoji": ":thumbsup:", "user": { ... }, "created_at": "2025-11-07T08:05:00Z" }],
  "created_at": "2025-11-07T08:04:00Z",
  "edited_at": "2025-11-07T08:06:00Z"
}
```

Deleted messages return `204` with no body.

### Direct Messages

| Method | Path | Description |
| --- | --- | --- |
| GET | `/messages/dm/` | List DM channels for the user. |
| POST | `/messages/dm/` | Create or reuse a DM channel. |
| GET | `/messages/dm/{dm_id}/` | Retrieve DM channel metadata. |
| DELETE | `/messages/dm/{dm_id}/` | Leave/delete DM channel. |
| GET | `/messages/dm/{dm_id}/messages/` | List DM messages (newest first). |
| POST | `/messages/dm/{dm_id}/messages/` | Send a DM message. |

**Create DM Channel Body**
```json
{
  "participant_ids": ["<other_user_uuid>"]
}
```
The creator is automatically added. If a channel with the exact participant set already exists, it is returned.

**DM Message Body**: `{ "content": "Hey there" }`

---

## Realtime WebSockets

Meshup exposes websocket channels for both server channels and private direct messages. In both cases you must provide a JWT access token via query string `?token=<access>` or header `Authorization: Bearer <access>`, and payloads are JSON objects with an `event` key plus an optional `payload` dictionary.

### Channel Streams

- **Endpoint**: `wss://flowdrix.tech/ws/v1/realtime/servers/{server_id}/channels/{channel_id}/`

#### Client → Server Events

| Event | Description | Payload |
| --- | --- | --- |
| `message.send` | Persist a channel message and broadcast it in real time. | `{ "content": "Hello team!", "reply_to": "<optional message uuid>" }` |
| `typing.start` | Notify other members you started typing. | `{}` |
| `typing.stop` | Notify other members you stopped typing. | `{}` |
| `presence.ping` | Heartbeat to confirm the connection is alive. | `{}` |

#### Server → Client Events

| Event | Trigger |
| --- | --- |
| `message.created` | Emitted when a message is saved via REST or websocket, includes serialized `Message` payload. |
| `message.ack` | Immediate acknowledgement containing the saved message after `message.send`. |
| `typing.start` / `typing.stop` | Broadcast from other users typing updates. |
| `presence.join` / `presence.leave` | User connected or disconnected from the channel socket. |
| `presence.alive` | Response to `presence.ping`, indicates the server connection remains active. |

> **Tip:** REST-created messages also trigger the websocket `message.created` event, keeping HTTP and websocket clients synchronized.

### Direct Message Streams

- **Endpoint**: `wss://flowdrix.tech/ws/v1/realtime/direct-messages/{dm_id}/`

#### Client → Server Events

| Event | Description | Payload |
| --- | --- | --- |
| `message.send` | Persist a direct message and push it to engaged participants. | `{ "content": "Hey there" }` |
| `typing.start` | Notify the other participant(s) that you started typing. | `{}` |
| `typing.stop` | Notify the other participant(s) that you stopped typing. | `{}` |
| `presence.ping` | Heartbeat to confirm the connection is alive. | `{}` |

#### Server → Client Events

| Event | Trigger |
| --- | --- |
| `message.created` | Emitted when a DM is saved via REST or websocket, includes serialized `DirectMessageMessage` payload. |
| `message.ack` | Immediate acknowledgement containing the saved DM after `message.send`. |
| `typing.start` / `typing.stop` | Broadcast from other users typing in the DM. |
| `presence.join` / `presence.leave` | Participant connected or disconnected from the DM socket. |
| `presence.alive` | Response to `presence.ping`, indicates the DM connection remains active. |

---

## Notes

| Method | Path | Description |
| --- | --- | --- |
| GET | `/notes/{server_id}/` | List notes for a server (filters: `is_pinned`, `is_locked`, `created_by`). |
| POST | `/notes/{server_id}/` | Create a note. |
| GET | `/notes/{server_id}/{note_id}/` | Retrieve note. |
| PUT/PATCH | `/notes/{server_id}/{note_id}/` | Update note (creates version history). |
| DELETE | `/notes/{server_id}/{note_id}/` | Soft-delete note. |
| GET | `/notes/{server_id}/{note_id}/versions/` | List version history. |
| POST | `/notes/{server_id}/{note_id}/restore/` | Restore to a specific version (`version_number`). |
| POST | `/notes/{server_id}/{note_id}/pin/` | Toggle pinned state. |
| POST | `/notes/{server_id}/{note_id}/lock/` | Toggle locked state. |

**Note Schema**
```json
{
  "id": "<uuid>",
  "title": "Sprint Retro",
  "content": "Action items...",
  "server": "<server_uuid>",
  "created_by": { ... },
  "last_edited_by": { ... },
  "version": 6,
  "version_count": 6,
  "is_pinned": true,
  "is_locked": false,
  "tags": ["retro", "sprint-42"],
  "collaborators": [{ "id": "<uuid>", "user": { ... }, "permission": "edit", "added_at": "2025-11-01T12:00:00Z" }],
  "created_at": "2025-10-15T09:00:00Z",
  "updated_at": "2025-11-07T10:00:00Z"
}
```

Restore requests require `{"version_number": <int>}` and generate new version entries to preserve history.

---

## Tasks

| Method | Path | Description |
| --- | --- | --- |
| GET | `/tasks/{server_id}/` | List tasks (supports filters: `status`, `priority`, `assigned_to`, `channel`, `assigned_to_me=true`). |
| POST | `/tasks/{server_id}/` | Create a task. |
| GET | `/tasks/{server_id}/{task_id}/` | Retrieve task. |
| PUT/PATCH | `/tasks/{server_id}/{task_id}/` | Update task. |
| DELETE | `/tasks/{server_id}/{task_id}/` | Soft-delete task. |
| GET/POST | `/tasks/{server_id}/{task_id}/comments/` | List or create comments. |
| POST | `/tasks/{server_id}/{task_id}/attachments/` | Upload a file attachment (`multipart/form-data`). |
| POST | `/tasks/{server_id}/{task_id}/assign/` | Assign to a member (`{"user_id": "<uuid>"}`). |
| POST | `/tasks/{server_id}/{task_id}/complete/` | Mark task complete.

### Task Schema (`TaskSerializer`)
```json
{
  "id": "<uuid>",
  "title": "Design review",
  "description": "Finalize mockups",
  "assigned_to": { ... },
  "assigned_by": { ... },
  "server": "<server_uuid>",
  "channel": "<channel_uuid>",
  "status": "in_progress",      // pending, in_progress, completed, overdue, cancelled
  "priority": "high",           // low, medium, high, urgent
  "progress": 70,
  "due_date": "2025-11-10T17:00:00Z",
  "start_date": "2025-11-03T09:00:00Z",
  "completed_at": null,
  "tags": ["design", "ux"],
  "attachments": ["https://cdn/..."],
  "comments_count": 4,
  "attachments_count": 2,
  "is_overdue": false,
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-07T12:00:00Z"
}
```

**Create/Update Fields**
- `title` (required), `description`
- `assigned_to_id` (optional UUID)
- `channel` (optional channel UUID)
- `status`, `priority`, `progress` (0-100), `due_date`, `start_date`, `tags`

Comments accept `{ "content": "Please review" }`. Nested replies use `reply_to` in the body.

Attachments require `file` form field and return metadata with uploader info.

---

## Events

| Method | Path | Description |
| --- | --- | --- |
| GET | `/events/{server_id}/` | List events (filters: `event_type`, `status`, `created_by`, date range via `start_date`, `end_date`). |
| POST | `/events/{server_id}/` | Create event. |
| GET | `/events/{server_id}/{event_id}/` | Retrieve event. |
| PUT/PATCH | `/events/{server_id}/{event_id}/` | Update event. |
| DELETE | `/events/{server_id}/{event_id}/` | Soft-delete event. |
| POST | `/events/{server_id}/{event_id}/rsvp/` | RSVP (`rsvp_status`, optional `notes`). |
| GET | `/events/{server_id}/calendar/?month=11&year=2025` | Monthly calendar view. |
| GET | `/events/{server_id}/upcoming/` | Events in next 7 days. |

### Event Schema
```json
{
  "id": "<uuid>",
  "title": "Sprint Demo",
  "description": "Showcase new work",
  "server": "<server_uuid>",
  "channel": "<channel_uuid>",
  "created_by": { ... },
  "event_type": "meeting",          // meeting, deadline, announcement, milestone, reminder, other
  "status": "scheduled",            // scheduled, ongoing, completed, cancelled, postponed
  "start_time": "2025-11-09T15:00:00Z",
  "end_time": "2025-11-09T16:00:00Z",
  "all_day": false,
  "location": "Conference Room A",
  "meeting_link": "https://meet.example.com/demo",
  "recurrence_type": "weekly",     // none, daily, weekly, monthly, yearly, custom
  "recurrence_end_date": "2025-12-20T16:00:00Z",
  "recurrence_interval": 1,
  "attendees_data": [
    {
      "id": "<uuid>",
      "user": { ... },
      "rsvp_status": "attending",   // pending, attending, not_attending, maybe, tentative
      "is_organizer": true,
      "is_required": false,
      "notes": "Will dial in",
      "responded_at": "2025-11-07T12:30:00Z",
      "invited_at": "2025-11-01T09:00:00Z"
    }
  ],
  "attendee_count": 5,
  "attending_count": 4,
  "reminder_minutes_before": [15, 60],
  "tags": ["sprint", "demo"],
  "color": "#3498db",
  "created_at": "2025-10-20T08:00:00Z",
  "updated_at": "2025-11-07T13:00:00Z"
}
```

Create/update bodies accept `attendee_ids` (list of user UUIDs). Non-members are ignored. The creator is auto-added as organizer.

RSVP request body example:
```json
{
  "rsvp_status": "attending",
  "notes": "Flying in"
}
```

Calendar responses:
```json
{
  "month": 11,
  "year": 2025,
  "events": [ ... EventSerializer objects ... ]
}
```

---

## Polls

| Method | Path | Description |
| --- | --- | --- |
| GET | `/polls/{server_id}/` | List polls (filters: `status`, `created_by`, `channel`). |
| POST | `/polls/{server_id}/` | Create poll. |
| GET | `/polls/{server_id}/{poll_id}/` | Retrieve poll with options. |
| PUT/PATCH | `/polls/{server_id}/{poll_id}/` | Update poll. |
| DELETE | `/polls/{server_id}/{poll_id}/` | Soft-delete poll. |
| POST | `/polls/{server_id}/{poll_id}/vote/` | Submit votes (`option_ids`). |
| DELETE | `/polls/{server_id}/{poll_id}/unvote/` | Remove user votes. |
| GET | `/polls/{server_id}/{poll_id}/results/` | View results (may require voting first). |
| POST | `/polls/{server_id}/{poll_id}/close/` | Close poll (creator, owner, or admin). |
| GET/POST | `/polls/{server_id}/{poll_id}/comments/` | List/Create poll comments. |

### Create Body
```json
{
  "question": "Where should we host the offsite?",
  "description": "Vote for preferred location",
  "channel": "<channel_uuid>",
  "allow_multiple_votes": false,
  "allow_add_options": false,
  "anonymous_votes": false,
  "show_results_before_vote": true,
  "expires_at": "2025-11-15T23:59:00Z",
  "options": ["Lake cabin", "City hotel", "Beach resort"]
}
```

**Poll Schema** (`PollSerializer`)
```json
{
  "id": "<uuid>",
  "question": "Where should we host the offsite?",
  "description": "Vote for preferred location",
  "server": "<server_uuid>",
  "channel": "<channel_uuid>",
  "created_by": { ... },
  "status": "active",          // draft, active, closed
  "allow_multiple_votes": false,
  "allow_add_options": false,
  "anonymous_votes": false,
  "show_results_before_vote": true,
  "expires_at": "2025-11-15T23:59:00Z",
  "total_votes": 12,
  "options": [
    {
      "id": "<uuid>",
      "option_text": "Lake cabin",
      "position": 0,
      "vote_count": 5,
      "percentage": 41.67,
      "has_voted": true,
      "added_by": { ... },
      "created_at": "2025-11-05T10:00:00Z"
    }
  ],
  "user_votes": ["<option_uuid>"]
}
```

`/results/` adds `percentage` and optionally `voters` if `anonymous_votes` is false.

Comments use `{ "content": "Great option" }`.

---

## Events & Polls Permissions Reminder
- Users must belong to the server (and not be banned) to interact.
- Poll votes enforce `allow_multiple_votes` and status/expiry automatically.
- Event RSVP statuses: `pending`, `attending`, `not_attending`, `maybe`, `tentative`.

---

## Settings

| Method | Path | Description |
| --- | --- | --- |
| GET | `/settings/user/` | Retrieve authenticated user settings. |
| PUT/PATCH | `/settings/user/` | Update user settings. |
| GET | `/settings/servers/{server_id}/` | Retrieve server settings (member + permission). |
| PUT/PATCH | `/settings/servers/{server_id}/` | Update server settings (owner/admin). |
| GET | `/settings/notifications/` | List notification preferences for user. |
| POST | `/settings/notifications/` | Create preference (`server`, `notification_level`, optional mute fields). |
| GET | `/settings/notifications/{id}/` | Retrieve a preference. |
| PUT/PATCH | `/settings/notifications/{id}/` | Update preference. |
| DELETE | `/settings/notifications/{id}/` | Delete preference. |

### User Settings Schema
```json
{
  "id": "<uuid>",
  "theme": "dark",                  // light, dark, auto
  "language": "en",                 // en, es, fr, de, ja
  "compact_mode": true,
  "email_notifications": true,
  "push_notifications": true,
  "desktop_notifications": true,
  "notification_sound": true,
  "notify_messages": true,
  "notify_mentions": true,
  "notify_tasks": true,
  "notify_events": true,
  "notify_polls": true,
  "show_online_status": true,
  "allow_direct_messages": true,
  "show_email": false,
  "reduced_motion": false,
  "high_contrast": false,
  "updated_at": "2025-11-07T12:30:00Z"
}
```

### Server Settings Schema
```json
{
  "id": "<uuid>",
  "default_notifications": true,
  "explicit_content_filter": true,
  "verification_level": 2,          // 0-4
  "require_2fa_for_admin": false,
  "auto_moderation": true,
  "banned_words": ["spoiler"],
  "enable_tasks": true,
  "enable_notes": true,
  "enable_events": true,
  "enable_polls": true,
  "max_members": 250,
  "max_channels": 75,
  "updated_at": "2025-11-07T11:00:00Z"
}
```

### Notification Preference Schema
```json
{
  "id": "<uuid>",
  "server": "<server_uuid>",
  "notification_level": "mentions",   // all, mentions, nothing
  "mute_server": false,
  "mute_until": null,
  "updated_at": "2025-11-07T11:05:00Z"
}
```

Creating or updating preferences automatically binds them to the authenticated user.

---

## Direct Message Lifecycle Summary
1. Optionally `POST /auth/register/` to create a second user.
2. `POST /messages/dm/` with participant IDs to start a DM.
3. `POST /messages/dm/{dm_id}/messages/` to send messages.
4. `GET /messages/dm/{dm_id}/messages/` to fetch conversation history.
5. `DELETE /messages/dm/{dm_id}/` to close the DM channel.

---

## Notes on Soft Deletes
- Messages, notes, tasks, events, and polls perform soft deletes (`is_deleted=true`). Clients should treat a `204` response as success, but future list responses omit removed items.

## Rate Limiting & Throttling
- Default DRF throttling is not enabled in this codebase. If deployed behind an API gateway, apply rate limits per token.

## Swagger / OpenAPI
Interactive docs are available at `/swagger/` and `/redoc/` when the server is running.

---

For any endpoint not documented here (e.g., admin-only endpoints), refer to the Django admin site or extend the ViewSets as needed.
