"""
检查核心逻辑测试：用临时生成的小表格验证两种模式的输出，不依赖真实稿件。
运行：在项目根目录执行 backend/venv/bin/python -m pytest tests
"""

import json
import os
import random
import subprocess
import sys

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock

BACKEND = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, BACKEND)

from checker_core import ExcelChecker, RowLimitError, WordIndex  # noqa: E402
from check_worker import FILTER_ERROR_MESSAGE, is_filter_error  # noqa: E402

ERR_DICT = {
    'err': {'的的': '的', '裏': '裡'},
    'warn': {'里裏裡': '①鄰里②萬里無雲③裡面', '麵面': '①麵粉②面子'},
    'repeat': ['哈'],
    'transhint': {'ちょっと': '一點、有點', '先輩': '前輩'},
}
TERM_DICT = {
    'word': [
        {'ja': '先輩', 'zh': '學長', 'note': '稱呼'},
        {'ja': '魔術師', 'zh': '魔術師'},
    ]
}


def make_workbook(path, rows, sheets=1):
    """生成表格：第一行是表头，之后每行 B 列为待检查文本"""
    wb = Workbook()
    for i in range(sheets):
        ws = wb.active if i == 0 else wb.create_sheet(f'S{i + 1}')
        ws.append(['ID', '文本'])
        for text in rows:
            ws.append([1, text])
    wb.save(path)
    return path


def red_chars(value):
    if not isinstance(value, CellRichText):
        return ''
    return ''.join(block.text for block in value if isinstance(block, TextBlock))


# ---------- WordIndex ----------

def test_word_index_matches_bruteforce():
    rng = random.Random(0)
    alphabet = '的確裡裏面麵哈先輩魔術師ちょっと'
    words = [''.join(rng.choice(alphabet) for _ in range(rng.randint(1, 3))) for _ in range(200)]
    words.append('')  # 空词：与 `'' in text` 一致，任何文本都命中
    index = WordIndex(words)
    for _ in range(300):
        text = ''.join(rng.choice(alphabet) for _ in range(rng.randint(0, 20)))
        expected = [i for i, w in enumerate(words) if w in text]
        assert index.find(text) == expected


# ---------- 易错字词模式 ----------

def test_common_check(tmp_path):
    src = make_workbook(tmp_path / 'in.xlsx', ['他的的確確在這裏', '麵粉放在裡面', '哈哈哈', '沒有問題'])
    out = tmp_path / 'out.xlsx'
    ExcelChecker(ERR_DICT, TERM_DICT).process_file(
        str(src), str(out), {'mode': 'common', 'inputCol': 'B', 'outputCol1': 'C', 'outputCol2': 'D'}
    )
    ws = load_workbook(out, rich_text=True).active

    # 第 2 行：错误词按词典顺序；易混淆字整组提示一次；叠字
    assert ws['C2'].value == '的的→的\r\n裏→裡'
    assert ws['D2'].value == '里裏裡：①鄰里②萬里無雲③裡面\r\n出現疊字 的 確'
    assert red_chars(ws['B2'].value) == '裏'

    # 第 3 行（C1）：两组易混淆字，组内出现的字全部标红（空提示保存后读回为 None）
    assert ws['C3'].value is None
    assert ws['D3'].value == '里裏裡：①鄰里②萬里無雲③裡面\r\n麵面：①麵粉②面子'
    assert red_chars(ws['B3'].value) == '麵裡面'

    # 第 4 行：词典里的允许叠字不提示；第 5 行无提示且正文保持纯文本
    assert ws['D4'].value is None
    assert ws['C5'].value is None and ws['D5'].value is None
    assert ws['B5'].value == '沒有問題'
    assert ws['A1'].value == 'ID'  # 表头不处理


def test_common_check_skips_empty_and_short_rows(tmp_path):
    src = make_workbook(tmp_path / 'in.xlsx', [None, '裏'])
    out = tmp_path / 'out.xlsx'
    ExcelChecker(ERR_DICT, TERM_DICT).process_file(
        str(src), str(out), {'mode': 'common', 'inputCol': 'B', 'outputCol1': 'C', 'outputCol2': 'D'}
    )
    ws = load_workbook(out).active
    assert ws['C2'].value is None
    assert ws['C3'].value == '裏→裡'


# ---------- 统一词模式 ----------

def test_spec_check_with_transhint(tmp_path):
    src = make_workbook(tmp_path / 'in.xlsx', ['先輩、ちょっと\n待って', '魔術師', 'なし'])
    out = tmp_path / 'out.xlsx'
    ExcelChecker(ERR_DICT, TERM_DICT).process_file(
        str(src), str(out),
        {'mode': 'spec', 'inputCol': 'B', 'outputCol1': 'C', 'includeTransHint': True},
    )
    ws = load_workbook(out).active
    # 统一词带备注；易塞翻词里与统一词重复的「先輩」不再提示
    assert ws['C2'].value == '先輩(稱呼)：學長\r\n【易塞翻詞，提供參考釋義】\r\nちょっと：一點、有點'
    assert ws['C3'].value == '魔術師：魔術師'
    assert ws['C4'].value is None


