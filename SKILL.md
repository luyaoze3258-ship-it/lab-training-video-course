---
name: lab-training-video-course
description: "把自己录的实验室仪器培训视频（手机拍、多人对话、口语多）剪成面向学生的编号课程系列：只留要点、去口癖和长停顿、字幕条加注意/参数/术语提示卡、片头片尾小结、安全须知课，并出课程目录、操作手册、规范性检查和本地识别存疑确认网页。用 BaoCut 剪，每课是可编辑的子视频。当用户说「把这几个培训视频剪一下」「参考之前的剪辑规范」「做成课程系列」，或目录里新放了仪器操作录像要剪成教学课时使用。不用于口播短视频、Vlog、宣传片。"
metadata:
  version: "1.1.0"
  works-with: "Claude Code, Codex, WorkBuddy 等支持 Agent Skills（SKILL.md）的智能体"
---

> 下文的 `<技能目录>` 指本 SKILL.md 所在目录的绝对路径；`scripts/`、`templates/` 都在它下面。

# 实验室培训视频 → 课程系列

脚本：`scripts/course.py`（主流程）、`scripts/cards.py`（字卡渲染）；模板：`templates/plan_example.py`、`templates/qpage.html`。
需要：BaoCut 命令行 `baocut`（`baocut runtime ensure` 启动）、ffmpeg、Python 3.9+ 与 Pillow、一款中文字体（自动查找 macOS / Linux / Windows 常见字体，或设环境变量 `LTVC_FONT`）。
首次使用先运行 `bash <技能目录>/install.sh --check` 检查依赖。

## 剪辑规范（默认都要满足，用户另有要求时以用户为准）

- 只留关键操作和讲解，剪掉寒暄、闲聊、学员试操作、与操作无关的讨论（如采购、品牌）。
- 去口癖和长停顿；放大、标注；注意 / 参数 / 术语提示卡；每课有片头和片尾小结；做音频处理。
- **课程之间内容不重复**：多个视频讲同一件事时，以讲得最全的那个为主，其余只补它没有的。
- 按教学顺序编号（不是按素材顺序）：第00课安全须知 → 设备认识 → 操作 → 维护与应急。
- 对照国标、高校规范、厂商规程检查操作，不合规处做成【注意】卡，并写进 `规范性检查.md`。
- 交付：课程 mp4、`课程目录.html`、`课程目录.md`、`操作手册.md`、`规范性检查.md`、`识别存疑待确认.md`，加上本地确认网页。
  markdown 都要带 frontmatter（name/status/created/updated），时间用 `date -u +"%Y-%m-%dT%H:%M:%SZ"` 取真实值。
- 用中文回复和写文档。

## 流程

1. **探测素材**：`ffprobe` 看时长、帧率、`rotation`。带 `rotation=-90`、但用 `-noautorotate` 截出来是正的横屏，说明是横拍误标 → 计划里设 `rotate270: True`。
2. **转录**：`baocut transcribe --file <绝对路径> --language zh-CN --json`，长视频放后台跑。用 `baocut videos list --json` 找视频目录（`dir` 字段）。
3. **导出句子**：`python3 <技能目录>/scripts/course.py sentences <BaoCut视频目录> <工作目录>/sentX.json`，同时生成可读的 `.txt`，每行是 `mm:ss 句子`。
4. **看画面**：`ffmpeg -noautorotate -i 源 -vf "fps=1/20,scale=192:-1,tile=10x8"` 拼缩略图，和文稿对照；读面板标签时截高清帧放大看。
5. **先出方案，再动手**。素材之间有重叠时，先停下来问用户两件事（有提问工具就用提问工具）：合并成一个系列还是分开；用 BaoCut 还是 ffmpeg（默认 BaoCut）。方案列出每课的标题、来源时间段、要剪掉什么。
6. **写计划**：复制 `<技能目录>/templates/plan_example.py` 到工作目录改写。
   - `keeps` 写保留段，起点必须是某句开头那一秒（照 `.txt` 里的时间写）。
   - `overlays` 每条是一行底部字幕，可以带一张提示卡。
   - 字幕要按画面核对过的理解来写，不要照抄识别原文。
   - 纯字卡课 `src: "slides"`。面板讲解课可以先用 PIL 在高清帧上画标注图，再挂到 `panel`。
