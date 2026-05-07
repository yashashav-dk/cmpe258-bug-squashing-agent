from agent.tools_impl import edit_file, read_file


def test_edit_file_is_idempotent_when_new_content_already_present(tmp_path):
    target = tmp_path / "buggy.py"
    target.write_text("def f():\n    return 2\n", encoding="utf-8")

    result = edit_file(
        str(target),
        old_content="return 1",
        new_content="return 2",
    )

    assert "already present" in result


def test_read_file_directory_gives_actionable_error(tmp_path):
    directory = tmp_path / "case_dir"
    directory.mkdir()

    result = read_file(str(directory))

    assert "is a directory" in result
    assert "ls -F" in result
