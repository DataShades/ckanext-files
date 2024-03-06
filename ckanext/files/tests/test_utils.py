from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from ckanext.files import base, exceptions, utils

from faker import Faker  # isort: skip # noqa: F401


def test_registry(faker):
    # type: (Faker) -> None
    """Brief test of registry functionality."""

    registry = utils.Registry()
    key = faker.word()
    value = object()

    assert registry.get(key) is None

    registry.register(key, value)
    assert registry.get(key) is value
    assert list(registry) == [key]

    registry.reset()
    assert registry.get(key) is None
    assert list(registry) == []


def test_collector():
    """Brief test of collector functionality."""

    collection, collector = utils.make_collector()
    assert collection == {}

    @collector
    def func():  # pragma: no cover
        pass

    assert collection == {"func": func}


class TestEnsureSize:
    def test_empty(self):
        """Filesize identified even if it's not set initially."""

        assert utils.ensure_size(FileStorage(), 0) == 0

    def test_not_empty(self):
        """Big files cause exception."""

        upload = FileStorage(BytesIO(b" " * 10))
        assert utils.ensure_size(upload, 15) == 10

        with pytest.raises(exceptions.LargeUploadError):
            utils.ensure_size(upload, 5)


class TestCombineCapabilities:
    def test_reflexive_combination(self):
        """Combination of unit with itself leaves a single unit."""

        first = utils.combine_capabilities(
            base.Capability.CREATE,
            base.Capability.CREATE,
        )
        second = utils.combine_capabilities(base.Capability.CREATE)
        assert first == second

    def test_commutative_combination(self):
        """Order of combination does not change the result"""

        first = utils.combine_capabilities(
            base.Capability.CREATE,
            base.Capability.REMOVE,
        )
        second = utils.combine_capabilities(
            base.Capability.REMOVE,
            base.Capability.CREATE,
        )
        assert first == second

    def test_associative_combination(self):
        """Rearranging the combination sequence does not change the result."""

        first = utils.combine_capabilities(
            utils.combine_capabilities(base.Capability.CREATE, base.Capability.REMOVE),
            base.Capability.MULTIPART_UPLOAD,
        )
        second = utils.combine_capabilities(
            utils.combine_capabilities(
                base.Capability.CREATE,
                base.Capability.MULTIPART_UPLOAD,
            ),
            base.Capability.REMOVE,
        )
        third = utils.combine_capabilities(
            utils.combine_capabilities(
                base.Capability.REMOVE,
                base.Capability.MULTIPART_UPLOAD,
            ),
            base.Capability.CREATE,
        )

        assert first == second == third

    def test_clusters(self):
        """Clusters can be combined with the same result as individual units."""

        first = utils.combine_capabilities(
            base.Capability.CREATE,
            base.Capability.REMOVE,
        )
        second = utils.combine_capabilities(
            base.Capability.MULTIPART_UPLOAD,
            base.Capability.STREAM,
        )

        clusters = utils.combine_capabilities(first, second)
        units = utils.combine_capabilities(
            base.Capability.CREATE,
            base.Capability.REMOVE,
            base.Capability.MULTIPART_UPLOAD,
            base.Capability.STREAM,
        )
        assert clusters == units


class TestExcludeCapabilities:
    def test_not_intersecting_exclusion(self):
        """Nothing changes when non existing unit excluded."""

        cluster = utils.combine_capabilities(
            base.Capability.CREATE,
            base.Capability.REMOVE,
        )

        assert (
            utils.exclude_capabilities(cluster, base.Capability.MULTIPART_UPLOAD)
            == cluster
        )

    def test_exclusion_of_single_unit(self):
        """Single unit exclusion leaves all other units inside cluster."""

        cluster = utils.combine_capabilities(
            base.Capability.CREATE,
            base.Capability.REMOVE,
        )

        assert utils.exclude_capabilities(
            cluster,
            base.Capability.CREATE,
        ) == utils.combine_capabilities(base.Capability.REMOVE)

    def test_multi_unit_exclusion(self):
        """Multiple units can be excluded at once."""

        cluster = utils.combine_capabilities(
            base.Capability.CREATE,
            base.Capability.REMOVE,
            base.Capability.STREAM,
        )
        assert utils.exclude_capabilities(
            cluster,
            base.Capability.REMOVE,
            base.Capability.CREATE,
        ) == utils.combine_capabilities(base.Capability.STREAM)

    def test_exclusion_of_cluster(self):
        """The whole cluster can be excluded at once."""

        cluster = utils.combine_capabilities(
            base.Capability.CREATE,
            base.Capability.REMOVE,
            base.Capability.STREAM,
        )

        empty = utils.exclude_capabilities(
            cluster,
            utils.combine_capabilities(base.Capability.CREATE, base.Capability.STREAM),
        )
        assert empty == utils.combine_capabilities(base.Capability.REMOVE)


class TestParseFilesize:
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
    def test_valid_sizes(self, value, size):
        # type: (str, int) -> None
        """Human-readable filesize is parsed into number of bytes."""

        assert utils.parse_filesize(value) == size

    def test_empty_string(self):
        """Empty string causes an exception"""
        with pytest.raises(ValueError):
            utils.parse_filesize("")

    def test_invalid_multiplier(self):
        """Empty string causes an exception"""

        with pytest.raises(ValueError):
            utils.parse_filesize("1PB")
