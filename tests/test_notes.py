"""Categorized notes, drafts, managed attachments, trash, and library staging."""

from io import BytesIO
import json
from pathlib import Path
import sqlite3
from zipfile import ZipFile

import pytest
from streamlit.testing.v1 import AppTest

from quant_lab import notes, paths, storage


def test_hierarchical_categories_drafts_and_recycle_bin(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    parent = notes.create_category("研究")
    child = notes.create_category("港股", parent)
    with pytest.raises(ValueError, match="子分类"):
        notes.move_category(parent, child)
    notes.save_draft("draft-a", title="腾讯", content="# 草稿", category_id=child)
    assert notes.latest_draft()["content"] == "# 草稿"
    note_id = notes.save_note(title="腾讯", content="# 正文", category_id=child, draft_id="draft-a")
    assert notes.latest_draft() is None
    assert notes.list_library_items(category_id=parent)[0]["id"] == note_id
    notes.trash_item("笔记", note_id)
    assert not notes.list_library_items()
    assert notes.list_library_items(trashed=True)[0]["id"] == note_id
    notes.restore_item("笔记", note_id)
    notes.delete_category(parent)
    assert notes.get_note(note_id)["category_id"] == child
    assert next(row for row in notes.list_categories() if row["id"] == child)["parent_id"] is None


def test_attachment_validation_hash_export_and_permanent_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    notes.save_draft("draft-file", title="附件", content="正文")
    png = b"\x89PNG\r\n\x1a\n" + b"sample"
    attachment = notes.save_attachment(png, "chart.png", draft_id="draft-file")
    with pytest.raises(ValueError, match="白名单"):
        notes.save_attachment(b"MZ", "danger.exe", draft_id="draft-file")
    note_id = notes.save_note(title="附件", content=f"![图](attachment://{attachment['id']})",
                              draft_id="draft-file")
    promoted = notes.list_attachments(note_id=note_id)[0]
    assert promoted["stored_relpath"].startswith(f"notes/attachments/{note_id}/")
    assert notes.attachment_bytes(promoted) == png
    with ZipFile(BytesIO(notes.export_note_zip(note_id))) as archive:
        assert archive.read("attachments/chart.png") == png
        manifest = json.loads(archive.read("attachments.json"))
        assert manifest[0]["sha256"] == attachment["sha256"]
    managed = tmp_path / promoted["stored_relpath"]
    notes.trash_item("笔记", note_id)
    notes.permanent_delete_item("笔记", note_id)
    assert not managed.exists()


def test_attachment_deduplicates_across_saved_note_and_active_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    data = b"%PDF-1.4\n%%EOF"
    note_id = notes.save_note(title="附件去重", content="正文")
    original = notes.save_attachment(data, "evidence.pdf", note_id=note_id)
    notes.save_draft("resume-draft", title="附件去重", content="正文", note_id=note_id)

    duplicate = notes.save_attachment(
        data, "renamed.pdf", draft_id="resume-draft", related_note_id=note_id,
    )
    assert duplicate["duplicate"] is True and duplicate["id"] == original["id"]
    assert notes.list_attachments(draft_id="resume-draft") == []

    second = notes.save_attachment(b"%PDF-1.4\nsecond", "second.pdf", draft_id="resume-draft")
    notes.save_note(
        title="附件去重", content="正文", note_id=note_id, draft_id="resume-draft",
    )
    saved = notes.list_attachments(note_id=note_id)
    assert {item["id"] for item in saved} == {original["id"], second["id"]}

    notes.save_draft("legacy-duplicate", title="附件去重", content="正文", note_id=note_id)
    legacy = notes.save_attachment(data, "legacy-copy.pdf", draft_id="legacy-duplicate")
    legacy_path = tmp_path / legacy["stored_relpath"]
    notes.save_note(
        title="附件去重", content="正文", note_id=note_id, draft_id="legacy-duplicate",
    )
    assert not legacy_path.exists()
    assert len([item for item in notes.list_attachments(note_id=note_id)
                if item["sha256"] == original["sha256"]]) == 1


def test_stage_library_copies_database_and_writes_nonsecret_pointer(tmp_path, monkeypatch):
    local = tmp_path / "local"
    monkeypatch.delenv("QUANT_LAB_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    old_root = paths.default_data_dir()
    storage.save_learning_note("旧笔记", "保留正文", path=old_root / "research.sqlite3")
    target = paths.stage_library(tmp_path / "documents")
    assert target == (tmp_path / "documents" / "QuantLabCNHK").resolve()
    assert (target / "database" / "research.sqlite3").is_file()
    assert paths.user_data_dir() == target
    assert storage.list_learning_notes(target / "database" / "research.sqlite3")[0]["content"] == "保留正文"
    pointer = json.loads(paths.bootstrap_path().read_text(encoding="utf-8"))
    assert Path(pointer["data_root"]) == target
    assert "sk-" not in json.dumps(pointer)


def test_first_run_requires_library_setup(tmp_path, monkeypatch):
    monkeypatch.delenv("QUANT_LAB_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "fresh-local"))
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    assert not app.exception
    assert any("创建 Quant Lab 专用资料库" in item.value for item in app.get("html"))
    assert not app.sidebar.radio


def test_library_location_labels_are_unambiguous(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path / "library-labels"))
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    next(item for item in app.button if item.label == "⚙").click().run()

    assert app.text_input(key="settings_library_parent").label == "选择新的存放文件夹"
    captions = [str(item.value) for item in app.caption]
    assert "当前资料库位置" in captions
    assert "迁移后的资料库位置" in captions
    assert "当前资料根目录" not in captions
    assert not [item for item in app.text_input if item.label == "资料库父目录"]
    assert any("QuantLabCNHK" in str(item.value) for item in app.code)


def test_notes_panel_opens_on_restored_editor_and_keeps_new_draft(monkeypatch, tmp_path):
    data_dir = tmp_path / "notes-ui"
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(data_dir))
    notes.save_draft("existing-draft", title="最近草稿", content="# 未完成正文")
    note_id = notes.save_note(title="资料库笔记", content="已保存正文")

    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    next(item for item in app.button if item.label == "研究笔记").click().run()

    assert app.text_input(key="note_editor_title").value == "最近草稿"
    assert app.text_area(key="note_editor_content").value == "# 未完成正文"
    assert app.button(key="note_save").label == "保存笔记"
    assert app.button(key="note_new").label == "新建笔记"
    assert not [item for item in app.subheader if item.value == "研究笔记与实验档案"]
    assert any(item.label == "更多选项（分类与附件）" for item in app.expander)
    assert app.button(key="notes_open_management")
    assert app.button(key="notes_panel_history")
    assert not [item for item in app.selectbox if item.label == "内容类型"]
    assert not [item for item in app.selectbox if item.label == "分类范围"]

    app.text_input(key="note_editor_title").input("更新中的草稿").run()
    app.button(key="note_new").click().run()
    assert app.text_input(key="note_editor_title").value == ""
    assert app.text_area(key="note_editor_content").value == ""
    with sqlite3.connect(paths.database_path()) as db:
        drafts = db.execute("SELECT id,title FROM note_drafts ORDER BY updated_at").fetchall()
    assert len(drafts) == 2
    assert any(title == "更新中的草稿" for _, title in drafts)

    app.button(key="notes_panel_history").click().run()
    assert app.text_input(key="notes_history_search")
    assert not [item for item in app.selectbox if item.label == "选择实验"]
    app.button(key=f"note_history_open_{note_id}").click().run()
    assert app.session_state["notes_view"] == "reader"
    assert not [item for item in app.text_area if item.label == "Markdown 正文"]
    app.button(key="notes_reader_edit").click().run()
    assert app.session_state["note_editor_note_id"] == note_id
    assert app.text_input(key="note_editor_title").value == "资料库笔记"
    assert app.text_area(key="note_editor_content").value == "已保存正文"
    assert any("scrollTo" in str(item.value) for item in app.get("html"))


def test_notes_panel_falls_back_to_most_recent_saved_note(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path / "saved-note-resume"))
    older = notes.save_note(title="较早笔记", content="旧内容")
    latest = notes.save_note(title="最近笔记", content="继续记录")
    assert latest > older and notes.latest_draft() is None

    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    next(item for item in app.button if item.label == "研究笔记").click().run()

    assert app.session_state["notes_view"] == "editor"
    assert app.session_state["note_editor_note_id"] == latest
    assert app.text_input(key="note_editor_title").value == "最近笔记"
    assert app.text_area(key="note_editor_content").value == "继续记录"


