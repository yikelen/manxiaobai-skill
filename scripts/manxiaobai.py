#!/usr/bin/env python3
"""
漫小白 CLI 封装 — 自动加载 .env、选择 Key、处理响应、上传 COS
用法：
  python3 scripts/manxiaobai.py --prompt "描述"                    # 文生图
  python3 scripts/manxiaobai.py --prompt "描述" --image ref.png    # 图生图
  python3 scripts/manxiaobai.py --prompt "描述" --image a.png --image b.png  # 多参考图
  python3 scripts/manxiaobai.py --prompt "描述" --video 6          # 文生视频
"""
import os, sys, json, base64, time, subprocess, argparse
from pathlib import Path
from openai import OpenAI

SKILL_DIR = Path(__file__).resolve().parent.parent


def load_env():
    """加载 .env 文件"""
    env_file = SKILL_DIR / ".env"
    if not env_file.exists():
        print("错误: .env 文件不存在，请先配置凭证", file=sys.stderr)
        sys.exit(1)
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v.strip().strip("'\"")


def pick_key(model: str) -> str:
    """自动选择 Key"""
    if model.startswith("gpt-image-2"):
        return os.environ.get("MANXIAOBAI_IMAGINE_KEY", "")
    elif model.startswith("grok-imagine-"):
        return os.environ.get("MANXIAOBAI_GROK_KEY", "")
    raise ValueError(f"不支持的模型: {model}")


def cos_upload(local_path: str, key: str) -> str:
    """上传 COS 返回公网 URL"""
    cos_node = SKILL_DIR / "scripts" / "cos_upload.js"
    if not cos_node.exists():
        _write_cos_upload_script(cos_node)

    result = subprocess.run(
        ["node", str(cos_node), local_path, key],
        capture_output=True, text=True, timeout=60,
        cwd=str(SKILL_DIR),
        env={**os.environ, "NODE_OPTIONS": "--no-deprecation"},
    )
    data = json.loads(result.stdout)
    if not data.get("success"):
        raise RuntimeError(f"COS 上传失败: {data.get('error')}")
    return data["url"]


def _write_cos_upload_script(path: Path):
    """生成 COS 上传辅助脚本"""
    path.write_text("""\
const COS = require('cos-nodejs-sdk-v5');
const fs = require('fs');
const [file, key] = process.argv.slice(2);
const cos = new COS({
  SecretId: process.env.TENCENT_COS_SECRET_ID,
  SecretKey: process.env.TENCENT_COS_SECRET_KEY,
});
cos.putObject({
  Bucket: process.env.TENCENT_COS_BUCKET,
  Region: process.env.TENCENT_COS_REGION,
  Key: key,
  Body: fs.createReadStream(file),
}, (e, d) => {
  if (e) { console.log(JSON.stringify({success:false,error:e.message})); process.exit(1); }
  const url = `https://${process.env.TENCENT_COS_BUCKET}.cos.${process.env.TENCENT_COS_REGION}.myqcloud.com/${key}`;
  console.log(JSON.stringify({success:true, url}));
});
""")


def handle_response(resp) -> bytes:
    """处理响应：自动识别 base64 或 URL"""
    url = resp.data[0].url or ""
    b64 = getattr(resp.data[0], "b64_json", "") or ""

    if b64 and len(b64) > 1000:
        return base64.b64decode(b64)
    if url.startswith("data:"):
        return base64.b64decode(url.split(",", 1)[1])
    if url.startswith("http"):
        import urllib.request
        return urllib.request.urlopen(url).read()
    raise ValueError("无法识别的响应格式")


def text_to_image(args) -> str:
    """文生图 → 返回 COS 公网 URL"""
    client = OpenAI(api_key=pick_key(args.model), base_url="https://api.manxiaobai.online/v1")
    start = time.time()
    r = client.images.generate(model=args.model, prompt=args.prompt, n=1, size=args.size)
    img = handle_response(r)
    tmp = f"/tmp/manxiaobai_{int(start)}.png"
    with open(tmp, "wb") as f:
        f.write(img)
    ts = time.strftime("%Y%m%d_%H%M%S")
    return cos_upload(tmp, f"images/{args.model}_{ts}.png")


def image_to_image(args) -> str:
    """图生图（单/多参考图）→ 返回 COS 公网 URL"""
    client = OpenAI(api_key=pick_key(args.model), base_url="https://api.manxiaobai.online/v1")

    if not args.image:
        print("错误: 图生图需要 --image 参数", file=sys.stderr)
        sys.exit(1)

    # OpenAI SDK 的 images.edit 使用文件路径
    start = time.time()
    r = client.images.edit(
        model=args.model,
        prompt=args.prompt,
        image=open(args.image[0], "rb"),
        n=1,
        size=args.size,
    )
    img = handle_response(r)
    tmp = f"/tmp/manxiaobai_edit_{int(start)}.png"
    with open(tmp, "wb") as f:
        f.write(img)
    ts = time.strftime("%Y%m%d_%H%M%S")
    return cos_upload(tmp, f"images/edit_{args.model}_{ts}.png")


def video_generate(args) -> str:
    """视频生成 → 返回视频 ID，需手动轮询下载"""
    import requests
    key = pick_key(args.model)
    headers = {"Authorization": f"Bearer {key}"}
    data = {
        "model": args.model,
        "prompt": args.prompt,
        "seconds": str(args.video),
        "size": args.size or "1792x1024",
        "resolution_name": "720p",
        "preset": "normal",
    }
    files = {}
    if args.image:
        files["input_reference[]"] = open(args.image[0], "rb")

    r = requests.post("https://api.manxiaobai.online/v1/videos", headers=headers, data=data, files=files)
    task = r.json()
    print(f"task_id: {task['task_id']}")
    print(f"轮询: curl https://api.manxiaobai.online/v1/videos/{task['task_id']}")
    print(f"下载: curl -L -o out.mp4 https://api.manxiaobai.online/v1/videos/{task['task_id']}/content -H 'Authorization: Bearer {key}'")
    return task["task_id"]


def main():
    load_env()

    parser = argparse.ArgumentParser(description="漫小白 CLI")
    parser.add_argument("--model", default="gpt-image-2-1k", help="模型名")
    parser.add_argument("--prompt", required=True, help="提示词")
    parser.add_argument("--image", action="append", help="参考图（可多次指定）")
    parser.add_argument("--size", default="1024x1024", help="输出尺寸")
    parser.add_argument("--video", type=int, help="生成视频（传秒数 6 或 10）")
    args = parser.parse_args()

    if args.video:
        result = video_generate(args)
    elif args.image:
        result = image_to_image(args)
    else:
        result = text_to_image(args)

    print(result)


if __name__ == "__main__":
    main()
