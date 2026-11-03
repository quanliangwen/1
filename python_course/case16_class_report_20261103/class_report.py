"""第16案例 班级成绩报告增强版。

仅用Python 3.10+标准库；report(records)保留原课堂案例的返回约定。
运行 python class_report.py demo，或 python class_report.py --help。
"""
from __future__ import annotations

import argparse
import copy
import csv
import html
import json
import math
import os
import statistics
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

FIELDS = ["student_id", "name", "class", "exam", "subject", "score"]
ALIASES = {"学号": "student_id", "姓名": "name", "班级": "class",
           "考试": "exam", "科目": "subject", "成绩": "score"}
MISSING = {"", "缺考", "未录入", "none", "null", "na", "n/a", "--"}
BASE = Path(__file__).resolve().parent


class DataError(ValueError):
    """可向使用者展示的数据错误。"""


def parse_score(value):
    """缺考保持None，0分保留为0，拒绝布尔值、非有限值及越界分数。"""
    if value is None or isinstance(value, str) and value.strip().lower() in MISSING:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise DataError("成绩必须为0至100的数字，缺考请留空")
    try:
        score = float(value)
    except (ValueError, OverflowError):
        raise DataError("成绩不能转换为数字") from None
    if not math.isfinite(score) or not 0 <= score <= 100:
        raise DataError("成绩必须是0至100之间的有限数值")
    return score


def text_field(value, label, default=None):
    if value is None and default is not None:
        return default
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise DataError(label + "必须为文字")
    text = str(value).strip()
    if not text and default is not None:
        return default
    if not text:
        raise DataError(label + "不能为空")
    return text


def record_key(row):
    return tuple(row[k] for k in ("class", "exam", "student_id", "subject"))


def normalize_records(records):
    """不修改输入；无效行和重复行进入问题清单，重复成绩保留首行。

    老案例仅有class和score也可使用；缺省学号按行生成。
    同一班级学号只能对应一个姓名，支持同名不同学号的学生。
    """
    clean, issues, seen, names = [], [], set(), {}
    for index, source in enumerate(records, 1):
        try:
            if not isinstance(source, dict):
                raise DataError("记录必须为字典")
            mapped = {}
            for key, value in source.items():
                if key is None:
                    raise DataError("CSV数据列多于表头列，请检查分隔符")
                key = key.strip() if isinstance(key, str) else key
                key = ALIASES.get(key, key)
                if key in mapped:
                    raise DataError("同一字段使用了重复表头或中英文别名")
                mapped[key] = value
            if "score" not in mapped:
                raise DataError("缺少score或成绩字段；缺考请明确填写空值")
            sid = text_field(mapped.get("student_id"), "学号", f"ROW{index:05}")
            row = {
                "student_id": sid,
                "name": text_field(mapped.get("name"), "姓名", sid),
                "class": text_field(mapped.get("class"), "班级"),
                "exam": text_field(mapped.get("exam"), "考试", "默认考试"),
                "subject": text_field(mapped.get("subject"), "科目", "综合成绩"),
                "score": parse_score(mapped["score"]),
            }
            key = record_key(row)
            identity = (row["class"], sid)
            if key in seen:
                raise DataError("同班级、考试、学号、科目的成绩重复，保留首条")
            if identity in names and names[identity] != row["name"]:
                raise DataError("同一班级学号对应不同姓名")
            names[identity] = row["name"]
            seen.add(key)
            clean.append(row)
        except (DataError, TypeError) as exc:
            issues.append({"row": index, "reason": str(exc),
                           "record": repr(source)})
    return clean, issues


def check_thresholds(pass_line=60, excellent_line=90):
    p, e = parse_score(pass_line), parse_score(excellent_line)
    if p is None or e is None or p > e:
        raise DataError("阈值应满足0 ≤ 及格线 ≤ 优秀线 ≤ 100")
    return p, e


