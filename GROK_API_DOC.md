# Grok API 使用文档（grok.tap365.org）

> 最后验证时间：2026-03-19  
> 部署地址：`https://grok.tap365.org`  
> 后端落点：局域网 `192.168.2.107:3035`，通过 FRP + Caddy + Cloudflare 暴露

## 1. 当前状态

已实测可用：
- 文本对话
- 文生图
- 图生图
- 文生视频
- 图生视频
- Swagger 文档
- 管理后台

健康检查：
```bash
curl https://grok.tap365.org/health
```

返回：
```json
{"status":"ok"}
```

Swagger：
- `https://grok.tap365.org/docs`

管理后台：
- `https://grok.tap365.org/admin/login`

---

## 2. 鉴权说明

### 2.1 业务接口
当前这套实例的业务接口**未额外启用前台 API Key**，直接调用即可。

也就是说，下面这些接口当前可以直接打：
- `/v1/chat/completions`
- `/v1/images/generations`
- `/v1/images/edits`
- `/v1/videos`
- `/v1/files/image/...`

### 2.2 管理接口
管理接口需要后台口令：

```txt
Authorization: Bearer grok2api
```

这个值来自：
- `app.app_key = "grok2api"`

例如：
```bash
curl https://grok.tap365.org/v1/admin/config \
  -H 'Authorization: Bearer grok2api'
```

### 2.3 业务接口
前台 `/v1/...` 业务接口现在也必须带 Bearer Key：

```txt
Authorization: Bearer sk-sublb123456
```

---

## 3. 当前实例的关键配置

### 3.1 已配置代理
当前后端访问 Grok 上游时，**自动走服务端代理**，不是客户端自己挂代理。

所以：
- 你本机请求 `https://grok.tap365.org/...`
- **本机不开 ClashX 也能正常用**

当前服务端配置的是统一上游代理，已经写进 Grok2API 后台配置。

### 3.2 Token 类型
这套项目核心吃的不是官方 `sk-*`，而是 **Grok Web 的 `sso` token**。

后台支持：
- `ssoBasic`
- `ssoSuper`

可填格式：
- 纯 token
- 或 `sso=xxx`

---

## 4. 基础调用

统一 Base URL：

```txt
https://grok.tap365.org/v1
```

建议先设环境变量：

```bash
export GROK_BASE_URL="https://grok.tap365.org/v1"
```

---

## 5. 文本对话

### 5.1 最小可用示例

```bash
curl "$GROK_BASE_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-4.1-fast",
    "messages": [
      {"role": "user", "content": "你好，回一个字"}
    ],
    "stream": false
  }'
```

