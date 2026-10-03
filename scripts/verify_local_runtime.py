"""Launch and stop owned local processes; verify API/UI and official MCP client."""
import asyncio
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

async def protocol(token: str, result: dict) -> None:
    async with httpx.AsyncClient(headers={"Authorization": "Bearer " + token}) as client:
        async with streamable_http_client("http://127.0.0.1:8001/mcp", http_client=client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert len(tools.tools) == 4
                for name, arguments in (("get_evidence_ledger", {"applicant_id": result["applicant_id"]}),
                    ("get_assessment_snapshot", {"assessment_id": result["assessment_id"]}),
                    ("get_explanation_factors", {"assessment_id": result["assessment_id"]})):
                    output = await session.call_tool(name, arguments)
                    assert not output.isError

def main() -> int:
    processes = []
    for port in (8000, 8501, 8001):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                print("FAIL: required local runtime port already in use")
                return 1
    Path(".pytest_temp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=".pytest_temp") as temporary:
        root = Path(temporary).resolve()
        if not root.is_relative_to(Path(".pytest_temp").resolve()):
            raise RuntimeError("runtime workspace escaped its configured root")
        token = str(uuid4())
        env = os.environ | {"AGROGAMI_DATABASE_URL": "sqlite:///" + (root / "runtime.db").as_posix(),
            "AGROGAMI_PRIVATE_DATA_DIR": str(root / "private"), "AGROGAMI_DEMO_TOKENS": json.dumps({token: "reviewer"}),
            "AGROGAMI_MCP_ENABLED": "true", "AGROGAMI_MCP_AUTH_TOKEN": token,
            "AGROGAMI_MCP_HOST": "127.0.0.1", "AGROGAMI_MCP_PORT": "8001"}
        commands = [
            [sys.executable, "-m", "uvicorn", "agrogami.api.app:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"],
            [sys.executable, "-m", "streamlit", "run", "src/agrogami/ui/app.py", "--server.address=127.0.0.1", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"],
            [sys.executable, "-m", "agrogami.mcp.server"]]
        try:
            for command in commands:
                processes.append(subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
            for url in ("http://127.0.0.1:8000/ready", "http://127.0.0.1:8501/_stcore/health"):
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
            with urlopen("http://127.0.0.1:8000/docs", timeout=5) as response:
                assert b"Research Prototype" in response.read()
            result = run(APIClient("http://127.0.0.1:8000", token))
            asyncio.run(protocol(token, result))
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
