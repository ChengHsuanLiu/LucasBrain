"""
共用 Markdown -> PDF 產生器。

被 generate_stock_report.py、generate_weekly_focus.py、generate_daily_report.py 共用，
避免同一段「frontmatter/emoji清理 + HTML樣式 + Edge headless列印」邏輯各自維護一份。

設計語言參考外資券商研報：serif標題、細線分隔、無框線表格、色塊評等徽章、Step區塊換頁。
"""
import os
import re
import pathlib
import tempfile
import time
import subprocess

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

CSS = """
    @page {
        size: a4;
        margin: 1.9cm 1.6cm 1.8cm 1.6cm;
    }
    * { box-sizing: border-box; }
    body {
        font-family: "Microsoft JhengHei", "Segoe UI", system-ui, sans-serif;
        font-size: 10pt;
        line-height: 1.65;
        color: #1f2937;
        background-color: #ffffff;
    }
    em {
        font-style: normal;
        color: #6b7280;
        font-size: 8.5pt;
        letter-spacing: 0.02em;
    }
    h1 {
        font-family: "Noto Serif TC", "PMingLiU", "Microsoft JhengHei", serif;
        font-size: 22pt;
        font-weight: 700;
        color: #111827;
        margin: 2px 0 2px 0;
        letter-spacing: 0.01em;
    }
    h1 + h3 {
        font-family: "Microsoft JhengHei", sans-serif;
        font-size: 12pt;
        font-weight: 400;
        color: #4b5563;
        margin: 0 0 14px 0;
        border: none;
        padding: 0;
    }
    h2 {
        font-family: "Noto Serif TC", "PMingLiU", "Microsoft JhengHei", serif;
        font-size: 14.5pt;
        font-weight: 700;
        color: #111827;
        margin-top: 4px;
        margin-bottom: 14px;
        padding-bottom: 8px;
        border-bottom: 2px solid #111827;
    }
    h3 {
        font-size: 11pt;
        font-weight: 700;
        color: #111827;
        margin-top: 20px;
        margin-bottom: 8px;
        padding-top: 10px;
        border-top: 1px solid #d1d5db;
    }
    h4 {
        font-size: 10pt;
        color: #1f2937;
        margin-top: 14px;
        margin-bottom: 6px;
        font-weight: 700;
    }
    p, ul, ol {
        margin: 0 0 10px 0;
    }
    li {
        margin-bottom: 4px;
    }
    hr {
        border: none;
        border-top: 1px solid #d1d5db;
        margin: 16px 0;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 8px 0 16px 0;
        font-size: 8.3pt;
    }
    th {
        background: #ffffff;
        color: #111827;
        font-weight: 700;
        text-align: left;
        padding: 5px 7px;
        border-top: 1.5px solid #111827;
        border-bottom: 1px solid #111827;
        white-space: nowrap;
    }
    td {
        padding: 5px 7px;
        border-bottom: 1px solid #e5e7eb;
        vertical-align: top;
    }
    tr:last-child td {
        border-bottom: 1px solid #111827;
    }
    tr:nth-child(even) td {
        background-color: #f9fafb;
    }
    blockquote {
        border-left: 3px solid #9ca3af;
        padding: 3px 12px;
        margin: 12px 0;
        color: #4b5563;
        font-size: 9.3pt;
    }
    blockquote p { margin: 0; }
    code {
        font-family: "Consolas", "Microsoft JhengHei", monospace;
        background-color: #f3f4f6;
        color: #111827;
        padding: 1px 4px;
        border-radius: 2px;
        font-size: 8.7pt;
    }
    .badge {
        display: inline-block;
        padding: 1px 8px;
        border-radius: 3px;
        font-size: 8.3pt;
        font-weight: 700;
        letter-spacing: 0.02em;
        white-space: nowrap;
    }
    .badge-green { color: #065f46; background: #d1fae5; }
    .badge-amber { color: #92400e; background: #fef3c7; }
    .badge-red { color: #991b1b; background: #fee2e2; }
    .badge-lg {
        font-size: 12pt;
        padding: 3px 16px;
        border-radius: 4px;
    }
    .rating-bar {
        display: flex;
        align-items: center;
        gap: 18px;
        padding: 10px 0;
        border-top: 1px solid #d1d5db;
        border-bottom: 1px solid #d1d5db;
        margin-bottom: 18px;
    }
    .rating-bar-item {
        font-size: 10pt;
        color: #374151;
    }
    .step-page-break {
        page-break-before: always;
        break-before: page;
    }
"""

_EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001FAFF\U00002300-\U000023FF\U00002B00-\U00002BFF"
    "\U00002600-\U000026FF\U00002700-\U000027BF\U0000FE0F]+",
    flags=re.UNICODE,
)


def _preprocess_markdown(md_text):
    processed = md_text
    processed = re.sub(r'\[!NOTE\]', r'**註：**', processed)
    processed = re.sub(r'\[!TIP\]', r'**提示：**', processed)
    processed = re.sub(r'\[!IMPORTANT\]', r'**重要：**', processed)
    processed = re.sub(r'\[!WARNING\]', r'**警示：**', processed)
    processed = re.sub(r'\[!CAUTION\]', r'**注意：**', processed)

    # YAML frontmatter is for machine/AI consumption only — strip it entirely from the PDF.
    processed = re.sub(r'^---\n.*?\n---\n', '', processed, count=1, flags=re.DOTALL)

    # Strip any remaining emoji for a clean, professional look — also catches emoji
    # embedded in note content pulled in verbatim from 10_Stocks/.
    processed = _EMOJI_PATTERN.sub("", processed)
    processed = re.sub(r'[ \t]+\n', '\n', processed)

    def clean_links(match):
        text = match.group(1)
        if '|' in text:
            return text.split('|', 1)[1]
        return text
    processed = re.sub(r'`?\[\[([^\]]+)\]\]`?', clean_links, processed)
    return processed


def render_markdown_to_pdf(report_lines, output_dir, filename_stem, extra_css=""):
    """report_lines: list[str]，跟寫 .md 檔用的同一份內容。
    output_dir/filename_stem 決定暫存 HTML 與最終 PDF 的路徑 (filename_stem 不含副檔名)。
    extra_css: 附加在共用樣式之後的額外 CSS (例如特定報告的表格欄寬、換頁規則覆寫)。
    回傳產出的 pdf_path；失敗時印出警告並回傳 None，不中斷呼叫端流程。
    """
    import markdown

    pdf_path = os.path.join(output_dir, f"{filename_stem}.pdf")
    try:
        md_text = '\n'.join(report_lines)
        processed_md = _preprocess_markdown(md_text)
        # md_in_html：只有明確標註 markdown="1" 的 HTML 區塊才會遞迴處理內部的 markdown 語法
        # (例如表格)，對既有沒有該屬性的 raw HTML (如 step-page-break) 完全不影響。
        html_body = markdown.markdown(processed_md, extensions=['tables', 'fenced_code', 'md_in_html'])

        html_content = f"""
        <html>
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <style>
{CSS}
{extra_css}
        </style>
        </head>
        <body>
        {html_body}
        </body>
        </html>
        """

        temp_html_path = os.path.join(output_dir, f"{filename_stem}_temp.html")
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        temp_html_uri = pathlib.Path(temp_html_path).resolve().as_uri()

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        with tempfile.TemporaryDirectory(prefix="edge_pdf_profile_") as edge_profile_dir:
            cmd = [
                EDGE_PATH,
                "--headless",
                "--disable-gpu",
                f"--user-data-dir={edge_profile_dir}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                temp_html_uri
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # msedge.exe's headless print-to-pdf writes the PDF asynchronously and can
            # exit (subprocess.run returns) before the file is fully flushed to disk.
            # Deleting the source HTML right after subprocess.run() used to race that
            # write: the still-running render would then fail to find the (already
            # deleted) HTML and bake an ERR_FILE_NOT_FOUND page into the PDF instead of
            # the report. Wait for the PDF to appear and its size to stabilize first.
            deadline = time.time() + 20
            last_size = -1
            stable_checks = 0
            while time.time() < deadline:
                if os.path.exists(pdf_path):
                    size = os.path.getsize(pdf_path)
                    if size > 0 and size == last_size:
                        stable_checks += 1
                        if stable_checks >= 2:
                            break
                    else:
                        stable_checks = 0
                    last_size = size
                time.sleep(0.5)

        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)

        print(f"Successfully generated PDF at:\n{pdf_path}\n")
        return pdf_path
    except Exception as e:
        print(f"Warning: Failed to generate PDF: {e}")
        return None
