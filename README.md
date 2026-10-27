# lab-training-video-course

把自己用手机录的**实验室仪器培训视频**，交给 AI 智能体剪成面向学生的**编号课程系列**。

- 只留关键操作和讲解，自动去掉口癖（嗯、呃、啊…）和长停顿，剪掉闲聊
- 每课都有：片头、底部步骤字幕条、【注意】/【参数】/【术语】提示卡、片尾小结
- 自动出一节「第00课 安全须知」
- 一并交付：可双击打开的 `课程目录.html`（播放器 + 搜索 + 文档页签）、`课程目录.md`、`操作手册.md`、`规范性检查.md`（对照国标、高校规范、厂商规程），以及**本地识别存疑确认网页**（每条附原声片段，确认后导出 JSON）
- 用 BaoCut 剪辑，每课都是可在 BaoCut 编辑器里继续调整的子视频

这是一个 [Agent Skills](https://agentskills.io) 格式的技能（`SKILL.md` + 脚本），适用于 **Claude Code、Codex、WorkBuddy** 等支持 Skills 的智能体。

## 安装

### 一行安装（Claude Code / Codex，macOS 或 Linux）

```bash
git clone https://github.com/luyaoze3258-ship-it/lab-training-video-course.git ~/lab-training-video-course
bash ~/lab-training-video-course/install.sh
```

`install.sh` 会：
1. 检查依赖：python3、Pillow、ffmpeg、baocut、中文字体；缺 Pillow 时自动安装。
2. 把技能软链接到 `~/.claude/skills/`、`~/.codex/skills/`、`~/.agents/skills/`。

以后 `git pull` 就能更新。只检查依赖：`bash install.sh --check`；想复制而不是软链接：`bash install.sh --copy`。

### 只装到 Codex

```bash
git clone https://github.com/luyaoze3258-ship-it/lab-training-video-course.git ~/.codex/skills/lab-training-video-course
```

### WorkBuddy 及其他智能体

到 [Releases](https://github.com/luyaoze3258-ship-it/lab-training-video-course/releases) 下载 `lab-training-video-course.zip`，在智能体的「技能管理 → 导入技能」里导入；或把整个仓库目录放进它的技能目录。

## 依赖

| 依赖 | 用途 | 安装 |
|---|---|---|
| BaoCut（含命令行 `baocut`） | 转录、剪辑、导出 | 安装 BaoCut 桌面应用，启用命令行 |
| ffmpeg | 纯字卡课、存疑确认页的原声片段 | `brew install ffmpeg` / `sudo apt install ffmpeg` / `winget install ffmpeg` |
| Python 3.9+、Pillow | 画字卡 | `pip install -r requirements.txt` |
| 中文字体 | 字卡文字 | 自动查找系统字体；Linux：`sudo apt install fonts-noto-cjk`；也可 `export LTVC_FONT=字体路径` |

## 使用

装好后新开一个会话，对智能体说：

> 把 ~/Videos/某仪器培训 里的几个视频剪成课程系列

智能体会按 `SKILL.md` 的流程走：
1. 探测素材，用 BaoCut 转录。
2. 导出句子、看画面，先给你一份分课方案确认。
3. 写课程计划 `plan.py`，先试出一课给你看，再并行出全部。
4. 抽帧验收，写好四份文档，生成存疑确认网页。

你在网页里确认完识别存疑的地方、导出 JSON 交回，它会改好字幕再重出对应的课。

也可以手动跑脚本：

```bash
S=~/lab-training-video-course/scripts
python3 $S/course.py sentences <BaoCut视频目录> sentA.json                 # 导出句子（写计划用）
cp ~/lab-training-video-course/templates/plan_example.py plan.py          # 按示例写计划
python3 $S/course.py build plan.py 01                                     # 先出一课
python3 $S/course.py build plan.py                                        # 出全部
python3 $S/course.py qpage plan.py questions.json ./存疑确认               # 生成本地确认网页
python3 $S/course.py index ~/Downloads/某仪器培训课程                       # 生成课程目录.html
```

计划文件的格式见 [`templates/plan_example.py`](templates/plan_example.py)。

## 目录

```
SKILL.md                 智能体读的流程与规范
install.sh               依赖检查 + 安装
scripts/course.py        主流程：sentences / build / qpage
scripts/cards.py         字幕条、提示卡、幻灯片渲染；纯字卡课出片
scripts/index_page.py    课程目录.html 生成
templates/index.html     课程目录网页模板
templates/plan_example.py  课程计划示例
templates/qpage.html     存疑确认网页模板
```

## 已知限制

- BaoCut 没有降噪，导出时只做响度统一。
- 字幕条和提示卡是静态图片。
- 每课出片约 5～8 分钟，多课可以分组并行跑。
- BaoCut 只引用原始视频文件，出片完成前不要删除原视频。

## License

MIT
