#!/usr/bin/env python
"""One-click smoke test for the Meshup REST API."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Sequence

import requests

UTC = timezone.utc


@dataclass
class StepResult:
    """Capture the outcome of a single API request."""

    name: str
    success: bool
    status_code: Optional[int] = None
    detail: str = ""
    url: Optional[str] = None


class APISmokeTester:
    """Exercise all Meshup API surfaces end-to-end."""

    def __init__(self, base_url: str, email: Optional[str] = None, password: Optional[str] = None, *, verbose: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.verbose = verbose
        self.results: list[StepResult] = []

        random_token = uuid.uuid4().hex
        self.email = email or f"smoke_{random_token[:8]}@meshup.test"
        self.password = password or f"Meshup!{random_token[8:16]}"
        self.username = f"smoke_{random_token[16:24]}"

        self.user_id: Optional[str] = None
        self.refresh_token: Optional[str] = None

        # Resources created during the run
        self.server_id: Optional[str] = None
        self.channel_id: Optional[str] = None
        self.extra_channel_id: Optional[str] = None
        self.message_id: Optional[str] = None
        self.note_id: Optional[str] = None
        self.task_id: Optional[str] = None
        self.event_id: Optional[str] = None
        self.poll_id: Optional[str] = None
        self.poll_option_ids: list[str] = []
        self.dm_id: Optional[str] = None
        self.secondary_user_id: Optional[str] = None
        self.notification_preference_id: Optional[str] = None
        self._message_reaction = ":thumbsup:"

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """Run the full smoke test suite."""
        try:
            critical_steps: Sequence[callable[[], bool]] = (
                self.register_user,
                self.login_user,
                self.refresh_access_token,
                self.password_reset_request,
                self.list_users,
                self.fetch_user_profile,
                self.update_user_profile,
                self.retrieve_user_detail,
                self.create_server,
                self.fetch_server_list,
                self.fetch_server_roles,
                self.create_channel,
                self.fetch_channel_list,
                self.fetch_channel_detail,
                self.update_channel,
                self.create_additional_channel,
                self.delete_additional_channel,
                self.create_message,
                self.fetch_message_detail,
                self.fetch_channel_messages,
                self.react_to_message,
                self.pin_and_unpin_message,
                self.update_message,
                self.unreact_message,
                self.delete_message,
                self.confirm_message_deleted,
                self.create_note,
                self.fetch_notes,
                self.pin_note,
                self.update_note,
                self.fetch_note_versions,
                self.restore_note,
                self.lock_note,
                self.delete_note,
                self.create_task,
                self.list_tasks,
                self.update_task,
                self.assign_task,
                self.complete_task,
                self.create_task_comment,
                self.list_task_comments,
                self.delete_task,
                self.create_event,
                self.fetch_event_detail,
                self.update_event,
                self.rsvp_event,
                self.fetch_event_calendar,
                self.fetch_upcoming_events,
                self.delete_event,
                self.create_poll,
                self.fetch_poll_detail,
                self.vote_on_poll,
                self.poll_results,
                self.poll_comment,
                self.list_poll_comments,
                self.unvote_poll,
                self.close_poll,
                self.delete_poll,
                self.fetch_user_settings,
                self.update_user_settings,
                self.fetch_server_settings,
                self.update_server_settings,
                self.create_notification_preference,
                self.list_notification_preferences,
                self.get_notification_preference,
                self.update_notification_preference,
                self.delete_notification_preference,
                self.create_secondary_user,
                self.create_dm_channel,
                self.list_dm_channels,
                self.get_dm_channel,
                self.send_dm_message,
                self.fetch_dm_messages,
                self.delete_dm_channel,
                self.logout_user,
            )

            for step in critical_steps:
                if not step():
                    break
        finally:
            self.print_summary()
        return all(result.success for result in self.results)

    def build_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def request(self, name: str, method: str, path: str, *, expected_status: Iterable[int] = (200,), **kwargs) -> Optional[requests.Response]:
        url = self.build_url(path)
        try:
            response = self.session.request(method.upper(), url, timeout=15, **kwargs)
        except Exception as exc:  # noqa: broad-except
            self._record(name, False, detail=str(exc), url=url)
            if self.verbose:
                print(f"[FAIL] {name}: {exc}")
            return None

        success = response.status_code in expected_status
        detail = self._summarize_response(response, success)
        self._record(name, success, status_code=response.status_code, detail=detail, url=url)
        if self.verbose:
            label = "PASS" if success else "FAIL"
            print(f"[{label}] {name} -> {response.status_code}")
            if self.verbose and detail:
                print(f"    {detail}")
        return response if success else None

    def _summarize_response(self, response: requests.Response, success: bool) -> str:
        snippet = response.text
        if response.headers.get("Content-Type", "").startswith("application/json"):
            try:
                parsed = response.json()
                snippet = json.dumps(parsed, ensure_ascii=False)[:400]
            except Exception:  # noqa: broad-except
                snippet = response.text[:400]
        else:
            snippet = response.text[:400]
        if success:
            return snippet
        return f"status={response.status_code} body={snippet}"

    def _record(self, name: str, success: bool, *, status_code: Optional[int] = None, detail: str = "", url: Optional[str] = None) -> None:
        self.results.append(StepResult(name=name, success=success, status_code=status_code, detail=detail, url=url))

    def _isoformat(self, delta: timedelta) -> str:
        dt = datetime.now(tz=UTC) + delta
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # ------------------------------------------------------------------
    # Authentication steps
    # ------------------------------------------------------------------

    def register_user(self) -> bool:
        payload = {
            "email": self.email,
            "username": self.username,
            "password": self.password,
            "password_confirm": self.password,
        }
        response = self.request(
            "Auth: Register",
            "post",
            "/auth/register/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        data = response.json()
        self.user_id = data["user"]["id"]
        return True

    def login_user(self) -> bool:
        payload = {"email": self.email, "password": self.password}
        response = self.request(
            "Auth: Login",
            "post",
            "/auth/login/",
            json=payload,
            expected_status=(200,),
        )
        if not response:
            return False
        data = response.json()
        self.session.headers["Authorization"] = f"Bearer {data['access']}"
        self.refresh_token = data.get("refresh")
        self.user_id = data.get("user", {}).get("id", self.user_id)
        return True

    def refresh_access_token(self) -> bool:
        if not self.refresh_token:
            self._record("Auth: Refresh", False, detail="Missing refresh token")
            return False
        response = self.request(
            "Auth: Refresh",
            "post",
            "/auth/token/refresh/",
            json={"refresh": self.refresh_token},
            expected_status=(200,),
        )
        if not response:
            return False
        access = response.json().get("access")
        if access:
            self.session.headers["Authorization"] = f"Bearer {access}"
        return True

    def password_reset_request(self) -> bool:
        response = self.request(
            "Auth: Password Reset Request",
            "post",
            "/auth/password-reset/",
            json={"email": self.email},
            expected_status=(200,),
        )
        return bool(response)

    # ------------------------------------------------------------------
    # User profile steps
    # ------------------------------------------------------------------

    def list_users(self) -> bool:
        response = self.request(
            "User: List",
            "get",
            "/users/",
            expected_status=(200,),
        )
        return bool(response)

    def fetch_user_profile(self) -> bool:
        response = self.request(
            "User: Me",
            "get",
            "/users/me/",
            expected_status=(200,),
        )
        return bool(response)

    def update_user_profile(self) -> bool:
        response = self.request(
            "User: Me Patch",
            "patch",
            "/users/me/",
            json={"bio": "Updated by smoke test", "custom_status": "Testing"},
            expected_status=(200,),
        )
        return bool(response)

    def retrieve_user_detail(self) -> bool:
        if not self.user_id:
            self._record("User: Retrieve", False, detail="Missing user ID")
            return False
        response = self.request(
            "User: Retrieve",
            "get",
            f"/users/{self.user_id}/",
            expected_status=(200,),
        )
        return bool(response)

    def logout_user(self) -> bool:
        if not self.refresh_token:
            self._record("Auth: Logout", False, detail="Missing refresh token")
            return False
        response = self.request(
            "Auth: Logout",
            "post",
            "/auth/logout/",
            json={"refresh": self.refresh_token},
            expected_status=(200,),
        )
        return bool(response)

    # ------------------------------------------------------------------
    # Server & channel steps
    # ------------------------------------------------------------------

    def create_server(self) -> bool:
        payload = {
            "name": "Smoke Test Server",
            "description": "Automated smoke test server",
            "region": "us-east",
            "is_public": False,
            "verification_level": 0,
        }
        response = self.request(
            "Server: Create",
            "post",
            "/servers/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        self.server_id = response.json()["id"]
        return True

    def fetch_server_list(self) -> bool:
        return bool(
            self.request(
                "Server: List",
                "get",
                "/servers/",
                expected_status=(200,),
            )
        )

    def fetch_server_roles(self) -> bool:
        if not self.server_id:
            self._record("Server: Roles", False, detail="Missing server ID")
            return False
        return bool(
            self.request(
                "Server: Roles",
                "get",
                f"/servers/{self.server_id}/roles/",
                expected_status=(200,),
            )
        )

    def create_channel(self) -> bool:
        if not self.server_id:
            self._record("Channel: Create", False, detail="Missing server ID")
            return False
        payload = {
            "name": "general-smoke",
            "description": "Channel created by smoke test",
            "channel_type": "text",
        }
        response = self.request(
            "Channel: Create",
            "post",
            f"/channels/{self.server_id}/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        self.channel_id = response.json()["id"]
        return True

    def fetch_channel_list(self) -> bool:
        if not self.server_id:
            self._record("Channel: List", False, detail="Missing server ID")
            return False
        return bool(
            self.request(
                "Channel: List",
                "get",
                f"/channels/{self.server_id}/",
                expected_status=(200,),
            )
        )

    def fetch_channel_detail(self) -> bool:
        if not self.server_id or not self.channel_id:
            self._record("Channel: Detail", False, detail="Missing identifiers")
            return False
        return bool(
            self.request(
                "Channel: Detail",
                "get",
                f"/channels/{self.server_id}/{self.channel_id}/",
                expected_status=(200,),
            )
        )

    def update_channel(self) -> bool:
        if not self.server_id or not self.channel_id:
            self._record("Channel: Update", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Channel: Update",
            "patch",
            f"/channels/{self.server_id}/{self.channel_id}/",
            json={"description": "Updated by smoke test"},
            expected_status=(200,),
        )
        return bool(response)

    def create_additional_channel(self) -> bool:
        if not self.server_id:
            self._record("Channel: Secondary Create", False, detail="Missing server ID")
            return False
        payload = {
            "name": "temp-smoke",
            "description": "Temporary channel for smoke coverage",
            "channel_type": "text",
        }
        response = self.request(
            "Channel: Secondary Create",
            "post",
            f"/channels/{self.server_id}/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        self.extra_channel_id = response.json()["id"]
        return True

    def delete_additional_channel(self) -> bool:
        if not self.server_id or not self.extra_channel_id:
            self._record("Channel: Secondary Delete", False, detail="Missing channel ID")
            return False
        response = self.request(
            "Channel: Secondary Delete",
            "delete",
            f"/channels/{self.server_id}/{self.extra_channel_id}/",
            expected_status=(204,),
        )
        if response:
            self.extra_channel_id = None
            return True
        return False

    # ------------------------------------------------------------------
    # Messaging steps
    # ------------------------------------------------------------------

    def create_message(self) -> bool:
        if not self.channel_id:
            self._record("Message: Create", False, detail="Missing channel ID")
            return False
        payload = {"content": "Smoke test message"}
        response = self.request(
            "Message: Create",
            "post",
            f"/messages/channels/{self.channel_id}/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        self.message_id = response.json()["id"]
        return True

    def fetch_message_detail(self) -> bool:
        if not self.channel_id or not self.message_id:
            self._record("Message: Detail", False, detail="Missing identifiers")
            return False
        return bool(
            self.request(
                "Message: Detail",
                "get",
                f"/messages/channels/{self.channel_id}/{self.message_id}/",
                expected_status=(200,),
            )
        )

    def fetch_channel_messages(self) -> bool:
        if not self.channel_id:
            self._record("Message: List", False, detail="Missing channel ID")
            return False
        return bool(
            self.request(
                "Message: List",
                "get",
                f"/messages/channels/{self.channel_id}/",
                expected_status=(200,),
            )
        )

    def react_to_message(self) -> bool:
        if not self.channel_id or not self.message_id:
            self._record("Message: React", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Message: React",
            "post",
            f"/messages/channels/{self.channel_id}/{self.message_id}/react/",
            json={"emoji": self._message_reaction},
            expected_status=(200, 201),
        )
        return bool(response)

    def pin_and_unpin_message(self) -> bool:
        if not self.channel_id or not self.message_id:
            self._record("Message: Pin", False, detail="Missing identifiers")
            return False
        pin_resp = self.request(
            "Message: Pin",
            "post",
            f"/messages/channels/{self.channel_id}/{self.message_id}/pin/",
            expected_status=(200,),
        )
        unpin_resp = self.request(
            "Message: Unpin",
            "delete",
            f"/messages/channels/{self.channel_id}/{self.message_id}/unpin/",
            expected_status=(200,),
        )
        return bool(pin_resp and unpin_resp)

    def update_message(self) -> bool:
        if not self.channel_id or not self.message_id:
            self._record("Message: Update", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Message: Update",
            "patch",
            f"/messages/channels/{self.channel_id}/{self.message_id}/",
            json={"content": "Smoke test message (edited)"},
            expected_status=(200,),
        )
        return bool(response)

    def unreact_message(self) -> bool:
        if not self.channel_id or not self.message_id:
            self._record("Message: Unreact", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Message: Unreact",
            "delete",
            f"/messages/channels/{self.channel_id}/{self.message_id}/unreact/",
            params={"emoji": self._message_reaction},
            expected_status=(204,),
        )
        return bool(response)

    def delete_message(self) -> bool:
        if not self.channel_id or not self.message_id:
            self._record("Message: Delete", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Message: Delete",
            "delete",
            f"/messages/channels/{self.channel_id}/{self.message_id}/",
            expected_status=(204,),
        )
        return bool(response)

    def confirm_message_deleted(self) -> bool:
        if not self.channel_id or not self.message_id:
            self._record("Message: Confirm Delete", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Message: Confirm Delete",
            "get",
            f"/messages/channels/{self.channel_id}/{self.message_id}/",
            expected_status=(404,),
        )
        if response:
            self.message_id = None
            return True
        return False

    # ------------------------------------------------------------------
    # Notes steps
    # ------------------------------------------------------------------

    def create_note(self) -> bool:
        if not self.server_id:
            self._record("Note: Create", False, detail="Missing server ID")
            return False
        payload = {
            "title": "Smoke Note",
            "content": "This note was created by the API smoke test.",
            "tags": ["smoke", "automation"],
        }
        response = self.request(
            "Note: Create",
            "post",
            f"/notes/{self.server_id}/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        self.note_id = response.json()["id"]
        return True

    def fetch_notes(self) -> bool:
        if not self.server_id:
            self._record("Note: List", False, detail="Missing server ID")
            return False
        return bool(
            self.request(
                "Note: List",
                "get",
                f"/notes/{self.server_id}/",
                expected_status=(200,),
            )
        )

    def pin_note(self) -> bool:
        if not self.server_id or not self.note_id:
            self._record("Note: Pin", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Note: Pin Toggle",
            "post",
            f"/notes/{self.server_id}/{self.note_id}/pin/",
            expected_status=(200,),
        )
        return bool(response)

    def update_note(self) -> bool:
        if not self.server_id or not self.note_id:
            self._record("Note: Update", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Note: Update",
            "patch",
            f"/notes/{self.server_id}/{self.note_id}/",
            json={
                "content": "Updated note content via smoke test",
                "change_description": "Smoke test update",
            },
            expected_status=(200,),
        )
        return bool(response)

    def fetch_note_versions(self) -> bool:
        if not self.server_id or not self.note_id:
            self._record("Note: Versions", False, detail="Missing identifiers")
            return False
        return bool(
            self.request(
                "Note: Versions",
                "get",
                f"/notes/{self.server_id}/{self.note_id}/versions/",
                expected_status=(200,),
            )
        )

    def restore_note(self) -> bool:
        if not self.server_id or not self.note_id:
            self._record("Note: Restore", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Note: Restore",
            "post",
            f"/notes/{self.server_id}/{self.note_id}/restore/",
            json={"version_number": 1},
            expected_status=(200,),
        )
        return bool(response)

    def lock_note(self) -> bool:
        if not self.server_id or not self.note_id:
            self._record("Note: Lock", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Note: Lock Toggle",
            "post",
            f"/notes/{self.server_id}/{self.note_id}/lock/",
            expected_status=(200,),
        )
        return bool(response)

    def delete_note(self) -> bool:
        if not self.server_id or not self.note_id:
            self._record("Note: Delete", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Note: Delete",
            "delete",
            f"/notes/{self.server_id}/{self.note_id}/",
            expected_status=(204,),
        )
        if response:
            self.note_id = None
            return True
        return False

    # ------------------------------------------------------------------
    # Tasks steps
    # ------------------------------------------------------------------

    def create_task(self) -> bool:
        if not self.server_id:
            self._record("Task: Create", False, detail="Missing server ID")
            return False
        payload = {
            "title": "Smoke Task",
            "description": "Task generated by the smoke test.",
            "channel": self.channel_id,
            "priority": "medium",
            "status": "pending",
            "tags": ["smoke"],
        }
        response = self.request(
            "Task: Create",
            "post",
            f"/tasks/{self.server_id}/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        self.task_id = response.json()["id"]
        return True

    def list_tasks(self) -> bool:
        if not self.server_id:
            self._record("Task: List", False, detail="Missing server ID")
            return False
        return bool(
            self.request(
                "Task: List",
                "get",
                f"/tasks/{self.server_id}/",
                expected_status=(200,),
            )
        )

    def update_task(self) -> bool:
        if not self.server_id or not self.task_id:
            self._record("Task: Update", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Task: Update",
            "patch",
            f"/tasks/{self.server_id}/{self.task_id}/",
            json={"description": "Updated task description", "progress": 10},
            expected_status=(200,),
        )
        return bool(response)

    def assign_task(self) -> bool:
        if not self.server_id or not self.task_id or not self.user_id:
            self._record("Task: Assign", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Task: Assign",
            "post",
            f"/tasks/{self.server_id}/{self.task_id}/assign/",
            json={"user_id": self.user_id},
            expected_status=(200,),
        )
        return bool(response)

    def complete_task(self) -> bool:
        if not self.server_id or not self.task_id:
            self._record("Task: Complete", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Task: Complete",
            "post",
            f"/tasks/{self.server_id}/{self.task_id}/complete/",
            expected_status=(200,),
        )
        return bool(response)

    def create_task_comment(self) -> bool:
        if not self.server_id or not self.task_id:
            self._record("Task: Comment", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Task: Comment",
            "post",
            f"/tasks/{self.server_id}/{self.task_id}/comments/",
            json={"content": "Looks good to me."},
            expected_status=(201,),
        )
        return bool(response)

    def list_task_comments(self) -> bool:
        if not self.server_id or not self.task_id:
            self._record("Task: Comments List", False, detail="Missing identifiers")
            return False
        return bool(
            self.request(
                "Task: Comments List",
                "get",
                f"/tasks/{self.server_id}/{self.task_id}/comments/",
                expected_status=(200,),
            )
        )

    def delete_task(self) -> bool:
        if not self.server_id or not self.task_id:
            self._record("Task: Delete", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Task: Delete",
            "delete",
            f"/tasks/{self.server_id}/{self.task_id}/",
            expected_status=(204,),
        )
        if response:
            self.task_id = None
            return True
        return False

    # ------------------------------------------------------------------
    # Events steps
    # ------------------------------------------------------------------

    def create_event(self) -> bool:
        if not self.server_id:
            self._record("Event: Create", False, detail="Missing server ID")
            return False
        start_time = self._isoformat(timedelta(hours=1))
        end_time = self._isoformat(timedelta(hours=2))
        payload = {
            "title": "Smoke Event",
            "description": "Event created by smoke test.",
            "channel": self.channel_id,
            "event_type": "meeting",
            "status": "scheduled",
            "start_time": start_time,
            "end_time": end_time,
            "location": "Virtual",
            "tags": ["smoke"],
            "reminder_minutes_before": [15],
        }
        response = self.request(
            "Event: Create",
            "post",
            f"/events/{self.server_id}/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        self.event_id = response.json()["id"]
        return True

    def fetch_event_detail(self) -> bool:
        if not self.server_id or not self.event_id:
            self._record("Event: Detail", False, detail="Missing identifiers")
            return False
        return bool(
            self.request(
                "Event: Detail",
                "get",
                f"/events/{self.server_id}/{self.event_id}/",
                expected_status=(200,),
            )
        )

    def update_event(self) -> bool:
        if not self.server_id or not self.event_id:
            self._record("Event: Update", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Event: Update",
            "patch",
            f"/events/{self.server_id}/{self.event_id}/",
            json={"location": "Updated virtual room"},
            expected_status=(200,),
        )
        return bool(response)

    def rsvp_event(self) -> bool:
        if not self.server_id or not self.event_id:
            self._record("Event: RSVP", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Event: RSVP",
            "post",
            f"/events/{self.server_id}/{self.event_id}/rsvp/",
            json={"rsvp_status": "attending"},
            expected_status=(200,),
        )
        return bool(response)

    def fetch_event_calendar(self) -> bool:
        if not self.server_id:
            self._record("Event: Calendar", False, detail="Missing server ID")
            return False
        now = datetime.now()
        params = {"month": now.month, "year": now.year}
        return bool(
            self.request(
                "Event: Calendar",
                "get",
                f"/events/{self.server_id}/calendar/",
                params=params,
                expected_status=(200,),
            )
        )

    def fetch_upcoming_events(self) -> bool:
        if not self.server_id:
            self._record("Event: Upcoming", False, detail="Missing server ID")
            return False
        return bool(
            self.request(
                "Event: Upcoming",
                "get",
                f"/events/{self.server_id}/upcoming/",
                expected_status=(200,),
            )
        )

    def delete_event(self) -> bool:
        if not self.server_id or not self.event_id:
            self._record("Event: Delete", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Event: Delete",
            "delete",
            f"/events/{self.server_id}/{self.event_id}/",
            expected_status=(204,),
        )
        if response:
            self.event_id = None
            return True
        return False

    # ------------------------------------------------------------------
    # Poll steps
    # ------------------------------------------------------------------

    def create_poll(self) -> bool:
        if not self.server_id:
            self._record("Poll: Create", False, detail="Missing server ID")
            return False
        expires_at = self._isoformat(timedelta(days=1))
        payload = {
            "question": "Smoke Poll Question",
            "description": "Poll created by smoke test.",
            "channel": self.channel_id,
            "expires_at": expires_at,
            "allow_multiple_votes": False,
            "allow_add_options": False,
            "anonymous_votes": False,
            "show_results_before_vote": True,
            "options": ["Option A", "Option B"],
        }
        response = self.request(
            "Poll: Create",
            "post",
            f"/polls/{self.server_id}/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        data = response.json()
        self.poll_id = data["id"]
        self.poll_option_ids = [option["id"] for option in data.get("options", [])]
        if not self.poll_option_ids:
            # Fetch poll detail to obtain option identifiers
            detail_resp = self.request(
                "Poll: Detail",
                "get",
                f"/polls/{self.server_id}/{self.poll_id}/",
                expected_status=(200,),
            )
            if detail_resp:
                detail_data = detail_resp.json()
                self.poll_option_ids = [option["id"] for option in detail_data.get("options", [])]
        return True

    def fetch_poll_detail(self) -> bool:
        if not self.server_id or not self.poll_id:
            self._record("Poll: Detail", False, detail="Missing identifiers")
            return False
        return bool(
            self.request(
                "Poll: Detail",
                "get",
                f"/polls/{self.server_id}/{self.poll_id}/",
                expected_status=(200,),
            )
        )

    def vote_on_poll(self) -> bool:
        if not self.server_id or not self.poll_id or not self.poll_option_ids:
            self._record("Poll: Vote", False, detail="Missing identifiers")
            return False
        payload = {"option_ids": [self.poll_option_ids[0]]}
        response = self.request(
            "Poll: Vote",
            "post",
            f"/polls/{self.server_id}/{self.poll_id}/vote/",
            json=payload,
            expected_status=(200,),
        )
        return bool(response)

    def poll_results(self) -> bool:
        if not self.server_id or not self.poll_id:
            self._record("Poll: Results", False, detail="Missing identifiers")
            return False
        return bool(
            self.request(
                "Poll: Results",
                "get",
                f"/polls/{self.server_id}/{self.poll_id}/results/",
                expected_status=(200,),
            )
        )

    def poll_comment(self) -> bool:
        if not self.server_id or not self.poll_id:
            self._record("Poll: Comment", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Poll: Comment",
            "post",
            f"/polls/{self.server_id}/{self.poll_id}/comments/",
            json={"content": "Poll looks great."},
            expected_status=(201,),
        )
        return bool(response)

    def list_poll_comments(self) -> bool:
        if not self.server_id or not self.poll_id:
            self._record("Poll: Comments List", False, detail="Missing identifiers")
            return False
        return bool(
            self.request(
                "Poll: Comments List",
                "get",
                f"/polls/{self.server_id}/{self.poll_id}/comments/",
                expected_status=(200,),
            )
        )

    def unvote_poll(self) -> bool:
        if not self.server_id or not self.poll_id:
            self._record("Poll: Unvote", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Poll: Unvote",
            "delete",
            f"/polls/{self.server_id}/{self.poll_id}/unvote/",
            expected_status=(200,),
        )
        return bool(response)

    def close_poll(self) -> bool:
        if not self.server_id or not self.poll_id:
            self._record("Poll: Close", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Poll: Close",
            "post",
            f"/polls/{self.server_id}/{self.poll_id}/close/",
            expected_status=(200,),
        )
        return bool(response)

    def delete_poll(self) -> bool:
        if not self.server_id or not self.poll_id:
            self._record("Poll: Delete", False, detail="Missing identifiers")
            return False
        response = self.request(
            "Poll: Delete",
            "delete",
            f"/polls/{self.server_id}/{self.poll_id}/",
            expected_status=(204,),
        )
        if response:
            self.poll_id = None
            self.poll_option_ids = []
            return True
        return False

    # ------------------------------------------------------------------
    # Settings steps
    # ------------------------------------------------------------------

    def fetch_user_settings(self) -> bool:
        return bool(
            self.request(
                "Settings: User Get",
                "get",
                "/settings/user/",
                expected_status=(200,),
            )
        )

    def update_user_settings(self) -> bool:
        response = self.request(
            "Settings: User Patch",
            "patch",
            "/settings/user/",
            json={"theme": "light", "compact_mode": True},
            expected_status=(200,),
        )
        return bool(response)

    def fetch_server_settings(self) -> bool:
        if not self.server_id:
            self._record("Settings: Server Get", False, detail="Missing server ID")
            return False
        return bool(
            self.request(
                "Settings: Server Get",
                "get",
                f"/settings/servers/{self.server_id}/",
                expected_status=(200,),
            )
        )

    def update_server_settings(self) -> bool:
        if not self.server_id:
            self._record("Settings: Server Patch", False, detail="Missing server ID")
            return False
        response = self.request(
            "Settings: Server Patch",
            "patch",
            f"/settings/servers/{self.server_id}/",
            json={"max_members": 250, "enable_polls": True},
            expected_status=(200,),
        )
        return bool(response)

    def create_notification_preference(self) -> bool:
        if not self.server_id:
            self._record("Settings: Notifications Create", False, detail="Missing server ID")
            return False
        response = self.request(
            "Settings: Notifications Create",
            "post",
            "/settings/notifications/",
            json={"server": self.server_id, "notification_level": "mentions"},
            expected_status=(201,),
        )
        if not response:
            return False
        data = response.json()
        self.notification_preference_id = data.get("id")
        return True

    def list_notification_preferences(self) -> bool:
        response = self.request(
            "Settings: Notifications List",
            "get",
            "/settings/notifications/",
            expected_status=(200,),
        )
        if not response:
            return False
        if self.notification_preference_id is None:
            try:
                payload = response.json()
            except Exception:  # noqa: broad-except
                payload = []
            if isinstance(payload, dict):
                candidates = payload.get("results") or payload.get("data") or []
            else:
                candidates = payload
            if isinstance(candidates, list) and candidates:
                first = candidates[0]
                if isinstance(first, dict):
                    self.notification_preference_id = first.get("id")
        return True

    def get_notification_preference(self) -> bool:
        if not self.notification_preference_id:
            self._record("Settings: Notifications Detail", False, detail="Missing preference ID")
            return False
        return bool(
            self.request(
                "Settings: Notifications Detail",
                "get",
                f"/settings/notifications/{self.notification_preference_id}/",
                expected_status=(200,),
            )
        )

    def update_notification_preference(self) -> bool:
        if not self.notification_preference_id:
            self._record("Settings: Notifications Patch", False, detail="Missing preference ID")
            return False
        response = self.request(
            "Settings: Notifications Patch",
            "patch",
            f"/settings/notifications/{self.notification_preference_id}/",
            json={"notification_level": "all"},
            expected_status=(200,),
        )
        return bool(response)

    def delete_notification_preference(self) -> bool:
        if not self.notification_preference_id:
            self._record("Settings: Notifications Delete", False, detail="Missing preference ID")
            return False
        response = self.request(
            "Settings: Notifications Delete",
            "delete",
            f"/settings/notifications/{self.notification_preference_id}/",
            expected_status=(204,),
        )
        if response:
            self.notification_preference_id = None
            return True
        return False

    # ------------------------------------------------------------------
    # Direct message steps
    # ------------------------------------------------------------------

    def create_secondary_user(self) -> bool:
        payload = {
            "email": f"{uuid.uuid4().hex[:8]}@meshup.test",
            "username": f"aux_{uuid.uuid4().hex[:6]}",
            "password": "Meshup!9876",
            "password_confirm": "Meshup!9876",
        }
        response = self.request(
            "Auth: Register Secondary",
            "post",
            "/auth/register/",
            json=payload,
            expected_status=(201,),
        )
        if not response:
            return False
        self.secondary_user_id = response.json()["user"]["id"]
        return True

    def create_dm_channel(self) -> bool:
        if not self.secondary_user_id:
            self._record("DM: Create", False, detail="Missing secondary user ID")
            return False
        response = self.request(
            "DM: Create",
            "post",
            "/messages/dm/",
            json={"participant_ids": [self.secondary_user_id]},
            expected_status=(201, 200),
        )
        if not response:
            return False
        self.dm_id = response.json()["id"]
        return True

    def send_dm_message(self) -> bool:
        if not self.dm_id:
            self._record("DM: Message Create", False, detail="Missing DM ID")
            return False
        response = self.request(
            "DM: Message Create",
            "post",
            f"/messages/dm/{self.dm_id}/messages/",
            json={"content": "Hello from smoke test."},
            expected_status=(201,),
        )
        return bool(response)

    def list_dm_channels(self) -> bool:
        response = self.request(
            "DM: List",
            "get",
            "/messages/dm/",
            expected_status=(200,),
        )
        if not response:
            return False
        if self.dm_id is None:
            try:
                payload = response.json()
            except Exception:  # noqa: broad-except
                payload = []
            if isinstance(payload, dict):
                candidates = payload.get("results") or payload.get("data") or []
            else:
                candidates = payload
            if isinstance(candidates, list) and candidates:
                first = candidates[0]
                if isinstance(first, dict):
                    self.dm_id = first.get("id")
        return True

    def get_dm_channel(self) -> bool:
        if not self.dm_id:
            self._record("DM: Detail", False, detail="Missing DM ID")
            return False
        return bool(
            self.request(
                "DM: Detail",
                "get",
                f"/messages/dm/{self.dm_id}/",
                expected_status=(200,),
            )
        )

    def fetch_dm_messages(self) -> bool:
        if not self.dm_id:
            self._record("DM: Messages List", False, detail="Missing DM ID")
            return False
        return bool(
            self.request(
                "DM: Messages List",
                "get",
                f"/messages/dm/{self.dm_id}/messages/",
                expected_status=(200,),
            )
        )

    def delete_dm_channel(self) -> bool:
        if not self.dm_id:
            self._record("DM: Delete", False, detail="Missing DM ID")
            return False
        response = self.request(
            "DM: Delete",
            "delete",
            f"/messages/dm/{self.dm_id}/",
            expected_status=(204,),
        )
        if response:
            self.dm_id = None
            return True
        return False

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_summary(self) -> None:
        print("\n=== Meshup API Smoke Test Summary ===")
        if not self.results:
            print("No steps executed.")
            return
        name_width = max(len(result.name) for result in self.results) + 2
        for result in self.results:
            status = "PASS" if result.success else "FAIL"
            code = result.status_code if result.status_code is not None else "--"
            detail = result.detail.replace("\n", " ")
            if len(detail) > 120:
                detail = detail[:117] + "..."
            print(f"{status:<5} {result.name:<{name_width}} {code:<4} {detail}")
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        print(f"\nPassed {passed}/{total} steps")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Meshup API smoke tester")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("MESHUP_API_BASE", "http://localhost:8000/api/v1"),
        help="Base URL for the Meshup API (default: %(default)s)",
    )
    parser.add_argument("--email", help="Reuse an existing account email for the smoke test")
    parser.add_argument("--password", help="Password for the provided account")
    parser.add_argument("--verbose", action="store_true", help="Print per-step diagnostics")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    tester = APISmokeTester(args.base_url, args.email, args.password, verbose=args.verbose)
    success = tester.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
