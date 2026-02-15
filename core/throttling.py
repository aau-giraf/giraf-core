"""Rate-limiting throttle classes for sensitive endpoints."""

from ninja.throttling import AnonRateThrottle, AuthRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Limit login attempts to 5/min per IP."""

    scope = "login"

    def __init__(self) -> None:
        super().__init__(rate="5/min")


class RegisterRateThrottle(AnonRateThrottle):
    """Limit registration attempts to 3/min per IP."""

    scope = "register"

    def __init__(self) -> None:
        super().__init__(rate="3/min")


class InvitationSendRateThrottle(AuthRateThrottle):
    """Limit invitation sends to 10/min per authenticated user."""

    scope = "invitation_send"

    def __init__(self) -> None:
        super().__init__(rate="10/min")
