"""Offline contract tests for the manual content runtime."""

from pathlib import Path
import ast
from collections import Counter
import shutil
import sys

import pytest

from quant_lab.manual_content import (
    CATEGORY_ORDER,
    ContentValidationError,
    content_root,
    load_manual_content,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = PROJECT_ROOT / "docs" / "knowledge-drafts"


def _content_copy(tmp_path: Path) -> Path:
    target = tmp_path / "knowledge-drafts"
    shutil.copytree(CONTENT_ROOT, target)
    return target


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_loads_all_manuals_and_articles_offline(monkeypatch, tmp_path):
    forbidden_user_dir = tmp_path / "must-not-be-created"
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(forbidden_user_dir))
    monkeypatch.setattr(
        "socket.create_connection",
        lambda *args, **kwargs: pytest.fail("内容加载不得访问网络"),
    )

    library = load_manual_content()

    assert len(library.manuals) == 10
    assert len(library.articles) == 85
    assert len({article.id for article in library.articles}) == 85
    assert library.category_order == CATEGORY_ORDER
    assert not forbidden_user_dir.exists()


def test_complete_catalog_distribution_matches_reviewed_content():
    library = load_manual_content()

    assert Counter(article.category for article in library.articles) == {
        "market_data": 10,
        "return_risk": 10,
        "strategy_execution": 10,
        "backtest_research": 10,
        "portfolio": 8,
        "statistics": 9,
        "machine_learning": 8,
        "programming_engineering": 20,
    }
    assert Counter(article.software_status for article in library.articles) == {
        "implemented": 61,
        "needs_code_review": 13,
        "theory_only": 10,
        "academy_demo": 1,
    }
    assert all(item.body.strip() and item.source_path.is_file() for item in (*library.manuals, *library.articles))


def test_queries_by_stable_id_category_and_relationships():
    library = load_manual_content()

    article = library.get_article("ohlcv")
    assert article.title == "开高低收与成交量"
    assert article.english_title == "OHLCV"
    assert article.source_path.name == "ohlcv.md"
    assert len(library.articles_in_category("market_data")) == 10
    assert {item.id for item in library.prerequisites_for("ohlcv")} == {"instrument_identity"}
    assert "simple_return" in {item.id for item in library.related_for("ohlcv")}
    assert library.get_manual("quick_start").title.startswith("快速开始")


@pytest.mark.parametrize(
    ("query", "expected_id"),
    (
        ("开高低收与成交量", "ohlcv"),
        ("Next-Open Execution", "next_open_execution"),
        ("价量数据", "ohlcv"),
    ),
)
def test_searches_chinese_title_english_title_and_alias(query, expected_id):
    results = load_manual_content().search_articles(query)
    assert expected_id in {article.id for article in results}


def test_searches_plain_text_body_and_can_filter_category():
    library = load_manual_content()
    results = library.search_articles("已经结束的交易日", category="market_data")
    assert "ohlcv" in {article.id for article in results}
    assert "market_data" in {page.id for page in library.search_manuals("缓存状态")}
    assert library.search_articles("   ") == ()
    assert library.search_manuals("   ") == ()


def test_all_prerequisites_and_related_articles_resolve():
    library = load_manual_content()
    ids = {article.id for article in library.articles}
    for article in library.articles:
        assert set(article.prerequisites) <= ids
        assert set(article.related_articles) <= ids


def test_missing_required_frontmatter_fails(tmp_path):
    root = _content_copy(tmp_path)
    article = root / "articles" / "market_data" / "ohlcv.md"
    _replace(article, "english_title: OHLCV\n", "")

    with pytest.raises(ContentValidationError, match="缺少必填字段.*english_title"):
        load_manual_content(root)


def test_invalid_software_status_fails(tmp_path):
    root = _content_copy(tmp_path)
    article = root / "articles" / "market_data" / "ohlcv.md"
    _replace(article, "software_status: implemented", "software_status: published")

    with pytest.raises(ContentValidationError, match="非法 software_status"):
        load_manual_content(root)


def test_duplicate_article_id_fails(tmp_path):
    root = _content_copy(tmp_path)
    article = root / "articles" / "market_data" / "ohlcv.md"
    _replace(article, "id: ohlcv", "id: instrument_identity")

    with pytest.raises(ContentValidationError, match="专业文章 ID 重复：instrument_identity"):
        load_manual_content(root)


def test_missing_related_article_fails(tmp_path):
    root = _content_copy(tmp_path)
    article = root / "articles" / "market_data" / "ohlcv.md"
    _replace(article, "prerequisites: [instrument_identity]", "prerequisites: [missing_article]")

    with pytest.raises(ContentValidationError, match="不存在的文章 ID：missing_article"):
        load_manual_content(root)


def test_missing_content_resource_fails(tmp_path):
    with pytest.raises(ContentValidationError, match="内容目录不完整"):
        load_manual_content(tmp_path / "absent")


def test_missing_expected_manual_fails(tmp_path):
    root = _content_copy(tmp_path)
    (root / "manual" / "quick_start.md").unlink()

    with pytest.raises(ContentValidationError, match="缺少 quick_start"):
        load_manual_content(root)


def test_frozen_resource_root_does_not_depend_on_current_directory(monkeypatch, tmp_path):
    bundled = tmp_path / "bundle" / "docs" / "knowledge-drafts"
    bundled.mkdir(parents=True)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.chdir(tmp_path)

    assert content_root() == bundled.resolve()


def test_runtime_module_does_not_import_streamlit():
    source = (PROJECT_ROOT / "quant_lab" / "manual_content.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert "streamlit" not in imported_roots


def test_pyinstaller_recipe_bundles_the_read_only_content():
    recipe = (PROJECT_ROOT / "QuantLab.spec").read_text(encoding="utf-8")
    assert '"docs" / "knowledge-drafts"' in recipe
    assert '"docs/knowledge-drafts"' in recipe
