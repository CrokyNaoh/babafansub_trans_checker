"""
检查子进程入口：每次检查在独立进程中运行，结束后内存全部归还系统。

用法（由 app.py 调用，不直接给用户使用）：
    python check_worker.py <job.json>

job.json 字段：
    input / output   : 输入、输出 xlsx 路径
    err_dict         : 已按项目标签过滤的错误词典
    term_dict        : 项目术语词典
    config           : 前端提交的检查配置（mode、inputCol 等）
    max_rows         : 每个工作表允许的最大行数

成功时退出码 0；失败时退出码 1，并在 stdout 输出 {"error": "...", "kind": "..."}。
kind 为 row_limit / filter 时属于用户可自行修正的问题，父进程返回 400。
"""

import json
import sys

from checker_core import ExcelChecker, RowLimitError

# openpyxl 读不了筛选条件时的报错（常见于 WPS 开着筛选保存的文件），原始错误包在异常链里
FILTER_ERROR_MARK = 'containing a wildcard'
FILTER_ERROR_MESSAGE = '請關閉篩選後重試'


def is_filter_error(exc):
    """沿异常链查找筛选条件解析失败的原始错误"""
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if FILTER_ERROR_MARK in str(exc):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def main(job_path):
    with open(job_path, 'r', encoding='utf-8') as f:
        job = json.load(f)

    checker = ExcelChecker(job['err_dict'], job['term_dict'])
    checker.process_file(
        job['input'],
        job['output'],
        job['config'],
        max_rows=job.get('max_rows'),
    )


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except RowLimitError as e:
        print(json.dumps({'error': str(e), 'kind': 'row_limit'}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:  # 子进程边界：把异常转成结构化信息交给父进程
        if is_filter_error(e):
            print(json.dumps({'error': FILTER_ERROR_MESSAGE, 'kind': 'filter'}, ensure_ascii=False))
            sys.exit(1)
        print(json.dumps({'error': str(e), 'kind': type(e).__name__}, ensure_ascii=False))
        sys.exit(1)
