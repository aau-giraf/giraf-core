"""Cross-cutting exception types for GIRAF Core API."""


class ServiceError(Exception):
    """Base exception for service layer operations."""


class BadRequestError(ServiceError):
    """The request is malformed or invalid."""


class ResourceNotFoundError(ServiceError):
    """The requested resource was not found."""


class ConflictError(ServiceError):
    """The operation conflicts with existing state (e.g. duplicates)."""


class BusinessValidationError(ServiceError):
    """The operation violates a business rule."""


class InvitationError(ServiceError):
    """Base exception for invitation operations."""


class ReceiverNotFoundError(InvitationError, ResourceNotFoundError):
    """No user exists with the given email."""


class AlreadyMemberError(InvitationError, ConflictError):
    """The user is already a member of the organization."""


class DuplicateInvitationError(InvitationError, ConflictError):
    """A pending invitation already exists for this user+org."""


class InvitationSendError(InvitationError, BadRequestError):
    """Generic send failure — hides specific cause to prevent enumeration."""
