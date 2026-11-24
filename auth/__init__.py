"""Accounts: email + password login, signed-cookie sessions, CSRF, invite and reset tokens.

repository.py owns the SQL, service.py the rules (password length, rate limit, token expiry),
session.py the Flask session and the request guards. api/auth.py is the HTTP layer.
"""
