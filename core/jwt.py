"""Custom JWT token schema that embeds org_roles into the access token.

When a user logs in via /token/pair, their membership roles are embedded
as a claim in both the JWT payload and the JSON response body.
"""

from ninja import Schema
from ninja_jwt.schema import TokenObtainInputSchemaBase
from ninja_jwt.tokens import RefreshToken


class TokenObtainPairOutputSchema(Schema):
    refresh: str
    access: str
    org_roles: dict[str, str] = {}


class TokenObtainPairInputSchema(TokenObtainInputSchemaBase):
    @classmethod
    def get_response_schema(cls) -> type[Schema]:
        return TokenObtainPairOutputSchema

    @classmethod
    def get_token(cls, user) -> dict:
        values: dict[str, object] = {}
        refresh = RefreshToken.for_user(user)

        # Build org_roles: {org_id: role} from memberships
        org_roles = {}
        for membership in user.memberships.select_related("organization").all():
            org_roles[str(membership.organization_id)] = membership.role

        # Embed in JWT payload (before generating access token)
        refresh["org_roles"] = org_roles

        values["refresh"] = str(refresh)
        values["access"] = str(refresh.access_token)  # type: ignore[attr-defined]
        values["org_roles"] = org_roles
        return values  # type: ignore[return-value]
