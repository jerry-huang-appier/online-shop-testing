# online-shop-testing
static online shop platform for testing

## BotBonnie 帳號資訊（透過 ets-agent MCP）

頁面底部的「BotBonnie 帳號資訊」區塊會用 Bot ID 查詢 BotBonnie 的 `bot` 設定。
流程：瀏覽器 → `server.py`（MCP client）→ ets-agent MCP (`describe_table` / `query_table` / `get_item`,
`connection=botbonnie`) → AWS DynamoDB。只讀，token / secret 類欄位會被遮蔽。

### 怎麼跑

1. 在 `ets-agent-mcp/.env` 填好 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_BOTBONNIE_ROLE_ARN`（從 team vault 拿）。
2. 啟動 ets-agent MCP（需 VPN）：

   ```bash
   cd ../ets-agent-mcp && uv run python -m servers.main
   ```

3. 另開一個終端機啟動商店：

   ```bash
   uv run python server.py
   ```

4. 開 http://127.0.0.1:3000/#botbonnie ，輸入 Bot ID（登入 console.botbonnie.com 後網址列裡的 `bot-xxxx`）。

> 直接雙擊開 `index.html` 只會有靜態商店，BotBonnie 區塊需要 `server.py`。

環境變數：`ETS_AGENT_MCP_URL`（預設 `http://localhost:8000/mcp`）、`SHOP_HOST` / `SHOP_PORT`（預設 `127.0.0.1:3000`，
請勿綁到 `0.0.0.0` —— 這個 API 背後是 AWS 權限，不應對外公開）。
