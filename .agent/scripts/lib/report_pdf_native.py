"""
不依賴瀏覽器的 Markdown -> PDF 產生器（reportlab原生Platypus版本）。

背景：`report_pdf.py` 靠 headless Edge 列印 HTML 產生 PDF，但在本機環境下
Edge headless 的 print-to-pdf 靜默失敗（進程立刻return卻沒真的產生檔案，
且原本的等待邏輯逾時後仍誤報成功）。這裡改用 reportlab 直接組 Platypus
flowables，不經過瀏覽器、也不經過xhtml2pdf的CSS `@font-face`（該路徑在本機
同樣測試失敗，中文一律變黑色方塊）。中文字型改為直接用
pdfmetrics.registerFont() 註冊 Windows 內建的 Microsoft JhengHei(.ttc)，
這個路徑實測正常。

只處理vault筆記常見的markdown子集：frontmatter、# ~ #### 標題、
`> [!TYPE]`callout區塊、一般blockquote、`---`分隔線、pipe表格、
`-`/`  -`項目符號清單、**bold**、`` `code` ``、`[[wikilink]]`/`[[target|alias]]`。
不是完整的markdown/CommonMark實作，遇到超出子集的語法會被當一般段落處理。
"""
import os
import re

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable,
)

_FONT_DIR = r"C:\Windows\Fonts"
_FONTS_REGISTERED = False


def _ensure_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("JhengHei", os.path.join(_FONT_DIR, "msjh.ttc"), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("JhengHei-Bold", os.path.join(_FONT_DIR, "msjhbd.ttc"), subfontIndex=0))
    _FONTS_REGISTERED = True


def _styles():
    return {
        "h1": ParagraphStyle("h1", fontName="JhengHei-Bold", fontSize=19, leading=25,
                              spaceAfter=10, textColor=colors.HexColor("#111827")),
        "h2": ParagraphStyle("h2", fontName="JhengHei-Bold", fontSize=14.5, leading=19,
                              spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#111827")),
        "h3": ParagraphStyle("h3", fontName="JhengHei-Bold", fontSize=11.5, leading=16,
                              spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#111827")),
        "h4": ParagraphStyle("h4", fontName="JhengHei-Bold", fontSize=10, leading=14,
                              spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#1f2937")),
        "body": ParagraphStyle("body", fontName="JhengHei", fontSize=9.8, leading=15,
                                spaceAfter=6, textColor=colors.HexColor("#1f2937")),
        "bullet1": ParagraphStyle("bullet1", fontName="JhengHei", fontSize=9.8, leading=14.5,
                                   leftIndent=12, spaceAfter=3, textColor=colors.HexColor("#1f2937")),
        "bullet2": ParagraphStyle("bullet2", fontName="JhengHei", fontSize=9.8, leading=14.5,
                                   leftIndent=26, spaceAfter=3, textColor=colors.HexColor("#1f2937")),
        "quote": ParagraphStyle("quote", fontName="JhengHei", fontSize=9, leading=13.5,
                                 leftIndent=10, spaceAfter=4, textColor=colors.HexColor("#4b5563")),
        "cell": ParagraphStyle("cell", fontName="JhengHei", fontSize=8, leading=11.5,
                                textColor=colors.HexColor("#1f2937")),
        "cellhead": ParagraphStyle("cellhead", fontName="JhengHei-Bold", fontSize=8.2, leading=11.5,
                                    textColor=colors.white),
    }


_EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001FAFF\U00002300-\U000023FF\U00002B00-\U00002BFF"
    "\U00002600-\U000026FF\U00002700-\U000027BF\U0000FE0F]+",
    flags=re.UNICODE,
)
_CALLOUT_LABELS = {
    "NOTE": "註", "TIP": "提示", "IMPORTANT": "重要", "WARNING": "警示", "CAUTION": "注意",
}


def _clean_inline(text):
    text = _EMOJI_PATTERN.sub("", text).strip()

    def repl_link(m):
        inner = m.group(1)
        return inner.split("|", 1)[1] if "|" in inner else inner
    text = re.sub(r"`?\[\[([^\]]+)\]\]`?", repl_link, text)

    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8">\1</font>', text)
    # markdown links [text](url) -> clickable reportlab <link>, kept after escaping
    # so a literal "&" inside a query string is already valid "&amp;" in the href.
    text = re.sub(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)",
                   r'<link href="\2" color="#2563eb"><u>\1</u></link>', text)
    return text


def _strip_frontmatter(text):
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)


