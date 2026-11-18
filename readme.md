# AI Operations Agent

## 開發環境

需要 Python 3.12 與 Poetry 2。在專案根目錄執行：

```powershell
poetry install
poetry run python --version
```

`poetry.toml` 將虛擬環境設在專案根目錄的 `.venv`。`poetry.lock` 固定安裝版本，預設也會安裝開發測試套件。

## 初始化 SQLite 與啟動 API

預設資料庫為專案根目錄下的 `operations.db`。後端和初始化腳本均從專案根目錄載入 `.env`，其中的 SQLite 相對檔案路徑也以專案根目錄為準。若要自訂位置，請將 `.env.example` 複製成 `.env` 並設定 `DATABASE_URL`。在專案根目錄執行：

```powershell
poetry run python -m backend.scripts.init_db
poetry run uvicorn backend.app.main:app --reload
```

在另一個 PowerShell 視窗送出請求：

```powershell
curl.exe -i http://127.0.0.1:8000/health
```

預期收到 HTTP `200 OK` 與 `{"status":"ok"}`。健康檢查用來確認應用程式能接收請求。瀏覽 `http://127.0.0.1:8000/docs` 可透過 Swagger UI 試送請求。

### Alembic Migration

`init_db` 會顯示本次連線的資料庫檔案和目前的 Alembic revision。空白資料庫可直接初始化。若是舊版 SQLite，請先備份資料庫，再執行同一個指令。它會比對歷史結構。只有原本三張營運表的資料庫會補建兩張 Agent 表，已有五張表的資料庫會登記對應版本。結構比對失敗時，指令會停止並保留原資料。

完成首次初始化後，可以使用這些指令查詢版本及套用後續 migration：

```powershell
poetry run alembic current
poetry run alembic history
poetry run alembic upgrade head
```

之後修改 ORM 時，從已升到 `head` 的開發資料庫產生 revision，再先檢查產出的變更，尤其是 SQLite 的欄位或約束異動。

```powershell
poetry run alembic revision --autogenerate -m "describe schema change"
```

### 使用 PostgreSQL

本機仍可使用預設 SQLite。要切換至 PostgreSQL，先在 PostgreSQL 建立專案資料庫，接著把 `.env` 裡的 `DATABASE_URL` 改成下列格式，並填入自己的連線資料。

```dotenv
DATABASE_URL=postgresql+psycopg://db_user:replace_me@127.0.0.1:5432/operations
```

若密碼含有 `@`、`#` 等 URL 保留字元，請先做百分比編碼。設定後，使用相同的 Alembic revision 初始化 PostgreSQL，再啟動 API：

```powershell
poetry install
poetry run alembic upgrade head
poetry run alembic current
poetry run uvicorn backend.app.main:app --reload
```

空白 PostgreSQL 可透過原有的 seed 腳本載入模擬資料。Alembic 會建立或升級資料表，SQLite 的既有資料需另行搬移。

## Phase 1 API

| 方法與路徑 | 用途 |
| --- | --- |
| `POST /products` | 新增商品 |
| `GET /products` | 依 `name`、`sku`、`min_stock`、`max_stock`、`stock_below` 篩選 |
| `GET /products/{product_id}` | 查詢商品 |
| `PATCH /products/{product_id}` | 修改指定欄位 |
| `DELETE /products/{product_id}` | 刪除商品，若已有訂單明細引用則回傳 `409` |
| `POST /orders` | 建立模擬訂單及明細 |
| `GET /orders` | 依 `status`、`start`、`end` 查詢 |
| `GET /orders/{order_id}` | 查詢訂單與明細 |
| `GET /sales/summary` | 依必要的 `start`、`end` 統計銷量與金額，可另指定 `product_id` |

- 商品和訂單列表可用 `limit` 與 `offset` 分頁。商品名稱使用子字串搜尋，SKU 使用區分大小寫的精確比對。庫存上下限包含邊界，`stock_below` 為嚴格小於。
- 訂單的 `items` 由 `product_id` 與 `quantity` 組成，每個商品在一張訂單出現一次。訂單和明細同一筆交易儲存，成交單價取自建立時的商品價格。模擬訂單的建立不扣庫存。
- 金額採單一幣別、小數兩位，以最小貨幣單位的整數儲存，API 回傳十進位字串。
- 銷售額為明細成交單價乘以數量的總和，僅計入 `completed`，另有 `pending`、`cancelled` 兩種狀態。日期時間請帶時區，統一轉成 UTC，區間為 `[start, end)`。

## 載入模擬資料

