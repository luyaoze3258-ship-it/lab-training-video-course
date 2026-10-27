"""字卡渲染：幻灯片（片头/小结/安全须知）与 BaoCut 用的不透明字幕条、提示卡，以及纯字卡课的 ffmpeg 出片。"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
COLORS = {"注意": (200, 40, 40), "参数": (30, 100, 200), "术语": (30, 140, 80)}
FONT_CANDIDATES = [  # 环境变量 LTVC_FONT 优先，其次按 macOS / Linux / Windows 常见中文字体找
    os.environ.get("LTVC_FONT", ""),
    "/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc", "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
]
FONT = next((p for p in FONT_CANDIDATES if p and os.path.exists(p)), None)


def font(sz):
    if not FONT:
        sys.exit("❌ 找不到中文字体：安装 Noto Sans CJK（Linux: apt install fonts-noto-cjk），或设置环境变量 LTVC_FONT=字体文件路径")
    return ImageFont.truetype(FONT, sz)


def wrap(text, f, maxw, draw):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=f) > maxw:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    return lines + [cur] if cur else lines


def slide_png(path, title, lines=(), sub=None, image=None):
    im = Image.new("RGB", (W, H), (22, 34, 52))
    d = ImageDraw.Draw(im)
    if image:
        im.paste(Image.open(image).convert("RGB").resize((W, H)), (0, 0))
        d.rectangle([0, 0, W, 70], fill=(22, 34, 52))
        d.text((30, 14), title, font=font(36), fill="white")
        im.save(path)
        return
    d.text((80, 80 if lines else 260), title, font=font(52), fill="white")
    if sub:
        d.text((80, 160 if lines else 350), sub, font=font(32), fill=(170, 200, 230))
    y = 240
    for ln in lines:
        for j, part in enumerate(wrap(ln, font(32), W - 220, d)):
            d.text((100 if j == 0 else 132, y), ("• " if j == 0 else "") + part, font=font(32), fill=(235, 235, 235))
            y += 48
        y += 10
    im.save(path)


def caption_png(path, text):
    """底部字幕条：不透明（BaoCut 导出不认透明通道），返回画中画位置（画幅百分比）。"""
    f = font(34)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = wrap(text, f, W - 120, probe)
    bh = 24 + 48 * len(lines)
    im = Image.new("RGB", (W, bh), (24, 28, 32))
    dr = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        dr.text(((W - dr.textlength(ln, font=f)) / 2, 12 + 48 * i), ln, font=f, fill="white")
    im.save(path)
    return {"x": 50, "y": round(100 - bh / H * 50, 3), "w": 100}


def card_png(path, kind, text):
    """左上角提示卡（注意/参数/术语）：不透明，返回画中画位置。"""
    f, fk = font(28), font(26)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = wrap(text, f, 520, probe)
    bw = int(max(160, 40 + max(probe.textlength(l, font=f) for l in lines)))
    bh = 64 + 40 * len(lines)
    c = COLORS[kind]
    im = Image.new("RGB", (bw, bh), (250, 250, 250))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, bw - 1, bh - 1], outline=c, width=4)
    dr.rectangle([0, 0, 96, 40], fill=c)
    dr.text((16, 4), kind, font=fk, fill="white")
    for i, ln in enumerate(lines):
        dr.text((20, 52 + 40 * i), ln, font=f, fill=(20, 20, 20))
    im.save(path)
    return {"x": round((24 + bw / 2) / W * 100, 3), "y": round((24 + bh / 2) / H * 100, 3), "w": round(bw / W * 100, 3)}


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
       "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]


def _run(cmd):
    r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", *cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"❌ ffmpeg 失败: {r.stderr[-1200:]}")


def slides_lesson(L, out_dir, work_dir, sub):
    """纯字卡课（如第00课安全须知）：片头 + 每页幻灯片，静音，ffmpeg 拼接。"""
    d = f"{work_dir}/{L['no']}"
    os.makedirs(d, exist_ok=True)
    pages = [(f"第{L['no']}课  {L['title']}", (), L.get("sub", sub), None, 3)] + \
            [(it["slide"], it.get("lines", ()), None, it.get("image"), it["dur"]) for it in L["items"]]
    parts = []
    for i, (title, lines, s, img, dur) in enumerate(pages):
        p, out = f"{d}/{i:02d}.png", f"{d}/{i:02d}.mp4"
        slide_png(p, title, lines, sub=s, image=img)
        _run(["-loop", "1", "-t", str(dur), "-i", p, "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=stereo",
              "-vf", f"scale={W}:{H},fps=30", "-shortest", *ENC, out])
        parts.append(out)
    with open(f"{d}/list.txt", "w") as f:
        f.writelines(f"file '{x}'\n" for x in parts)
    os.makedirs(out_dir, exist_ok=True)
    final = f"{out_dir}/第{L['no']}课_{L['title']}.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", f"{d}/list.txt", "-c", "copy", "-movflags", "+faststart", final])
    print(f"✅ 第{L['no']}课 → {final}", flush=True)
