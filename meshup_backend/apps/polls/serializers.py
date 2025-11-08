"""Serializers for polls and voting."""
from rest_framework import serializers

from apps.users.serializers import UserBasicSerializer

from .models import Poll, PollComment, PollOption, PollVote


class PollOptionSerializer(serializers.ModelSerializer):
    """Serializer for poll options with vote statistics."""

    percentage = serializers.SerializerMethodField()
    has_voted = serializers.SerializerMethodField()
    added_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = PollOption
        fields = (
            "id",
            "option_text",
            "position",
            "vote_count",
            "percentage",
            "has_voted",
            "added_by",
            "created_at",
        )
        read_only_fields = ("id", "vote_count", "created_at")

    def get_percentage(self, obj):
        return round(obj.calculate_percentage(), 2)

    def get_has_voted(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.votes.filter(user=request.user).exists()
        return False


class PollCommentSerializer(serializers.ModelSerializer):
    """Serializer for poll comments."""

    author = UserBasicSerializer(read_only=True)

    class Meta:
        model = PollComment
        fields = ("id", "author", "content", "created_at")
        read_only_fields = ("id", "author", "created_at")


class PollSerializer(serializers.ModelSerializer):
    """Complete serializer for polls."""

    created_by = UserBasicSerializer(read_only=True)
    options = PollOptionSerializer(many=True, read_only=True)
    user_votes = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    can_vote = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = (
            "id",
            "question",
            "description",
            "server",
            "channel",
            "created_by",
            "status",
            "allow_multiple_votes",
            "allow_add_options",
            "anonymous_votes",
            "show_results_before_vote",
            "expires_at",
            "total_votes",
            "options",
            "user_votes",
            "is_expired",
            "can_vote",
            "created_at",
            "updated_at",
            "closed_at",
        )
        read_only_fields = ("id", "created_by", "total_votes", "created_at", "updated_at", "closed_at")

    def get_user_votes(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            votes = obj.votes.filter(user=request.user)
            return [str(vote.option.id) for vote in votes]
        return []

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_can_vote(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if obj.status != "active" or obj.is_expired():
            return False
        if not obj.allow_multiple_votes:
            return not obj.votes.filter(user=request.user).exists()
        return True


class PollCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating polls."""

    options = serializers.ListField(
        child=serializers.CharField(max_length=200),
        min_length=2,
        write_only=True,
        help_text="List of poll options",
    )

    class Meta:
        model = Poll
        fields = (
            "question",
            "description",
            "channel",
            "allow_multiple_votes",
            "allow_add_options",
            "anonymous_votes",
            "show_results_before_vote",
            "expires_at",
            "options",
        )

    def validate_options(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Poll must have at least 2 options")
        if len(value) > 20:
            raise serializers.ValidationError("Poll cannot have more than 20 options")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Poll options must be unique")
        return value

    def create(self, validated_data):
        options_data = validated_data.pop("options")
        poll = Poll.objects.create(**validated_data)
        request = self.context.get("request")
        created_by = request.user if request and request.user.is_authenticated else None
        for index, option_text in enumerate(options_data):
            PollOption.objects.create(
                poll=poll,
                option_text=option_text,
                position=index,
                added_by=created_by,
            )
        return poll
