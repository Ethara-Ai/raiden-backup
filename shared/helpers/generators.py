"""Property-based generators for hypothesis-driven fuzz tests.

Used in tier3 only — tier1/tier2 use UUID-based random fixtures.
Targets the URI parser, filter semantics, and human-readable byte boundaries
where impls are most likely to fail in the tail.
"""
from hypothesis import strategies as st


# AWS S3 bucket name validator. Subset of the full rules:
#   3-63 chars, lowercase letters / digits / hyphens, no leading/trailing hyphen,
#   no consecutive periods, no IP-like names.
bucket_names = st.from_regex(
    r"^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$",
    fullmatch=True,
).filter(lambda b: ".." not in b and not b.startswith("xn--"))


# S3 keys can contain a wide range of bytes; restrict to a manageable subset.
s3_keys = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="/-._",
    ),
    min_size=1, max_size=200,
).filter(lambda k: not k.startswith("/"))


# Byte sizes covering human-readable boundaries.
# Source: awscli/customizations/s3/utils.py human_readable_size:
#   1 -> '1 Byte', 2..1023 -> 'N Bytes', >=1024 -> '<N>.<N> KiB' (base-2 IEC).
hr_byte_sizes = st.one_of(
    st.just(0),
    st.just(1),
    st.just(2),
    st.integers(min_value=3, max_value=1023),
    st.just(1024),
    st.just(1025),
    st.integers(min_value=1024, max_value=10**6),
    st.integers(min_value=10**9, max_value=10**11),
)


# fnmatch-style filter patterns.
filter_patterns = st.one_of(
    st.just("*"),
    st.just("*.txt"),
    st.just("*.log"),
    st.just("dir/*"),
    st.just(".git/*"),
    st.just("?.txt"),
    st.just("[a-z]*.txt"),
)
