import pytest

from ai_review.analyzers.python_ast import PythonAnalyzer
from ai_review.analyzers.errors import AnalyzerError


def test_python_analyzer_top_level_only():
    source = """
import os

def top_level(a, b):
    return a + b

class Foo:
    def method(self):
        return 1

    def nested(self):
        def inner():
            return 2
        return inner()
"""
    analyzer = PythonAnalyzer()
    summary = analyzer.analyze_content(source)

    functions = [fn["name"] for fn in summary["functions"]]
    assert functions == ["top_level"]

    classes = [cls["name"] for cls in summary["classes"]]
    assert classes == ["Foo"]


def test_python_analyzer_invalid_syntax():
    analyzer = PythonAnalyzer()
    with pytest.raises(AnalyzerError):
        analyzer.analyze_content("def bad(:\n")
