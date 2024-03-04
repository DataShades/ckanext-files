import pytest

from ckanext.files import utils


@pytest.mark.parametrize(
    ["value", "size"],
    [
        ("1", 1),
        ("1b", 1),
        ("1kb", 10**3),
        ("1kib", 2**10),
        ("1mb", 10**6),
        ("1mib", 2**20),
        ("1gb", 10**9),
        ("1gib", 2**30),
        ("1tb", 10**12),
        ("1tib", 2**40),
        ("  117  ", 117),
        ("0.7 mib", 734003),
        ("1b", 1),
        ("1 kib", 1024),
        ("10.43 kib", 10680),
        ("1024b", 1024),
        ("11 GiB", 11811160064),
        ("117 b", 117),
        ("117 kib", 119808),
        ("117b", 117),
        ("117kib", 119808),
        ("11GiB", 11811160064),
        ("1mib", 1048576),
        ("343.1MiB", 359766425),
        ("5.2 mib", 5452595),
        ("58 kib", 59392),
    ],
)
def test_filesize_parser(value, size):
    # type: (str, int) -> None
    assert utils.parse_filesize(value) == size