def summarize(scores, pass_line=60, excellent_line=90):
    """率的分母为有效成绩数；无有效成绩时均值和率均为None。"""
    pass_line, excellent_line = check_thresholds(pass_line, excellent_line)
    scores = [parse_score(s) for s in scores]
    values = [s for s in scores if s is not None]
    total, count = len(scores), len(values)
    bands = {"90–100": 0, "80–89.99": 0, "70–79.99": 0,
             "60–69.99": 0, "0–59.99": 0}
    for v in values:
        band = ("90–100" if v >= 90 else "80–89.99" if v >= 80 else
                "70–79.99" if v >= 70 else "60–69.99" if v >= 60 else "0–59.99")
        bands[band] += 1
    return {"record_count": total, "valid_count": count,
            "missing_count": total-count,
            "attendance_rate": count/total if total else None,
            "mean": statistics.mean(values) if count else None,
            "median": statistics.median(values) if count else None,
            "min": min(values) if count else None,
            "max": max(values) if count else None,
            "stddev": statistics.pstdev(values) if count else None,
            "pass_count": sum(v >= pass_line for v in values),
            "fail_count": sum(v < pass_line for v in values),
            "excellent_count": sum(v >= excellent_line for v in values),
            "pass_rate": sum(v >= pass_line for v in values)/count if count else None,
            "excellent_rate": sum(v >= excellent_line for v in values)/count if count else None,
            "distribution": bands}


def report(records):
    """兼容原题：返回班级→平均分，忽略None，全缺考班级不进入这个简版结果。"""
    clean, issues = normalize_records(records)
    if issues:
        raise DataError("简版report输入有误：" + issues[0]["reason"])
    groups = defaultdict(list)
    for row in clean:
        if row["score"] is not None:
            groups[row["class"]].append(row["score"])
    return {name: statistics.mean(values) for name, values in sorted(groups.items())}