def _parse_table(lines, i):
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    rows = [header]
    j = i + 2
    while j < len(lines) and lines[j].strip().startswith("|"):
        rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
        j += 1
    return rows, j


def build_story(md_text, table_width_cm=17.0):
    styles = _styles()
    text = _strip_frontmatter(md_text)
    lines = text.split("\n")
    story = []
    n = len(lines)
    i = 0

    in_callout = False
    callout_label = ""
    callout_buf = []

    def flush_callout():
        nonlocal callout_buf, callout_label
        if callout_buf:
            label = f"<b>{callout_label}：</b>" if callout_label else ""
            content = label + " ".join(_clean_inline(l) for l in callout_buf)
            t = Table([[Paragraph(content, styles["quote"])]], colWidths=[table_width_cm * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#fde68a")),
                ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor("#d97706")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        callout_buf = []
        callout_label = ""

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            flush_callout()
            rows, next_i = _parse_table(lines, i)
            ncols = len(rows[0])
            colw = (table_width_cm * cm) / ncols
            data = [
                [Paragraph(_clean_inline(c), styles["cellhead"] if r == 0 else styles["cell"]) for c in row]
                for r, row in enumerate(rows)
            ]
            t = Table(data, colWidths=[colw] * ncols, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 10))
            i = next_i
            continue

        m_callout_start = re.match(r"^>\s*\[!(\w+)\]", stripped)
        if m_callout_start:
            flush_callout()
            in_callout = True
            callout_label = _CALLOUT_LABELS.get(m_callout_start.group(1).upper(), m_callout_start.group(1))
            i += 1
            continue
        if in_callout:
            if stripped.startswith(">"):
                content = stripped.lstrip(">").strip()
                if content:
                    callout_buf.append(content)
                i += 1
                continue
            else:
                flush_callout()
                in_callout = False
                continue

        if stripped == "---":
            flush_callout()
            story.append(HRFlowable(width="100%", thickness=0.75,
                                     color=colors.HexColor("#d1d5db"), spaceBefore=6, spaceAfter=10))
            i += 1
            continue

        if stripped.startswith("#### "):
            flush_callout()
            story.append(Paragraph(_clean_inline(stripped[5:]), styles["h4"]))
            i += 1
            continue
        if stripped.startswith("### "):
            flush_callout()
            story.append(Paragraph(_clean_inline(stripped[4:]), styles["h3"]))
            i += 1
            continue
        if stripped.startswith("## "):
            flush_callout()
            story.append(Paragraph(_clean_inline(stripped[3:]), styles["h2"]))
            i += 1
            continue
        if stripped.startswith("# "):
            flush_callout()
            story.append(Paragraph(_clean_inline(stripped[2:]), styles["h1"]))
            i += 1
            continue

        if stripped.startswith("> "):
            flush_callout()
            story.append(Paragraph(_clean_inline(stripped[2:]), styles["quote"]))
            i += 1
            continue

        m_bullet = re.match(r"^(\s*)-\s+(.*)$", line)
        if m_bullet:
            flush_callout()
            indent = len(m_bullet.group(1))
            style = styles["bullet2"] if indent >= 2 else styles["bullet1"]
            story.append(Paragraph("• " + _clean_inline(m_bullet.group(2)), style))
            i += 1
            continue

        if not stripped:
            flush_callout()
            i += 1
            continue

        flush_callout()
        story.append(Paragraph(_clean_inline(stripped), styles["body"]))
        i += 1

    flush_callout()
    return story


def render_markdown_to_pdf_native(md_path, pdf_path):
    """讀取md_path、產生pdf_path，回傳pdf_path。不經過瀏覽器/xhtml2pdf。"""
    _ensure_fonts()
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    story = build_story(md_text)
    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        topMargin=1.9 * cm, bottomMargin=1.8 * cm, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
    )
    doc.build(story)
    return pdf_path
