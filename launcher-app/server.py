#!/usr/bin/env python3

#
# Copyright (C) 2026 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

import base64
import hashlib
import hmac
import json
import os
import re
import signal
import sys
import threading
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import ldap3
from ldap3.utils.conv import escape_filter_chars

DATA_DIR = os.environ.get("LAUNCHER_DATA_DIR", "/data")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
LISTEN_PORT = int(os.environ.get("LAUNCHER_PORT", "8080"))

AUTH_MODE = os.environ.get("AUTH_MODE", "public")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "").encode()
SESSION_COOKIE = "launcher_session"
SESSION_TTL = 8 * 3600
# "Keep me logged in": each visit pushes the expiry back by REMEMBER_TTL
REMEMBER_TTL = 7 * 24 * 3600
# A remembered session reads the account and its groups again from LDAP at
# most this often, so a locked account or a removed group takes effect soon.
RECHECK_INTERVAL = 3600

LDAP_HOST = os.environ.get("LDAP_HOST", "")
LDAP_PORT = int(os.environ.get("LDAP_PORT", "0") or 0)
LDAP_BIND_DN = os.environ.get("LDAP_USER", "")
LDAP_BIND_PASSWORD = os.environ.get("LDAP_PASS", "")
LDAP_BASE = os.environ.get("LDAP_BASE", "")
LDAP_SCHEMA = os.environ.get("LDAP_SCHEMA", "rfc2307")

# Brute force guard: after MAX_FAILURES failed logins from one IP inside
# FAILURE_WINDOW seconds, the login answers 429 until the window expires.
# Kept above the 5 POST 401 that CrowdSec http-generic-401-bf needs to ban,
# so a fast attack still reaches CrowdSec as 401 before it turns into 429.
MAX_FAILURES = 10
FAILURE_WINDOW = 900

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
}

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")

failures = {}
failures_lock = threading.Lock()


def log(message):
    print(message, file=sys.stderr, flush=True)


def read_json(name, default):
    try:
        with open(os.path.join(DATA_DIR, name)) as fp:
            return json.load(fp)
    except (OSError, ValueError):
        return default


def sign(payload):
    return hmac.new(SESSION_SECRET, payload, hashlib.sha256).hexdigest()


def make_session(user, display_name, groups, remember):
    now = int(time.time())
    payload = json.dumps({
        "u": user, "n": display_name, "g": groups, "r": remember, "c": now,
        "e": now + (REMEMBER_TTL if remember else SESSION_TTL),
    }).encode()
    data = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return data + "." + sign(data.encode())


def session_cookie(user, display_name, groups, remember):
    value = make_session(user, display_name, groups, remember)
    # Without "keep me logged in" the cookie dies with the browser, and the
    # server still refuses it after SESSION_TTL
    max_age = f"Max-Age={REMEMBER_TTL}; " if remember else ""
    return f"{SESSION_COOKIE}={value}; Path=/; {max_age}HttpOnly; Secure; SameSite=Lax"


