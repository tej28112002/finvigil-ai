"""
Journal (Phase 15.1 continuation, priority #7) -- JournalService: fixed
psychology taxonomy enforcement and cascade-delete behavior (soft-delete
entry, hard-delete tags). BRD FR-JRN-02/03. Re-verified here as a
permanent test, not just the one-time manual verification from when
Phase 10 was originally built.

Valid tag names are read from app.core.journal_taxonomy.PSYCHOLOGY_TAGS
directly (the actual source of truth this project defines), not
duplicated/guessed here.
"""
from uuid import uuid4

import pytest

from app.core.journal_taxonomy import PSYCHOLOGY_TAGS
from app.services.journal_service import JournalService
from tests.fakes import FakeJournalEntryRepository, FakeJournalTagRepository

VALID_TAG = next(iter(PSYCHOLOGY_TAGS))  # any real tag, not hardcoded/guessed


def make_service():
    entry_repo = FakeJournalEntryRepository()
    tag_repo = FakeJournalTagRepository()
    return JournalService(entry_repo, tag_repo), entry_repo, tag_repo


def test_create_entry_from_text_rejects_empty_transcript():
    service, _, _ = make_service()
    with pytest.raises(ValueError, match="cannot be empty"):
        service.create_entry_from_text(uuid4(), "   ")


def test_create_entry_from_text_strips_whitespace():
    service, _, _ = make_service()
    entry = service.create_entry_from_text(uuid4(), "  Sold too early again  ")
    assert entry.transcript == "Sold too early again"


def test_add_tags_rejects_invalid_tag_not_in_taxonomy():
    service, entry_repo, _ = make_service()
    user_id = uuid4()
    entry = entry_repo.create_entry(user_id, "test entry")

    with pytest.raises(ValueError, match="Invalid tag"):
        service.add_tags(user_id, entry.id, ["definitely_not_a_real_tag"])


def test_add_tags_accepts_valid_taxonomy_tag():
    service, entry_repo, tag_repo = make_service()
    user_id = uuid4()
    entry = entry_repo.create_entry(user_id, "test entry")

    result = service.add_tags(user_id, entry.id, [VALID_TAG])

    assert len(result) == 1
    assert result[0].tag_name == VALID_TAG
    assert len(tag_repo.get_by_entry(entry.id)) == 1


def test_add_tags_mixed_valid_and_invalid_rejects_the_whole_batch():
    """One invalid tag in a batch call must reject ALL of them, not
    silently apply the valid ones and drop the bad one."""
    service, entry_repo, tag_repo = make_service()
    user_id = uuid4()
    entry = entry_repo.create_entry(user_id, "test entry")

    with pytest.raises(ValueError, match="Invalid tag"):
        service.add_tags(user_id, entry.id, [VALID_TAG, "not_real"])

    assert tag_repo.get_by_entry(entry.id) == []


def test_add_tags_deduplicates_against_already_applied_tags():
    """journal_tags has UNIQUE(journal_entry_id, tag_name) at the DB
    level -- re-adding an already-present tag must be a silent no-op, not
    a duplicate row or a DB error."""
    service, entry_repo, tag_repo = make_service()
    user_id = uuid4()
    entry = entry_repo.create_entry(user_id, "test entry")

    service.add_tags(user_id, entry.id, [VALID_TAG])
    second_call_result = service.add_tags(user_id, entry.id, [VALID_TAG])

    assert second_call_result == []
    assert len(tag_repo.get_by_entry(entry.id)) == 1  # still just one, not two


def test_add_tags_on_nonexistent_or_wrong_owner_entry_returns_none():
    service, entry_repo, _ = make_service()
    owner = uuid4()
    stranger = uuid4()
    entry = entry_repo.create_entry(owner, "test entry")

    assert service.add_tags(stranger, entry.id, [VALID_TAG]) is None
    assert service.add_tags(owner, uuid4(), [VALID_TAG]) is None


def test_delete_entry_soft_deletes_entry_and_hard_deletes_tags():
    """FR-JRN-03: cascades transcript (soft-delete flag on the entry) +
    tags (hard-deleted, no soft-delete column exists on journal_tags)."""
    service, entry_repo, tag_repo = make_service()
    user_id = uuid4()
    entry = entry_repo.create_entry(user_id, "test entry")
    service.add_tags(user_id, entry.id, [VALID_TAG])
    assert len(tag_repo.get_by_entry(entry.id)) == 1

    result = service.delete_entry(user_id, entry.id)

    assert result is True
    assert entry.is_deleted is True  # soft delete, entry row itself still exists
    assert tag_repo.get_by_entry(entry.id) == []  # tags hard-deleted
    assert entry.id in tag_repo.delete_by_entry_calls


def test_delete_entry_wrong_owner_returns_false_and_does_not_delete():
    service, entry_repo, tag_repo = make_service()
    owner = uuid4()
    stranger = uuid4()
    entry = entry_repo.create_entry(owner, "test entry")
    service.add_tags(owner, entry.id, [VALID_TAG])

    result = service.delete_entry(stranger, entry.id)

    assert result is False
    assert entry.is_deleted is False
    assert len(tag_repo.get_by_entry(entry.id)) == 1  # tags untouched


def test_soft_deleted_entry_excluded_from_get_by_id_and_user():
    """After delete, the entry must no longer be reachable via the normal
    lookup path -- confirms the soft-delete flag is actually honored, not
    just set and ignored."""
    service, entry_repo, _ = make_service()
    user_id = uuid4()
    entry = entry_repo.create_entry(user_id, "test entry")
    service.delete_entry(user_id, entry.id)

    assert service.get_entry_detail(user_id, entry.id) is None
