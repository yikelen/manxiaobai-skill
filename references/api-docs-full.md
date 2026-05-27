# 漫小白 API 完整文档

> 来源: https://api.manxiaobai.online/about
> 版本: 2026-05-24

## BASE URL
```
https://api.manxiaobai.online/v1
```

认证：`Authorization: Bearer YOUR_API_KEY`

---

## 一、快速开始

检查模型列表：
```bash
curl https://api.manxiaobai.online/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

最小生图测试：
```bash
curl https://api.manxiaobai.online/v1/images/generations \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2-1k",
    "prompt": "一张适合漫剧封面的二次元少女头像，干净背景，精致光影",
    "size": "1024x1024",
    "response_format": "url"
  }'
```

---

## 二、当前推荐模型

| 模型名 | 用途 | 接口 |
|---|---|---|
| gpt-image-2 | 兼容生图模型 | /images/generations、/images/edits |
| gpt-image-2-1k | Imagine2 1K | /images/generations、/images/edits |
| gpt-image-2-2k | Imagine2 2K | /images/generations、/images/edits |
| gpt-image-2-4k | Imagine2 4K | /images/generations、/images/edits |
| grok-imagine-image | Grok 文生图 | /images/generations |
| grok-imagine-image-edit | Grok 图生图 | /images/edits |
| grok-imagine-video | Grok 视频 | /videos |

---

## 三、Imagine2 / GPT Image 2 文生图

**POST /images/generations**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| model | string | 是 | gpt-image-2-1k、gpt-image-2-2k、gpt-image-2-4k |
| prompt | string | 是 | 图片提示词 |
| size | string | 否 | 输出尺寸 |
| quality | string | 否 | 推荐 auto |
| n | number | 否 | 生成数量，建议 1 |
| response_format | string | 否 | 推荐 url |

---

## 四、图生图 / 改图

**POST /images/edits** (multipart/form-data)

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| model | string | 是 | gpt-image-2-xk |
| prompt | string | 是 | 描述期望改动 |
| image[] | file | 是 | 参考图（可多次传） |
| size | string | 否 | 输出尺寸 |
| quality | string | 否 | 推荐 auto |
| response_format | string | 否 | 推荐 url |

多参考图按上传顺序传给模型，提示词中明确"图一、图二、图三"分别代表什么。

---

## 五、Imagine2 尺寸表

**1K 常用：** 1024x1024、1536x1024、1024x1536、1824x1024、1024x1824
**2K 常用：** 2048x2048、2048x1152、1152x2048、2048x1536、1536x2048
**4K 常用：** 2880x2880、3840x2160、2160x3840、3312x2480、2480x3312、3840x1648

---

## 六、Grok 图片

**Grok 文生图：** `POST /images/generations` + `model: grok-imagine-image`
**Grok 图生图：** `POST /images/edits` + `model: grok-imagine-image-edit`（建议 1024x1024）

---

## 七、Grok 视频

**POST /videos** (multipart/form-data)

| 参数 | 推荐值 | 说明 |
|---|---|---|
| seconds | 6、10 | 当前只支持 6s 或 10s |
| size | 1024x1024、1792x1024、1024x1792 | 对应 1:1、16:9、9:16 |
| resolution_name | 720p | 推荐默认 |
| preset | normal | 推荐默认 |

任务模式：提交 → 轮询 `GET /videos/VIDEO_ID` → 下载 `GET /videos/VIDEO_ID/content`

---

## 八、错误说明

| 错误 | 原因 | 处理 |
|---|---|---|
| 401 | Key 错误/未携带 | 检查 Authorization header |
| model_not_found | 模型名错误/无权限 | 检查模型列表和分组 |
| invalid size | 尺寸不支持 | 换尺寸表中值 |
| upstream error | 上游额度/风控 | 记录详情，稍后重试 |

---

## 九、生产建议

- API Key 放服务端，不写前端代码
- 图片默认读 `data[0].url`，尽快下载保存
- 不要默认用 b64_json
- 视频用任务轮询
- 超时：1K 180s+、2K 300s+、4K 600s+