实测返回过：
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "嗨"
      }
    }
  ]
}
```

### 5.2 常用文本模型

- `grok-4.1-fast`：通用最快，适合大多数文本请求
- `grok-4`
- `grok-4.1-mini`
- `grok-4.1-thinking`
- `grok-4-heavy`

---


## 5.3 生图 / 生视频节奏约束（P0）

不管是 `grok-cli` 还是直接调接口，只要是图片 / 视频生成，都不要连续猛打。

必须遵守：
- 禁止并发批量生成
- 必须串行，一次只打一张图 / 一个视频
- 每次成功生成后加入**随机间隔**再发下一次请求
- 若出现 `429` / `503` / `No available tokens` / `rate_limit_exceeded` / `无可用渠道`，立即退避，不要继续撞

建议节奏：
- 正常情况：随机等待 **8–25 秒**
- 上游不稳或上一张耗时明显偏长：随机等待 **20–45 秒**
- 遇到限流 / 通道耗尽：退避 **60–180 秒**

Bash 示例：

```bash
for prompt in prompts/*.txt; do
  grok-cli image "$(cat "$prompt")"
  sleep $((RANDOM % 18 + 8))
done
```

## 6. 文生图

### 6.1 正确模型
文生图接口必须用：

```txt
grok-imagine-1.0
```

不要用：
- `grok-imagine-1.0-fast`

之前实测，如果在 `/v1/images/generations` 里误传 `grok-imagine-1.0-fast`，会直接 400。

### 6.2 示例

```bash
curl "$GROK_BASE_URL/images/generations" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-imagine-1.0",
    "prompt": "一只橘猫，极简白底插画",
    "size": "1024x1024",
    "response_format": "url"
  }'
```

返回格式：
```json
{
  "data": [
    {
      "url": "/v1/files/image/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.jpg"
    }
  ]
}
```

拼完整地址即可访问：

```txt
https://grok.tap365.org/v1/files/image/<image_id>.jpg
```

---

## 7. 图生图

接口：

```txt
POST /v1/images/edits
```

模型：

```txt
grok-imagine-1.0-edit
```

请求方式：`multipart/form-data`

### 示例

```bash
curl "$GROK_BASE_URL/images/edits" \
  -X POST \
  -F 'model=grok-imagine-1.0-edit' \
  -F 'prompt=保留主体构图，改成电影感暖色调，细节更真实' \
  -F 'size=1024x1024' \
  -F 'response_format=url' \
  -F 'image=@/path/to/reference.jpg'
```

如果参考图已经是服务端生成的图，也可以先下载再编辑，或者直接使用本地已有图片。

---

## 8. 文生视频

接口：

```txt
POST /v1/videos
```

模型：

```txt
grok-imagine-1.0-video
```

### 示例

```bash
curl "$GROK_BASE_URL/videos" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只橘猫在窗边打哈欠，电影感",
    "model": "grok-imagine-1.0-video",
    "size": "1792x1024",
    "seconds": 6,
    "quality": "standard"
  }'
```

返回里会给出视频 URL。

---

## 9. 图生视频

同样走：

```txt
POST /v1/videos
```

支持两种参考图方式：
- `input_reference=@file`
- `image_reference`（结构化 JSON）

目前最稳的是直接传文件。

### 示例

```bash
curl "$GROK_BASE_URL/videos" \
  -X POST \
  -F 'model=grok-imagine-1.0-video' \
  -F 'prompt=基于这张图生成6秒动态视频，主体自然呼吸，轻微镜头推进，电影感，真实光影' \
  -F 'size=1792x1024' \
  -F 'seconds=6' \
  -F 'quality=standard' \
  -F 'input_reference=@/path/to/reference.jpg'
```

---

## 10. 已验证过的一张参考图

之前已生成过一张图：

```txt
https://grok.tap365.org/v1/files/image/77070a38-bb41-4248-8ff9-e680918a463f.jpg
```

可直接拿它做图生图或图生视频参考。

例如先下载：

```bash
curl -L 'https://grok.tap365.org/v1/files/image/77070a38-bb41-4248-8ff9-e680918a463f.jpg' -o ref.jpg
```

然后用于 `/v1/images/edits` 或 `/v1/videos`。

---

## 11. 视频下载说明

Grok 返回的视频 URL 往往是：
- `https://assets.grok.com/...generated_video.mp4`

这个链接**不一定能直接裸下**，因为常常依赖：
- cookie
- referer
- origin
- 当前 sso 会话

所以会出现：
- 浏览器黑屏
- `curl` 直接下返回 403

### 解决方式
不要直接信任 `assets.grok.com` 外链，稳妥做法是：
1. 先在服务端或已登录环境里取带会话的请求
2. 再下载到本地

之前已经成功下载过一个本地文件：
- `/Users/houzi/Downloads/grok_ref_video_20260319_1.mp4`

---

## 12. 管理后台使用

地址：

```txt
https://grok.tap365.org/admin/login
```

当前后台密码：

```txt
grok2api
```

后台可做：
- 添加 `ssoBasic` / `ssoSuper` token
- 查看 token 状态
- 调整代理配置
- 查看缓存
- 在线改配置

建议后续动作：
- 改掉默认后台密码
- 视情况启用前台 `api_key`

---

## 13. 常见坑

### 13.1 生图模型传错
错误：
- 在 `/v1/images/generations` 里传 `grok-imagine-1.0-fast`

结果：
- 400

正确做法：
- 改为 `grok-imagine-1.0`

### 13.2 不是你本机代理问题
如果你是调用：
- `https://grok.tap365.org/v1/...`

那这套实例已经在服务端走代理了，**不是要求你本机必须挂 ClashX**。

### 13.3 assets.grok.com 直链 403
不是视频坏了，而是资源链路需要会话。

---

## 14. 推荐调用模板

### 文本

```bash
curl https://grok.tap365.org/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"grok-4.1-fast",
    "messages":[{"role":"user","content":"写一个三行摘要"}],
    "stream":false
  }'
```

### 生图

```bash
curl https://grok.tap365.org/v1/images/generations \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"grok-imagine-1.0",
    "prompt":"一个未来感黑金配色的产品海报",
    "size":"1024x1024",
    "response_format":"url"
  }'
```

### 图生图

```bash
curl https://grok.tap365.org/v1/images/edits \
  -X POST \
  -F 'model=grok-imagine-1.0-edit' \
  -F 'prompt=改成赛博朋克夜景风格' \
  -F 'size=1024x1024' \
  -F 'response_format=url' \
  -F 'image=@./ref.jpg'
```

### 图生视频

```bash
curl https://grok.tap365.org/v1/videos \
  -X POST \
  -F 'model=grok-imagine-1.0-video' \
  -F 'prompt=让画面产生轻微运动和镜头推进，持续6秒' \
  -F 'size=1792x1024' \
  -F 'seconds=6' \
  -F 'quality=standard' \
  -F 'input_reference=@./ref.jpg'
```

---

## 15. 后续建议

这套已经能用，但从运维角度还差两件事：

1. **改后台默认密码**  
   现在还是 `grok2api`

2. **前台接口已经加了 api_key**  
   现在业务接口必须传 `Authorization: Bearer sk-sublb123456`

如果要，我下一步可以继续补：
- Python 调用示例
- Node.js 调用示例
- OpenAI SDK 兼容调用示例
- 一份更正式的 README / 部署文档整合版
