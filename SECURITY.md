# Security Implementation Guide

## Overview
This document describes the security measures implemented in the MarktplaatsSearch API to protect user data and prevent unauthorized access.

## Security Features

### 1. Secure Token Generation
- **Implementation**: Cryptographically secure random tokens using Python's `secrets` module
- **Token Format**: `mps_<64 hex characters>` (256 bits of entropy)
- **Location**: `auth.py::generate_secure_token()`

### 2. Token Storage
- **Never stored in plaintext** - all tokens are hashed before database storage
- **Hashing Algorithm**: HMAC-SHA256 with environment-specific salt
- **Database Field**: `api_token_hash` (replaced plaintext `api_token`)

### 3. Authentication Flow
```
Client Request → Bearer Token → Token Validation → Hash Comparison → User Authentication
```

### 4. User Management Endpoints

| Endpoint | Method | Description | Security Notes |
|----------|--------|-------------|----------------|
| `/api/auth/register` | POST | Create new user | Returns token only once |
| `/api/auth/me` | GET | Get user info | Requires authentication |
| `/api/auth/rotate-token` | POST | Generate new token | Invalidates old token |
| `/api/auth/deactivate` | DELETE | Deactivate account | Soft delete |

### 5. Environment Configuration
- **File**: `.env` (never commit to version control)
- **Key Settings**:
  - `TOKEN_SALT`: Unique salt for token hashing
  - `TOKEN_EXPIRY_DAYS`: Optional token expiration
  - `DEV_MODE`: Must be `false` in production
  - `CREATE_DEFAULT_USER`: Must be `false` in production

### 6. Security Headers
- Token validation with format checking
- Constant-time comparison to prevent timing attacks
- User activity tracking for audit logs
- Account status checking (active/inactive)

## Migration from Insecure Version

### For Existing Deployments
1. **Backup your database** before migration
2. Run the migration script:
   ```bash
   python migrate_db.py
   ```
3. The script will:
   - Create a timestamped backup
   - Hash existing plaintext tokens
   - Update the database schema
   - Preserve existing tokens (users can still authenticate with them)

### For New Deployments
1. Copy `.env.example` to `.env`
2. Update configuration values
3. Start the application normally
4. Use `/api/auth/register` to create users

## Security Best Practices

### Token Management
- **Rotate tokens regularly** using `/api/auth/rotate-token`
- **Never share tokens** in logs, emails, or version control
- **Use HTTPS** in production to prevent token interception
- **Set token expiry** in production environments

### Configuration
```bash
# Production .env settings
DEV_MODE=false
CREATE_DEFAULT_USER=false
TOKEN_EXPIRY_DAYS=30
API_RELOAD=false
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_ENABLED=true
```

### Database Security
- Use strong database passwords
- Restrict database access to application only
- Regular backups with encryption
- Monitor for suspicious activity

## Security Checklist

### Deployment Checklist
- [ ] `.env` file created and secured
- [ ] `DEV_MODE=false` in production
- [ ] `CREATE_DEFAULT_USER=false` in production
- [ ] Unique `TOKEN_SALT` generated
- [ ] HTTPS configured
- [ ] CORS origins restricted
- [ ] Rate limiting enabled
- [ ] Database backups configured

### Code Review Checklist
- [ ] No hardcoded credentials
- [ ] All tokens hashed before storage
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info
- [ ] Logging doesn't include tokens
- [ ] Dependencies up to date

## Vulnerability Reporting
If you discover a security vulnerability, please:
1. Do NOT create a public issue
2. Contact the maintainers privately
3. Allow time for a fix before disclosure

## OWASP Top 10 Compliance

| Risk | Mitigation |
|------|------------|
| A01: Broken Access Control | Token-based authentication, user ownership verification |
| A02: Cryptographic Failures | SHA256 hashing, secure token generation |
| A03: Injection | Parameterized queries via SQLAlchemy ORM |
| A04: Insecure Design | Defense in depth, principle of least privilege |
| A05: Security Misconfiguration | Environment-based config, secure defaults |
| A06: Vulnerable Components | Regular dependency updates (see pyproject.toml) |
| A07: Authentication Failures | Token rotation, optional expiry, activity tracking |
| A08: Data Integrity Failures | Input validation on all endpoints |
| A09: Logging Failures | Structured logging, no sensitive data in logs |
| A10: SSRF | URL validation in web fetch operations |

## Testing Security

### Manual Testing
```bash
# Test registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"user_identifier": "testuser"}'

# Test authentication
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test token rotation
curl -X POST http://localhost:8000/api/auth/rotate-token \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Automated Security Testing
Consider using:
- `bandit` for Python security linting
- `safety` for dependency vulnerability scanning
- `pytest` with security-focused test cases
- API fuzzing tools

## Monitoring

### What to Monitor
- Failed authentication attempts
- Token rotation frequency
- Unusual API usage patterns
- Database query performance
- Error rates by endpoint

### Logging
- User authentication events
- Token rotations
- Account deactivations
- API errors
- Rate limit violations

## Future Enhancements
- [ ] Two-factor authentication (2FA)
- [ ] OAuth2/OpenID Connect support
- [ ] API key scopes/permissions
- [ ] IP-based rate limiting
- [ ] Webhook for security events
- [ ] Audit log export functionality