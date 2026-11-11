"""
对比 dump_results.py 导出的新旧结果：提示列、正文、行高、列宽必须逐格一致。
标红字允许「新版是旧版的超集」（C1 改动后同组易混淆字全部标红），会单独统计。

用法：python tests/regression/compare_results.py old.json new.json
有不一致时退出码为 1。
"""
import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        old = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        new = json.load(f)

    bad = red_more = red_rows = 0
    for sheet in old:
        if sheet not in new:
            print(f"缺少工作表：{sheet}")
            bad += 1
            continue
        if old[sheet]["widths"] != new[sheet]["widths"]:
            print(sheet, "列宽不同", old[sheet]["widths"], new[sheet]["widths"])
            bad += 1
        if len(old[sheet]["rows"]) != len(new[sheet]["rows"]):
            print(sheet, "行数不同")
            bad += 1
        for i, (a, b) in enumerate(zip(old[sheet]["rows"], new[sheet]["rows"])):
            if a[0] != b[0] or a[1] != b[1] or a[3] != b[3]:
                bad += 1
                if bad <= 5:
                    print(sheet, i + 1, "不同", a, b)
            if a[2] or b[2]:
                red_rows += 1
            if a[2] != b[2]:
                if not set(a[2]) <= set(b[2]) or len(b[2]) < len(a[2]):
                    bad += 1
                    print(sheet, i + 1, "标红变少", a[2], b[2])
                else:
                    red_more += 1

    print(f"不一致={bad}  标红行={red_rows}  标红增加的行(C1)={red_more}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
