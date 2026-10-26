"""Offline, read-only runtime for the bundled manual and knowledge articles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence
import re
import sys
import unicodedata


SOFTWARE_STATUSES = frozenset(
    {"implemented", "academy_demo", "theory_only", "needs_code_review"}
)
CATEGORY_ORDER = (
    "market_data",
    "return_risk",
    "strategy_execution",
    "backtest_research",
    "portfolio",
    "statistics",
    "machine_learning",
    "programming_engineering",
)
CATEGORY_TITLES = MappingProxyType(
    {
        "market_data": "市场与数据",
        "return_risk": "收益与风险",
        "strategy_execution": "策略与执行",
        "backtest_research": "回测与研究",
        "portfolio": "组合分析",
        "statistics": "统计推断",
        "machine_learning": "机器学习",
        "programming_engineering": "Python、数据处理与工程",
    }
)
MANUAL_ORDER = (
    "quick_start",
    "workspace",
    "market_data",
    "strategy",
    "backtest",
    "risk_portfolio",
    "statistics_ml",
    "academy",
    "deepseek",
    "research_notes",
)
EXPECTED_ARTICLE_COUNT = 85

_REQUIRED_ARTICLE_FIELDS = (
    "id",
    "title",
    "english_title",
    "aliases",
    "category",
    "software_status",
    "related_modules",
    "prerequisites",
    "related_articles",
    "source_ids",
    "last_verified",
)
_LIST_FIELDS = frozenset(
    {"aliases", "related_modules", "prerequisites", "related_articles", "source_ids"}
)
_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
_HEADING_PATTERN = re.compile(r"^#\s+(.+?)\s*$")


class ContentValidationError(ValueError):
    """The bundled manual content is missing, malformed, or inconsistent."""


@dataclass(frozen=True, slots=True)
class ManualPage:
    id: str
    title: str
    body: str
    related_articles: tuple[str, ...]
    footer: str
    source_path: Path
    summary: str
    search_text: str


@dataclass(frozen=True, slots=True)
class KnowledgeArticle:
    id: str
    title: str
    english_title: str
    aliases: tuple[str, ...]
    category: str
    software_status: str
    related_modules: tuple[str, ...]
    prerequisites: tuple[str, ...]
    related_articles: tuple[str, ...]
    source_ids: tuple[str, ...]
    last_verified: date
    body: str
    source_path: Path
    summary: str
    search_text: str


@dataclass(frozen=True, slots=True)
class ContentSearchResult:
    kind: str
    item_id: str
    title: str
    english_title: str
    category: str | None
    software_status: str | None
    score: int
    match_reason: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class ManualContentLibrary:
    manuals: tuple[ManualPage, ...]
    articles: tuple[KnowledgeArticle, ...]
    category_order: tuple[str, ...] = CATEGORY_ORDER
    _manual_by_id: Mapping[str, ManualPage] = field(init=False, repr=False, compare=False)
    _article_by_id: Mapping[str, KnowledgeArticle] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        manual_by_id = _unique_index(self.manuals, "手册")
        article_by_id = _unique_index(self.articles, "专业文章")
        article_ids = set(article_by_id)
        for page in self.manuals:
            missing = [reference for reference in page.related_articles if reference not in article_ids]
            if missing:
                raise ContentValidationError(
                    f"{page.source_path}: 相关术语引用了不存在的文章 ID：{', '.join(missing)}"
                )
        for article in self.articles:
            for field_name, references in (
                ("prerequisites", article.prerequisites),
                ("related_articles", article.related_articles),
            ):
                missing = [reference for reference in references if reference not in article_ids]
                if missing:
                    raise ContentValidationError(
                        f"{article.source_path}: {field_name} 引用了不存在的文章 ID："
                        f"{', '.join(missing)}"
                    )
        object.__setattr__(self, "_manual_by_id", MappingProxyType(manual_by_id))
        object.__setattr__(self, "_article_by_id", MappingProxyType(article_by_id))

    def get_manual(self, manual_id: str) -> ManualPage:
        try:
            return self._manual_by_id[manual_id]
        except KeyError as exc:
            raise KeyError(f"未知手册 ID：{manual_id}") from exc

    def get_article(self, article_id: str) -> KnowledgeArticle:
        try:
            return self._article_by_id[article_id]
        except KeyError as exc:
            raise KeyError(f"未知专业文章 ID：{article_id}") from exc

    def articles_in_category(self, category: str) -> tuple[KnowledgeArticle, ...]:
        if category not in self.category_order:
            raise KeyError(f"未知专业文章分类：{category}")
        return tuple(article for article in self.articles if article.category == category)

    def prerequisites_for(self, article_id: str) -> tuple[KnowledgeArticle, ...]:
        article = self.get_article(article_id)
        return tuple(self.get_article(reference) for reference in article.prerequisites)

    def related_for(self, article_id: str) -> tuple[KnowledgeArticle, ...]:
        article = self.get_article(article_id)
        return tuple(self.get_article(reference) for reference in article.related_articles)

    def search_articles(
        self, query: str, *, category: str | None = None
    ) -> tuple[KnowledgeArticle, ...]:
        terms = _normalize_search_text(query).split()
        if not terms:
            return ()
        candidates = self.articles if category is None else self.articles_in_category(category)
        return tuple(
            article
            for article in candidates
            if all(term in article.search_text for term in terms)
        )

    def search_manuals(self, query: str) -> tuple[ManualPage, ...]:
        terms = _normalize_search_text(query).split()
        if not terms:
            return ()
        return tuple(
            page
            for page in self.manuals
            if all(term in page.search_text for term in terms)
        )

    def search(self, query: str) -> tuple[ContentSearchResult, ...]:
        normalized_query = _normalize_search_text(query)
        terms = normalized_query.split()
        if not terms:
            return ()
        results: list[tuple[ContentSearchResult, int, int]] = []
        for index, article in enumerate(self.articles):
            if not all(term in article.search_text for term in terms):
                continue
            score, reason, excerpt = _rank_match(
                normalized_query,
                terms,
                article.id,
                (article.title, article.english_title, *article.aliases),
                article.summary,
                article.body,
            )
            results.append((ContentSearchResult(
                kind="article",
                item_id=article.id,
                title=article.title,
                english_title=article.english_title,
                category=article.category,
                software_status=article.software_status,
                score=score,
                match_reason=reason,
                excerpt=excerpt,
            ), 0, index))
        for index, page in enumerate(self.manuals):
            if not all(term in page.search_text for term in terms):
                continue
            score, reason, excerpt = _rank_match(
                normalized_query,
                terms,
                page.id,
                (page.title,),
                page.summary,
                "\n".join((page.body, page.footer)),
            )
            results.append((ContentSearchResult(
                kind="manual",
                item_id=page.id,
                title=page.title,
                english_title="",
                category=None,
                software_status=None,
                score=score,
                match_reason=reason,
                excerpt=excerpt,
            ), 1, index))
        return tuple(item for item, _, _ in sorted(
            results, key=lambda value: (-value[0].score, value[1], value[2])
        ))


def content_root() -> Path:
    """Return the source or PyInstaller content root without using the CWD."""
    candidates: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.extend(
            (
                Path(bundle_root) / "docs" / "knowledge-drafts",
                Path(bundle_root) / "quant_lab" / "resources" / "manual_content",
            )
        )
    source_root = Path(__file__).resolve().parents[1]
    candidates.extend(
        (
            source_root / "docs" / "knowledge-drafts",
            Path(__file__).resolve().parent / "resources" / "manual_content",
        )
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    checked = ", ".join(str(candidate) for candidate in candidates)
    raise ContentValidationError(f"找不到使用手册内容资源；已检查：{checked}")


def load_manual_content(root: Path | None = None) -> ManualContentLibrary:
    """Discover, parse, and validate every bundled manual and article."""
    root = (root or content_root()).resolve()
    manual_dir = root / "manual"
    article_dir = root / "articles"
    if not manual_dir.is_dir() or not article_dir.is_dir():
        raise ContentValidationError(f"内容目录不完整：{root}")

    actual_manual_ids = {path.stem for path in manual_dir.glob("*.md")}
    expected_manual_ids = set(MANUAL_ORDER)
    if actual_manual_ids != expected_manual_ids:
        missing = sorted(expected_manual_ids - actual_manual_ids)
        unexpected = sorted(actual_manual_ids - expected_manual_ids)
        detail = []
        if missing:
            detail.append(f"缺少 {', '.join(missing)}")
        if unexpected:
            detail.append(f"存在未登记文件 {', '.join(unexpected)}")
        raise ContentValidationError(f"手册资源必须恰好包含 10 篇：{'；'.join(detail)}")
    manuals = tuple(parse_manual_page(manual_dir / f"{manual_id}.md") for manual_id in MANUAL_ORDER)

    article_paths = tuple(sorted(article_dir.rglob("*.md")))
    if len(article_paths) != EXPECTED_ARTICLE_COUNT:
        raise ContentValidationError(
            f"专业文章资源应为 {EXPECTED_ARTICLE_COUNT} 篇，实际为 {len(article_paths)} 篇。"
        )
    articles = tuple(parse_knowledge_article(path) for path in article_paths)
    ordered_articles = tuple(
        article
        for category in CATEGORY_ORDER
        for article in sorted(
            (item for item in articles if item.category == category),
            key=lambda item: item.id,
        )
    )
    if len(ordered_articles) != len(articles):
        raise ContentValidationError("专业文章包含未登记分类。")
    return ManualContentLibrary(manuals=manuals, articles=ordered_articles)


def parse_manual_page(path: Path) -> ManualPage:
    text = _read_text(path)
    lines = text.splitlines()
    if not lines:
        raise ContentValidationError(f"{path}: 手册为空。")
    match = _HEADING_PATTERN.fullmatch(lines[0])
    if not match:
        raise ContentValidationError(f"{path}: 手册首行必须是一级标题。")
    title = match.group(1).strip()
    raw_body = "\n".join(lines[1:]).strip()
    body, related_articles, footer = _split_manual_related(raw_body, path)
    if not body:
        raise ContentValidationError(f"{path}: 手册正文为空。")
    summary = _section_paragraph(body, "这一页是做什么的")
    return ManualPage(
        id=path.stem,
        title=title,
        body=body,
        related_articles=related_articles,
        footer=footer,
        source_path=path.resolve(),
        summary=summary,
        search_text=_normalize_search_text(
            f"{title}\n{' '.join(related_articles)}\n{_markdown_to_text(body)}\n{_markdown_to_text(footer)}"
        ),
    )


def parse_knowledge_article(path: Path) -> KnowledgeArticle:
    text = _read_text(path)
    metadata, body = _split_frontmatter(text, path)
    missing = [field_name for field_name in _REQUIRED_ARTICLE_FIELDS if field_name not in metadata]
    if missing:
        raise ContentValidationError(f"{path}: frontmatter 缺少必填字段：{', '.join(missing)}")

    scalars = {
        field_name: _required_scalar(metadata[field_name], field_name, path)
        for field_name in (
            "id", "title", "english_title", "category", "software_status", "last_verified"
        )
    }
    lists = {
        field_name: _parse_inline_list(metadata[field_name], field_name, path)
        for field_name in _LIST_FIELDS
    }
    if not _ID_PATTERN.fullmatch(scalars["id"]):
        raise ContentValidationError(f"{path}: id 只能包含小写字母、数字和下划线。")
    if scalars["category"] not in CATEGORY_ORDER:
        raise ContentValidationError(f"{path}: 非法 category：{scalars['category']}")
    if scalars["software_status"] not in SOFTWARE_STATUSES:
        raise ContentValidationError(
            f"{path}: 非法 software_status：{scalars['software_status']}"
        )
    for field_name in ("aliases", "related_modules", "source_ids"):
        if not lists[field_name]:
            raise ContentValidationError(f"{path}: {field_name} 不得为空。")
    if not body:
        raise ContentValidationError(f"{path}: Markdown 正文为空。")
    try:
        last_verified = date.fromisoformat(scalars["last_verified"])
    except ValueError as exc:
        raise ContentValidationError(
            f"{path}: last_verified 必须是 YYYY-MM-DD 日期。"
        ) from exc

    summary = _section_paragraph(body, "一句话解释")
    searchable = "\n".join(
        (scalars["title"], scalars["english_title"], *lists["aliases"], _markdown_to_text(body))
    )
    return KnowledgeArticle(
        id=scalars["id"],
        title=scalars["title"],
        english_title=scalars["english_title"],
        aliases=lists["aliases"],
        category=scalars["category"],
        software_status=scalars["software_status"],
        related_modules=lists["related_modules"],
        prerequisites=lists["prerequisites"],
        related_articles=lists["related_articles"],
        source_ids=lists["source_ids"],
        last_verified=last_verified,
        body=body,
        source_path=path.resolve(),
        summary=summary,
        search_text=_normalize_search_text(searchable),
    )


def _split_manual_related(body: str, path: Path) -> tuple[str, tuple[str, ...], str]:
    lines = body.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == "## 相关术语")
    except StopIteration as exc:
        raise ContentValidationError(f"{path}: 手册缺少“相关术语”区段。") from exc
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    related: list[str] = []
    for line_number, line in enumerate(lines[start + 1:end], start=start + 2):
        match = re.fullmatch(r"\s*-\s+`([a-z0-9_]+)`(?:\s+.+)?\s*", line)
        if match:
            related.append(match.group(1))
        elif line.strip() and not line.startswith("相关词条正文将在后续批次提供"):
            raise ContentValidationError(f"{path}:{line_number}: 相关术语行格式无效。")
    if not related:
        raise ContentValidationError(f"{path}: 相关术语不得为空。")
    return (
        "\n".join(lines[:start]).strip(),
        tuple(related),
        "\n".join(lines[end:]).strip(),
    )


def _section_paragraph(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.lstrip("# ").strip() == heading),
        -1,
    )
    candidates = lines[start + 1:] if start >= 0 else lines
    paragraph: list[str] = []
    for line in candidates:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("#"):
            if paragraph:
                break
            continue
        if stripped.startswith(("- ", "|", "```")):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    summary = _markdown_to_text(" ".join(paragraph))
    if summary:
        return summary
    plain = _markdown_to_text(markdown)
    return plain[:180] + ("…" if len(plain) > 180 else "")


def _rank_match(
    query: str,
    terms: list[str],
    item_id: str,
    metadata_fields: tuple[str, ...],
    summary: str,
    body: str,
) -> tuple[int, str, str]:
    normalized_id = _normalize_search_text(item_id)
    normalized_fields = tuple(_normalize_search_text(value) for value in metadata_fields)
    normalized_summary = _normalize_search_text(summary)
    plain_body = _markdown_to_text(body)
    normalized_body = _normalize_search_text(plain_body)
    if query == normalized_id or query in normalized_fields:
        score, reason = 1000, "标题或别名完全匹配"
    elif any(field.startswith(query) for field in normalized_fields):
        score, reason = 820, "标题或别名开头匹配"
    elif any(query in field for field in normalized_fields):
        score, reason = 720, "标题或别名匹配"
    elif query in normalized_summary:
        score, reason = 460, "核心解释匹配"
    else:
        score, reason = 220, "正文匹配"
    for term in terms:
        if term == normalized_id or any(term in field for field in normalized_fields):
            score += 30
        elif term in normalized_summary:
            score += 12
        else:
            score += min(normalized_body.count(term), 5)
    score += min(normalized_body.count(query), 5)
    excerpt = summary
    if query not in normalized_summary and query in normalized_body:
        excerpt = _matching_excerpt(plain_body, query)
    return score, reason, excerpt


def _matching_excerpt(text: str, normalized_query: str) -> str:
    normalized_text = _normalize_search_text(text)
    position = normalized_text.find(normalized_query)
    if position < 0:
        return text[:180] + ("…" if len(text) > 180 else "")
    start = max(0, position - 55)
    end = min(len(text), position + len(normalized_query) + 105)
    return ("…" if start else "") + text[start:end].strip() + ("…" if end < len(text) else "")


def _split_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ContentValidationError(f"{path}: 专业文章必须以 frontmatter 开始。")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise ContentValidationError(f"{path}: frontmatter 缺少结束分隔符。") from exc
    metadata: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or ":" not in line:
            raise ContentValidationError(f"{path}:{line_number}: frontmatter 行格式无效。")
        key, value = line.split(":", 1)
        key = key.strip()
        if not _ID_PATTERN.fullmatch(key):
            raise ContentValidationError(f"{path}:{line_number}: frontmatter 字段名无效。")
        if key in metadata:
            raise ContentValidationError(f"{path}:{line_number}: frontmatter 字段重复：{key}")
        metadata[key] = value.strip()
    return metadata, "\n".join(lines[end + 1 :]).strip()


def _required_scalar(value: str, field_name: str, path: Path) -> str:
    value = _strip_matching_quotes(value.strip())
    if not value or value.startswith("["):
        raise ContentValidationError(f"{path}: {field_name} 必须是非空文本。")
    return value


def _parse_inline_list(value: str, field_name: str, path: Path) -> tuple[str, ...]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise ContentValidationError(f"{path}: {field_name} 必须使用 [a, b] 列表格式。")
    inner = value[1:-1].strip()
    if not inner:
        return ()
    items = tuple(_strip_matching_quotes(item.strip()) for item in inner.split(","))
    if any(not item for item in items):
        raise ContentValidationError(f"{path}: {field_name} 包含空条目。")
    return items


def _strip_matching_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ContentValidationError(f"无法读取内容资源：{path}") from exc


def _unique_index(items: Sequence[ManualPage | KnowledgeArticle], label: str) -> dict[str, object]:
    index: dict[str, object] = {}
    for item in items:
        if item.id in index:
            raise ContentValidationError(f"{label} ID 重复：{item.id}")
        index[item.id] = item
    return index


def _markdown_to_text(markdown: str) -> str:
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", markdown)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[`*_>#|~-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()
