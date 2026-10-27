"""课程计划示例：两段素材（A = 厂家完整讲解，手机横拍带旋转标记；B = 补充实操）剪成 4 课。
复制到工作目录改写，然后：python3 <技能目录>/scripts/course.py build plan.py [课号 ...]

SOURCES: 每路素材一项
  baocut     BaoCut 视频目录（`baocut videos list --json` 的 dir）
  file       原始视频文件（做存疑确认页的原声片段用）
  sentences  `course.py sentences` 导出的 json
  rotate270  手机横拍却带 -90° 旋转标记时设 True（ffprobe 看 rotation=-90，且 -noautorotate 截帧是正的）
LESSONS: src 为 SOURCES 的键，或 "slides"（纯字卡课，items 每页 {slide, lines, dur}）
  keeps      保留段 [起句时刻, 止时刻)：起句时刻写成某句开头那一秒（mm:ss 或秒，照 sentences 导出的 .txt）
  overlays   [起句时刻, 底部字幕, (注意|参数|术语, 卡片文字)]，显示到下一条为止；卡片可省略
  recap      片尾小结要点
  panel      可选：片头后插一张标注图（12 秒），panel_title 是它的标题"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.expanduser("~/Videos/培训原始录像")          # 原始视频所在目录
BAOCUT = os.path.expanduser("~/.baocut/projects/CLI")      # BaoCut 项目目录

SERIES = "某仪器培训课程"                  # 存疑确认页标题、导出文件名
SUB = "某仪器操作与维护培训"               # 片头副标题
OUT = os.path.expanduser("~/Downloads/某仪器培训课程")      # 成片输出目录
WORK = f"{HERE}/work"                     # 字卡等中间文件
SOURCES = {
    "A": {"baocut": f"{BAOCUT}/vendor-training", "file": f"{RAW}/vendor-training.mp4",
          "sentences": f"{HERE}/sentA.json", "rotate270": True},
    "B": {"baocut": f"{BAOCUT}/hands-on", "file": f"{RAW}/hands-on.mp4",
          "sentences": f"{HERE}/sentB.json"},
}

LESSONS = [
    {"no": "00", "src": "slides", "title": "安全须知", "sub": "上手设备前必看", "items": [
        {"slide": "个人防护", "dur": 9, "lines": [
            "操作全程佩戴护目镜和手套",
            "带压部件严禁拆卸；拆前确认压力表归零"]},
        {"slide": "操作原则", "dur": 8, "lines": [
            "阀门开关要慢，分步调节",
            "视频中【注意】卡片是按规范补充的要求，详见《规范性检查.md》"]},
    ]},

    {"no": "01", "src": "A", "title": "认识设备面板",
     "panel": f"{HERE}/panel_annot.jpg", "panel_title": "设备面板各部件",
     "keeps": [["00:12", "01:40"], ["02:05", "03:30"]],          # 01:40–02:05 闲聊剪掉
     "overlays": [
         ["00:12", "气源从墙上接入，经入口阀进入设备"],
         ["00:48", "三块压力表：入口压力 / 驱动压力 / 输出压力", ("术语", "驱动压力：推动泵工作的压缩空气压力")],
         ["02:05", "调压阀顺时针增大，逆时针减小"],
     ],
     "recap": ["认清三块压力表", "调压阀顺时针增大"]},

    {"no": "02", "src": "A", "title": "加压操作",
     "keeps": [["03:30", "06:10"]],
     "overlays": [
         ["03:30", "① 打开入口阀 ② 打开驱动开关 ③ 慢慢调调压阀，盯住压力表"],
         ["04:15", "每次调一点，等压力稳定再调下一次", ("注意", "分步加压，防止超压")],
         ["05:20", "输出压力比测试压力高 10% 左右", ("参数", "输出压力 ≈ 测试压力 × 1.1")],
     ],
     "recap": ["入口阀 → 驱动开关 → 慢调调压阀", "等稳定再调"]},

    {"no": "03", "src": "B", "title": "接头拆装与检漏",
     "keeps": [[11, 26], [34, 70]],                               # B 直接写秒
     "overlays": [
         [11, "拆接头前确认压力归零；慢慢拧，拧松后稍等放掉余气", ("注意", "脸避开接头")],
         [34, "装：擦净密封面 → 手拧紧 → 扳手再拧约半圈", ("参数", "圈数以接头厂商规程为准")],
     ],
     "recap": ["拆：确认无压 → 慢拧", "装：擦净 → 手紧 → 扳手 → 检漏"]},
]
