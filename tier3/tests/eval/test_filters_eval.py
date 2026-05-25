import string

from hypothesis import HealthCheck, given, settings, strategies as st

from helpers import moto_state
from helpers.isomorphic import IsomorphicTransform


_BUCKET_PBT_SETTINGS = settings(
    max_examples=8,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


@_BUCKET_PBT_SETTINGS
@given(
    txt_count=st.integers(min_value=1, max_value=4),
    log_count=st.integers(min_value=1, max_value=4),
)
def test_filter_exclude_all_include_txt_pbt(cli, s3, tmp_workdir, request, txt_count, log_count):
    import uuid as _uuid
    example_id = _uuid.uuid4().hex[:8]
    iso = IsomorphicTransform(seed=f"tier3-filter-pbt-{request.node.name}-{txt_count}-{log_count}-{example_id}")
    bucket = iso.bucket("pbt-bucket")
    s3.create_bucket(Bucket=bucket)

    src = tmp_workdir / f"src-{example_id}"
    src.mkdir(parents=True, exist_ok=True)
    expected_txt = set()
    for i in range(txt_count):
        name = f"file-{i}.txt"
        (src / name).write_text(f"t{i}")
        expected_txt.add(name)
    for i in range(log_count):
        (src / f"file-{i}.log").write_text(f"l{i}")

    r = cli(
        "s3", "cp", "--no-progress", f"{src.name}/", f"s3://{bucket}/",
        "--recursive", "--exclude", "*", "--include", "*.txt",
    )
    assert r.returncode == 0
    keys = set(moto_state.list_keys(s3, bucket))
    assert keys == expected_txt


def test_filter_root_prefixing_dot_files(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier3-filter-root-{request.node.name}")
    bucket = iso.bucket("root-bucket")
    s3.create_bucket(Bucket=bucket)

    src = tmp_workdir / "src"
    src.mkdir()
    (src / ".gitignore").write_text("ignored")
    (src / "real.txt").write_text("kept")

    r = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{bucket}/",
        "--recursive", "--exclude", ".gitignore",
    )
    assert r.returncode == 0
    keys = set(moto_state.list_keys(s3, bucket))
    assert "real.txt" in keys
    assert ".gitignore" not in keys


def test_filter_no_filters_uploads_all(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier3-filter-noop-{request.node.name}")
    bucket = iso.bucket("noop-bucket")
    s3.create_bucket(Bucket=bucket)

    src = tmp_workdir / "src"
    src.mkdir()
    for name in ("a.txt", "b.log", "c.md"):
        (src / name).write_text(name)

    r = cli("s3", "cp", "--no-progress", "src/", f"s3://{bucket}/", "--recursive")
    assert r.returncode == 0
    assert set(moto_state.list_keys(s3, bucket)) == {"a.txt", "b.log", "c.md"}


def test_filter_include_then_exclude_keeps_nothing(cli, s3, tmp_workdir, request):
    iso = IsomorphicTransform(seed=f"tier3-filter-reverse-{request.node.name}")
    bucket = iso.bucket("rev-bucket")
    s3.create_bucket(Bucket=bucket)

    src = tmp_workdir / "src"
    src.mkdir()
    (src / "z.txt").write_text("z")

    r_baseline = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{bucket}/", "--recursive",
    )
    assert r_baseline.returncode == 0
    assert "z.txt" in moto_state.list_keys(s3, bucket)
    s3.delete_object(Bucket=bucket, Key="z.txt")

    r = cli(
        "s3", "cp", "--no-progress", "src/", f"s3://{bucket}/",
        "--recursive", "--include", "*.txt", "--exclude", "*",
    )
    assert r.returncode == 0
    assert moto_state.list_keys(s3, bucket) == []
