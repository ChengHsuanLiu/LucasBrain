"""
把任一份vault裡的 Markdown 檔案轉成PDF，不需要瀏覽器。

用途：像CREDO.md這種沒有專屬 g 指令、只是想「看一下PDF長什麼樣子」的
臨時筆記，或是 report_pdf.py(headless Edge)在本機失效時的備援。

用法：
    python .agent/scripts/render_markdown_pdf.py <md路徑> [<pdf路徑>]

<pdf路徑> 省略時，預設輸出到跟 <md路徑> 同資料夾、副檔名改成 .pdf。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.report_pdf_native import render_markdown_to_pdf_native

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python .agent/scripts/render_markdown_pdf.py <md路徑> [<pdf路徑>]")
        sys.exit(1)

    md_path = sys.argv[1]
    if len(sys.argv) >= 3:
        pdf_path = sys.argv[2]
    else:
        pdf_path = os.path.splitext(md_path)[0] + ".pdf"

    out = render_markdown_to_pdf_native(md_path, pdf_path)
    print(f"Generated: {out}")
