# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in GIRAF Core, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email the project maintainers directly. Include:

- A description of the vulnerability
- Steps to reproduce the issue
- The potential impact
- Any suggested fixes (optional)

We will acknowledge receipt within 48 hours and aim to provide an initial assessment within one week.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |

## Security Measures

GIRAF Core implements the following security measures:

- **Authentication:** JWT-based authentication with configurable token lifetimes
- **Authorization:** Role-based access control (owner > admin > member) per organization
- **Rate limiting:** Login, registration, and invitation endpoints are rate-limited
- **Token blacklisting:** Refresh tokens can be revoked via the blacklist endpoint
- **Password validation:** Django's built-in password validators (minimum length, common password check, numeric check)
- **Input validation:** Pydantic schemas validate all API inputs
- **CORS:** Configurable allowed origins (restricted in production)
