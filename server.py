"""Shop backend: serves index.html and proxies BotBonnie reads to ets-agent MCP.

The browser cannot talk to the MCP server directly (MCP session protocol, no
CORS, and it would expose AWS-backed tools to anyone who opens the page), so
this process is the MCP *client*. It only calls read-only DynamoDB tools on the
`botbonnie` AWS connection and redacts token-like fields before they reach the
browser.

Usage:
    uv run python server.py            # http://127.0.0.1:3000

Env:
    ETS_AGENT_MCP_URL  ets-agent MCP endpoint (default http://localhost:8000/mcp)
    SHOP_HOST/SHOP_PORT  bind address (default 127.0.0.1:3000 — keep it local)
"""
import json
import os
import re
from pathlib import Path

import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

MCP_URL = os.getenv("ETS_AGENT_MCP_URL", "http://localhost:8000/mcp")
CONNECTION = "botbonnie"
BOT_TABLE = "bot"
ROOT = Path(__file__).resolve().parent

_BOT_ID = re.compile(r"^bot-[A-Za-z0-9_-]{1,64}$")
_SECRET_KEY = re.compile(r"token|secret|password|passwd|api_?key|credential|access_?key|private", re.I)

# Key schema of the bot table, looked up once via describe_table.
_bot_keys: dict | None = None


async def call_tool(name: str, args: dict) -> dict:
    """Call one ets-agent MCP tool and return its JSON result as a dict."""
    async with streamable_http_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, {**args, "connection": CONNECTION})
    if result.isError:
        text = " ".join(c.text for c in result.content if getattr(c, "text", None))
        return {"error": text or f"{name} failed"}
    if isinstance(result.structuredContent, dict):
        data = result.structuredContent
        # FastMCP wraps non-object returns as {"result": ...}
        return data["result"] if set(data) == {"result"} and isinstance(data["result"], dict) else data
    text = next((c.text for c in result.content if getattr(c, "text", None)), "{}")
    return json.loads(text)


def redact(value):
    """Mask values under token/secret-looking keys, recursively."""
    if isinstance(value, dict):
        return {k: ("***" if _SECRET_KEY.search(k) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


async def bot_keys() -> dict:
    global _bot_keys
    if _bot_keys is None:
        info = await call_tool("describe_table", {"table_name": BOT_TABLE})
        if "error" in info:
            raise RuntimeError(info["error"])
        _bot_keys = info.get("key_schema") or {}
    return _bot_keys


async def health(request):
    try:
        info = await call_tool("check_dynamodb_auth", {})
    except Exception as e:  # MCP server down / unreachable
        return JSONResponse({"ok": False, "error": f"Cannot reach ets-agent MCP at {MCP_URL}: {e}"}, 502)
    if "error" in info:
        return JSONResponse({"ok": False, "error": info["error"]}, 502)
    return JSONResponse({"ok": True, "connection": info.get("connection"), "account_id": info.get("account_id")})


async def get_bot(request):
    bot_id = request.path_params["bot_id"].strip()
    if not _BOT_ID.match(bot_id):
        return JSONResponse({"error": "Bot ID 格式應為 bot-xxxxxxxx"}, 400)
    try:
        keys = await bot_keys()
        hash_key, range_key = keys.get("HASH"), keys.get("RANGE")
        if not hash_key:
            return JSONResponse({"error": f"Table {BOT_TABLE!r} has no partition key"}, 502)
        if range_key:
            # Versioned table (e.g. botVersion PROD / LATEST / snapshots): read the partition.
            res = await call_tool("query_table", {
                "table_name": BOT_TABLE,
                "key_condition_expression": "#pk = :b",
                "expression_attribute_names": {"#pk": hash_key},
                "expression_attribute_values": {":b": bot_id},
                "limit": 50,
            })
            items = res.get("items") or []
        else:
            res = await call_tool("get_item", {"table_name": BOT_TABLE, "key": {hash_key: bot_id}})
            items = [res["item"]] if res.get("item") else []
    except RuntimeError as e:  # tool-level error, e.g. AWS creds / AssumeRole
        return JSONResponse({"error": str(e)}, 502)
    except Exception as e:
        return JSONResponse({"error": f"Cannot reach ets-agent MCP at {MCP_URL}: {e}"}, 502)
    if "error" in res:
        return JSONResponse({"error": res["error"]}, 502)
    if not items:
        return JSONResponse({"error": f"找不到 {bot_id}"}, 404)

    # Prefer the deployed PROD version when the table is versioned.
    primary = next((i for i in items if i.get(range_key) == "PROD"), items[0]) if range_key else items[0]
    return JSONResponse({
        "bot_id": bot_id,
        "key_schema": keys,
        "versions": [i.get(range_key) for i in items] if range_key else [],
        "item": redact(primary),
    })


async def index(request):
    return FileResponse(ROOT / "index.html")


app = Starlette(routes=[
    Route("/", index),
    Route("/api/botbonnie/health", health),
    Route("/api/botbonnie/bots/{bot_id}", get_bot),
])

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("SHOP_HOST", "127.0.0.1"), port=int(os.getenv("SHOP_PORT", "3000")))
