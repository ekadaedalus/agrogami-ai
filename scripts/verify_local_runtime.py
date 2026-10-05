"""Launch and stop owned local processes; verify API/UI and official MCP client."""
import asyncio
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from uuid import uuid4
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from agrogami.ui.api_client import APIClient
from scripts.smoke_test import run

REPOSITORY = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify isolated synthetic API/UI/Prism runtimes")
    for name, default in (("api", 8000), ("ui", 8501), ("mcp", 8001)):
        parser.add_argument(f"--{name}-port", type=int, default=default,
                            help="Local port; use 0 for an available operating-system-assigned port")
    return parser.parse_args(argv)


def select_ports(requested: tuple[int, int, int]) -> tuple[int, int, int]:
    """Validate/bind together so ephemeral choices are distinct and occupied ports fail."""
    if len(requested) != 3 or any(not 0 <= port <= 65535 for port in requested):
        raise ValueError("runtime port must be between 0 and 65535")
    selected = []
    with ExitStack() as sockets:
        for port in requested:
            sock = sockets.enter_context(socket.socket())
            if os.name == "nt":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                raise ValueError("runtime port is unavailable") from None
            selected.append(sock.getsockname()[1])
    # Another process can race after these reservations close; startup checks
    # below still fail if any owned process cannot bind its selected port.
    return selected[0], selected[1], selected[2]


def runtime_environment(root: Path, token: str, ports: tuple[int, int, int]) -> dict[str, str]:
    """Do not inherit database, credential, grant or model settings from the caller."""
    env = {name: value for name, value in os.environ.items()
           if not name.upper().startswith("AGROGAMI_") and name.upper() != "DATABASE_URL"}
    api_port, _, mcp_port = ports
    return env | {"AGROGAMI_ENV": "development", "AGROGAMI_DEMO_MODE": "true",
        "AGROGAMI_LOCAL_DEMO_MODE": "true", "AGROGAMI_ENABLE_REAL_MODELS": "false",
        "AGROGAMI_DATABASE_URL": "sqlite:///" + (root / "runtime.db").as_posix(),
        "AGROGAMI_PRIVATE_DATA_DIR": str(root / "private"),
        "AGROGAMI_MODEL_CACHE_DIR": str(root / "model_cache"),
        "AGROGAMI_DOCS_DIR": str(REPOSITORY / "docs"),
        "AGROGAMI_API_URL": f"http://127.0.0.1:{api_port}",
        "AGROGAMI_PUBLIC_API_URL": f"http://127.0.0.1:{api_port}",
        "AGROGAMI_DEMO_TOKENS": json.dumps({token: "reviewer"}),
        "AGROGAMI_APPLICANT_GRANTS": "{}",
        "AGROGAMI_MCP_ENABLED": "true", "AGROGAMI_MCP_AUTH_TOKEN": token,
        "AGROGAMI_MCP_HOST": "127.0.0.1", "AGROGAMI_MCP_PORT": str(mcp_port)}


async def protocol(token: str, result: dict, mcp_port: int = 8001) -> None:
    async with httpx.AsyncClient(headers={"Authorization": "Bearer " + token}) as client:
        async with streamable_http_client(f"http://127.0.0.1:{mcp_port}/mcp", http_client=client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert len(tools.tools) == 4
                for name, arguments in (("get_evidence_ledger", {"applicant_id": result["applicant_id"]}),
                    ("get_assessment_snapshot", {"assessment_id": result["assessment_id"]}),
                    ("get_explanation_factors", {"assessment_id": result["assessment_id"]})):
                    output = await session.call_tool(name, arguments)
                    assert not output.isError

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    processes = []
    try:
        api_port, ui_port, mcp_port = select_ports((args.api_port, args.ui_port, args.mcp_port))
    except ValueError:
        print("FAIL: requested local runtime port unavailable or invalid")
        return 1
    workspace = REPOSITORY / ".pytest_temp"
    workspace.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="runtime-", dir=workspace) as temporary:
        root = Path(temporary).resolve()
        if not root.is_relative_to(workspace.resolve()):
            raise RuntimeError("runtime workspace escaped its configured root")
        token = str(uuid4())
        env = runtime_environment(root, token, (api_port, ui_port, mcp_port))
        api_url = f"http://127.0.0.1:{api_port}"
        commands = [
            [sys.executable, "-m", "uvicorn", "agrogami.api.app:app", "--host", "127.0.0.1", "--port", str(api_port), "--no-access-log"],
            [sys.executable, "-m", "streamlit", "run", str(REPOSITORY / "src/agrogami/ui/app.py"), "--server.address=127.0.0.1", f"--server.port={ui_port}", "--server.headless=true", "--browser.gatherUsageStats=false"],
            [sys.executable, "-m", "agrogami.mcp.server"]]
        try:
            for command in commands:
                # The fresh cwd has no .env, so Settings cannot load private
                # repository settings after the environment has been scrubbed.
                processes.append(subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
            for url in (api_url + "/ready", f"http://127.0.0.1:{ui_port}/_stcore/health"):
                for attempt in range(60):
                    if any(process.poll() is not None for process in processes):
                        raise RuntimeError("process terminated")
                    try:
                        with urlopen(url, timeout=1) as response:
                            assert response.status == 200
                        break
                    except OSError:
                        time.sleep(.25)
                else:
                    raise RuntimeError("startup timeout")
            with urlopen(api_url + "/docs", timeout=5) as response:
                documentation = response.read()
                assert b"<h1>Agrogami AI</h1>" in documentation
                assert b"Traceable underwriting from financial records traditional credit systems ignore" in documentation
                assert b"Demo environment" in documentation
            result = run(APIClient(api_url, token))
            asyncio.run(protocol(token, result, mcp_port))
            return 0
        except Exception:
            print("FAIL: live runtime verification; no success claimed")
            return 1
        finally:
            for process in processes:
                if process.poll() is None:
                    if os.name == "nt":
                        # Windows venv launchers can own a child interpreter. Stop only this owned tree.
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            # Windows child-process handles can close just after the launcher wait completes.
            for attempt in range(20):
                try:
                    for database in root.glob("*.db"):
                        with database.open("ab"):
                            pass
                    break
                except PermissionError:
                    time.sleep(.25)

if __name__ == "__main__":
    result = main()
    if result == 0:
        print("PASS: API, Streamlit, Prism launched; live flow and official SDK reads verified; owned processes stopped and temporary storage cleaned")
    raise SystemExit(result)
