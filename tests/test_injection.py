from benchmark.injection import InjectionError, apply_injection
from benchmark.manifest import BenchmarkCase


def make_case() -> BenchmarkCase:
    return BenchmarkCase(
        case_id="case_replace",
        source_type="historical",
        repo_url="https://example.com/repo.git",
        repo_name="repo",
        base_commit="abc",
        python_version="3.11",
        install=["pip install -e ."],
        test_command="pytest tests/test_a.py -q",
        regression_test_command=None,
        allowed_paths=["src/"],
        target_file="src/mod.py",
        injection_patch="patch",
        expected_failures=["tests/test_a.py::test_one"],
        tags=["historical"],
        difficulty="medium",
        seed=5,
        metadata={"injection_mode": "replace", "old_content": "return 1", "new_content": "return 2"},
    )


def test_apply_replace_injection(tmp_path):
    workspace = tmp_path / "repo"
    src = workspace / "src"
    src.mkdir(parents=True)
    target = src / "mod.py"
    target.write_text("def f():\n    return 1\n", encoding="utf-8")

    case = make_case()
    apply_injection(case, workspace_dir=str(workspace))

    assert "return 2" in target.read_text(encoding="utf-8")


def test_rejects_scope_violation(tmp_path):
    workspace = tmp_path / "repo"
    src = workspace / "src"
    src.mkdir(parents=True)
    target = src / "mod.py"
    target.write_text("def f():\n    return 1\n", encoding="utf-8")

    case = make_case()
    case = BenchmarkCase(**{**case.__dict__, "target_file": "../outside.py"})
    try:
        apply_injection(case, workspace_dir=str(workspace))
        assert False, "Expected scope failure"
    except InjectionError as exc:
        assert "escapes workspace scope" in str(exc)