def analyze(records, pass_line=60, excellent_line=90, weights=None):
    """班级按考试隔离统计；个人仅对本班本次全部科目齐全者排名。

    未出现在某学生名下、但出现在其班级考试中的科目，记作待补录。
    只有有效成绩参与加权平均，权重默认1；不完整学生不参加综合排名。
    """
    pass_line, excellent_line = check_thresholds(pass_line, excellent_line)
    weights = dict(weights or {})
    for subject, weight in weights.items():
        if isinstance(weight, bool):
            raise DataError("科目权重必须为正数")
        try:
            number = float(weight)
        except (ValueError, TypeError, OverflowError):
            raise DataError("科目权重必须为正数") from None
        if not math.isfinite(number) or number <= 0:
            raise DataError("科目权重必须为有限正数")
        weights[subject] = number
    clean, issues = normalize_records(records)
    classes, subjects, students, expected = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(set)
    for row in clean:
        group = (row["class"], row["exam"])
        classes[group].append(row["score"])
        subjects[(*group, row["subject"])].append(row["score"])
        students[(*group, row["student_id"])].append(row)
        expected[group].add(row["subject"])
    class_rows = [dict(zip(("class", "exam"), key), **summarize(values, pass_line, excellent_line))
                  for key, values in sorted(classes.items())]
    subject_rows = [dict(zip(("class", "exam", "subject"), key), **summarize(values, pass_line, excellent_line))
                    for key, values in sorted(subjects.items())]
    student_rows = []
    for (class_name, exam, sid), rows in sorted(students.items()):
        valid = [row for row in rows if row["score"] is not None]
        numerator = sum((Decimal(str(r["score"]))*Decimal(str(weights.get(r["subject"], 1)))
                         for r in valid), Decimal(0))
        denominator = sum((Decimal(str(weights.get(r["subject"], 1))) for r in valid), Decimal(0))
        average = float(numerator/denominator) if denominator else None
        needed = expected[class_name, exam]
        absent = sorted(r["subject"] for r in rows if r["score"] is None)
        unrecorded = sorted(needed - {r["subject"] for r in rows})
        fails = sorted(r["subject"] for r in valid if r["score"] < pass_line)
        student_rows.append({"class": class_name, "exam": exam, "student_id": sid,
            "name": rows[0]["name"], "valid_subjects": len(valid),
            "expected_subjects": len(needed), "missing_subjects": absent,
            "unrecorded_subjects": unrecorded, "failed_subjects": fails,
            "total": sum(r["score"] for r in valid) if valid else None,
            "weighted_mean": average, "complete": len(valid) == len(needed),
            "rank": None, "change": None, "scores": {r["subject"]: r["score"] for r in rows}})
    by_group = defaultdict(list)
    for student in student_rows:
        by_group[student["class"], student["exam"]].append(student)
    for group in by_group.values():
        eligible = sorted((s for s in group if s["complete"]),
                          key=lambda s: (-round(s["weighted_mean"], 8), s["student_id"]))
        previous, rank = None, 0
        for position, student in enumerate(eligible, 1):
            key = round(student["weighted_mean"], 8)
            if key != previous:
                rank = position
            student["rank"] = rank
            previous = key
    for row in class_rows:
        group = by_group[row["class"], row["exam"]]
        row["student_count"] = len(group)
        row["complete_students"] = sum(s["complete"] for s in group)
        row["unrecorded_count"] = sum(len(s["unrecorded_subjects"]) for s in group)
    for row in subject_rows:
        row["unrecorded_count"] = len(by_group[row["class"], row["exam"]])-row["record_count"]
    # 只对科目集合、完整性都匹配的相邻考试计算进步；考试顺序为名称排序。
    histories = defaultdict(list)
    for row in student_rows:
        histories[row["class"], row["student_id"]].append(row)
    for history in histories.values():
        history.sort(key=lambda s: s["exam"])
        for before, after in zip(history, history[1:]):
            if (before["complete"] and after["complete"] and
                    set(before["scores"]) == set(after["scores"])):
                after["change"] = after["weighted_mean"] - before["weighted_mean"]
    return {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "settings": {"pass_line": pass_line, "excellent_line": excellent_line, "weights": weights},
        "overview": summarize([r["score"] for r in clean], pass_line, excellent_line),
        "classes": class_rows, "subjects": subject_rows, "students": student_rows,
        "records": clean, "issues": issues,
        "notes": ["缺考不按0分处理；及格率、优秀率分母为有效成绩数。",
                  "班级均分是有效单科成绩的算术平均；总览跨考试，仅供整体数据检查。",
                  "个人综合排名限同班同次考试科目齐全者，按加权均分降序并列排名1、2、2、4。",
                  "并列比较保留8位小数；显示保留2位。科目权重默认1。",
                  "缺考与未录入科目均阻止综合排名；无成绩的均值、率、名次显示—。",
                  "未录入数为本班本次已识别学生与科目组合中缺少的记录；出勤率以已提供记录数为分母。",
                  "进步值按考试名称升序比较相邻考试；建议考试名使用01_期中、02_期末。",
                  "科目清单从本班本次已有数据推断；全班均未提供的科目无法自动识别。",
                  "重复成绩保留首条并在问题清单中记录；报告不会修改原数据。"]}


