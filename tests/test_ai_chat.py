"""Persistent DeepSeek conversations stay scoped, searchable, and secret-safe."""

from pathlib import Path

from quant_lab import ai_chat, storage


def test_conversation_messages_persist_search_rename_and_delete(tmp_path: Path) -> None:
    database = tmp_path / "chat.sqlite3"
    conversation = ai_chat.create_conversation(
        "scope-a", {"market": "A 股", "symbol": "600519", "notes": "private"},
        path=database, conversation_id="conversation-a",
    )
    assert conversation["title"] == "新对话"
    assert "notes" not in conversation["context"]

    ai_chat.add_message(
        conversation["id"], turn_id="turn-a", role="user",
        content="解释简单收益率", path=database,
    )
    assistant = ai_chat.add_message(
        conversation["id"], turn_id="turn-a", role="assistant",
        content="最终回答", model="deepseek-flash", complete=False,
        finish_reason="aborted", error="连接中断", context={"market": "A 股"},
        path=database,
    )
    assert ai_chat.get_conversation(conversation["id"], database)["title"] == "解释简单收益率"
    assert ai_chat.list_conversations("最终回答", database)[0]["message_count"] == 2
    assert ai_chat.latest_conversation("scope-a", database)["id"] == conversation["id"]

    note_id = storage.save_learning_note("保存的回答", "正文", path=database)
    ai_chat.update_message(
        assistant["id"], content="最终回答已补全", complete=True,
        finish_reason="stop", error="", saved_note_id=note_id, path=database,
    )
    loaded = ai_chat.list_messages(conversation["id"], database)
    assert loaded[-1]["content"] == "最终回答已补全"
    assert loaded[-1]["complete"] is True and loaded[-1]["saved_note_id"] == note_id

    ai_chat.rename_conversation(conversation["id"], "收益率学习", database)
    assert ai_chat.list_conversations("收益率学习", database)[0]["title"] == "收益率学习"
    ai_chat.delete_conversation(conversation["id"], database)
    assert ai_chat.list_conversations(path=database) == []


def test_chat_storage_redacts_key_and_separates_scopes(tmp_path: Path) -> None:
    database = tmp_path / "scopes.sqlite3"
    secret = "sk-chat-history-secret-123456"
    first = ai_chat.create_conversation("scope-a", path=database)
    second = ai_chat.create_conversation("scope-b", path=database)
    ai_chat.add_message(
        first["id"], turn_id="one", role="user", content=f"问题 {secret}",
        secrets=(secret,), path=database,
    )
    ai_chat.add_message(second["id"], turn_id="two", role="user", content="另一个研究", path=database)

    assert ai_chat.latest_conversation("scope-a", database)["id"] == first["id"]
    assert ai_chat.latest_conversation("scope-b", database)["id"] == second["id"]
    assert secret not in database.read_bytes().decode("utf-8", errors="ignore")
