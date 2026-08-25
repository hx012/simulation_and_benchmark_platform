"""One-shot, manual W3 OAuth2 callback verification.

This is an integration probe, not platform authentication code. It deliberately
does not write W3 tokens, authorization codes, or user information to disk.

Run it on the server that receives the public callback, after its reverse proxy
has mapped the callback path to this script's listening port. It requires a
test W3 application and a test account. The W3 application must use PKCE and
the client_secret_post token authentication mode. Never use production
credentials while the registered redirect URI uses HTTP.

Example (Linux deployment host):
    export W3_OAUTH_CLIENT_ID='...'
    export W3_OAUTH_CLIENT_SECRET='...'
    export W3_OAUTH_REDIRECT_URI='http://mskpp-aibench.hicomputing.huawei.com/api/auth/w3/callback'
    python backend/scripts/test_w3_oauth_callback.py --listen-port 18000

The script prints an authorization URL. Open it in a browser, complete W3
login, then inspect only the final success/failure message printed by this
script. Do not copy the callback URL or its `code` parameter into chat.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


DEFAULT_AUTHORIZE_URL = "https://uniportal.huawei.com/saaslogin1/oauth2/authorize"
DEFAULT_ACCESS_TOKEN_URL = "https://uniportal.huawei.com/saaslogin1/oauth2/accesstoken"
DEFAULT_USERINFO_URL = "https://uniportal.huawei.com/saaslogin1/oauth2/userinfo"
DEFAULT_SCOPE = "base.profile"


@dataclass
class CallbackResult:
    code: str | None = None
    error: str | None = None
    error_description: str | None = None


def base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def request_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - W3 URL is operator configured.
            body = response.read().decode("utf-8")
    except HTTPError as error:
        raise RuntimeError(f"W3 returned HTTP {error.code}; token details were not logged.") from error
    except URLError as error:
        raise RuntimeError(f"Unable to reach W3: {error.reason}") from error

    try:
        value = json.loads(body)
    except json.JSONDecodeError as error:
        raise RuntimeError("W3 returned a non-JSON response; response body was not logged.") from error
    if not isinstance(value, dict):
        raise RuntimeError("W3 returned an unexpected JSON response shape.")
    return value


def make_handler(expected_path: str, expected_state: str, result: CallbackResult):
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - HTTP handler API name.
            parsed = urlparse(self.path)
            if parsed.path != expected_path:
                self.send_error(404, "Unexpected callback path")
                return
            values = parse_qs(parsed.query)
            received_state = values.get("state", [""])[0]
            if not received_state or not secrets.compare_digest(received_state, expected_state):
                result.error = "OAuth state validation failed"
                self._respond(400, "W3 callback rejected: invalid state. You may close this page.")
                return
            if values.get("error"):
                result.error = values["error"][0]
                result.error_description = values.get("error_description", [""])[0]
                self._respond(400, "W3 authorization was not completed. You may close this page.")
                return
            result.code = values.get("code", [""])[0] or None
            if result.code is None:
                result.error = "Callback did not contain an authorization code"
                self._respond(400, "W3 callback did not contain a code. You may close this page.")
                return
            self._respond(200, "W3 callback received. Return to the terminal for verification results.")

        def _respond(self, status: int, message: str) -> None:
            encoded = message.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            # Callback URLs contain an authorization code. Never write request lines to logs.
            return

    return CallbackHandler


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify W3 OAuth2 callback, PKCE, and required user identity fields."
    )
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=18000)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--authorize-url", default=os.environ.get("W3_OAUTH_AUTHORIZE_URL", DEFAULT_AUTHORIZE_URL))
    parser.add_argument("--token-url", default=os.environ.get("W3_OAUTH_TOKEN_URL", DEFAULT_ACCESS_TOKEN_URL))
    parser.add_argument("--userinfo-url", default=os.environ.get("W3_OAUTH_USERINFO_URL", DEFAULT_USERINFO_URL))
    parser.add_argument("--scope", default=os.environ.get("W3_OAUTH_SCOPE", DEFAULT_SCOPE))
    parser.add_argument(
        "--show-userinfo-fields",
        action="store_true",
        help="Print selected test user's identity fields to this terminal. Do not use in shared terminals or CI logs.",
    )
    args = parser.parse_args()

    client_id = env("W3_OAUTH_CLIENT_ID")
    client_secret = env("W3_OAUTH_CLIENT_SECRET")
    redirect_uri = env("W3_OAUTH_REDIRECT_URI")
    redirect = urlparse(redirect_uri)
    if redirect.scheme not in {"http", "https"} or not redirect.netloc or not redirect.path:
        raise SystemExit("W3_OAUTH_REDIRECT_URI must be an absolute callback URL with a path.")

    state = secrets.token_urlsafe(32)
    code_verifier = base64url(secrets.token_bytes(64))
    code_challenge = base64url(hashlib.sha256(code_verifier.encode("ascii")).digest())
    authorization_params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': args.scope,
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    authorization_url = f"{args.authorize_url}?{urlencode(authorization_params)}"

    result = CallbackResult()
    server = ThreadingHTTPServer(
        (args.listen_host, args.listen_port),
        make_handler(redirect.path, state, result),
    )
    server.timeout = 1
    print("W3 OAuth2 callback probe is listening.")
    print(f"Local listener: http://{args.listen_host}:{args.listen_port}{redirect.path}")
    print("Ensure the public domain's reverse proxy routes that callback path to this listener.")
    print("\nOpen this authorization URL in a browser:\n")
    print(authorization_url)
    print(f"\nWaiting up to {args.timeout_seconds} seconds. Authorization codes and tokens will not be printed.")

    deadline = time.monotonic() + args.timeout_seconds
    while time.monotonic() < deadline and not (result.code or result.error):
        server.handle_request()
    server.server_close()

    if result.error:
        print(f"FAILED: W3 callback was received but rejected: {result.error}")
        return 1
    if not result.code:
        print("FAILED: No callback reached the listener before timeout.")
        return 1

    try:
        token = request_json(args.token_url, {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code": result.code,
            "code_verifier": code_verifier,
        }, {})
        access_token = token.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError("Token response did not contain access_token.")
        userinfo = request_json(args.userinfo_url, {
            "client_id": client_id,
            "access_token": access_token,
            "scope": args.scope,
        }, {})
    except RuntimeError as error:
        print(f"FAILED: {error}")
        return 1
    finally:
        # Do not intentionally retain credentials after the one-shot probe completes.
        code_verifier = ""
        result.code = None

    required_fields = ("globalUserID", "uid", "displayName")
    missing_fields = [
        field for field in required_fields
        if not isinstance(userinfo.get(field), str) or not userinfo[field].strip()
    ]
    if missing_fields:
        print(
            "FAILED: UserInfo succeeded but did not include non-empty required fields: "
            + ", ".join(missing_fields)
        )
        return 1

    print("SUCCESS: callback, PKCE token exchange, and UserInfo all completed.")
    print("SUCCESS: UserInfo includes non-empty globalUserID, uid, and displayName.")
    print(f"INFO: tenantId returned: {'yes' if userinfo.get('tenantId') else 'no'}")
    print(f"INFO: uuid returned: {'yes' if userinfo.get('uuid') else 'no'}")
    print(f"INFO: employeeNumber returned: {'yes' if userinfo.get('employeeNumber') else 'no'}")
    if args.show_userinfo_fields:
        print("WARNING: printing selected test-user fields to this terminal only; do not copy them to logs or chat.")
        for field in ("tenantId", "uuid", "globalUserID", "uid", "displayName", "employeeNumber"):
            value = userinfo.get(field)
            print(f"USERINFO {field}: {value if value is not None else '<not returned>'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
