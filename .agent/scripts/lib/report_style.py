"""
報告共用文字上色/格式化工具，供 generate_daily_report.py 與 scan_momentum_score.py 共用。

配色慣例（全部報告一致）：正值/上漲/強勢 = 亮橘紅色，負值/下跌/轉弱 = 綠色（「漲橘跌綠」，
與台股慣用紅漲綠跌相反，是本專案自訂慣例，沿用即可不要改回紅綠）。
對應的 CSS class (num-up/num-down/flag-red/text-green/text-blue/text-purple) 定義在
`lib/report_pdf.py` 的共用 CSS 裡，任何用這裡函式產生 HTML 片段的報告都能直接吃到樣式，
不需要各自在 extra_css 裡重複定義一次。
"""


def fmt_pct(v, decimals=2):
    return f"{v:+.{decimals}f}%" if v is not None else "N/A"


def fmt_num(v):
    return f"{v:,.0f}" if v is not None else "N/A"


def colorize(text, is_up, bold=True):
    cls = "num-up" if is_up else "num-down"
    style = "" if bold else ' style="font-weight:400;"'
    return f'<span class="{cls}"{style}>{text}</span>'


def colorize_signed(value, fmt="{:+.2f}%", flip=False, bold=True):
    """依正負號幫數字上色：預設正值(含0)用亮橘紅色、負值用綠色（漲橘跌綠慣例）。
    bold=False 時保留顏色但不加粗（用於族群/動能表格等不需要粗體強調的欄位）。"""
    if value is None:
        return "N/A"
    text = fmt.format(value)
    is_up = (value >= 0) if not flip else (value < 0)
    return colorize(text, is_up, bold=bold)


def flag_red(text):
    return f'<span class="flag-red">{text}</span>'


def flag_green(text):
    return f'<span class="text-green">{text}</span>'


def flag_blue(text):
    """區塊標題/子標題統一用藍色凸顯。"""
    return f'<span class="text-blue">{text}</span>'


def flag_purple(text):
    """白話解讀備註，用紫色凸顯（與藍色標題區隔）。"""
    return f'<span class="text-purple">{text}</span>'
