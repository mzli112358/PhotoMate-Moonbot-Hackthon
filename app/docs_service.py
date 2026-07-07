from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import markdown

from app.config import ROOT_DIR

PLAN_DIR = ROOT_DIR / "docs" / "plan"

DOC_CATALOG = [
    {"id": "overview", "title": "项目概览", "file": None, "hero": True},
    {"id": "plan2", "title": "会议纪要（正式版）", "file": "AI草案整理2.md", "hero": False},
    {"id": "plan1", "title": "会议整理（详版）", "file": "AI草案整理1.md", "hero": False},
]


def _strip_meta_lines(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if "不可以被修改" in line:
            continue
        lines.append(line)
    # 去掉文档开头重复的「草案整理」标题行（保留正式标题）
    while lines and lines[0].strip() in ("", "---"):
        lines.pop(0)
    if lines and "草案整理" in lines[0] and lines[0].startswith("#"):
        lines.pop(0)
        while lines and lines[0].strip() in ("", "---"):
            lines.pop(0)
    return "\n".join(lines).strip()


def _extract_toc(md_text: str) -> list[dict[str, Any]]:
    toc: list[dict[str, Any]] = []
    for i, line in enumerate(md_text.splitlines()):
        m = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        toc.append({"id": f"sec-{i}", "title": title, "level": level})
    return toc


def _inject_heading_ids(html: str, toc: list[dict[str, Any]]) -> str:
    idx = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal idx
        level = match.group(1)
        inner = match.group(2)
        if idx < len(toc):
            anchor = toc[idx]["id"]
            idx += 1
            return f'<h{level} id="{anchor}">{inner}</h{level}>'
        return match.group(0)

    return re.sub(r"<h([1-3])>(.*?)</h\1>", repl, html, flags=re.DOTALL)


def _render_markdown(md_text: str) -> tuple[str, list[dict[str, Any]]]:
    toc = _extract_toc(md_text)
    html = markdown.markdown(
        md_text,
        extensions=["extra", "tables", "nl2br"],
        output_format="html5",
    )
    return _inject_heading_ids(html, toc), toc


def overview_html() -> str:
    return """
<blockquote class="doc-lead">
  <p><strong>PhotoMate</strong> — 基于银河通用 G1 的移动摄影助理。机器人接过你的手机、帮你构图、代按快门，照片直接留在你的手机里。</p>
</blockquote>
<figure class="doc-hero">
  <img src="/assets/images/robot-hero.jpg" alt="PhotoMate 拍照机器人整机概念图" />
  <figcaption>整机概念设计：手机夹具、Insta360 相机、补光灯、口袋打印机与胸前交互屏</figcaption>
</figure>
<h2 id="sec-overview-highlights">核心亮点</h2>
<ul>
  <li><strong>移动摄影师</strong>：会场巡航，导航至预设合影机位</li>
  <li><strong>双拍摄模式</strong>：用户手机（隐私优先）或机器人自带相机（算法空间更大）</li>
  <li><strong>灵巧手交互</strong>：右手点快门，左手稳手机，完整「递—拍—还」闭环</li>
  <li><strong>活动场景落地</strong>：毕业典礼、展会、品牌活动即拍即得</li>
</ul>
<h2 id="sec-overview-flow">典型服务流程</h2>
<ol>
  <li>机器人巡航或待命，主动询问拍照需求</li>
  <li>引导用户至最佳机位（地图航点导航）</li>
  <li>选择手机拍摄或机器人相机拍摄</li>
  <li>语音引导站位与倒计时</li>
  <li>自动构图并触发快门</li>
  <li>可选打印实体照片或扫码获取电子版</li>
</ol>
<p class="doc-muted">详细方案见左侧目录中的会议纪要文档。</p>
"""


def load_document(doc_id: str) -> dict[str, Any]:
    entry = next((d for d in DOC_CATALOG if d["id"] == doc_id), None)
    if not entry:
        raise KeyError(doc_id)

    if entry["id"] == "overview":
        return {
            "id": "overview",
            "title": entry["title"],
            "html": overview_html(),
            "toc": [
                {"id": "sec-overview-highlights", "title": "核心亮点", "level": 2},
                {"id": "sec-overview-flow", "title": "典型服务流程", "level": 2},
            ],
            "hero": True,
        }

    path = PLAN_DIR / str(entry["file"])
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = _strip_meta_lines(path.read_text(encoding="utf-8"))
    html, toc = _render_markdown(raw)
    return {
        "id": entry["id"],
        "title": entry["title"],
        "html": html,
        "toc": toc,
        "hero": False,
    }


def catalog() -> list[dict[str, Any]]:
    return [
        {"id": d["id"], "title": d["title"], "hero": d.get("hero", False)}
        for d in DOC_CATALOG
    ]
