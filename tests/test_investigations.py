"""The list of past investigations, and the memory file staying out of git."""

import subprocess

from login_investigator import investigations
from login_investigator.investigations import MAX_QUESTION_CHARS, list_all, start


def test_a_new_case_is_listed(tmp_path):
    path = tmp_path / "m.sqlite"
    case = start("Anything suspicious last night?", path)
    assert list_all(path) == [case]
    assert case.started_at.tzinfo is not None


def test_cases_are_listed_newest_first(tmp_path):
    path = tmp_path / "m.sqlite"
    first = start("first", path)
    second = start("second", path)
    assert [c.thread_id for c in list_all(path)] == [second.thread_id, first.thread_id]


def test_thread_ids_are_unique_and_random(tmp_path):
    path = tmp_path / "m.sqlite"
    ids = {start("same question", path).thread_id for _ in range(20)}
    assert len(ids) == 20


def test_the_first_question_is_tidied_and_shortened(tmp_path):
    case = start("  why\n\n   so   many\tfailures " + "x" * 500, tmp_path / "m.sqlite")
    assert case.first_question.startswith("why so many failures x")
    assert len(case.first_question) == MAX_QUESTION_CHARS


def test_no_cases_gives_an_empty_list(tmp_path):
    assert list_all(tmp_path / "new" / "m.sqlite") == []


def test_the_memory_file_and_its_side_files_are_git_ignored():
    # SQLite in WAL mode writes -wal and -shm files next to the database. They hold conversations.
    memory = investigations.MEMORY_PATH
    for name in (memory, memory.with_name(memory.name + "-wal"),
                 memory.with_name(memory.name + "-shm")):
        relative = name.relative_to(investigations.REPO_ROOT)
        check = subprocess.run(["git", "check-ignore", "-q", str(relative)],
                               cwd=investigations.REPO_ROOT)
        assert check.returncode == 0, f"{relative} is not git-ignored"