7. **校验计划**：`python3 -c` 载入 Plan，对每课调用 `keep_bounds` 和 `sent_at`，确认锚点都能对上，并打印每课保留的时长。
8. **试出一课**：`python3 <技能目录>/scripts/course.py build plan.py 01`，然后抽帧检查：画面方向对、视频没被盖黑、字幕条和提示卡位置对、片头片尾都在。
9. **并行出全部**（每课约 5～8 分钟，主要花在逐张放图）。要在 bash 里分组跑，zsh 不会拆分 `$g`：
   `bash -c 'for g in "02 06 10" "03 07 11" "04 08 12" "05 09 13"; do python3 <技能目录>/scripts/course.py build plan.py $g > log_${g// /_}.txt 2>&1 & done; wait'`。整条命令要用智能体的「后台运行」能力跑（没有就用 `nohup … &` 并把输出写进日志）。
   注意：在一次性 shell 调用里只用 `&` 放后台，进程会随 shell 退出被杀掉。
10. **验收**：每课抽 4 帧拼一张总览图检查，ffprobe 记录时长。声音顺不顺要用户来听，汇报时写明哪些只是抽帧看过。
11. **文档**：写课程目录（课号、标题、时长、关键词、来源时间段、剪掉了什么）、操作手册、规范性检查、识别存疑。
    - `课程目录.md` 的表格固定为 `| 课号 | 标题 | 时长 | 关键词 | 来源 | 部分 |`，「部分」写分组名（如 安全 / 增压泵 / LNT 低温附件）。
    - 然后运行 `python3 <技能目录>/scripts/course.py index <课程输出目录>`，生成 `课程目录.html`：双击打开，左边是播放器，右边是按部分分组的课程列表（带封面帧），可以搜索，播完自动接下一课，操作手册和规范性检查在页签里。时长取自成片实际长度；文档改动后重新运行即可。
12. **存疑确认网页**：写 `questions.json`，每条 `{id,src,s,e,lesson,asr,cur,ask}`（s、e 是源视频秒），然后运行
    `python3 <技能目录>/scripts/course.py qpage plan.py questions.json <输出目录>/存疑确认`。
    - 生成的本地 HTML 双击就能打开，每条带原声片段，答案存在浏览器里。
    - 用户全部选完点「导出结果」，得到 JSON：`{"q01":{"c":"ok|edit|skip","v":"正确说法"}}`。
    - 拿到结果后改计划里的字幕，重跑对应课程。重跑会自动撤销上一次做过的修改。
13. **记录**：智能体有记忆或笔记机制时，记下这次的系列、输出位置和新踩的坑。

## BaoCut 的坑（都已在脚本里处理，排查时参考）

- `videos derive` 出来的子视频，素材 ID 和父视频不同：要从子视频的视频片段上读 `asset.id`。
- 带旋转标记的横拍片：`setStyle mode=pip` + `setTransform {x:50,y:50,w:56.25,rot:270}`；只设 rot=90 会倒置并缩小。
- 导出不认 PNG 透明通道，透明处会变黑、整个画面被盖住：字幕条和提示卡都做成不透明的小图，用画中画摆放。
- 图片加到时间线上默认 5 秒：同一轨上间隔不到 5 秒的两张会重叠报错（TIMELINE_OVERLAP），所以要一张一张放、放一张裁一张。
- `edits apply` 返回的 `createdIds` 顺序和操作顺序不一致：按片段 name 查 ID。
- `inspect` 里的 recentHistory 只有最近几条，完整历史用 `videos history`。有些事务撤不了（UNDO_UNAVAILABLE），跳过即可。
- `derive` 是幂等的：同一区间再调用会拿回原来那个子视频（reused），要先撤销自己上次做的修改再重做。
- 中途杀掉出片进程时，BaoCut 里已经提交的导出任务不会停，会一直占着导出队列（导出是一个接一个排队的），还会用旧内容覆盖成片：先 `baocut jobs list --json` 找出这些任务，用 `baocut jobs cancel <jobId>` 取消。
- 被杀掉的那次运行留下的子视频，撤销可能清不干净，会残留重复的字幕轨道：脚本检测到残留就停下，这时用 `FRESH=1 python3 … build plan.py NN` 派生一个全新子视频，旧的让用户在 BaoCut 里手动删。
- `videos frames` 取的是素材原帧，看不到旋转和叠加：检查合成效果要 `export --range a:b --purpose preview`。
- 字幕层：派生时用 `--captions=false`，识别错字太多，改用自己写的字幕条。
- 没有降噪，只有导出时 `--loudness`。
- `speech sentences` 每次调用句子编号都从头算：合并多段结果时按起点时间去重。
- BaoCut 只链接原始文件：交付前提醒用户别删原视频，删了就不能重新导出。删除视频这类操作要让用户自己来做。

## 其他坑

- 在 shell 循环或 heredoc 里调 ffmpeg 必须加 `-nostdin`，否则它会吃掉 stdin，后面几行参数就丢了。
- 本机 ffmpeg 没有 drawtext 和 subtitles 滤镜：文字一律用 PIL 画成图片。
- 课程标题里不能有 `/`（导出文件名会失败）。
- 磁盘空间常常紧张：中间文件放临时目录，用完清理。
