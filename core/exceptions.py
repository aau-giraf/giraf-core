"""Cross-cutting exception types for GIRAF Core API."""


class InvitationError(Exception):
    """Base exception for invitation operations."""


class ReceiverNotFoundError(InvitationError):
    """No user exists with the given email."""


class AlreadyMemberError(InvitationError):
    """The user is already a member of the organization."""


class DuplicateInvitationError(InvitationError):
    """A pending invitation already exists for this user+org."""
