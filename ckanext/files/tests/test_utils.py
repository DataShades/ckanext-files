import tempfile
from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from ckanext.files import exceptions, shared, utils
from ckanext.files.shared import Capability

from faker import Faker  # isort: skip # noqa: F401


def test_registry(faker):
    # type: (Faker) -> None
    """Brief test of registry functionality."""

    registry = utils.Registry[object]()
    key = faker.word()
    value = object()

    assert registry.get(key) is None
    with pytest.raises(KeyError):
        registry[key]

    registry.register(key, value)
    assert registry.get(key) is value
    assert registry[key] is value

    assert list(registry) == [key]

    registry.reset()
    assert registry.get(key) is None
    assert list(registry) == []


class TestEnsureSize:
    def test_empty(self):
        """Filesize identified even if it's not set initially."""

        assert utils.ensure_size(shared.make_upload(""), 0) == 0

    def test_not_empty(self):
        """Big files cause exception."""

        upload = shared.make_upload(BytesIO(b" " * 10))
        assert utils.ensure_size(upload, 15) == 10

        with pytest.raises(exceptions.LargeUploadError):
            utils.ensure_size(upload, 5)


class TestCapabilities:
    def test_reflexive_combination(self):
        """Combination of unit with itself leaves a single unit."""

        first = Capability.combine(
            Capability.CREATE,
            Capability.CREATE,
        )
        second = Capability.combine(Capability.CREATE)
        assert first is second

    def test_commutative_combination(self):
        """Order of combination does not change the result"""

        first = Capability.combine(
            Capability.CREATE,
            Capability.REMOVE,
        )
        second = Capability.combine(
            Capability.REMOVE,
            Capability.CREATE,
        )
        assert first is second

    def test_associative_combination(self):
        """Rearranging the combination sequence does not change the result."""

        first = Capability.combine(
            Capability.combine(Capability.CREATE, Capability.REMOVE),
            Capability.MULTIPART_UPLOAD,
        )
        second = Capability.combine(
            Capability.combine(
                Capability.CREATE,
                Capability.MULTIPART_UPLOAD,
            ),
            Capability.REMOVE,
        )
        third = Capability.combine(
            Capability.combine(
                Capability.REMOVE,
                Capability.MULTIPART_UPLOAD,
            ),
            Capability.CREATE,
        )

        assert first == second == third

    def test_clusters(self):
        """Clusters can be combined with the same result as individual units."""

        first = Capability.combine(
            Capability.CREATE,
            Capability.REMOVE,
        )
        second = Capability.combine(
            Capability.MULTIPART_UPLOAD,
            Capability.STREAM,
        )

        clusters = Capability.combine(first, second)
        units = Capability.combine(
            Capability.CREATE,
            Capability.REMOVE,
            Capability.MULTIPART_UPLOAD,
            Capability.STREAM,
        )
        assert clusters is units

    def test_not_intersecting_exclusion(self):
        """Nothing changes when non-existing unit excluded."""
        cluster = Capability.combine(
            Capability.CREATE,
            Capability.REMOVE,
        )

        assert Capability.exclude(cluster, Capability.MULTIPART_UPLOAD) is cluster

    def test_exclusion_of_single_unit(self):
        """Single unit exclusion leaves all other units inside cluster."""

        cluster = Capability.combine(
            Capability.CREATE,
            Capability.REMOVE,
        )

        assert Capability.exclude(
            cluster,
            Capability.CREATE,
        ) is Capability.combine(Capability.REMOVE)

    def test_multi_unit_exclusion(self):
        """Multiple units can be excluded at once."""

        cluster = Capability.combine(
            Capability.CREATE,
            Capability.REMOVE,
            Capability.STREAM,
        )
        assert Capability.exclude(
            cluster,
            Capability.REMOVE,
            Capability.CREATE,
        ) == Capability.combine(Capability.STREAM)

    def test_exclusion_of_cluster(self):
        """The whole cluster can be excluded at once."""

        cluster = Capability.combine(
            Capability.CREATE,
            Capability.REMOVE,
            Capability.STREAM,
        )

        empty = Capability.exclude(
            cluster,
            Capability.combine(Capability.CREATE, Capability.STREAM),
        )
        assert empty == Capability.combine(Capability.REMOVE)

    def test_can_single_capability(self):
        """Individual capabilites are identified in cluster."""
        cluster = Capability.combine(Capability.CREATE, Capability.REMOVE)
        assert cluster.can(Capability.CREATE)
        assert cluster.can(Capability.REMOVE)
        assert not cluster.can(Capability.STREAM)

    def test_can_cluster_capability(self):
        """Cluster capabilites are identified in cluster."""
        cluster = Capability.combine(
            Capability.CREATE,
            Capability.REMOVE,
            Capability.STREAM,
        )

        assert cluster.can(Capability.combine(Capability.CREATE, Capability.REMOVE))
        assert not cluster.can(Capability.combine(Capability.CREATE, Capability.MOVE))


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


class TestMakeUpload:
    def test_file_storage(self):
        """FileStorage instances returned as-is."""
        upload = utils.make_upload(FileStorage())
        assert isinstance(upload, shared.Upload)

    def test_tempfile(self):
        """Temp files converted into Upload."""
        fd = tempfile.SpooledTemporaryFile()
        fd.write(b"hello")
        fd.seek(0)
        upload = utils.make_upload(fd)
        assert isinstance(upload, utils.Upload)
        assert upload.stream.read() == b"hello"

    def test_str(self, faker):
        # type: (Faker) -> None
        """Strings converted into Upload."""
        string = faker.pystr()
        upload = utils.make_upload(string)

        assert isinstance(upload, shared.Upload)
        assert upload.stream.read() == string.encode()

    def test_bytes(self, faker):
        # type: (Faker) -> None
        """Bytes converted into Upload."""
        binary = faker.binary(100)
        upload = utils.make_upload(binary)

        assert isinstance(upload, shared.Upload)
        assert upload.stream.read() == binary

    def test_wrong_type(self):
        """Any unexpected value causes an exception."""
        with pytest.raises(TypeError):
            utils.make_upload(123)