def read_session(value):
    if not value or "." not in value or not SESSION_SECRET:
        return None
    data, signature = value.rsplit(".", 1)
    if not hmac.compare_digest(sign(data.encode()), signature):
        return None
    try:
        session = json.loads(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
    except ValueError:
        return None
    if session.get("e", 0) < time.time():
        return None
    return session


def too_many_failures(ip):
    now = time.time()
    with failures_lock:
        # Prune every address, or a spread out attack would grow the dict forever
        for key in list(failures):
            failures[key] = [t for t in failures[key] if now - t < FAILURE_WINDOW]
            if not failures[key]:
                del failures[key]
        return len(failures.get(ip, [])) >= MAX_FAILURES


def record_failure(ip):
    with failures_lock:
        failures.setdefault(ip, []).append(time.time())


def clear_failures(ip):
    with failures_lock:
        failures.pop(ip, None)


def ldap_connection(user=None, password=None):
    # No schema read and no referral chasing: on AD the first downloads megabytes
    # at each bind, the second waits on DNS zones the container cannot reach
    server = ldap3.Server(LDAP_HOST, port=LDAP_PORT, connect_timeout=5, get_info=ldap3.NONE)
    return ldap3.Connection(server, user=user, password=password, auto_bind=True,
                            raise_exceptions=True, receive_timeout=10, read_only=True,
                            auto_referrals=False)


def ldap_find_user(conn, username):
    """Return (dn, uid, display_name, group_filter, group_attribute), or None
    when the user does not exist or is locked."""
    if LDAP_SCHEMA == "ad":
        user_filter = f"(&(objectClass=user)(objectCategory=person)(sAMAccountName={escape_filter_chars(username)}))"
        attributes = ["sAMAccountName", "displayName", "userAccountControl"]
    else:
        user_filter = f"(&(objectClass=posixAccount)(objectClass=inetOrgPerson)(uid={escape_filter_chars(username)}))"
        attributes = ["uid", "displayName", "cn", "pwdAccountLockedTime"]
    conn.search(LDAP_BASE, user_filter, attributes=attributes)
    if len(conn.entries) != 1:
        return None
    entry = conn.entries[0]
    user_dn = entry.entry_dn
    if LDAP_SCHEMA == "ad":
        if int(entry.userAccountControl.value or 0) & 0x2:
            return None
        uid = str(entry.sAMAccountName.value)
        display_name = str(entry.displayName.value or uid)
        return user_dn, uid, display_name, f"(&(objectClass=group)(member={escape_filter_chars(user_dn)}))", "sAMAccountName"
    if entry.pwdAccountLockedTime.value:
        return None
    uid = str(entry.uid.value)
    display_name = str(entry.displayName.value or entry.cn.value or uid)
    return user_dn, uid, display_name, f"(&(objectClass=posixGroup)(memberUid={escape_filter_chars(uid)}))", "cn"


def ldap_groups(conn, group_filter, group_attribute):
    conn.search(LDAP_BASE, group_filter, attributes=[group_attribute])
    return sorted(str(e[group_attribute].value) for e in conn.entries)


def ldap_authenticate(username, password):
    """Return (user, display_name, groups) or None when the credentials are wrong."""
    username = username.strip()
    # An empty password would turn the user bind into an anonymous bind that succeeds
    if not username or not password or not LDAP_HOST:
        return None

    # One service connection for both lookups; groups are returned only after the password check
    with ldap_connection(LDAP_BIND_DN, LDAP_BIND_PASSWORD) as conn:
        found = ldap_find_user(conn, username)
        if not found:
            return None
        user_dn, uid, display_name, group_filter, group_attribute = found
        groups = ldap_groups(conn, group_filter, group_attribute)

    try:
        ldap_connection(user_dn, password).unbind()
    except (ldap3.core.exceptions.LDAPBindError, ldap3.core.exceptions.LDAPInvalidCredentialsResult):
        return None
    return uid, display_name, groups


def ldap_refresh(uid):
    """Read a logged in user again: (uid, display_name, groups), or None when
    the account is gone or locked."""
    with ldap_connection(LDAP_BIND_DN, LDAP_BIND_PASSWORD) as conn:
        found = ldap_find_user(conn, uid)
        if not found:
            return None
        user_dn, uid, display_name, group_filter, group_attribute = found
        return uid, display_name, ldap_groups(conn, group_filter, group_attribute)


def visible_apps(session):
    """Merge discovered apps, admin overrides and external links for the viewer."""
    discovered = read_json("apps.json", {}).get("apps", [])
    settings = read_json("settings.json", {})
    overrides = settings.get("apps", {})
    user_groups = set(session["g"]) if session else set()

    def allowed(groups):
        if AUTH_MODE != "ldap" or not groups:
            return True
        return bool(user_groups.intersection(groups))

    apps = []
    for app in discovered:
        override = overrides.get(app["id"], {})
        if override.get("hidden") or not allowed(override.get("groups", [])):
            continue
        apps.append({
            "name": override.get("name") or app["name"],
            "host": app["host"],
            "url": app["url"],
            "logo": app.get("logo", ""),
            "category": override.get("category", ""),
            "external": False,
        })
    for link in settings.get("links", []):
        if not allowed(link.get("groups", [])):
            continue
        apps.append({
            "name": link["name"],
            "host": re.sub(r"^https?://", "", link["url"]).split("/")[0],
            "url": link["url"],
            "logo": "",
            "category": link.get("category", ""),
            "external": True,
        })
    return {"categories": settings.get("categories", []), "apps": apps}


class Handler(BaseHTTPRequestHandler):
    server_version = "launcher"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def client_ip(self):
        # The port is bound to 127.0.0.1, so only Traefik reaches us: trust its headers
        real_ip = self.headers.get("X-Real-Ip", "").strip()
        if real_ip:
            return real_ip
        forwarded = self.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
        return self.client_address[0]

    def log_message(self, format, *args):
        pass

    def log_request(self, code="-", size="-"):
        duration = int((time.monotonic() - getattr(self, "started", time.monotonic())) * 1000)
        path = self.path.split("?", 1)[0]
        log(f'{self.client_ip()} "{self.command} {path}" {int(code)} {duration}ms')

    def send(self, status, body=b"", content_type="application/json; charset=utf-8", headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
        headers = dict(headers or {})
        if getattr(self, "renewed_cookie", None) and "Set-Cookie" not in headers:
            headers["Set-Cookie"] = self.renewed_cookie
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, status, payload, headers=None):
        self.send(status, json.dumps(payload).encode(), headers=headers)

    def send_file(self, path):
        content_type = STATIC_TYPES.get(os.path.splitext(path)[1])
        if not content_type or not os.path.isfile(path):
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        with open(path, "rb") as fp:
            self.send(HTTPStatus.OK, fp.read(), content_type)

    def session(self):
        """Return the valid session of the request, or None. A remembered
        session is checked against LDAP and renewed; the new cookie goes in
        self.renewed_cookie for the response."""
        self.renewed_cookie = None
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(SESSION_COOKIE)
        session = read_session(morsel.value if morsel else "")
        if not session or not session.get("r") or time.time() - session.get("c", 0) < RECHECK_INTERVAL:
            return session
        try:
            result = ldap_refresh(session["u"])
        except ldap3.core.exceptions.LDAPException as ex:
            # LDAP is down: keep the session as it is and try again next visit
            log(f"LDAP error: {ex}")
            return session
        if not result:
            log(f"session revoked user={session['u']!r} ip={self.client_ip()}")
            self.renewed_cookie = f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax"
            return None
        uid, display_name, groups = result
        self.renewed_cookie = session_cookie(uid, display_name, groups, True)
        return {"u": uid, "n": display_name, "g": groups, "r": True}

    def read_body(self):
        """Read the request body, or close the connection when it cannot be
        read whole: unread bytes would be parsed as the next request."""
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            length = -1
        if self.headers.get("Transfer-Encoding") or length < 0 or length > 4096:
            self.close_connection = True
            return None
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw)
        except ValueError:
            return None

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self.started = time.monotonic()
        self.renewed_cookie = None
        self.read_body()
        path = self.path.split("?", 1)[0]
        if path == "/":
            return self.send_file(os.path.join(STATIC_DIR, "index.html"))
        if path == "/api/config":
            return self.api_config()
        if path == "/api/apps":
            # A leftover cookie of the LDAP mode must not trigger LDAP lookups
            session = self.session() if AUTH_MODE == "ldap" else None
            if AUTH_MODE == "ldap" and not session:
                return self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "login_required"})
            return self.send_json(HTTPStatus.OK, visible_apps(session))
        if path == "/brand/logo":
            for name in ("logo.png", "logo.jpg"):
                custom = os.path.join(DATA_DIR, "brand", name)
                if os.path.isfile(custom):
                    return self.send_file(custom)
            return self.send_file(os.path.join(STATIC_DIR, "ns8-logo.png"))
        match = re.match(r"^/(static|i18n|logos)/([^/]+)$", path)
        if match and SAFE_NAME.match(match.group(2)):
            folder = {
                "static": STATIC_DIR,
                "i18n": os.path.join(STATIC_DIR, "i18n"),
                "logos": os.path.join(DATA_DIR, "logos"),
            }[match.group(1)]
            return self.send_file(os.path.join(folder, match.group(2)))
        return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):
        self.started = time.monotonic()
        self.renewed_cookie = None
        # Read it before any early answer, so the connection stays in sync
        body = self.read_body()
        path = self.path.split("?", 1)[0]
        if path == "/api/login":
            return self.api_login(body)
        if path == "/api/logout":
            return self.send(HTTPStatus.NO_CONTENT, headers={
                "Set-Cookie": f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax"})
        return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def api_config(self):
        settings = read_json("settings.json", {})
        session = self.session() if AUTH_MODE == "ldap" else None
        self.send_json(HTTPStatus.OK, {
            "auth_mode": AUTH_MODE,
            "welcome": settings.get("welcome", ""),
            "support": settings.get("support", {}),
            "user": {"name": session["u"], "display_name": session["n"]} if session else None,
        })

    def api_login(self, body):
        if AUTH_MODE != "ldap":
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        ip = self.client_ip()
        if too_many_failures(ip):
            log(f"login blocked ip={ip}")
            return self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too_many_attempts"},
                                  headers={"Retry-After": str(FAILURE_WINDOW)})
        if not isinstance(body, dict) or not isinstance(body.get("username"), str) \
                or not isinstance(body.get("password"), str):
            return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "bad_request"})
        username = body["username"][:256]
        remember = body.get("remember") is True
        try:
            result = ldap_authenticate(username, body["password"])
        except ldap3.core.exceptions.LDAPException as ex:
            log(f"LDAP error: {ex}")
            return self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "ldap_unavailable"})
        if not result:
            record_failure(ip)
            log(f"login failed user={username!r} ip={ip}")
            return self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "invalid_credentials"})
        clear_failures(ip)
        uid, display_name, groups = result
        log(f"login ok user={uid!r} ip={ip} remember={remember}")
        self.send_json(HTTPStatus.OK, {"name": uid, "display_name": display_name},
                       headers={"Set-Cookie": session_cookie(uid, display_name, groups, remember)})


if __name__ == "__main__":
    if AUTH_MODE == "ldap" and not SESSION_SECRET:
        log("SESSION_SECRET is missing: LDAP mode cannot start")
        sys.exit(1)
    # As PID 1 in the container, Python would otherwise ignore the SIGTERM of podman stop
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    log(f"launcher listening on port {LISTEN_PORT}, auth mode {AUTH_MODE}")
    ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Handler).serve_forever()
