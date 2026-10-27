"""实验室培训视频 → 编号课程系列（BaoCut）。

  python3 course.py sentences <BaoCut视频目录> <输出.json>     导出句子列表（start/end 秒、text），写计划用
  python3 course.py build <plan.py> [课号 ...]                 按计划出课（派生子视频→旋正→字卡→剪→去口癖→片头片尾→导出）
  python3 course.py qpage <plan.py> <questions.json> <输出目录>  做本地识别存疑确认网页（含原声片段）

plan.py 的写法见 ../templates/plan_example.py。"""
import importlib.util, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cards import slide_png, caption_png, card_png, slides_lesson  # noqa: E402

HARD_FILLERS = {"嗯", "呃", "啊", "哦", "额", "唉", "哎", "诶", "嗯嗯", "啊啊", "哦哦"}
LABELS = ("从「", "撤销")


# ---------- BaoCut 调用 ----------
def bc(*args):
    r = subprocess.run(["baocut", *args, "--json"], capture_output=True, text=True)
    txt = r.stdout.strip()
    try:
        d = json.loads(txt[txt.rindex('{"ok"'):])
    except ValueError:
        sys.exit(f"❌ baocut {' '.join(args[:3])} 输出无法解析: {r.stderr[-800:]}{txt[-800:]}")
    if not d.get("ok"):
        sys.exit(f"❌ baocut {' '.join(args[:3])} 失败: {json.dumps(d.get('error'), ensure_ascii=False)[:1200]}")
    return d["result"]


def inspect(v):
    return bc("videos", "inspect", v)


def apply(v, label, ops):
    return bc("edits", "apply", v, "--expected-revision", inspect(v)["revision"], "--label", label,
              "--operations", json.dumps(ops, ensure_ascii=False))


def ids_by_name(v, names):
    m = {i.get("name"): i["id"] for i in inspect(v)["items"]}
    return [m[n] for n in names]


def place(v, name, asset, start, end, track, extra=lambda iid: []):
    """放一张图并裁到 [start, end)。图片默认 5 秒，离得近会重叠，所以逐张放、逐张裁。"""
    apply(v, f"放{name}", [{"type": "addItem", "asset": asset, "at": round(start, 3), "trackId": track, "name": name}])
    iid = ids_by_name(v, [name])[0]
    apply(v, f"{name}时长", [{"type": "trimItem", "itemId": iid, "edge": "end", "at": round(end, 3)}] + extra(iid))


def reset(v):
    """派生是幂等的：重跑时把本脚本做过的修改全部撤销，回到刚派生的状态。"""
    skip = set()
    for _ in range(200):
        mine = [h for h in bc("videos", "history", v)["entries"]  # inspect 的 recentHistory 只有最近几笔
                if not h["undone"] and not h["label"].startswith(LABELS) and h["transactionId"] not in skip]
        if not mine:
            return
        tx = mine[0]["transactionId"]
        r = subprocess.run(["baocut", "edits", "undo", v, "--transaction-id", tx, "--json"], capture_output=True, text=True)
        if '"ok":true' not in r.stdout.replace(" ", ""):
            skip.add(tx)
    sys.exit(f"❌ {v} 撤销不完，请在 BaoCut 里删掉这个子视频再重跑")


def find_suggestions(o):
    if isinstance(o, dict):
        if isinstance(o.get("suggestions"), list):
            return o["suggestions"]
        o = list(o.values())
    if isinstance(o, list):
        for x in o:
            r = find_suggestions(x)
            if r is not None:
                return r
    return None


# ---------- 句子与时间 ----------
def export_sentences(video, out):
    """按 1000 秒一段取句子；每次调用句子编号会重来，所以按起点去重。"""
    dur = inspect(video)["sequence"]["durationSeconds"]
    got, a = {}, 0
    while a < dur:
        for s in bc("speech", "sentences", video, "--range", f"{a}:{min(a + 1000, dur + 1)}")["sentences"]:
            got[round(s["start"], 2)] = {"start": s["start"], "end": s["end"], "text": s["text"]}
        a += 1000
    S = [got[k] for k in sorted(got)]
    json.dump(S, open(out, "w"), ensure_ascii=False)
    txt = os.path.splitext(out)[0] + ".txt"
    with open(txt, "w") as f:
        f.writelines(f"{int(s['start'] // 60):02d}:{int(s['start'] % 60):02d} {s['text']}\n" for s in S)
    print(f"✅ {len(S)} 句 → {out}（可读版 {txt}）")


