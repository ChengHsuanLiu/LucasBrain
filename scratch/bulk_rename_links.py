import io, os, re

base = r"C:\Users\User\Desktop\LucasBrain"

# safe 1:1 mappings only (IC設計 and 設備 handled separately due to ambiguity)
mapping = {
    "[[記憶體]]": "[[2_晶片層_記憶體HBM]]",
    "[[封裝測試]]": "[[2_晶片層_封裝測試]]",
    "[[CCL銅箔基板]]": "[[3_上游_載板PCB_CCL]]",
    "[[ABF載板]]": "[[3_上游_載板PCB_CCL]]",
    "[[PCB]]": "[[3_上游_載板PCB_CCL]]",
    "[[矽晶圓]]": "[[3_上游_材料矽晶圓光罩]]",
    "[[測試與探針卡]]": "[[3_上游_測試與探針卡]]",
    "[[散熱元件]]": "[[4_系統層_散熱機構]]",
    "[[BBU電源]]": "[[4_系統層_電源電力設備]]",
    "[[被動元件]]": "[[4_系統層_被動元件]]",
    "[[伺服器代工ODM]]": "[[4_系統層_伺服器ODM品牌]]",
    "[[光通訊]]": "[[4_系統層_光通訊光模組]]",
}

# files/dirs to skip entirely
skip_files = {
    os.path.join(base, "log.md"),
    os.path.join(base, "99_Templates", "Template_Stock.md"),
}
skip_dirs = {
    os.path.join(base, "98_Archives"),
    os.path.join(base, "30_Projects", "Weekly_Focus"),
    os.path.join(base, "30_Projects", "Daily_Report"),
    os.path.join(base, "40_Library"),
}

targets = [
    os.path.join(base, "10_Stocks"),
    os.path.join(base, "20_Garden"),
    os.path.join(base, "97_Settings"),
]

changed = []
for target in targets:
    for root, dirs, files in os.walk(target):
        if any(root.startswith(sd) for sd in skip_dirs):
            continue
        for fn in files:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(root, fn)
            if path in skip_files:
                continue
            with io.open(path, "r", encoding="utf-8") as f:
                content = f.read()
            orig = content
            for old, new in mapping.items():
                content = content.replace(old, new)
            if content != orig:
                with io.open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                changed.append(path)

# also handle index.md separately (not under those target dirs)
index_path = os.path.join(base, "index.md")
with io.open(index_path, "r", encoding="utf-8") as f:
    content = f.read()
orig = content
for old, new in mapping.items():
    content = content.replace(old, new)
if content != orig:
    with io.open(index_path, "w", encoding="utf-8") as f:
        f.write(content)
    changed.append(index_path)

with io.open(os.path.join(base, "scratch", "bulk_rename_result.txt"), "w", encoding="utf-8") as out:
    out.write("\n".join(changed))
print("changed files:", len(changed))