def test_spec_check_without_transhint(tmp_path):
    src = make_workbook(tmp_path / 'in.xlsx', ['先輩、ちょっと'])
    out = tmp_path / 'out.xlsx'
    ExcelChecker(ERR_DICT, TERM_DICT).process_file(
        str(src), str(out), {'mode': 'spec', 'inputCol': 'B', 'outputCol1': 'C'}
    )
    assert load_workbook(out).active['C2'].value == '先輩(稱呼)：學長'


# ---------- 工作表范围与行数上限 ----------

def test_check_all_sheets(tmp_path):
    src = make_workbook(tmp_path / 'in.xlsx', ['裏'], sheets=2)
    config = {'mode': 'common', 'inputCol': 'B', 'outputCol1': 'C', 'outputCol2': 'D'}
    out = tmp_path / 'first.xlsx'
    ExcelChecker(ERR_DICT, TERM_DICT).process_file(str(src), str(out), config)
    wb = load_workbook(out)
    assert wb['Sheet']['C2'].value == '裏→裡'
    assert wb['S2']['C2'].value is None

    out_all = tmp_path / 'all.xlsx'
    ExcelChecker(ERR_DICT, TERM_DICT).process_file(str(src), str(out_all), dict(config, checkAllSheets=True))
    assert load_workbook(out_all)['S2']['C2'].value == '裏→裡'


def test_row_limit(tmp_path):
    src = make_workbook(tmp_path / 'in.xlsx', ['a', 'b', 'c'])
    with pytest.raises(RowLimitError, match='「Sheet」4 行'):
        ExcelChecker(ERR_DICT, TERM_DICT).process_file(
            str(src), str(tmp_path / 'out.xlsx'),
            {'mode': 'common', 'inputCol': 'B', 'outputCol1': 'C', 'outputCol2': 'D'},
            max_rows=3,
        )


# ---------- 检查子进程 ----------

def run_worker(tmp_path, src, config, max_rows=None, env=None):
    job = {
        'input': str(src), 'output': str(tmp_path / 'out.xlsx'),
        'err_dict': ERR_DICT, 'term_dict': TERM_DICT, 'config': config, 'max_rows': max_rows,
    }
    job_path = tmp_path / 'job.json'
    job_path.write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
    return subprocess.run(
        [sys.executable, os.path.join(BACKEND, 'check_worker.py'), str(job_path)],
        capture_output=True, text=True, cwd=BACKEND, env=env,
    )


COMMON = {'mode': 'common', 'inputCol': 'B', 'outputCol1': 'C', 'outputCol2': 'D'}


def test_worker_success(tmp_path):
    src = make_workbook(tmp_path / 'in.xlsx', ['裏'])
    result = run_worker(tmp_path, src, COMMON)
    assert result.returncode == 0, result.stdout + result.stderr
    assert load_workbook(tmp_path / 'out.xlsx').active['C2'].value == '裏→裡'


def test_worker_saves_red_marks(tmp_path):
    """整格都是易混淆字时会写入纯标红的富文本，子进程必须能正常保存"""
    src = make_workbook(tmp_path / 'in.xlsx', ['裡面'])
    result = run_worker(tmp_path, src, COMMON)
    assert result.returncode == 0, result.stdout + result.stderr
    assert red_chars(load_workbook(tmp_path / 'out.xlsx', rich_text=True).active['B2'].value) == '裡面'


def test_worker_env_drops_openpyxl_lxml(monkeypatch):
    monkeypatch.setenv('OPENPYXL_LXML', 'False')
    import app
    assert 'OPENPYXL_LXML' not in app.worker_env()


def test_worker_row_limit(tmp_path):
    src = make_workbook(tmp_path / 'in.xlsx', ['a', 'b'])
    result = run_worker(tmp_path, src, COMMON, max_rows=2)
    info = json.loads(result.stdout.strip().splitlines()[-1])
    assert result.returncode == 1 and info['kind'] == 'row_limit'


def test_worker_broken_file(tmp_path):
    src = tmp_path / 'in.xlsx'
    src.write_bytes(b'not a zip')
    result = run_worker(tmp_path, src, COMMON)
    info = json.loads(result.stdout.strip().splitlines()[-1])
    assert result.returncode == 1 and info['kind'] == 'BadZipFile'


def test_is_filter_error_follows_exception_chain():
    try:
        try:
            raise ValueError('Value must be either numerical or a string containing a wildcard')
        except ValueError as inner:
            raise ValueError('Unable to read workbook') from inner
    except ValueError as outer:
        assert is_filter_error(outer)
    assert not is_filter_error(ValueError('other'))
    assert FILTER_ERROR_MESSAGE == '請關閉篩選後重試'
