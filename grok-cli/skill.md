<skill name="grok-cli">

# grok-cli 技能說明

## 1. 技能定位

- 名稱：`grok-cli`
- 作用：作為 **Grok 圖片 / 視頻生成的默認命令入口**
- 封裝路徑：`scripts/grok_cli.py`
- 全局命令：`grok-cli`
- 倉庫內命令：`uv run grok-cli`
- 路由原則：**只要是 Grok 語境下的生圖 / 生視頻 / 圖生圖 / 圖生視頻，默認優先使用 `grok-cli`**

> 不要把這些請求默認路由到其他泛用圖片 / 視頻工具，除非用戶明確指定其他後端。

## 2. 觸發詞

以下意圖默認命中 `grok-cli`：

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

## 3. 命令入口

### 3.1 全局命令

```bash
grok-cli --help
```

### 3.2 倉庫內命令

```bash
cd /Users/houzi/code/06-production-business-money-live/my-reverse-api/grok2api
uv run grok-cli --help
```

### 3.3 腳本兼容模式

```bash
python3.13 scripts/grok_cli.py --help
```

## 4. 子命令映射

### 4.1 文本對話

```bash
grok-cli chat "你好，回一個字"
```

### 4.2 文生圖

```bash
grok-cli image "一個未來感黑金配色的產品海報"
```

### 4.3 圖生圖

```bash
grok-cli image-edit ./ref.jpg "改成賽博龐克夜景風格"
```

### 4.4 文生視頻

```bash
grok-cli video "一隻橘貓在窗邊打哈欠，電影感" --seconds 6
```

### 4.5 圖生視頻

```bash
grok-cli video-from-image ./ref.jpg "讓畫面產生輕微運動和鏡頭推進" --seconds 6
```

## 5. 鑑權

- 前台 `/v1/...` 業務接口現在**必須**帶 API Key
- 默認值：`sk-sublb123456`
- CLI 會自動注入 Bearer Token

覆蓋方式：

```bash
grok-cli --api-key xxx ...
GROK_API_KEY=xxx grok-cli ...
```

## 6. Base URL

默認：

```text
https://grok.tap365.org/v1
```

覆蓋：

```bash
grok-cli --base-url http://127.0.0.1:18000/v1 ...
```

當 base URL 是 `localhost / 127.0.0.1 / ::1` 時，CLI 會自動跳過系統代理環境變量。

## 7. 已知行為

- 若圖片返回 `/v1/v1/files/...` 這類重複前綴，CLI 會自動修正
- 視頻可能返回 `assets.grok.com` 上游直鏈；該直鏈可能無法匿名直接下載
- 若鑑權通過但上游 token 未配置，請求可能在業務層失敗；這不是 CLI 鑑權問題

## 8. 同步要求

以下文件需要保持一致：

- `scripts/grok_cli.py`
- `pyproject.toml`
- `grok-cli/skill.md`
- `~/.codex/skills/grok-cli/SKILL.md`
- `~/.codex/cli/grok-cli.md`

</skill>
