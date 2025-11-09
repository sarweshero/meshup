from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
	initial = True

	dependencies = [
		("users", "0001_initial"),
		("servers", "0004_rename_server_invites_server_created_idx_server_invi_server__30c72f_idx_and_more"),
		("meshup_channels", "0002_initial"),
	]

	operations = [
		migrations.CreateModel(
			name="UserActivity",
			fields=[
				("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
				("status", models.CharField(choices=[("online", "Online"), ("away", "Away"), ("dnd", "Do Not Disturb"), ("invisible", "Invisible"), ("offline", "Offline")], db_index=True, default="offline", max_length=20)),
				("current_activity", models.CharField(choices=[("idle", "Idle"), ("browsing", "Browsing"), ("typing", "Typing"), ("in_call", "In Call"), ("in_meeting", "In Meeting"), ("streaming", "Streaming"), ("listening", "Listening to Audio"), ("watching", "Watching Video"), ("gaming", "Gaming"), ("custom", "Custom")], default="idle", max_length=20)),
				("custom_activity_text", models.CharField(blank=True, max_length=128)),
				("custom_activity_emoji", models.CharField(blank=True, max_length=10)),
				("last_seen", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
				("status_updated_at", models.DateTimeField(default=django.utils.timezone.now)),
				("activity_started_at", models.DateTimeField(default=django.utils.timezone.now)),
				("share_activity", models.BooleanField(default=True)),
				("activity_visibility", models.CharField(choices=[("everyone", "Everyone"), ("friends", "Friends Only"), ("servers", "Servers Only"), ("hidden", "Hidden")], default="everyone", max_length=20)),
				("updated_at", models.DateTimeField(auto_now=True)),
				("channel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="user_activities", to="meshup_channels.channel")),
				("server", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="user_activities", to="servers.server")),
				("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="activity", to="users.user")),
			],
			options={
				"db_table": "user_activities",
			},
		),
		migrations.CreateModel(
			name="ActivityLog",
			fields=[
				("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
				("activity_type", models.CharField(choices=[("message_sent", "Message Sent"), ("file_shared", "File Shared"), ("call_initiated", "Call Initiated"), ("call_joined", "Call Joined"), ("screen_shared", "Screen Shared"), ("task_created", "Task Created"), ("task_completed", "Task Completed"), ("note_created", "Note Created"), ("poll_created", "Poll Created"), ("poll_voted", "Poll Voted"), ("event_created", "Event Created"), ("event_rsvped", "Event RSVP")], db_index=True, max_length=50)),
				("resource_type", models.CharField(max_length=50)),
				("resource_id", models.UUIDField()),
				("details", models.JSONField(blank=True, default=dict)),
				("ip_address", models.GenericIPAddressField()),
				("user_agent", models.CharField(blank=True, max_length=500)),
				("device_type", models.CharField(choices=[("desktop", "Desktop"), ("mobile", "Mobile"), ("tablet", "Tablet"), ("unknown", "Unknown")], default="unknown", max_length=20)),
				("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
				("channel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activity_logs", to="meshup_channels.channel")),
				("server", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activity_logs", to="servers.server")),
				("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activity_logs", to="users.user")),
			],
			options={
				"db_table": "activity_logs",
				"ordering": ["-created_at"],
			},
		),
		migrations.CreateModel(
			name="ActivityStreak",
			fields=[
				("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
				("current_streak", models.IntegerField(default=0)),
				("best_streak", models.IntegerField(default=0)),
				("last_active_date", models.DateField(blank=True, null=True)),
				("streak_started_at", models.DateField(blank=True, null=True)),
				("updated_at", models.DateTimeField(auto_now=True)),
				("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="activity_streak", to="users.user")),
			],
			options={
				"db_table": "activity_streaks",
			},
		),
		migrations.CreateModel(
			name="ShareableActivity",
			fields=[
				("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
				("activity_type", models.CharField(choices=[("music", "Listening to Music"), ("game", "Playing Game"), ("article", "Reading Article"), ("video", "Watching Video"), ("podcast", "Listening to Podcast"), ("stream", "Watching Stream"), ("coding", "Coding"), ("designing", "Designing"), ("writing", "Writing")], db_index=True, max_length=20)),
				("title", models.CharField(max_length=255)),
				("description", models.TextField(blank=True)),
				("image_url", models.URLField(blank=True, null=True)),
				("service_name", models.CharField(max_length=100)),
				("service_id", models.CharField(max_length=255)),
				("external_url", models.URLField(blank=True, null=True)),
				("duration_seconds", models.IntegerField(blank=True, null=True)),
				("progress_seconds", models.IntegerField(default=0)),
				("is_public", models.BooleanField(default=True)),
				("started_at", models.DateTimeField(default=django.utils.timezone.now)),
				("updated_at", models.DateTimeField(auto_now=True)),
				("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="shareable_activity", to="users.user")),
			],
			options={
				"db_table": "shareable_activities",
			},
		),
		migrations.CreateModel(
			name="OnlinePresence",
			fields=[
				("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
				("is_online", models.BooleanField(db_index=True, default=True)),
				("came_online_at", models.DateTimeField(default=django.utils.timezone.now)),
				("went_offline_at", models.DateTimeField(blank=True, null=True)),
				("server", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="online_presences", to="servers.server")),
				("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="online_presences", to="users.user")),
			],
			options={
				"db_table": "online_presences",
			},
		),
		migrations.AddIndex(
			model_name="useractivity",
			index=models.Index(fields=["status", "-last_seen"], name="useractiv_status_7dc64d_idx"),
		),
		migrations.AddIndex(
			model_name="useractivity",
			index=models.Index(fields=["server", "status"], name="useractiv_server_6eedfa_idx"),
		),
		migrations.AddIndex(
			model_name="activitylog",
			index=models.Index(fields=["user", "-created_at"], name="activityl_user_id_46a491_idx"),
		),
		migrations.AddIndex(
			model_name="activitylog",
			index=models.Index(fields=["activity_type", "-created_at"], name="activityl_activity_99d9bf_idx"),
		),
		migrations.AddIndex(
			model_name="activitylog",
			index=models.Index(fields=["server", "-created_at"], name="activityl_server__2398f2_idx"),
		),
		migrations.AddIndex(
			model_name="shareableactivity",
			index=models.Index(fields=["activity_type"], name="shareable_activity_d6c89f_idx"),
		),
		migrations.AddIndex(
			model_name="onlinepresence",
			index=models.Index(fields=["server", "is_online"], name="onlinepre_server__d0f93f_idx"),
		),
		migrations.AddIndex(
			model_name="onlinepresence",
			index=models.Index(fields=["user", "server"], name="onlinepre_user_id_9183cb_idx"),
		),
		migrations.AddConstraint(
			model_name="onlinepresence",
			constraint=models.UniqueConstraint(fields=("user", "server"), name="onlinepresence_unique_user_server"),
		),
	]
