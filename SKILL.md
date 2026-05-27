---
name: manxiaobai-skill
description: "漫小白 API：Imagine2 文生图/图生图 + Grok 视频生成。CLI 一键调用，自动处理 Key 选择、base64/URL 响应、COS 上传。"
version: 1.3.0
metadata:
  hermes:
    tags: [image-generation, video-generation, manxiaobai, imagine2, grok, api]
    category: mlops
---

# 漫小白 API

BASE URL: `https://api.manxiaobai.online/v1` | 文档: https://api.manxiaobai.online/about

## 文件结构

```
manxiaobai-skill/
├── .env                       ← 凭证（不入库）
├── .gitignore
├── SKILL.md                   ← 本文件
├── requirements.txt           ← Python 依赖
├── references/
│   └── api-docs-full.md       ← 官方文档存档
└── scripts/
    └── manxiaobai.py          ← CLI 入口脚本
```

## 配置

编辑 `.env` 文件，填入凭证：

```bash
MANXIAOBAI_IMAGINE_KEY=
MANXIAOBAI_GROK_KEY=
TENCENT_COS_SECRET_ID=
TENCENT_COS_SECRET_KEY=
TENCENT_COS_REGION=
TENCENT_COS_BUCKET=
```

## CLI 使用

```bash
pip install -r requirements.txt
npm install

# Linux/Mac
python3 scripts/manxiaobai.py --prompt "提示词"

# Windows
python scripts/manxiaobai.py --prompt "提示词"
```

### 参数

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `--prompt` | 是 | — | 提示词 |
| `--model` | 否 | `gpt-image-2-1k` | 模型名 |
| `--size` | 否 | `1024x1024` | 输出尺寸 |
| `--image` | 否 | — | 参考图路径（图生图），可多次指定 |
| `--video` | 否 | — | 视频秒数，6 或 10 |

### 示例

```bash
# 文生图 → COS 链接
python3 scripts/manxiaobai.py --prompt "一只橘猫在窗台上晒太阳"

# 指定模型和尺寸
python3 scripts/manxiaobai.py --model gpt-image-2-2k --size 2048x1152 --prompt "二次元海报"

# 图生图（单参考图）
python3 scripts/manxiaobai.py --prompt "将背景改为樱花庭院" --image ref.png

# 多参考图
python3 scripts/manxiaobai.py --prompt "图一的角色放入图二的场景" --image char.png --image scene.png

# 文生视频（返回 task_id 和下载命令）
python3 scripts/manxiaobai.py --prompt "海边玩耍的小狗" --video 6

# 图生视频
python3 scripts/manxiaobai.py --prompt "镜头缓慢推进" --video 6 --image ref.png
```

所有生图命令返回统一格式：COS 公网 URL。

## 自动选择 Key

- `gpt-image-2*` → `MANXIAOBAI_IMAGINE_KEY`
- `grok-imagine-video` → `MANXIAOBAI_GROK_KEY`

## 模型选择

| 场景 | 模型 | 说明 |
|---|---|---|
| 头像、封面草稿、普通图 | `gpt-image-2-1k` | **默认首选** |
| 海报、角色设定、较高清 | `gpt-image-2-2k` | 高清素材 |
| 高分辨率成片 | `gpt-image-2-4k` | 耗时最长 |
| 返回 URL 直链 | `gpt-image-2` | 无需处理 base64 |

⚠️ 模型名和尺寸档位必须保持一致，不能混搭。

## 尺寸表

| 模型 | 可用尺寸 |
|---|---|
| gpt-image-2-1k | 1024x1024, 1536x1024, 1024x1536, 1824x1024, 1024x1824 |
| gpt-image-2-2k | 2048x2048, 2048x1152, 1152x2048, 2048x1536, 1536x2048 |
| gpt-image-2-4k | 2880x2880, 3840x2160, 2160x3840, 3312x2480, 2480x3312, 3840x1648 |
| gpt-image-2 | 1024x1024, 1536x1024, 1024x1536, 1824x1024, 1024x1824, 1360x1024, 1024x1360, 2384x1024 |

超时: 1K 180s+ / 2K 300s+ / 4K 600s+

## 视频生成

模型 `grok-imagine-video`。任务轮询模式，CLI 输出 task_id 和轮询/下载命令。

| 参数 | 值 |
|---|---|
| seconds | 6 或 10 |
| size | 1024x1024, 1792x1024, 1024x1792 |
| resolution_name | 720p |
| preset | normal |

典型耗时 ~60-70s（6s），输出 ~7MB MP4。

## 错误参考

| 错误 | 原因 |
|---|---|
| `401` | Key 错误或未携带 |
| `model_not_found` | 模型名写错或 Key 无权限 |
| `invalid size` | 尺寸不支持 |
| `upstream returned error` | 上游故障，稍后重试 |
| `Failed to fetch` | 超时 |
