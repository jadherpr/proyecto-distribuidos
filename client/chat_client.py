import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

COLORS = {
    "g1": "\033[36m",
    "g2": "\033[32m",
    "g3": "\033[33m",
    "g4": "\033[35m",
    "g5": "\033[34m",
}
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

print_lock = threading.Lock()


def request(method: str, url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        body = error.read().decode()
        print(f"error HTTP {error.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as error:
        print(f"no se pudo conectar con {url}: {error.reason}", file=sys.stderr)
        sys.exit(1)


def color_for(origin: str, own_origin: str) -> str:
    if origin == own_origin:
        return COLORS.get(origin, "\033[36m")
    return COLORS.get(origin, "\033[90m")


def prompt_line(full_user: str) -> str:
    return f"{BOLD}{full_user}>{RESET} "


def render(message: dict, own_origin: str, seen: set[str], full_user: str) -> bool:
    message_id = message.get("id")
    sender = message.get("from", message.get("from_user", "?"))
    origin = message.get("origin", "?")
    lamport = message.get("lamport", "?")
    body = message.get("body", "")
    if message_id is None or message_id in seen:
        return False
    seen.add(message_id)
    with print_lock:
        print()
        color = color_for(origin, own_origin)
        tag = "" if origin == own_origin else " [otro grupo]"
        print(f"{color}{BOLD}{sender}{tag}{RESET} {DIM}(L{lamport}){RESET}: {body}")
        sys.stdout.write(prompt_line(full_user))
        sys.stdout.flush()
    return True


class Poller(threading.Thread):
    def __init__(self, base: str, own_origin: str, seen: set[str], full_user: str, interval: float):
        super().__init__(daemon=True)
        self.base = base
        self.own_origin = own_origin
        self.seen = seen
        self.full_user = full_user
        self.interval = interval
        self.stop_event = threading.Event()

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                fresh = request("GET", f"{self.base}/messages")["messages"]
                for message in fresh:
                    render(message, self.own_origin, self.seen, self.full_user)
            except SystemExit:
                self.stop_event.set()
                return
            except Exception:
                pass
            time.sleep(self.interval)


def main() -> None:
    os.system("")

    parser = argparse.ArgumentParser(description="Cliente de chat del grupo")
    parser.add_argument("--server", required=True, help="URL del servidor del grupo, ej http://localhost:8000")
    parser.add_argument("--user", required=True, help="nombre local del usuario, ej ana")
    parser.add_argument("--poll", type=float, default=1.5, help="segundos entre consultas de mensajes")
    args = parser.parse_args()

    base = args.server.rstrip("/")

    status = request("GET", f"{base}/status")
    own_origin = status["server"]

    full_user = f"{args.user}@{own_origin}"
    users = request("GET", f"{base}/users")["users"]
    if full_user not in users:
        request("POST", f"{base}/users", {"name": args.user})
        print(f"usuario creado: {full_user}")
    else:
        print(f"usuario existente: {full_user}")

    seen: set[str] = set()
    history = request("GET", f"{base}/messages")["messages"]
    for message in history:
        render(message, own_origin, seen, full_user)

    poller = Poller(base, own_origin, seen, full_user, args.poll)
    poller.start()
    sys.stdout.write(prompt_line(full_user))
    sys.stdout.flush()

    while True:
        try:
            body = input()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        body = body.strip()
        if body == "/salir":
            break
        elif body:
            request("POST", f"{base}/messages", {"from": full_user, "body": body})
            sys.stdout.write(prompt_line(full_user))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
