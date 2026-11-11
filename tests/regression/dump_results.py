"""
用指定版本的代码跑一次检查，把结果导出成 JSON，供 compare_results.py 做新旧对比。

用法（在本地跑，不要在伺服器上跑大文件）：
    python tests/regression/dump_results.py <代码根目录> <稿件.xlsx> <项目ID> <common|spec> <检查列> <提示列1> [提示列2] <输出.json>

例：先用旧代码（如 git worktree 出来的目录）和新代码各导出一次，再对比：
    python tests/regression/dump_results.py /tmp/base 稿件.xlsx dc3 common J M N old.json
    python tests/regression/dump_results.py .        稿件.xlsx dc3 common J M N new.json
    python tests/regression/compare_results.py old.json new.json

需要 <代码根目录>/data 下有项目词典（data/*.json 不在 Git 里，需从伺服器复制）。
"""
import json
import sys

root = sys.argv[1]
sys.path.insert(0, root + "/backend")
sys.path.insert(0, root)

from openpyxl import load_workbook  # noqa: E402
from openpyxl.cell.rich_text import CellRichText, TextBlock  # noqa: E402

import app  # noqa: E402
from checker_core import ExcelChecker  # noqa: E402


def main():
    src, project_id, mode, input_col, out1 = sys.argv[2:7]
    out2 = sys.argv[7] if mode == "common" else None
    dump_path = sys.argv[-1]

    err_dict, term_dict = app.load_project_dicts(project_id)
    wb = load_workbook(src)
    names = wb.sheetnames
    checker = ExcelChecker(err_dict, term_dict)
    if mode == "common":
        checker.do_common_check(wb, names, input_col, out1, out2)
    else:
        checker.do_spec_check(wb, names, input_col, out1, True)

    cols = [out1] + ([out2] if out2 else [])
    result = {}
    for name in names:
        ws = wb[name]
        rows = []
        for r in range(1, ws.max_row + 1):
            hints = [ws[f"{c}{r}"].value for c in cols]
            value = ws[f"{input_col}{r}"].value
            red = ""
            if isinstance(value, CellRichText):
                red = "".join(b.text for b in value if isinstance(b, TextBlock))
            rows.append([hints, str(value) if value is not None else None, red, ws.row_dimensions[r].height])
        result[name] = {"rows": rows, "widths": [ws.column_dimensions[c].width for c in cols]}

    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    print("已导出", dump_path)


if __name__ == "__main__":
    main()
