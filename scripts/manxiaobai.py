#!/usr/bin/env python3
"""
漫小白 CLI — 自动加载 .env、选择 Key、处理响应、上传 COS

用法:
  python3 manxiaobai.py --prompt "描述"                           # 文生图
  python3 manxiaobai.py --prompt "描述" --image ref.png            # 图生图（单参考图）
  python3 manxiaobai.py --prompt "描述" --image a.png --image b.png  # 多参考图
  python3 manxiaobai.py --prompt "描述" --video 6                  # 文生视频
  python3 manxiaobai.py --prompt "描述" --video 6 --image ref.png  # 图生视频

参数:
  --prompt     提示词（必填）
  --model      模型名，默认 gpt-image-2-1k
  --size       输出尺寸，默认 1024x1024
  --image      参考图路径，可多次指定（图生图/图生视频）
  --video      视频秒数，传 6 或 10

返回:
  生图: COS 公网 URL
  视频: task_id + 轮询/下载命令
"""
import os, sys, json, base64, time, subprocess, argparse
import requests
from pathlib import Path
from openai import OpenAI

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gpt-image-2-1k"
DEFAULT_SIZE = "1024x1024"
VIDEO_SIZE = "1792x1024"


def load_env():
    env_file = SKILL_DIR / ".env"
    if not env_file.exists():
        sys.exit("错误: .env 文件不存在，请先配置凭证")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v.strip().strip("'\"")


def pick_key(model: str) -> str:
    if model.startswith("gpt-image-2"):
        return os.environ["MANXIAOBAI_IMAGINE_KEY"]
    if model.startswith("grok-imagine-"):
        return os.environ["MANXIAOBAI_GROK_KEY"]
    sys.exit(f"不支持的模型: {model}")


def cos_upload(local_path: str, key: str) -> str:
    r = subprocess.run(
        ["node", str(SKILL_DIR / "scripts" / "cos_upload.js"), local_path, key],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        sys.exit(f"COS 上传失败: {r.stderr}")
    return r.stdout.strip()


def handle_response(resp) -> bytes:
    url = resp.data[0].url or ""
    b64 = getattr(resp.data[0], "b64_json", "") or ""
    if b64 and len(b64) > 1000:
        return base64.b64decode(b64)
    if url.startswith("data:"):
        return base64.b64decode(url.split(",", 1)[1])
    if url.startswith("http"):
        import urllib.request
        return urllib.request.urlopen(url).read()
    sys.exit("无法识别的响应格式")


def generate_image(args) -> str:
    client = OpenAI(api_key=pick_key(args.model), base_url="https://api.manxiaobai.online/v1")
    start = time.time()

    if args.image:
        files_args = [("image[]", open(img, "rb")) for img in args.image]
        r = client.images.edit(model=args.model, prompt=args.prompt, image=open(args.image[0], "rb"), n=1, size=args.size)
    else:
        r = client.images.generate(model=args.model, prompt=args.prompt, n=1, size=args.size)

    img_data = handle_response(r)
    ext = "png"
    tmp = f"/tmp/manxiaobai_{int(start)}.{ext}"
    with open(tmp, "wb") as f:
        f.write(img_data)

    ts = time.strftime("%Y%m%d_%H%M%S")
    return cos_upload(tmp, f"images/{args.model}_{ts}.{ext}")


def generate_video(args) -> str:
    model = "grok-imagine-video"
    key = pick_key(model)
    headers = {"Authorization": f"Bearer {key}"}
    files = {
        "model": (None, model),
        "prompt": (None, args.prompt),
        "seconds": (None, str(args.video)),
        "size": (None, VIDEO_SIZE),
        "resolution_name": (None, "720p"),
        "preset": (None, "normal"),
    }
    if args.image:
        files["input_reference[]"] = (os.path.basename(args.image[0]), open(args.image[0], "rb"))

    r = requests.post("https://api.manxiaobai.online/v1/videos", headers=headers, files=files)
    task = r.json()
    if "task_id" not in task:
        sys.exit(f"视频提交失败: {json.dumps(task, ensure_ascii=False)}")
    tid = task["task_id"]
    print(f"task_id: {tid}")
    print(f"轮询: curl https://api.manxiaobai.online/v1/videos/{tid} -H 'Authorization: Bearer ...'")
    print(f"下载: curl -L -o out.mp4 https://api.manxiaobai.online/v1/videos/{tid}/content -H 'Authorization: Bearer ...'")
    return tid


def main():
    load_env()

    p = argparse.ArgumentParser(description="漫小白 CLI")
    p.add_argument("--prompt", required=True, help="提示词（必填）")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"模型名（默认 {DEFAULT_MODEL}）")
    p.add_argument("--size", default=DEFAULT_SIZE, help=f"输出尺寸（默认 {DEFAULT_SIZE}）")
    p.add_argument("--image", action="append", help="参考图路径，可多次指定")
    p.add_argument("--video", type=int, choices=[6, 10], help="生成视频，秒数（6 或 10）")
    args = p.parse_args()

    if args.video:
        result = generate_video(args)
    else:
        result = generate_image(args)

    print(result)


if __name__ == "__main__":
    main()
