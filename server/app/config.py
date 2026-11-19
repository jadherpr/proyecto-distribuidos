import os

GROUP_NAME = os.environ.get("GROUP_NAME", "g2")
PUBLIC_URL = os.environ.get("PUBLIC_URL", f"http://localhost:{os.environ.get('PORT', '8000')}")
CENTRAL_URL = os.environ.get("CENTRAL_URL", "http://localhost:9000")

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
DB_PATH = os.environ.get("DB_PATH", "/data/chat.db")

REGISTER_INTERVAL = float(os.environ.get("REGISTER_INTERVAL", "30"))
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL", "5"))
HEARTBEAT_MAX_FAILS = int(os.environ.get("HEARTBEAT_MAX_FAILS", "3"))

RETRY_BASE_SECONDS = float(os.environ.get("RETRY_BASE_SECONDS", "0.5"))
RETRY_MAX_SECONDS = float(os.environ.get("RETRY_MAX_SECONDS", "30"))

REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "5"))
