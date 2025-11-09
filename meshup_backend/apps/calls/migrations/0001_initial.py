from __future__ import annotations

import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0001_initial"),
        ("meshup_channels", "0002_initial"),
        ("meshup_messages", "0001_initial"),
        ("servers", "0004_rename_server_invites_server_created_idx_server_invi_server__30c72f_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CallSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("call_type", models.CharField(choices=[("voice", "Voice Call"), ("video", "Video Call"), ("group", "Group Call")], db_index=True, max_length=20)),
                ("status", models.CharField(choices=[("initiating", "Initiating"), ("ringing", "Ringing"), ("active", "Active"), ("on_hold", "On Hold"), ("ended", "Ended"), ("missed", "Missed"), ("declined", "Declined")], db_index=True, default="initiating", max_length=20)),
                ("call_token", models.CharField(max_length=500, unique=True)),
                ("room_id", models.CharField(db_index=True, max_length=255)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("is_recorded", models.BooleanField(default=False)),
                ("recording_url", models.URLField(blank=True, null=True)),
                ("recording_size", models.BigIntegerField(blank=True, null=True)),
                ("video_quality", models.CharField(choices=[("low", "Low (240p)"), ("standard", "Standard (480p)"), ("high", "High (720p)"), ("ultra", "Ultra (1080p)")], default="standard", max_length=20)),
                ("audio_codec", models.CharField(default="opus", max_length=50)),
                ("video_codec", models.CharField(default="vp9", max_length=50)),
                ("total_participants", models.IntegerField(default=2)),
                ("peak_participants", models.IntegerField(default=2)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="voice_calls", to="meshup_channels.channel")),
                ("dm_channel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="voice_calls", to="meshup_messages.directmessage")),
                ("initiator", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="initiated_calls", to="users.user")),
                ("server", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="call_sessions", to="servers.server")),
            ],
            options={
                "db_table": "call_sessions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CallParticipant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("audio_state", models.CharField(choices=[("active", "Active"), ("muted", "Muted"), ("off", "Off")], default="active", max_length=20)),
                ("video_state", models.CharField(choices=[("active", "Active"), ("muted", "Muted"), ("off", "Off")], default="active", max_length=20)),
                ("screen_share_state", models.CharField(choices=[("inactive", "Inactive"), ("active", "Active"), ("paused", "Paused")], default="inactive", max_length=20)),
                ("peer_id", models.CharField(db_index=True, max_length=255, unique=True)),
                ("network_quality", models.CharField(choices=[("excellent", "Excellent"), ("good", "Good"), ("fair", "Fair"), ("poor", "Poor")], default="good", max_length=20)),
                ("packet_loss_rate", models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)])),
                ("latency_ms", models.IntegerField(default=0)),
                ("bandwidth_mbps", models.FloatField(default=0.0)),
                ("joined_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                ("call", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participants", to="calls.callsession")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="call_participations", to="users.user")),
            ],
            options={
                "db_table": "call_participants",
            },
        ),
        migrations.CreateModel(
            name="CallQualityMetric",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("audio_level", models.IntegerField(validators=[django.core.validators.MinValueValidator(-127), django.core.validators.MaxValueValidator(0)])),
                ("audio_jitter_ms", models.FloatField()),
                ("audio_round_trip_time_ms", models.FloatField()),
                ("video_bitrate_kbps", models.IntegerField()),
                ("video_framerate", models.IntegerField()),
                ("video_resolution", models.CharField(max_length=20)),
                ("video_encoder_implementation", models.CharField(max_length=50)),
                ("bytes_sent", models.BigIntegerField()),
                ("bytes_received", models.BigIntegerField()),
                ("packets_lost", models.IntegerField()),
                ("connection_state", models.CharField(choices=[("new", "New"), ("connecting", "Connecting"), ("connected", "Connected"), ("disconnected", "Disconnected"), ("failed", "Failed"), ("closed", "Closed")], max_length=20)),
                ("cpu_usage_percent", models.FloatField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("recorded_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("call", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quality_metrics", to="calls.callsession")),
                ("participant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quality_metrics", to="calls.callparticipant")),
            ],
            options={
                "db_table": "call_quality_metrics",
                "ordering": ["-recorded_at"],
            },
        ),
        migrations.CreateModel(
            name="CallRecording",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("recording", "Recording"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")], default="recording", max_length=20)),
                ("file_url", models.URLField()),
                ("file_size", models.BigIntegerField()),
                ("duration_seconds", models.IntegerField()),
                ("transcript", models.TextField(blank=True)),
                ("transcript_language", models.CharField(default="en", max_length=10)),
                ("has_transcript", models.BooleanField(default=False)),
                ("storage_regions", models.JSONField(default=list)),
                ("is_public", models.BooleanField(default=False)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("allowed_viewers", models.ManyToManyField(blank=True, related_name="accessible_call_recordings", to="users.user")),
                ("call", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="recording", to="calls.callsession")),
            ],
            options={
                "db_table": "call_recordings",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ScreenShareSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("active", "Active"), ("paused", "Paused"), ("ended", "Ended")], default="active", max_length=20)),
                ("stream_id", models.CharField(db_index=True, max_length=255, unique=True)),
                ("resolution", models.CharField(max_length=20)),
                ("framerate", models.IntegerField()),
                ("bitrate_kbps", models.IntegerField()),
                ("include_audio", models.BooleanField(default=False)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("call", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="screen_shares", to="calls.callsession")),
                ("participant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="screen_shares", to="calls.callparticipant")),
            ],
            options={
                "db_table": "screen_share_sessions",
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="CallInvitation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined"), ("missed", "Missed")], db_index=True, default="pending", max_length=20)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("response_time_seconds", models.IntegerField(blank=True, null=True)),
                ("notification_sent", models.BooleanField(default=True)),
                ("notification_type", models.CharField(choices=[("push", "Push Notification"), ("email", "Email"), ("inapp", "In-App")], max_length=20)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("call", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitations", to="calls.callsession")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="call_invitations", to="users.user")),
            ],
            options={
                "db_table": "call_invitations",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["initiator", "-created_at"], name="callsessi_initia_86a4be_idx"),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["room_id"], name="callsessi_room_id_082be7_idx"),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["status", "-created_at"], name="callsessi_status_67bf4b_idx"),
        ),
        migrations.AddIndex(
            model_name="callsession",
            index=models.Index(fields=["server", "-created_at"], name="callsessi_server_2f1019_idx"),
        ),
        migrations.AddIndex(
            model_name="callparticipant",
            index=models.Index(fields=["call", "joined_at"], name="callparti_call_id_3a5ee0_idx"),
        ),
        migrations.AddIndex(
            model_name="callparticipant",
            index=models.Index(fields=["peer_id"], name="callparti_peer_id_1313a4_idx"),
        ),
        migrations.AddConstraint(
            model_name="callparticipant",
            constraint=models.UniqueConstraint(fields=("call", "user"), name="call_unique_participant"),
        ),
        migrations.AddIndex(
            model_name="callqualitymetric",
            index=models.Index(fields=["call", "-recorded_at"], name="callqualit_call_id_0540ee_idx"),
        ),
        migrations.AddIndex(
            model_name="callqualitymetric",
            index=models.Index(fields=["participant", "-recorded_at"], name="callqualit_partici_410a45_idx"),
        ),
        migrations.AddIndex(
            model_name="screensharesession",
            index=models.Index(fields=["call", "status"], name="screensha_call_id_346db2_idx"),
        ),
        migrations.AddIndex(
            model_name="screensharesession",
            index=models.Index(fields=["participant"], name="screensha_partici_f593a5_idx"),
        ),
        migrations.AddIndex(
            model_name="callinvitation",
            index=models.Index(fields=["recipient", "status"], name="callinvit_recipient_d5f51e_idx"),
        ),
        migrations.AddIndex(
            model_name="callinvitation",
            index=models.Index(fields=["recipient", "-created_at"], name="callinvit_recipient_f96127_idx"),
        ),
        migrations.AddConstraint(
            model_name="callinvitation",
            constraint=models.UniqueConstraint(fields=("call", "recipient"), name="call_unique_invitation"),
        ),
    ]
