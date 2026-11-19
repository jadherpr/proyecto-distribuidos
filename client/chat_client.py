import argparse
import json
import sys
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


def render(message: dict, own_origin: str, seen: set[str]) -> bool:
    message_id = message.get("id")
    sender = message.get("from", message.get("from_user", "?"))
    origin = message.get("origin", "?")
    lamport = message.get("lamport", "?")
    body = message.get("body", "")
    if message_id is None or message_id in seen:
        return False
    seen.add(message_id)
    color = color_for(origin, own_origin)
    tag = "" if origin == own_origin else " [otro grupo]"
    print(f"{color}{BOLD}{sender}{tag}{RESET} {DIM}(L{lamport}){RESET}: {body}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Cliente de chat del grupo")
    parser.add_argument("--server", required=True, help="URL del servidor del grupo, ej http://localhost:8000")
    parser.add_argument("--user", required=True, help="nombre local del usuario, ej ana")
    parser.add_argument("--poll", type=float, default=2.0, help="segundos entre consultas de mensajes")
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
        render(message, own_origin, seen)
    print(f"--- conectado a {base} como {full_user}; escribe y presiona Enter ---")

    while True:
        try:
            body = input(f"{BOLD}{full_user}>{RESET} ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        body = body.strip()
        if not body:
            time.sleep(0.1)
        elif body == "/salir":
            break
        else:
            request("POST", f"{base}/messages", {"from": full_user, "body": body})
        try:
            fresh = request("GET", f"{base}/messages")["messages"]
        except SystemExit:
            break
        for message in fresh:
            render(message, own_origin, seen)
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
