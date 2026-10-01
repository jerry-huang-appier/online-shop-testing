# online-shop-testing
static online shop platform for testing

Live: https://jerry-huang-appier.github.io/online-shop-testing/

## Integrations

- **AIQUA Web SDK** (app_id `6b4ce1e5264939e30dc6`) — web push + custom events
  (`product_added_to_cart`, `checkout_started`, `product_purchased`, `checkout_completed` with order total as `valueToSum`)
  and `identify` (`email` / `phoneNo` / `name`) on checkout. The service worker lives at the domain root in the
  `jerry-huang-appier.github.io` repo.
- **BotBonnie WebChat** (page `page-9042991d719141bab5ab7292`, bot `bot-hp_5XJSQ3`) — chat launcher on every page.

## BotBonnie bot lookup API（本機，透過 ets-agent MCP）

頁面上的查詢區塊已移除，但 `server.py` 仍提供唯讀 API，用 Bot ID 查 BotBonnie 的 `bot` 設定：
`server.py`（MCP client）→ ets-agent MCP（`describe_table` / `query_table` / `get_item`，`connection=botbonnie`）→ AWS DynamoDB。
token / secret 類欄位會被遮蔽。

1. 在 `ets-agent-mcp/.env` 填好 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_BOTBONNIE_ROLE_ARN`（從 team vault 拿）。
2. 啟動 ets-agent MCP：`cd ../ets-agent-mcp && PYTHONUTF8=1 uv run python -m servers.main`
3. 另開終端機：`uv run python server.py`
4. `curl http://127.0.0.1:3000/api/botbonnie/health`、`curl http://127.0.0.1:3000/api/botbonnie/bots/bot-xxxx`

環境變數：`ETS_AGENT_MCP_URL`（預設 `http://localhost:8000/mcp`）、`SHOP_HOST` / `SHOP_PORT`（預設 `127.0.0.1:3000`，
請勿綁到 `0.0.0.0` —— 這個 API 背後是 AWS 權限，不應對外公開）。
