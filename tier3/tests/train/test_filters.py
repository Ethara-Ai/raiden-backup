from helpers import moto_state


def test_filter_exclude_then_include_keeps_txt(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "a.txt").write_text("a")
    (src / "a.log").write_text("a")
    r = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/",
        "--recursive", "--exclude", "*", "--include", "*.txt",
    )
    assert r.returncode == 0
    assert set(moto_state.list_keys(s3, random_bucket)) == {"a.txt"}


def test_filter_include_then_exclude_keeps_nothing(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "a.txt").write_text("a")
    r_baseline = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/", "--recursive",
    )
    assert r_baseline.returncode == 0
    assert "a.txt" in moto_state.list_keys(s3, random_bucket)
    s3.delete_object(Bucket=random_bucket, Key="a.txt")

    r = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/",
        "--recursive", "--include", "*.txt", "--exclude", "*",
    )
    assert r.returncode == 0
    assert moto_state.list_keys(s3, random_bucket) == []


def test_filter_default_includes_all(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "a.txt").write_text("a")
    (src / "b.log").write_text("b")
    r = cli("s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/", "--recursive")
    assert r.returncode == 0
    assert set(moto_state.list_keys(s3, random_bucket)) == {"a.txt", "b.log"}


def test_filter_bare_include_is_noop(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "a.txt").write_text("a")
    (src / "b.log").write_text("b")
    r = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/",
        "--recursive", "--include", "*.txt",
    )
    assert r.returncode == 0
    assert set(moto_state.list_keys(s3, random_bucket)) == {"a.txt", "b.log"}


def test_filter_glob_question_mark(cli, s3, random_bucket, tmp_workdir):
    s3.create_bucket(Bucket=random_bucket)
    src = tmp_workdir / "src"
    src.mkdir()
    (src / "a.txt").write_text("1")
    (src / "ab.txt").write_text("2")
    r = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{random_bucket}/",
        "--recursive", "--exclude", "*", "--include", "?.txt",
    )
    assert r.returncode == 0
    assert set(moto_state.list_keys(s3, random_bucket)) == {"a.txt"}
