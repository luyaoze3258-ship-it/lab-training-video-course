"""生成课程目录 HTML：读 课程目录.md 的表格、成片实际时长、每课一张封面帧（内嵌），附操作手册与规范性检查。
用法：python3 index_page.py <课程输出目录>   （也可经 course.py index 调用）
课程目录.md 的表格：| 课号 | 标题 | 时长 | 关键词 | 来源 | 部分(可选) |；没有「部分」列时按 00=安全、其余=课程分组。"""
import base64, glob, html, json, os, re, subprocess, sys, tempfile

if len(sys.argv) < 2:
    sys.exit(__doc__)
D = os.path.expanduser(sys.argv[1])


def dur(f):
    s = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                             capture_output=True, text=True).stdout)
    return f"{int(s // 60)}:{int(s % 60):02d}", s


def poster(f, s):
    fd, tmp = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(s * 0.3), "-i", f, "-frames:v", "1",
                    "-vf", "scale=320:-2", "-q:v", "6", tmp], check=True)
    b = base64.b64encode(open(tmp, "rb").read()).decode()
    os.remove(tmp)
    return "data:image/jpeg;base64," + b


def strip_fm(t):
    return re.sub(r"\A---\n.*?\n---\n", "", t, flags=re.S)


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def md(t):
    """够用的 Markdown：标题、表格、有序/无序列表、段落。"""
    out, lines, i = [], strip_fm(t).splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s\-|:]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[1:]
            out.append("<div class=tbl><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) +
                       "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) +
                       "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,3}) (.*)", ln)
        if m:
            lv = len(m.group(1)) + 1
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
        elif re.match(r"^\s*(- |\d+\. )", ln):
            tag = "ol" if re.match(r"^\s*\d+\. ", ln) else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*(- |\d+\. )", lines[i]):
                items.append(re.sub(r"^\s*(- |\d+\. )", "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


cat = open(f"{D}/课程目录.md").read()
rows = [[c.strip() for c in ln.strip().strip("|").split("|")]
        for ln in cat.splitlines() if re.match(r"^\| \d\d \|", ln)]
lessons = []
for row in rows:
    no, title, kw = row[0], row[1], row[3]
    part = row[5] if len(row) > 5 and row[5] else ("安全" if no == "00" else "课程")
    f = glob.glob(f"{D}/第{no}课_*.mp4")
    if not f:
        sys.exit(f"❌ 找不到第{no}课视频")
    d, s = dur(f[0])
    lessons.append({"no": no, "title": title, "kw": kw, "dur": d, "secs": s,
                    "file": os.path.basename(f[0]), "img": poster(f[0], s),
                    "part": part})
total = sum(l["secs"] for l in lessons)
m = re.search(r"^# (.+?)( · 目录)?$", strip_fm(cat), flags=re.M)
title = m.group(1) if m else os.path.basename(D)
docs = [(n, md(open(f"{D}/{n}.md").read())) for n in ("操作手册", "规范性检查") if os.path.exists(f"{D}/{n}.md")]

tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../templates/index.html")).read()
page = (tpl.replace("{{TITLE}}", html.escape(title))
        .replace("{{META}}", f"{len(lessons)} 课 · 共 {int(total // 60)} 分钟")
        .replace("{{LESSONS}}", json.dumps(lessons, ensure_ascii=False))
        .replace("{{DOCTABS}}", "".join(f'<button type="button" class="tab" data-tab="d{i}">{n}</button>' for i, (n, _) in enumerate(docs)))
        .replace("{{DOCS}}", "".join(f'<section class="doc" id="d{i}" hidden>{h}</section>' for i, (_, h) in enumerate(docs))))
open(f"{D}/课程目录.html", "w").write(page)
print(f"✅ {D}/课程目录.html（{len(lessons)} 课，{os.path.getsize(f'{D}/课程目录.html') // 1024} KB）")