def test_note_save_keeps_a_resumable_working_copy(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path / "saved-working-copy"))
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    next(item for item in app.button if item.label == "研究笔记").click().run()
    app.text_input(key="note_editor_title").input("保存后继续").run()
    app.text_area(key="note_editor_content").input("下一次仍从这里开始").run()
    app.button(key="note_save").click().run()

    draft = notes.latest_draft()
    assert draft and draft["note_id"] == app.session_state["note_editor_note_id"]
    assert draft["title"] == "保存后继续"
    assert draft["content"] == "下一次仍从这里开始"


def test_history_reader_renders_markdown_and_category_search_includes_children(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path / "reader-category"))
    parent = notes.create_category("收益")
    child = notes.create_category("港股收益", parent)
    note_id = notes.save_note(
        title="复权说明", content="## 已渲染标题\n\n|列|值|\n|---|---|\n|A|1|",
        category_id=child,
    )
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    next(item for item in app.button if item.label == "研究笔记").click().run()
    app.button(key="notes_panel_history").click().run()

    app.text_input(key="notes_history_search").input("收益").run()
    assert app.button(key=f"notes_history_category_{parent}")
    app.button(key=f"notes_history_category_{parent}").click().run()
    assert app.button(key=f"note_history_open_{note_id}")
    app.button(key=f"note_history_open_{note_id}").click().run()

    assert app.session_state["notes_view"] == "reader"
    assert not [item for item in app.text_area if item.label == "Markdown 正文"]
    assert any("已渲染标题" in item.value for item in app.markdown)
    assert app.button(key="notes_reader_edit")
    app.button(key="notes_reader_edit").click().run()
    assert app.text_area(key="note_editor_content").value.startswith("## 已渲染标题")
