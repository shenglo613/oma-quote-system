"""Tests for dealer helper functions in src/db.py"""
import sys
from unittest.mock import MagicMock, patch

# Mock streamlit before importing src.db
_st_mock = MagicMock()
_st_mock.cache_data = lambda **kw: (lambda f: f)  # @st.cache_data(ttl=...)
_st_mock.cache_resource = lambda f: f              # @st.cache_resource (no parens)
sys.modules.setdefault("streamlit", _st_mock)
sys.modules.setdefault("supabase", MagicMock())

from src.db import add_dealer, remove_dealer  # noqa: E402


_MOCK_DEALERS: list[str] = []


def _mock_load():
    return list(_MOCK_DEALERS)


def _mock_save(dealers):
    _MOCK_DEALERS.clear()
    _MOCK_DEALERS.extend(dealers)


@patch("src.db.save_dealers", side_effect=_mock_save)
@patch("src.db.load_dealers", side_effect=_mock_load)
class TestAddDealer:
    def setup_method(self):
        _MOCK_DEALERS.clear()

    def test_add_success(self, _load, _save):
        ok, msg = add_dealer("新經銷商")
        assert ok is True
        assert "新經銷商" in _MOCK_DEALERS

    def test_add_strips_whitespace(self, _load, _save):
        ok, _ = add_dealer("  帶空白  ")
        assert ok is True
        assert "帶空白" in _MOCK_DEALERS

    def test_add_empty_fails(self, _load, _save):
        ok, msg = add_dealer("")
        assert ok is False
        assert "不可為空" in msg

    def test_add_whitespace_only_fails(self, _load, _save):
        ok, msg = add_dealer("   ")
        assert ok is False
        assert "不可為空" in msg

    def test_add_duplicate_fails(self, _load, _save):
        _MOCK_DEALERS.append("已存在")
        ok, msg = add_dealer("已存在")
        assert ok is False
        assert "已存在" in msg


@patch("src.db.save_dealers", side_effect=_mock_save)
@patch("src.db.load_dealers", side_effect=_mock_load)
class TestRemoveDealer:
    def setup_method(self):
        _MOCK_DEALERS.clear()
        _MOCK_DEALERS.extend(["經銷商A", "經銷商B"])

    def test_remove_success(self, _load, _save):
        ok, msg = remove_dealer("經銷商A")
        assert ok is True
        assert "經銷商A" not in _MOCK_DEALERS
        assert "經銷商B" in _MOCK_DEALERS

    def test_remove_nonexistent_fails(self, _load, _save):
        ok, msg = remove_dealer("不存在")
        assert ok is False
        assert "不存在" in msg
