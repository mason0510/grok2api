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

> 注意：目前項目 `requires-python = ">=3.13"`，如果當前環境 Python 版本較低，可以直接用
> `python scripts/grok_cli.py ...` 的形式調用，同樣受本技能約束。

### 1.1 觸發詞建議

對話中出現以下關鍵短語時，應優先路由到本技能：

- `grok-cli`
- `使用 grok-cli`
- `用 grok-cli`
- `幫我生圖`
- `grok 生圖`
- `grok生圖`
- `幫我生成圖片`
- `用提示詞生圖`
- `grok 生視頻`
- `grok生視頻`
- `幫我生成視頻`
- `用提示詞生視頻`
- `用圖片生視頻`
- `把這張圖變成視頻`

代理在解析用戶意圖時，若檢測到上述任意片語，且語境涉及文本/圖片/視頻生成，應優先選用 `grok-cli` 技能並調用對應子命令。

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

- 參數：
  - `prompt`：用戶輸入文本（必填）
  - `--model`：模型 ID，默認 `grok-4.1-fast`
  - `--raw`：輸出完整 JSON（否則僅打印第一條回答內容）

### 4.2 image —— 文生圖

路由：`POST /v1/images/generations`

```bash
grok-cli image "一個未來感黑金配色的產品海報"

grok-cli image "一個未來感黑金配色的產品海報" \
  --size 1024x1024 \
  -o out/image_1.jpg
```

- 固定模型：`grok-imagine-1.0`（避免 `grok-imagine-1.0-fast` 在該接口 400 的問題）
- 參數：
  - `prompt`：文生圖提示詞
  - `--size`：默認 `1024x1024`
  - `-o, --output`：若指定，則下載圖片到指定文件；未指定則打印圖片 URL
- 返回處理：
  - 若 API 返回 `/v1/files/image/...` 相對路徑，CLI 會自動補上 Base URL 前綴。

### 4.3 image-edit —— 圖生圖

路由：`POST /v1/images/edits`

```bash
grok-cli image-edit ./ref.jpg "改成賽博龐克夜景風格" \
  --size 1024x1024 \
  -o out/image_edit.jpg
```

- 固定模型：`grok-imagine-1.0-edit`
- 參數：
  - `image`：本地參考圖路徑
  - `prompt`：編輯提示詞
  - `--size`：默認 `1024x1024`
  - `-o, --output`：同 image
- 注意：
  - 當前後端有已知問題：若上游資產上傳（AssetsUpload）失敗，會返回 `502` + `"AssetsUploadReverse: Upload failed, 400"`，屬於服務端 upstream 問題，CLI 會打印詳細錯誤 JSON 以便排查。

### 4.4 video —— 文生視頻

路由：`POST /v1/videos`

```bash
grok-cli video "一隻橘貓在窗邊打哈欠，電影感" \
  --seconds 6 \
  --size 1792x1024 \
  -o out/video_text.mp4
```

- 固定模型：`grok-imagine-1.0-video`
- 參數：
  - `prompt`：視頻提示詞
  - `--size`：默認 `1792x1024`
  - `--seconds`：默認 `6`
  - `--quality`：默認 `standard`
  - `-o, --output`：若指定則下載 mp4 文件；否則打印視頻 URL
- 返回處理：
  - 優先從 JSON 中尋找 `url` / `video_url` 或 `data[*].url` / `files[*].url`。

### 4.5 video-from-image —— 圖生視頻

路由：`POST /v1/videos`

```bash
grok-cli video-from-image ./ref.jpg \
  "讓畫面產生輕微運動和鏡頭推進，持續6秒" \
  --seconds 6 \
  --size 1792x1024 \
  -o out/video_from_image.mp4
```

- 固定模型：`grok-imagine-1.0-video`
- 參數：
  - `image`：本地參考圖文件
  - `prompt`：描述運動與風格
  - 其他同 `video`
- 上傳字段：
  - 使用 `input_reference=@<file>` 字段提交參考圖，與 `GROK_API_DOC.md` 保持一致。

---

## 5. 常見錯誤與排查

### 5.0 requests 缺失 / 命令不可用

- 現象：
  - `ModuleNotFoundError: No module named 'requests'`
  - `uv run grok-cli` / `grok-cli` 不可用
- 直接原因：
  - 當前環境沒有安裝項目依賴，或沒有先執行 `uv sync --python 3.13`
- 正確做法：

```bash
cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/grok2api
uv sync --python 3.13
uv run grok-cli --help
```

### 5.1 模型傳錯導致 400

- 現象：
  - 在 `/v1/images/generations` 傳 `grok-imagine-1.0-fast` 會返回 400。
- CLI 中的處理：
  - `image` 子命令固定使用 `grok-imagine-1.0`，避免踩坑。

### 5.2 AssetsUpload 上游錯誤

- 現象：
  - `image-edit` 或 `video-from-image` 報：
    - `502` + `"AssetsUploadReverse: Upload failed, 400"`。
- 原因：
  - Grok 上游資產上傳鏈路問題，與 CLI 參數無關。
- 排查建議：
  - 檢查 Grok Web 後台 / 日誌
  - 確認上游是否限制文件大小 / 格式

### 5.3 assets.grok.com 直鏈 403

- 現象：
  - 直接用 `curl` 下 `https://assets.grok.com/...generated_video.mp4` 報 403。
- 原因：
  - 需要特定 cookie / referer / origin 或當前 sso 會話。
- 建議：
  - 在已登錄會話或後端中轉下載，或在 Grok2API 層增加本地緩存與重寫下載接口。

---

## 6. 與技能系統的集成（同步技能）

為了在 Claude Code / OpenCode 中使用 `grok-cli` 作為一級技能，可以將本目錄作為技能包安裝：

1. 將當前 `grok-cli` 目錄複製到本地技能目錄，例如：
   - Claude Code：`~/.claude/skills/grok-cli/`
   - OpenCode：`~/.config/opencode/skills/grok-cli/`

2. 確保其中包含：
   - `skill.md`（即本文件）
   - 對應 CLI 代碼路徑說明（`scripts/grok_cli.py`）

3. 在對話中即可使用觸發詞啟用本技能，例如：
   - 「使用 grok-cli 幫我生一張圖」
   - 「用 grok-cli 幫我生一個 6 秒視頻」

> 同步技能的實質是：保持 `skill.md` 與實際 CLI 行為一致，特別是：
> - 默認 API Key
> - `--api-key` / `GROK_API_KEY`
> - `--base-url`
> - localhost 自動跳過代理
> 當 CLI 參數或路由變更時，必須同步更新本文件，確保代理能準確調用。

</skill>