def read_records(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            raw_headers = [ALIASES.get(h.strip(), h.strip()) for h in (reader.fieldnames or [])]
            if len(raw_headers) != len(set(raw_headers)):
                raise DataError("CSV存在重复表头或同一字段的中英文重复列")
            headers = set(raw_headers)
            if not {"class", "score"} <= headers:
                raise DataError("CSV至少需要班级/class、成绩/score两列")
            return list(reader)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            data = data.get("records")
        if not isinstance(data, list):
            raise DataError("JSON必须为记录列表，或含records列表的对象")
        return data
    raise DataError("输入文件只支持UTF-8编码的CSV或JSON")


def atomic_json(path, data):
    """先完整写入临时文件，再原子替换；中途失败不破坏原文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_csv(path, headers, rows):
    # 对文字形式的公式起始符做转义，数字仍写为数字，便于表格软件使用。
    def safe(value):
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({key: safe(row.get(key)) for key in headers} for row in rows)


class GradeBook:
    """增删改查均在新列表验证成功后提交，查询返回独立副本。"""
    def __init__(self, records=()):
        self._records = []
        self.replace(records)

    @property
    def records(self):
        return copy.deepcopy(self._records)

    def replace(self, records):
        clean, issues = normalize_records(records)
        if issues:
            raise DataError(f"第{issues[0]['row']}条：{issues[0]['reason']}；数据未修改")
        self._records = clean

    def add(self, row):
        self.replace(self._records + [row])

    def update(self, key, score):
        new = self.records
        matches = [row for row in new if record_key(row) == tuple(key)]
        if not matches:
            raise DataError("找不到该班级、考试、学号、科目的记录")
        matches[0]["score"] = parse_score(score)
        self.replace(new)

    def delete(self, key):
        remaining = [row for row in self._records if record_key(row) != tuple(key)]
        if len(remaining) == len(self._records):
            raise DataError("找不到需要删除的记录")
        self.replace(remaining)

    def search(self, keyword="", class_name="", exam="", subject=""):
        return [r for r in self.records if
                (not keyword or keyword.casefold() in (r["student_id"]+r["name"]).casefold()) and
                (not class_name or class_name == r["class"]) and
                (not exam or exam == r["exam"]) and
                (not subject or subject == r["subject"])]

    def save(self, path):
        atomic_json(path, {"schema_version": 1, "records": self._records})

    @classmethod
    def load(cls, path):
        return cls(read_records(path)) if Path(path).exists() else cls()


def fmt(value, percent=False):
    if value is None:
        return "—"
    return f"{value:.1%}" if percent else f"{value:.2f}"


def text_report(data):
    lines = ["班级成绩报告", "="*40, "生成时间："+data["generated_at"], ""]
    for row in data["classes"]:
        lines += [f"{row['class']} / {row['exam']}：{row['student_count']}名学生",
            f"  有效成绩 {row['valid_count']} / 缺考 {row['missing_count']} / 未录入 {row['unrecorded_count']} / 完整学生 {row['complete_students']}",
            f"  均分 {fmt(row['mean'])} / 中位数 {fmt(row['median'])} / 标准差 {fmt(row['stddev'])}",
            f"  最高 {fmt(row['max'])} / 最低 {fmt(row['min'])} / 及格率 {fmt(row['pass_rate'], True)}",
            f"  优秀率 {fmt(row['excellent_rate'], True)}", ""]
    lines.append("个人综合成绩（仅完整学生排名）")
    for s in sorted(data["students"], key=lambda s: (s["class"], s["exam"], s["rank"] or math.inf, s["student_id"])):
        lines.append(f"{s['class']} | {s['exam']} | {s['student_id']} {s['name']} | "
            f"均分 {fmt(s['weighted_mean'])} | 名次 {s['rank'] or '—'} | "
            f"不及格 {','.join(s['failed_subjects']) or '无'} | "
            f"缺考 {','.join(s['missing_subjects']) or '无'} | 待补录 {','.join(s['unrecorded_subjects']) or '无'}")
    lines += ["", f"数据问题 {len(data['issues'])} 条"]
    lines += [f"  第{r['row']}条：{r['reason']}" for r in data["issues"]]
    lines += ["", "统计口径"] + ["  "+note for note in data["notes"]]
    return "\n".join(lines)+"\n"


def html_report(data):
    esc = lambda x: html.escape(str(x), quote=True)
    def table(headers, rows, attrs=""):
        return (f'<div class="table-wrap"><table {attrs}><thead><tr>'+"".join(f"<th scope='col'>{esc(h)}</th>" for h in headers)+
                "</tr></thead><tbody>"+"".join("<tr>"+"".join(f"<td>{esc(c)}</td>" for c in row)+"</tr>" for row in rows)+"</tbody></table></div>")
    overview = data["overview"]
    cards = "".join(f'<div class="kpi"><span>{label}</span><strong>{esc(value)}</strong></div>' for label, value in [
        ("班级 · 考试组合", len(data["classes"])), ("有效单科成绩", overview["valid_count"]),
        ("缺考记录", overview["missing_count"]), ("需检查数据", len(data["issues"]))])
    classes = table(["班级", "考试", "人数", "有效/缺考/未录入", "均分", "中位数", "标准差", "及格率", "优秀率"],
        [[r["class"], r["exam"], r["student_count"], f"{r['valid_count']}/{r['missing_count']}/{r['unrecorded_count']}",
          fmt(r["mean"]), fmt(r["median"]), fmt(r["stddev"]), fmt(r["pass_rate"], True), fmt(r["excellent_rate"], True)] for r in data["classes"]])
    subjects = table(["班级", "考试", "科目", "有效/缺考/未录入", "均分", "最高", "最低", "及格率"],
        [[r["class"], r["exam"], r["subject"], f"{r['valid_count']}/{r['missing_count']}/{r['unrecorded_count']}", fmt(r["mean"]),
          fmt(r["max"]), fmt(r["min"]), fmt(r["pass_rate"], True)] for r in data["subjects"]])
    student_rows = []
    for r in sorted(data["students"], key=lambda r: (r["class"], r["exam"], r["rank"] or math.inf, r["student_id"])):
        student_rows.append([r["class"], r["exam"], r["student_id"], r["name"],
            f"{r['valid_subjects']}/{r['expected_subjects']}", fmt(r["weighted_mean"]), r["rank"] or "—",
            fmt(r["change"]), ", ".join(r["failed_subjects"]) or "—",
            ", ".join(r["missing_subjects"]+r["unrecorded_subjects"]) or "—"])
    students = table(["班级", "考试", "学号", "姓名", "有效科目", "加权均分", "名次", "进步值", "不及格科目", "缺考或待录入"], student_rows, 'id="students"')
    bars = "".join(f'<div class="bar-row"><span>{esc(r["class"])} · {esc(r["exam"])}</span>'
        f'<div class="track"><div class="bar" style="width:{r["mean"] or 0:.2f}%"></div></div>'
        f'<b>{fmt(r["mean"])}</b></div>' for r in data["classes"])
    bands = "".join(f'<div class="band"><b>{count}</b><span>{esc(label)} 分</span></div>'
                    for label, count in overview["distribution"].items())
    issues = table(["数据行号", "问题", "原记录"], [[r["row"], r["reason"], r["record"]] for r in data["issues"]]) if data["issues"] else '<p class="ok">未发现无效行或重复成绩。</p>'
    options = lambda key: '<option value="">全部</option>'+"".join(f'<option>{esc(v)}</option>' for v in sorted({s[key] for s in data["students"]}))
    notes = "".join(f"<li>{esc(note)}</li>" for note in data["notes"])
    template = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="data:,"><title>班级成绩报告</title>
<style>
:root{font-family:system-ui,"Microsoft YaHei",sans-serif;color:#172f37;background:#f3f6f4;font-size:15px}*{box-sizing:border-box}body{margin:0}main{max-width:1240px;margin:auto;padding:38px 30px 70px}header{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-bottom:30px}.eyebrow{font-size:12px;letter-spacing:2px;color:#327466;font-weight:700}h1{font-size:36px;letter-spacing:-1px;margin:10px 0}h2{font-size:21px;margin:0 0 18px}p{line-height:1.8}.muted{color:#62757a;font-size:13px}button{cursor:pointer;background:#126957;color:#fff;border:0;padding:12px 20px;border-radius:8px;font:inherit}button:hover{background:#0e4d42}button:focus-visible,input:focus,select:focus{outline:3px solid #d8a749;outline-offset:3px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}.kpi,section{background:#fff;border:1px solid #dfe7e3;border-radius:12px}.kpi{padding:22px}.kpi span{font-size:13px;color:#62757a;display:block}.kpi strong{font-size:33px;display:block;margin-top:8px}section{padding:26px;margin:20px 0}.two{display:grid;grid-template-columns:1.3fr 1fr;gap:20px}.two section{min-width:0;margin:0}.bar-row{display:grid;grid-template-columns:180px 1fr 50px;gap:12px;align-items:center;margin:19px 0;font-size:13px}.track{background:#eaf1ed;height:11px;border-radius:20px;overflow:hidden}.bar{height:100%;background:#298371;border-radius:20px}.bands{display:flex;flex-wrap:wrap;gap:12px}.band{flex:1;min-width:95px;background:#f4f7f4;padding:16px 12px;border-radius:8px}.band b{display:block;font-size:27px}.band span{font-size:12px;color:#62757a;display:block;margin-top:9px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}th{text-align:left;background:#f1f5f2;color:#42635d}td,th{padding:13px 12px;border-bottom:1px solid #e7ede9}tbody tr:hover{background:#f5f9f6}td:last-child{max-width:450px;white-space:normal;overflow-wrap:anywhere}label{font-size:13px;color:#42635d}input,select{display:block;border:1px solid #cedbd4;border-radius:7px;background:white;padding:10px;font:inherit;max-width:100%}.filters{display:flex;flex-wrap:wrap;gap:16px;align-items:end;margin-bottom:16px}#query{width:260px}.ok{color:#126957}li{line-height:1.9;color:#52686d}.empty{padding:15px;color:#8a5b19}footer{padding:15px 0;font-size:12px;color:#62757a}@media(max-width:760px){main{padding:22px 16px}h1{font-size:28px}.cards{grid-template-columns:1fr 1fr;gap:10px}.two{grid-template-columns:1fr}section{padding:18px}.bar-row{grid-template-columns:140px 1fr 45px}header{align-items:start}}@media print{body{background:white;font-size:10pt}main{max-width:none;padding:0}button,.filters{display:none!important}.cards{grid-template-columns:repeat(4,1fr)}.two{display:block}.two section{margin:16px 0}section{border:0;padding:10px 0;border-radius:0}h2{break-after:avoid}tr{break-inside:avoid}.table-wrap{overflow:visible}table{white-space:normal;font-size:8pt}td,th{padding:5px}.kpi{padding:12px}h1{font-size:24pt}}
</style></head><body><main><header><div><span class="eyebrow">PYTHON · CLASSROOM / CASE 16</span><h1>班级成绩报告</h1><div class="muted">{time} · 缺考保留，统计有据</div></div><button id="print" type="button">打印 / 保存 PDF</button></header>
<div class="cards">{cards}</div><div class="two"><section><h2>班级均分概览</h2><div class="muted">按班级与考试分组 · 单科有效成绩均分 · 满分 100</div>{bars}</section><section><h2>有效成绩分布</h2><p class="muted">跨考试的单科记录数；缺考不进入分数段。</p><div class="bands">{bands}</div></section></div>
<section><h2>班级统计</h2>{classes}</section><section><h2>科目诊断</h2>{subjects}</section>
<section><h2>个人成绩与学习提醒</h2><p class="muted">筛选仅影响个人表；其他统计仍为全量数据。打印将保留当前筛选。</p><div class="filters"><label>学号或姓名<input id="query" type="search" placeholder="搜索学生"></label><label>班级<select id="class-filter">{class_options}</select></label><label>考试<select id="exam-filter">{exam_options}</select></label><label><input type="checkbox" id="attention">只看不及格或缺考</label><button type="button" id="reset">重置筛选</button></div><p class="muted" id="result-count" aria-live="polite"></p>{students}<p id="no-results" class="empty" hidden>没有符合条件的学生，请调整筛选。</p></section>
<section><h2>数据质量检查</h2><p class="muted">报告排除了 {issue_count} 条问题记录。行号指数据记录顺序，CSV表头不计入。</p>{issues}</section><section><h2>统计口径与使用说明</h2><ul>{notes}</ul><p class="muted">本报告及格线 {pass_line} 分，优秀线 {excellent_line} 分。分数段按固定 60 / 70 / 80 / 90 分划分，调整阈值不会改变固定分数段。</p></section><footer>第16案例增强版 · Python标准库生成 · 报告可离线打开 · 表格可通过配套CSV继续处理</footer></main>
<script>
const q=document.querySelector('#query'),c=document.querySelector('#class-filter'),e=document.querySelector('#exam-filter'),a=document.querySelector('#attention');
const rows=[...document.querySelectorAll('#students tbody tr')];
function filter(){let count=0;for(const row of rows){const t=[...row.cells].map(x=>x.textContent);const show=(!q.value||(t[2]+t[3]).toLowerCase().includes(q.value.toLowerCase()))&&(!c.value||t[0]===c.value)&&(!e.value||t[1]===e.value)&&(!a.checked||t[8]!=='—'||t[9]!=='—');row.hidden=!show;if(show)count++;}document.querySelector('#result-count').textContent=`显示 ${count} / ${rows.length} 条个人考试记录`;document.querySelector('#no-results').hidden=count!==0;}
for(const el of [q,c,e,a])el.addEventListener('input',filter);document.querySelector('#reset').addEventListener('click',()=>{q.value=c.value=e.value='';a.checked=false;filter();});document.querySelector('#print').addEventListener('click',()=>window.print());filter();
</script></body></html>'''
    replacements = {"time": esc(data["generated_at"]), "cards": cards, "bars": bars,
        "bands": bands, "classes": classes, "subjects": subjects, "students": students,
        "issues": issues, "notes": notes, "class_options": options("class"),
        "exam_options": options("exam"), "issue_count": len(data["issues"]),
        "pass_line": data["settings"]["pass_line"], "excellent_line": data["settings"]["excellent_line"]}
    # 一次替换，避免用户内容包含模板标记时被再次解释。
    import re
    return re.sub(r"\{("+"|".join(replacements)+r")\}", lambda m: str(replacements[m.group(1)]), template)


def export_report(data, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output/"report.json", data)
    (output/"班级成绩报告.txt").write_text(text_report(data), encoding="utf-8")
    (output/"班级成绩报告.html").write_text(html_report(data), encoding="utf-8")
    write_csv(output/"有效成绩.csv", FIELDS, data["records"])
    write_csv(output/"数据问题.csv", ["row", "reason", "record"], data["issues"])
    metrics = ["record_count", "valid_count", "missing_count", "unrecorded_count", "mean", "median", "stddev", "min", "max", "pass_rate", "excellent_rate"]
    write_csv(output/"班级统计.csv", ["class", "exam", "student_count", "complete_students"]+metrics, data["classes"])
    write_csv(output/"科目统计.csv", ["class", "exam", "subject"]+metrics, data["subjects"])
    write_csv(output/"个人统计.csv", ["class", "exam", "student_id", "name", "valid_subjects", "expected_subjects", "total", "weighted_mean", "rank", "change", "failed_subjects", "missing_subjects", "unrecorded_subjects"], data["students"])
    return output/"班级成绩报告.html"


def demo_records():
    """演示数据与真实学生无关，含0分、并列、缺考、待补录和两次考试。"""
    rows = []
    names = ["林同学", "周同学", "陈同学", "李同学", "王同学", "赵同学"]
    scores = [[95,90,85], [95,90,85], [80,75,70], [60,59,62], [40,50,None], [0,70,80]]
    for class_no, class_name in enumerate(["一班", "二班"], 1):
        for exam_no, exam in enumerate(["01_期中", "02_期末"]):
            for i, name in enumerate(names):
                for j, subject in enumerate(["语文", "数学", "英语"]):
                    if class_no == 2 and exam_no == 1 and i == 4 and j == 1:
                        continue
                    score = scores[i][j]
                    if score is not None and exam_no:
                        score = min(100, score+5)
                    rows.append({"student_id": f"{class_no}{i+1:03}", "name": name,
                        "class": class_name, "exam": exam, "subject": subject, "score": score})
    for i in range(2):
        for subject in ["语文", "数学", "英语"]:
            rows.append({"student_id": f"300{i+1}", "name": f"缺考示例{i+1}",
                "class": "三班", "exam": "01_期中", "subject": subject, "score": None})
    return rows


def run_demo(output):
    rows = demo_records()
    data = analyze(rows)
    path = export_report(data, output)
    write_csv(Path(output)/"示例成绩.csv", FIELDS, rows)
    dirty = rows + [copy.deepcopy(rows[0]), dict(rows[0], student_id="9991", score=120),
                    dict(rows[0], student_id="9992", score="nan")]
    write_csv(Path(output)/"异常数据示例.csv", FIELDS, dirty)
    GradeBook(rows).save(Path(output)/"示例成绩.json")
    print(text_report(data))
    print("离线HTML报告：", path.resolve())
    return data


def menu(data_path):
    """适合课堂演示的交互入口；每次成功修改后保存。"""
    book = GradeBook.load(data_path)
    while True:
        print("\n班级成绩管理：1查询 2新增 3修改成绩 4删除记录 5导入 6生成报告 0退出")
        before = book.records
        try:
            choice = input("请选择：").strip()
            if choice == "0":
                return
            if choice == "1":
                matches = book.search(input("输入学号/姓名片段，留空显示全部：").strip())
                print(json.dumps(matches, ensure_ascii=False, indent=2))
                print(f"共{len(matches)}条成绩记录")
                continue
            if choice == "2":
                values = [input(label+"：").strip() for label in ["学号", "姓名", "班级", "考试", "科目", "成绩（缺考留空）"]]
                book.add(dict(zip(FIELDS, values)))
            elif choice in {"3", "4"}:
                key = [input(label+"：").strip() for label in ["班级", "考试", "学号", "科目"]]
                if choice == "3":
                    book.update(key, input("新成绩（缺考留空）："))
                elif input("确认删除这条成绩？输入YES确认：").strip() == "YES":
                    book.delete(key)
                else:
                    print("已取消")
                    continue
            elif choice == "5":
                incoming = read_records(Path(input("CSV或JSON路径：").strip().strip('"')))
                book.replace(book.records+incoming)
            elif choice == "6":
                output = input("报告目录（留空使用输出）：").strip() or str(BASE/"输出")
                print("已生成：", export_report(analyze(book.records), output).resolve())
                continue
            else:
                print("请输入菜单中的数字")
                continue
            book.save(data_path)
            print("操作成功，已保存：", data_path)
        except (DataError, OSError, json.JSONDecodeError, csv.Error) as exc:
            book.replace(before)
            print("操作未完成：", exc)
        except (EOFError, KeyboardInterrupt):
            print("\n已退出；此前保存的数据仍保留。")
            return


def main(argv=None):
    parser = argparse.ArgumentParser(description="第16案例 班级成绩报告增强版（仅需Python标准库）")
    subs = parser.add_subparsers(dest="command")
    demo = subs.add_parser("demo", help="运行内置演示并输出报告")
    demo.add_argument("--out", type=Path, default=BASE/"输出")
    rep = subs.add_parser("report", help="读取CSV/JSON并生成HTML、TXT、CSV与JSON报告")
    rep.add_argument("--input", required=True, type=Path)
    rep.add_argument("--out", type=Path, default=BASE/"输出")
    rep.add_argument("--pass-line", type=float, default=60)
    rep.add_argument("--excellent-line", type=float, default=90)
    rep.add_argument("--weights", default="{}", help='科目权重JSON，例如 {"数学":2,"语文":1}')
    rep.add_argument("--weights-file", type=Path, help="从UTF-8 JSON文件读取科目权重，避免命令行引号问题")
    rep.add_argument("--strict", action="store_true", help="存在任何数据问题时拒绝生成报告")
    interactive = subs.add_parser("menu", help="交互式成绩管理，支持增删改查与导入")
    interactive.add_argument("--data", type=Path, default=BASE/"成绩数据.json")
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            parser.print_help()
            return 0
        if args.command == "demo":
            run_demo(args.out)
        elif args.command == "menu":
            menu(args.data)
        else:
            if args.weights_file and args.weights != "{}":
                raise DataError("--weights和--weights-file请选择其一")
            weights = (json.loads(args.weights_file.read_text(encoding="utf-8-sig"))
                       if args.weights_file else json.loads(args.weights))
            if not isinstance(weights, dict):
                raise DataError("--weights必须是科目到正数的JSON对象")
            data = analyze(read_records(args.input), args.pass_line, args.excellent_line, weights)
            if args.strict and data["issues"]:
                raise DataError(f"有{len(data['issues'])}条数据问题；严格模式未生成报告")
            # 防止输出文件覆盖本次CSV/JSON输入。
            targets = {"report.json", "班级成绩报告.txt", "班级成绩报告.html", "有效成绩.csv",
                       "数据问题.csv", "班级统计.csv", "科目统计.csv", "个人统计.csv"}
            if args.input.resolve().parent == args.out.resolve() and args.input.name in targets:
                raise DataError("输出目录中的同名文件会覆盖输入，请使用另一个--out目录")
            print(text_report(data))
            print("报告已生成：", export_report(data, args.out).resolve())
        return 0
    except (DataError, OSError, json.JSONDecodeError, csv.Error, UnicodeError) as exc:
        print("错误："+str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