初始化資料庫後，在同一個專案根目錄執行下列指令。指令僅接受空白資料庫，固定 `--seed` 與 `--as-of` 可重現同一批 5 筆商品與 50 筆訂單。驗收時可用 `DATABASE_URL` 指向另一個資料庫檔案。

```powershell
poetry run python -m backend.scripts.seed --seed 42 --as-of 2026-11-18
curl.exe "http://127.0.0.1:8000/products?stock_below=10"
curl.exe "http://127.0.0.1:8000/sales/summary?start=2026-10-19T00:00:00Z&end=2026-11-18T00:00:00Z"
```

## 執行測試

```powershell
poetry run python -m pytest backend/tests
```

PostgreSQL 整合測試需要在目前終端機提供 `TEST_POSTGRES_URL`，建議使用專用測試資料庫。連線帳號須能建立 schema。測試在獨立 schema 內套用 migration，並使用模擬 LLM 驗證 API，結束後回滾整筆交易。未提供測試連線時，pytest 會略過這一組。

```powershell
$env:TEST_POSTGRES_URL = Read-Host "輸入 PostgreSQL 測試連線字串"
poetry run python -m pytest backend/tests/test_postgresql.py
```

## Groq 連線測試

在專案根目錄的 `.env` 設定 `GROQ_API_KEY`，或透過環境變數提供。接著執行：

```powershell
poetry run python -m backend.scripts.test_groq
```

腳本預設透過 Groq 的 Chat Completions API 呼叫 `openai/gpt-oss-20b`，送出一句提示並印出模型回覆。可透過 `--model` 指定其他模型。

## Phase 2 AI Agent MVP

Agent 使用 `agent_runs` 和 `tool_executions` 資料表，由 Alembic 的 `0002_agent_audit` revision 建立。

```powershell
poetry run python -m backend.scripts.init_db
poetry run uvicorn backend.app.main:app --reload
```

在另一個終端機啟動 React 介面。前端使用 React 19 與 Vite 6，支援目前開發環境的 Node.js 20.16。

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

開啟 `http://127.0.0.1:5173`。可以點選補貨問題、送出後查看回覆、補貨明細與工具紀錄。若要重現既有 seed 的結果，可問「找出 2026-10-19T00:00:00Z 至 2026-11-18T00:00:00Z，庫存低於 10 且銷量超過 20 件的商品，提供補貨建議」。商品頁可搜尋、新增、編輯與刪除，訂單頁可依狀態、日期篩選並查看明細。

後端從 `.env` 或環境變數讀取 `GROQ_API_KEY` 和選填的 `GROQ_MODEL`（預設 `openai/gpt-oss-20b`）。Vite 將同源的 `/api` 請求轉發至本機 FastAPI。驗證正式前端建置可在 `frontend/` 執行 `npm.cmd run build`。

### 工具與執行紀錄

| API | 用途 |
| --- | --- |
| `POST /agent/runs` | 接收 `{"message":"…"}`，同步執行一次獨立提問並回傳 HTTP `201` 與執行結果。可從 `status` 判斷是否成功。 |
| `GET /agent/runs/{run_id}` | 依 UUID 查詢已儲存的執行狀態、回覆和工具紀錄。 |

FastAPI 將請求交給 Orchestrator。Groq 傳回結構化的工具呼叫，由 Tool Registry 比對白名單、使用 Pydantic 驗證參數、執行應用程式內的唯讀查詢。Orchestrator 持續把工具結果送回模型，直到取得最終答覆、遇到錯誤或達到執行上限。每次最多呼叫 6 個工具，單次 Groq 請求的 HTTP 逾時最多為 15 秒，整體流程以 60 秒為執行預算。

| 工具 | 用途 |
| --- | --- |
| `get_low_stock_products` | 查出庫存嚴格小於指定閾值的商品。 |
| `get_sales_summary` | 查詢指定期間的已完成訂單銷量與銷售額，可依商品篩選。 |
| `calculate_restock` | 可結合庫存與歷史銷量條件。建議量為 `max(0, ceil(日均銷量 × 提前期) + 安全庫存 − 目前庫存)`，預設提前期 14 天、安全庫存 5 件。 |

Agent 將每次提問、最終回覆和工具執行存到 SQLite。工具紀錄包括驗證後的參數、結果、狀態與錯誤摘要。前端顯示本次頁面內的提問，重新整理後仍可用執行 ID 查回個別紀錄。此 MVP 供本機開發使用，API 尚無登入與權限控制。CSV 匯出排在 Phase 3。
