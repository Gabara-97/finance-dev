# Security design
| Risk | Control |
|---|---|
| Credential theft | Supabase Auth hashes passwords; no credentials in code; `.env` git-ignored |
| Access to other users' data | RLS on every table + composite foreign keys so a record can't reference another user's category |
| Privilege escalation | Users can only update their own `full_name`; `role` is not writable |
| Injection | Validated inputs; PostgREST parameters (no string-built SQL); `textContent` rendering |
| Abuse | Per-IP rate limits, 16 KB body limit, CORS allow-list |
| Tampering with history | Audit trigger is `security definer`; clients have no write access to `audit_logs` |
| Secrets exposure | Service-role key never used; only the public anon key reaches the browser |

## Known limits (be aware)
- MFA is enforced at login by the frontend; the API does not yet require an `aal2` session. Enforce `aal2` in RLS or the API before handling real customer data.
- The `admin` role exists in the schema but no admin endpoints are built yet.
- Not independently audited. Do not treat it as production-ready for real financial data without a security review.
