# Phase 01: Security Critical Fixes

**Date:** 2024-12-29
**Priority:** 🔴 CRITICAL
**Status:** Pending
**Estimated Effort:** 2-3 days

---

## Context

Multiple critical security vulnerabilities identified that must be fixed before any production deployment.

---

## Issues to Fix

### 1. Remove Demo Authentication Bypass
**File:** `api/services/auth.py:154-166`
```python
# CURRENT - VULNERABLE
if login.password == "demo":
    return {"access_token": create_access_token(...)}
```

**Fix:**
```python
# Remove entirely OR gate with environment variable
if os.getenv('ENABLE_DEMO_MODE') == 'true' and login.password == "demo":
    logger.warning("Demo mode authentication used")
    return {"access_token": create_access_token(...)}
```

### 2. Require Mandatory Secrets
**File:** `api/config.py:15`
```python
# CURRENT - INSECURE DEFAULT
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
```

**Fix:**
```python
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable must be set")
```

### 3. Fix Cypher Injection
**File:** `api/db/neo4j.py:152`
```python
# CURRENT - VULNERABLE
query = f"MATCH (n:{namespace}) RETURN n LIMIT {limit}"
```

**Fix:**
```python
ALLOWED_NAMESPACES = {"Test_rel_2", "Test_rel_3", "Prod_rel_1"}
if namespace not in ALLOWED_NAMESPACES:
    raise ValueError(f"Invalid namespace: {namespace}")
query = f"MATCH (n:{namespace}) RETURN n LIMIT $limit"
result = session.run(query, limit=limit)
```

### 4. Sanitize Error Messages
**File:** `api/main.py:134`
```python
# CURRENT - LEAKS INTERNALS
return JSONResponse(content={"detail": str(exc)}, status_code=500)
```

**Fix:**
```python
import uuid
error_id = str(uuid.uuid4())[:8]
logger.error(f"[{error_id}] Internal error: {exc}", exc_info=True)
return JSONResponse(
    content={"detail": f"Internal server error. Reference: {error_id}"},
    status_code=500
)
```

### 5. Remove Hardcoded MySQL Credentials
**File:** `shared_functions/global_functions.py:236-239`
```python
# CURRENT - EMPTY BUT INSECURE PATTERN
conn = pymysql.connect(host='', user='admin', password='', database='')
```

**Fix:**
```python
def get_mysql_connection():
    required = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"Missing MySQL env vars: {missing}")
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )
```

### 6. Add SQL Parameterization
**File:** `shared_functions/global_functions.py:247, 266`
```python
# CURRENT - SQL INJECTION VULNERABLE
cursor.execute(query)
```

**Fix:**
```python
def query_mysql(query: str, params: tuple = None):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    finally:
        conn.close()
```

### 7. Fix Platform-Specific Import
**File:** `shared_functions/global_functions.py:17`
```python
# CURRENT - CRASHES ON LINUX/MACOS
import win32com.client as win32
```

**Fix:**
```python
import sys
if sys.platform == 'win32':
    import win32com.client as win32
else:
    win32 = None
```

---

## Success Criteria

- [ ] No hardcoded credentials in codebase
- [ ] All secrets loaded from environment variables
- [ ] Startup fails if required secrets missing
- [ ] No demo authentication bypass in production
- [ ] All SQL/Cypher queries parameterized
- [ ] Error messages don't expose internals
- [ ] Code runs on all platforms (Windows/Mac/Linux)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed vulnerability | Medium | High | Security audit after fixes |
| Breaking changes | Low | Medium | Test all auth flows |
| Env var misconfiguration | Medium | High | Document required vars |

---

## Next Steps

After completing Phase 01, proceed to [Phase 02: Error Handling](phase-02-error-handling.md)
