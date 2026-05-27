---
name: manxiaobai-skill
description: "漫小白 API：Imagine2 文生图/图生图（单参考图、多参考图）+ Grok 视频生成（文生视频、图生视频）。自动选择 Key、处理 base64/URL 两种响应格式。"
version: 1.2.0
metadata:
  hermes:
    tags: [image-generation, video-generation, manxiaobai, imagine2, grok, api]
    category: mlops
---

# 漫小白 API

BASE URL: `https://api.manxiaobai.online/v1` | 文档: https://api.manxiaobai.online/about

## 配置

编辑 skill 目录下的 `.env` 文件：

```bash
MANXIAOBAI_IMAGINE_KEY=   # Imagine2 生图/改图
MANXIAOBAI_GROK_KEY=      # Grok 视频生成
TENCENT_COS_SECRET_ID=
TENCENT_COS_SECRET_KEY=
TENCENT_COS_REGION=
TENCENT_COS_BUCKET=
```

使用前加载：

```bash
source .env
```

## 自动选择 Key

- `gpt-image-2*` → `$MANXIAOBAI_IMAGINE_KEY`
- `grok-imagine-video` → `$MANXIAOBAI_GROK_KEY`

## 模型选择

| 场景 | 模型 | 说明 |
|---|---|---|
| 头像、封面草稿、普通图 | `gpt-image-2-1k` | **默认首选** |
| 海报、角色设定、较高清 | `gpt-image-2-2k` | 高清素材 |
| 高分辨率成片 | `gpt-image-2-4k` | 耗时最长 |
| 返回 URL 直链 | `gpt-image-2` | 无需处理 base64 |

⚠️ 模型名和尺寸档位必须保持一致，不能混搭。

## 错误参考

| 错误 | 原因 |
|---|---|
| `401` | Key 错误或未携带 |
| `model_not_found` | 模型名写错或 Key 无权限 |
| `invalid size` | 尺寸不支持，API 返回 `allowed_sizes` |
| `upstream returned error` | 上游故障，稍后重试 |
| `Failed to fetch` | 超时，调大 `--max-time` |

## 生图: `POST /images/generations`

JSON body，默认 `gpt-image-2-1k`。

```bash
curl -s --max-time 300 "https://api.manxiaobai.online/v1/images/generations" \
  -H "Authorization: Bearer $MANXIAOBAI_IMAGINE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2-1k","prompt":"...","size":"1024x1024","response_format":"url"}'
```

### 尺寸表

| 模型 | 可用尺寸 |
|---|---|
| gpt-image-2-1k | 1024x1024, 1536x1024, 1024x1536, 1824x1024, 1024x1824 |
| gpt-image-2-2k | 2048x2048, 2048x1152, 1152x2048, 2048x1536, 1536x2048 |
| gpt-image-2-4k | 2880x2880, 3840x2160, 2160x3840, 3312x2480, 2480x3312, 3840x1648 |
| gpt-image-2 | 1024x1024, 1536x1024, 1024x1536, 1824x1024, 1024x1824, 1360x1024, 1024x1360, 2384x1024 |

超时: 1K 180s+ / 2K 300s+ / 4K 600s+

## 图生图/改图: `POST /images/edits`

**multipart/form-data**（不是 JSON）。

### 单参考图

```bash
curl -s --max-time 300 "https://api.manxiaobai.online/v1/images/edits" \
  -H "Authorization: Bearer $MANXIAOBAI_IMAGINE_KEY" \
  -F "model=gpt-image-2-1k" \
  -F "prompt=..." \
  -F "size=1024x1024" \
  -F "image[]=@/path/to/ref.png"
```

### 多参考图

按上传顺序对应图一、图二、图三，prompt 中明确说明各自作用：

```bash
curl -s --max-time 300 "https://api.manxiaobai.online/v1/images/edits" \
  -H "Authorization: Bearer $MANXIAOBAI_IMAGINE_KEY" \
  -F "model=gpt-image-2-1k" \
  -F "prompt=图一的角色放入图二的场景，换姿势，保持角色一致" \
  -F "size=1024x1024" \
  -F "image[]=@/tmp/char.png" \
  -F "image[]=@/tmp/scene.png"
```

### Pitfalls

- 必须用 `-F`（multipart），不能用 `-d`（JSON）
- `/images/generations` + multipart `image[]` 不可用（内部路由到 dall-e）
- `gpt-image-2` 返回 URL；`gpt-image-2-1k/-2k/-4k` 返回 base64

## 响应处理 + 上传 COS

`gpt-image-2` → URL → 下载；`gpt-image-2-1k/-2k/-4k` → base64 → 解码。最终上传 COS。

```bash
# 情况1: base64 响应（-1k/-2k/-4k）
B64=$(echo "$RESP" | python3 -c "import sys,json;u=json.load(sys.stdin)['data'][0]['url'];print(u.split(',',1)[1])")
echo "$B64" | base64 -d > /tmp/out.png

# 情况2: URL 响应（gpt-image-2 无档位）
URL=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['data'][0]['url'])")
curl -sL -o /tmp/out.png "$URL"

# 上传 COS（需安装 cos-nodejs-sdk-v5）
node -e "
const COS = require('cos-nodejs-sdk-v5');
const fs = require('fs');
const cos = new COS({SecretId:process.env.TENCENT_COS_SECRET_ID, SecretKey:process.env.TENCENT_COS_SECRET_KEY});
cos.putObject({Bucket:process.env.TENCENT_COS_BUCKET, Region:process.env.TENCENT_COS_REGION, Key:'images/out.png', Body:fs.createReadStream('/tmp/out.png')}, (e,d) => {
  if(e) { console.error(e); process.exit(1); }
  console.log('https://'+process.env.TENCENT_COS_BUCKET+'.cos.'+process.env.TENCENT_COS_REGION+'.myqcloud.com/images/out.png');
});
"
```

## 视频: `POST /videos`

任务轮询（提交 → 轮询 → 下载）。模型: `grok-imagine-video`

### 文生视频

```bash
# 1. 提交
TASK=$(curl -s "https://api.manxiaobai.online/v1/videos" \
  -H "Authorization: Bearer $MANXIAOBAI_GROK_KEY" \
  -F "model=grok-imagine-video" \
  -F "prompt=..." \
  -F "seconds=6" \
  -F "size=1792x1024" \
  -F "resolution_name=720p" \
  -F "preset=normal")
TASK_ID=$(echo "$TASK" | python3 -c "import sys,json;print(json.load(sys.stdin)['task_id'])")

# 2. 轮询
while true; do
  STATUS=$(curl -s "https://api.manxiaobai.online/v1/videos/$TASK_ID" \
    -H "Authorization: Bearer $MANXIAOBAI_GROK_KEY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status',''))")
  [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] && break
  sleep 10
done

# 3. 下载
curl -sL -o output.mp4 "https://api.manxiaobai.online/v1/videos/$TASK_ID/content" \
  -H "Authorization: Bearer $MANXIAOBAI_GROK_KEY"
```

### 图生视频

加 `-F "input_reference[]=@/path/to/ref.png"` 即可，其余同上。

### Pitfalls

- `seconds` 仅支持 6 或 10
- 典型耗时 ~60-70s（6s），输出 7MB 左右 MP4
