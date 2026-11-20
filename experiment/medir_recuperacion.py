import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
import urllib.request

COLORS = ["\033[92m", "\033[96m", "\033[93m", "\033[95m", "\033[94m"]
RESET = "\033[0m"


def http_get_json(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode())


def wait_healthy(url: str, deadline_seconds: float = 60.0) -> None:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        try:
            http_get_json(url, timeout=2.0)
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"{url} no respondio en {deadline_seconds}s")


def docker_compose(args: list[str], compose_dir: str, files: list[str]) -> None:
    cmd = ["docker", "compose"]
    for f in files:
        cmd += ["-f", f]
    cmd += args
    subprocess.run(cmd, cwd=compose_dir, check=True)


def send_messages(sender_url: str, user: str, count: int, rate: float, prefix: str) -> list[str]:
    ids = []
    for i in range(count):
        body = f"{prefix} msg {i}"
        req = urllib.request.Request(
            f"{sender_url}/messages",
            data=json.dumps({"from": user, "body": body}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5.0) as response:
            ids.append(json.loads(response.read().decode())["id"])
        if rate > 0:
            time.sleep(1.0 / rate)
    return ids


def target_has_all(target_url: str, ids: list[str]) -> bool:
    known = {m["id"] for m in http_get_json(f"{target_url}/messages")["messages"]}
    return all(i in known for i in ids)


def run_repetition(rep: int, args) -> dict:
    prefix = f"rep{rep}"
    print(f"\n=== Repeticion {rep} ===")

    wait_healthy(f"{args.target_url}/status")
    wait_healthy(f"{args.sender_url}/status")

    print(f"apagando {args.target} ...")
    docker_compose(["stop", args.target], args.compose_dir, args.compose_file)
    time.sleep(args.outage)

    print(f"enviando {args.count} mensajes a {args.rate:.2f} msg/s desde {args.sender} ...")
    ids = send_messages(args.sender_url, args.sender_user, args.count, args.rate, prefix)

    print(f"levantando {args.target} ...")
    docker_compose(["up", "-d", args.target], args.compose_dir, args.compose_file)

    start = time.time()
    deadline = start + args.timeout
    recovered_at = None
    while time.time() < deadline:
        try:
            if target_has_all(args.target_url, ids):
                recovered_at = time.time()
                break
        except (OSError, ValueError):
            pass  # el servidor aun esta arrancando
        time.sleep(0.2)

    if recovered_at is None:
        elapsed = None
        print(f"rep {rep}: TIMEOUT despues de {args.timeout}s")
    else:
        elapsed = recovered_at - start
        print(f"rep {rep}: recuperado en {elapsed:.2f}s ({len(ids)} mensajes)")

    return {
        "repeticion": rep,
        "mensajes": len(ids),
        "caida_s": args.outage,
        "tasa_msg_s": args.rate,
        "recuperacion_s": round(elapsed, 3) if elapsed is not None else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experimento: tiempo de recuperacion tras reiniciar el servidor del grupo"
    )
    parser.add_argument("--compose-dir", default=".")
    parser.add_argument("--compose-file", action="append", default=["docker-compose.yml"],
                        help="archivo compose (repetible)")
    parser.add_argument("--target", default="server", help="servicio compose que se apaga y levanta")
    parser.add_argument("--target-url", default="http://localhost:8000")
    parser.add_argument("--sender", default="server-b", help="servicio compose que envia durante la caida")
    parser.add_argument("--sender-url", default="http://localhost:8001")
    parser.add_argument("--sender-user", default="bob")
    parser.add_argument("--count", type=int, default=20, help="mensajes enviados durante la caida")
    parser.add_argument("--rate", type=float, default=5.0, help="mensajes por segundo durante la caida")
    parser.add_argument("--outage", type=float, default=10.0, help="segundos con el servidor apagado")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120.0, help="espera maxima de recuperacion por repeticion")
    parser.add_argument("--out", default="experiment/datos/resultados.csv")
    args = parser.parse_args()

    sender_full = f"{args.sender_user}@{args.sender}"

    rows = []
    for rep in range(1, args.repeats + 1):
        try:
            rows.append(run_repetition(rep, args))
        except (subprocess.CalledProcessError, RuntimeError) as error:
            print(f"rep {rep}: fallo ({error})", file=sys.stderr)
            rows.append({
                "repeticion": rep,
                "mensajes": args.count,
                "caida_s": args.outage,
                "tasa_msg_s": args.rate,
                "recuperacion_s": "ERROR",
            })

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["repeticion", "mensajes", "caida_s", "tasa_msg_s", "recuperacion_s"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nresultados escritos en {args.out}")

    times = [r["recuperacion_s"] for r in rows if isinstance(r["recuperacion_s"], float)]
    if times:
        print("\nResumen (tiempo de recuperacion, segundos):")
        print(f"  n={len(times)}  min={min(times):.2f}  media={statistics.mean(times):.2f}  "
              f"max={max(times):.2f}  desv={statistics.stdev(times):.2f}" if len(times) > 1 else
              f"  n={len(times)}  min={min(times):.2f}  media={statistics.mean(times):.2f}  max={max(times):.2f}")


if __name__ == "__main__":
    main()
