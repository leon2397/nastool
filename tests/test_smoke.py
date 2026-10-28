"""端到端冒烟：真实跑一次诊断 + 三种报告器。

刻意关掉测速 / SMART / AI / 外网，保证在任何机器上都能秒级跑完。
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nastool.core.runner import RunOptions, run_diagnostics
from nastool.reporters.html_reporter import HTMLReporter
from nastool.reporters.json_reporter import JSONReporter
from nastool.reporters.terminal import TerminalReporter


def _run(tmp):
    options = RunOptions(
        storage_path=tmp,
        do_speed_test=False,
        do_smart=False,
        do_ai=False,
        do_internet_check=False,
    )
    return run_diagnostics(options)


def test_full_diagnostic_structure():
    with tempfile.TemporaryDirectory() as tmp:
        result = _run(tmp)

    assert result.meta.generated_at
    assert result.meta.version
    assert 0 <= result.score.total <= 100
    assert result.score.grade in ("A", "B", "C", "D")
    assert result.platform.kind
    assert result.device.cpu.cores >= 0
    assert result.storage.target_path
    assert isinstance(result.overall_ok, bool)


def test_json_report():
    with tempfile.TemporaryDirectory() as tmp:
        result = _run(tmp)
        data = JSONReporter().build(result)

        for key in ("report_version", "tool", "overall", "score", "platform",
                    "device", "storage", "network", "services", "ai_accelerator"):
            assert key in data, f"缺少字段 {key}"

        assert data["overall"]["pass"] == result.overall_ok
        assert data["score"]["total"] == result.score.total
        assert isinstance(data["score"]["findings"], list)

        path = os.path.join(tmp, "r.json")
        jr = JSONReporter()
        jr.build(result)
        jr.dump(path)
        assert os.path.getsize(path) > 500


def test_html_report_selfcontained():
    with tempfile.TemporaryDirectory() as tmp:
        result = _run(tmp)
        html = HTMLReporter().build(result)

    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "健康评分" in html
    assert "http://" not in html.replace("http://www.w3.org", "")  # 不引外部资源
    assert "https://" not in html
    # 没有未替换的占位符
    assert "{score}" not in html and "{hostname}" not in html


def test_terminal_report_renders():
    with tempfile.TemporaryDirectory() as tmp:
        result = _run(tmp)
    text = str(TerminalReporter(color=False).full(result))
    assert "检测结论" in text
    assert "健康评分" in text
    assert "存储" in text
