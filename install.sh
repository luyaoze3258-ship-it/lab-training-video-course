#!/usr/bin/env bash
# 安装 lab-training-video-course 技能：检查依赖，并把本目录链接到各智能体的技能目录。
#   bash install.sh           检查依赖 + 安装到 Claude Code / Codex / 通用 ~/.agents/skills
#   bash install.sh --check   只检查依赖
#   bash install.sh --copy    复制而不是软链接（仓库目录之后要删掉时用）
set -euo pipefail

NAME="lab-training-video-course"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="link"
[[ "${1:-}" == "--copy" ]] && MODE="copy"

ok()   { printf '✅ %s\n' "$1"; }
warn() { printf '⚠️  %s\n' "$1"; }
fail=0

# ---------- 依赖 ----------
if command -v python3 >/dev/null; then ok "python3 $(python3 -c 'import sys;print(sys.version.split()[0])')"
else warn "缺 python3：请先安装 Python 3.9+"; fail=1; fi

if python3 -c 'import PIL' 2>/dev/null; then ok "Pillow"
elif [[ "${1:-}" != "--check" ]] && python3 -m pip install --user -q -r "$SRC/requirements.txt" 2>/dev/null; then ok "Pillow（已自动安装）"
else warn "缺 Pillow：python3 -m pip install --user pillow pyyaml"; fail=1; fi

if command -v ffmpeg >/dev/null; then ok "ffmpeg"
else warn "缺 ffmpeg：macOS: brew install ffmpeg；Ubuntu: sudo apt install ffmpeg；Windows: winget install ffmpeg"; fail=1; fi

if command -v baocut >/dev/null; then ok "baocut"
else warn "缺 baocut：安装 BaoCut 桌面应用并启用命令行（剪辑、转录都靠它）"; fail=1; fi

if python3 -c "import sys; sys.path.insert(0,'$SRC/scripts'); import cards; sys.exit(0 if cards.FONT else 1)" 2>/dev/null; then
  ok "中文字体 $(python3 -c "import sys; sys.path.insert(0,'$SRC/scripts'); import cards; print(cards.FONT)")"
else warn "找不到中文字体：Linux: sudo apt install fonts-noto-cjk；或 export LTVC_FONT=字体文件路径"; fail=1; fi

[[ "${1:-}" == "--check" ]] && exit $fail

# ---------- 安装到各智能体 ----------
install_to() {
  local dir="$1" label="$2" dest="$1/$NAME"
  mkdir -p "$dir"
  if [[ -e "$dest" || -L "$dest" ]]; then
    if [[ "$(cd "$dest" 2>/dev/null && pwd -P)" == "$(cd "$SRC" && pwd -P)" ]]; then ok "$label 已安装：$dest"; return; fi
    warn "$label 已有同名技能，跳过（先手动移走 $dest 再重装）"; return
  fi
  if [[ "$MODE" == "copy" ]]; then cp -R "$SRC" "$dest"; else ln -s "$SRC" "$dest"; fi
  ok "$label → $dest"
}
install_to "$HOME/.agents/skills" "通用 Agent Skills"
install_to "$HOME/.claude/skills" "Claude Code"
install_to "$HOME/.codex/skills"  "Codex"

echo
echo "WorkBuddy 等其他智能体：在它的技能管理里导入本目录（${SRC}），或导入 GitHub Release 里的 ${NAME}.zip。"
if [[ $fail -ne 0 ]]; then warn "上面有缺失的依赖，补齐后再用。"
else ok "全部就绪。新开一个会话，说「把这几个培训视频剪成课程」即可触发。"; fi