def secs(t):
    if isinstance(t, (int, float)):
        return float(t)
    m, s = t.split(":")
    return int(m) * 60 + int(s)


class Plan:
    def __init__(self, path):
        spec = importlib.util.spec_from_file_location("plan", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.m = m
        self.sent = {k: json.load(open(v["sentences"])) for k, v in m.SOURCES.items()}

    def sent_at(self, src, t):
        t = secs(t)
        hits = [s for s in self.sent[src] if t <= s["start"] < t + 1]
        if not hits:
            sys.exit(f"❌ 找不到 {src} {t}s 处的句子：时间要写成句子开头那一秒（见 sentences 导出的 .txt）")
        return hits[0]

    def keep_bounds(self, src, a, b):
        start = self.sent_at(src, a)["start"] - 0.1
        b = secs(b)
        last = max((s for s in self.sent[src] if s["start"] < b), key=lambda s: s["start"])
        return start, min(last["end"] + 0.2, b)


# ---------- 出一课 ----------
def build(P, L):
    m, no, src = P.m, L["no"], L["src"]
    S = m.SOURCES[src]
    d = f"{m.WORK}/{no}"
    os.makedirs(d, exist_ok=True)
    keeps = [P.keep_bounds(src, a, b) for a, b in L["keeps"]]
    span0, span1 = keeps[0][0], keeps[-1][1]

    r = bc("videos", "derive", S["baocut"], "--start", f"{span0:.3f}", "--end", f"{span1:.3f}",
           "--name", f"第{no}课 {L['title']}", "--captions=false", "--yes")
    v, t0 = r["video"]["videoId"], r["range"]["start"]
    if r["reused"]:
        reset(v)
    vitem = next(i for i in inspect(v)["items"] if i["type"] == "video")
    vid, asset = vitem["id"], vitem["asset"]["id"]  # 子视频的素材 ID 与父视频不同

    if S.get("rotate270"):  # 手机横拍却带 -90° 旋转标记：BaoCut 当竖屏读，转回横屏并铺满
        apply(v, "旋正画面", [{"type": "setStyle", "itemId": vid, "mode": "pip"},
                            {"type": "setTransform", "itemId": vid, "x": 50, "y": 50, "w": 56.25, "rot": 270}])

    # 字幕条 + 提示卡：剪之前按素材时间放，默认跟随剪口移动、缩短
    ovs = L["overlays"]
    times = [P.sent_at(src, o[0])["start"] for o in ovs]
    ends = times[1:] + [span1]
    parts = []
    for i, o in enumerate(ovs):
        p = f"{d}/cap{i:02d}.png"
        parts.append((f"字幕{i:02d}", "字幕条", p, caption_png(p, o[1]), times[i], ends[i]))
        if len(o) > 2:
            p = f"{d}/card{i:02d}.png"
            parts.append((f"提示{i:02d}", "提示卡", p, card_png(p, *o[2]), times[i], ends[i]))
    apply(v, "导入字卡", [{"type": "addTrack", "kind": "visual", "name": n} for n in ("字幕条", "提示卡")] +
          [{"type": "importAsset", "path": p, "name": n, "storage": "managed"} for n, _, p, *_ in parts])
    info = inspect(v)
    tracks = {t["name"]: t["id"] for t in info["tracks"]}
    assets = {a["name"]: a["id"] for a in info["assets"]}
    for n, tn, _, pos, a, e in parts:
        place(v, n, assets[n], a - t0, e - t0, tracks[tn],
              lambda iid, pos=pos: [{"type": "setStyle", "itemId": iid, "mode": "pip"},
                                    {"type": "setTransform", "itemId": iid, **pos}])

    gaps = [{"from": round(a[1], 3), "to": round(b[0], 3)} for a, b in zip(keeps, keeps[1:]) if b[0] - a[1] > 0.05]
    if gaps:
        apply(v, "剪掉离题段", [{"type": "addCuts", "assetId": asset, "cuts": gaps}])

    apply(v, "检测口癖与停顿", [{"type": "proposeCuts", "assetId": asset,
                                "detect": {"pauses": True, "fillers": True, "compressTo": 0.3, "fillerLanguage": "zh"}}])
    prop = next(x for x in inspect(v)["documents"] if x["kind"] == "editorial-proposal")
    sugg = find_suggestions(bc("documents", "read", v, "--document-id", prop["id"])) or []
    ids = [s["id"] for s in sugg if s.get("status", "pending") == "pending"
           and (s["kind"] == "pause" or s.get("text", "").strip("，。、 ") in HARD_FILLERS)]
    if ids:
        apply(v, "去口癖与长停顿", [{"type": "acceptCutSuggestions", "proposalId": prop["id"], "suggestionIds": ids}])

    heads = [(f"{d}/intro.png", 3, lambda p: slide_png(p, f"第{no}课  {L['title']}", sub=L.get("sub", m.SUB)))]
    if L.get("panel"):
        heads.append((f"{d}/panel.png", 12, lambda p: slide_png(p, L.get("panel_title", "设备部件"), image=L["panel"])))
    recap = (f"{d}/recap.png", 3 + 1.5 * len(L["recap"]), lambda p: slide_png(p, "本课小结", L["recap"]))
    for p, _, mk in heads + [recap]:
        mk(p)
    lead = sum(h[1] for h in heads)
    info = inspect(v)
    dur = info["sequence"]["durationSeconds"]
    apply(v, "给片头腾位置", [{"type": "moveItems", "moves": [
        {"itemId": i["id"], "offset": lead} for i in info["items"] if i["type"] != "caption"]}])
    apply(v, "导入片头片尾", [{"type": "addTrack", "kind": "visual", "name": "片头片尾"}] +
          [{"type": "importAsset", "path": p, "name": os.path.basename(p), "storage": "managed"} for p, _, _ in heads + [recap]])
    info = inspect(v)
    track = next(t["id"] for t in info["tracks"] if t["name"] == "片头片尾")
    assets = {a["name"]: a["id"] for a in info["assets"]}
    at = 0.0
    for p, ln, _ in heads + [recap]:
        if p == recap[0]:
            at = lead + dur
        place(v, os.path.basename(p), assets[os.path.basename(p)], at, at + ln, track)
        at += ln

    os.makedirs(m.OUT, exist_ok=True)
    name = f"第{no}课_{L['title']}.mp4"
    bc("export", v, "--kind", "video", "--format", "mp4", "--loudness", "--dir", m.OUT,
       "--file-name", name, "--overwrite", "--timeout", "1800")
    print(f"✅ 第{no}课 {v} → {m.OUT}/{name}", flush=True)


# ---------- 存疑确认页 ----------
def qpage(P, qfile, out):
    """questions.json: [{"id":"01","src":"C","s":33,"e":50,"lesson":"第01课","asr":"识别原文","cur":"当前字幕","ask":"要确认什么"}]"""
    Q = json.load(open(qfile))
    os.makedirs(f"{out}/clips", exist_ok=True)
    for q in Q:
        S = P.m.SOURCES[q["src"]]
        pre = ["-noautorotate"] if S.get("rotate270") else []  # 与 BaoCut 里旋正后的方向一致
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *pre, "-ss", str(q["s"]), "-t", str(q["e"] - q["s"]),
                            "-i", S["file"], "-vf", "scale=640:360,fps=30", "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", f"{out}/clips/q{q['id']}.mp4"])
        if r.returncode:
            sys.exit(f"❌ 切片段 q{q['id']} 失败")
    rows = [[q["id"], f"{q['src']} {int(q['s'] // 60)}:{int(q['s'] % 60):02d}", q["lesson"], q["asr"], q["cur"], q["ask"]] for q in Q]
    html = open(os.path.join(HERE, "../templates/qpage.html")).read()
    html = re.sub(r"const Q = \[.*?\n\];", lambda _: "const Q = " + json.dumps(rows, ensure_ascii=False, indent=1) + ";", html, flags=re.S)
    html = re.sub(r"已处理 <b id=\"done\">0</b>/\d+", f"已处理 <b id=\"done\">0</b>/{len(Q)}", html)
    html = html.replace("{{SERIES}}", P.m.SERIES)
    open(f"{out}/识别存疑确认.html", "w").write(html)
    print(f"✅ {len(Q)} 条 → {out}/识别存疑确认.html")


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:] or ["-h"]
    if cmd == "sentences":
        export_sentences(*rest)
    elif cmd == "build":
        P = Plan(rest[0])
        only = rest[1:]
        for L in P.m.LESSONS:
            if only and L["no"] not in only:
                continue
            if L["src"] == "slides":
                slides_lesson(L, P.m.OUT, P.m.WORK, P.m.SUB)
            else:
                build(P, L)
    elif cmd == "qpage":
        qpage(Plan(rest[0]), rest[1], rest[2])
    else:
        print(__doc__)
