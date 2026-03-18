<skill name="grok-cli">

# grok-cli 技能說明

## 1. 技能概述

- 名稱：`grok-cli`
- 作用：通過本地 CLI 快速調用 `https://grok.tap365.org/v1` 上的 Grok2API 實例，支持：
  - 文本對話（chat）
  - 文生圖（image）
  - 圖生圖（image-edit）
  - 文生視頻（video）
  - 圖生視頻（video-from-image）
- 封裝路徑：`scripts/grok_cli.py`
- CLI 名稱（console script）：`grok-cli`（已在 `pyproject.toml` 中配置）
- 路由原則：**只要是 Grok 語境下的生圖 / 生視頻 / 圖生圖 / 圖生視頻，默認優先使用 `grok-cli`**

> 注意：目前項目 `requires-python = ">=3.13"`，如果當前環境 Python 版本較低，可以直接用
> `python scripts/grok_cli.py ...` 的形式調用，同樣受本技能約束。

### 1.1 觸發詞建議

對話中出現以下關鍵短語時，應優先路由到本技能：

- `grok-cli`
- `使用 grok-cli`
- `用 grok-cli`
- `生圖`
- `生成圖片`
- `畫圖`
- `出圖`
- `文生圖`
- `圖生圖`
- `幫我生圖`
- `幫我生成圖片`
- `grok 生圖`
- `grok生圖`
- `生視頻`
- `生成視頻`
- `文生視頻`
- `圖生視頻`
- `幫我生視頻`
- `幫我生成視頻`
- `grok 生視頻`
- `grok生視頻`
- `用圖片生視頻`
- `把這張圖變成視頻`
- `把這張圖動起來`

代理在解析用戶意圖時，若檢測到上述任意片語，且語境涉及 Grok 的文本/圖片/視頻生成，應優先選用 `grok-cli` 技能並調用對應子命令，而不是走其他泛用圖片/視頻工具。

---

## 2. 安裝與環境

### 2.1 基本依賴

- Python 版本：`>=3.13`（推薦）
- 必需包：`requests`（已作為 CLI 內部依賴，隨 `grok2api` 一起安裝）

### 2.2 安裝為命令（推薦）

在滿足 Python 版本的虛擬環境或系統環境中：

```bash
cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/grok2api
uv sync --python 3.13
uv run grok-cli --help
```

如果要安裝到當前 Python 環境，也可以：

```bash
pip install -e .
grok-cli --help
```

成功後可直接使用：

```bash
grok-cli chat "你好，回一個字"
```

### 2.3 直接調用腳本（兼容模式）

如果暫時無法安裝成 console script，可在項目根目錄使用：

```bash
python scripts/grok_cli.py <subcommand> [...args]
```

本技能中的所有示例既適用於 `grok-cli` 也適用於 `python scripts/grok_cli.py`（只需將命令名替換即可）。

---

## 3. 基本配置

### 3.1 Base URL

- 默認 Base URL：

```text
https://grok.tap365.org/v1
```

- 可通過環境變量覆蓋：

```bash
export GROK_BASE_URL="https://grok.tap365.org/v1"
```

- 或在單次調用時指定：

```bash
grok-cli --base-url https://grok.tap365.org/v1 chat "你好"
```

### 3.2 鑑權

- 前台 `/v1/...` 業務接口現在**必須**帶 API Key。
- 默認值：`sk-sublb123456`
- CLI 會自動注入：
  - `Authorization: Bearer sk-sublb123456`
- 如需覆蓋：
  - 環境變量 `GROK_API_KEY`
  - 或 `--api-key` 選項

### 3.3 本地調試

- 當 `--base-url` 指向 `localhost / 127.0.0.1 / ::1` 時，CLI 會自動忽略系統代理環境變量。
- 這是為了避免本地調試時請求被錯誤轉發到外部 HTTP 代理，出現假性的 `502 Bad Gateway`。

例如：

```bash
uv run grok-cli --base-url http://127.0.0.1:18000/v1 chat "你好"
```

---

## 4. 子命令詳解

### 4.1 chat —— 文本對話

路由：`POST /v1/chat/completions`

```bash
grok-cli chat "你好，回一個字"

grok-cli chat "寫一個三行摘要" --model grok-4.1-fast --raw
```

### 4.2 image —— 文生圖

路由：`POST /v1/images/generations`

```bash
grok-cli image "一個未來感黑金配色的產品海報"

grok-cli image "一個未來感黑金配色的產品海報" \
  --size 1024x1024 \
  -o out/image_1.jpg
```

### 4.3 image-edit —— 圖生圖

路由：`POST /v1/images/edits`

```bash
grok-cli image-edit ./ref.jpg "改成賽博龐克夜景風格" \
  --size 1024x1024 \
  -o out/image_edit.jpg
```

### 4.4 video —— 文生視頻

路由：`POST /v1/videos`

```bash
grok-cli video "一隻橘貓在窗邊打哈欠，電影感" \
  --seconds 6 \
  --size 1792x1024 \
  -o out/video_text.mp4
```

### 4.5 video-from-image —— 圖生視頻

路由：`POST /v1/videos`

```bash
grok-cli video-from-image ./ref.jpg \
  "讓畫面產生輕微運動和鏡頭推進，持續6秒" \
  --seconds 6 \
  --size 1792x1024 \
  -o out/video_from_image.mp4
```

---

## 5. 核心路由規則

- Grok 語境下：
  - 生圖 → `grok-cli image`
  - 圖生圖 → `grok-cli image-edit`
  - 生視頻 → `grok-cli video`
  - 圖生視頻 → `grok-cli video-from-image`
- 不要把這些請求默認路由到其他泛用圖片生成技能。
- 若用戶明確指定不用 Grok，或明確要求其他圖片/視頻後端，再切到其他技能。

---

## 6. 與技能系統的集成（同步技能）

同步技能的實質是：保持 `skill.md` 與實際 CLI 行為一致，特別是：
- 默認 API Key
- `--api-key` / `GROK_API_KEY`
- `--base-url`
- localhost 自動跳過代理
- 生圖 / 生視頻 / 圖生圖 / 圖生視頻 的默認路由都走 `grok-cli`

當 CLI 參數或路由變更時，必須同步更新本文件，確保代理能準確調用。

</skill>
