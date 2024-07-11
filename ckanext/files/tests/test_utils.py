import hashlib
import tempfile
from io import BytesIO
from typing import Any

import pytest
from faker import Faker
from werkzeug.datastructures import FileStorage

from ckanext.files import shared, utils
from ckanext.files.shared import Capability


def test_registry(faker: Faker):
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


class TestHasingReader:
    def test_empty_hash(self):
        """Empty reader produces the hash of empty string."""
        reader = shared.HashingReader(BytesIO())
        reader.exhaust()

        assert reader.get_hash() == hashlib.md5().hexdigest()

    def test_hash(self, faker: Faker):
        """Reader's hash is based on the stream content."""
        content = faker.binary(100)
        expected = hashlib.md5(content).hexdigest()

        reader = shared.HashingReader(BytesIO(content))

        output = b""
        for chunk in reader:
            output += chunk

        assert output == content
        assert reader.get_hash() == expected


class TestCapabilities:
    def test_not_intersecting_exclusion(self):
        """Nothing changes when non-existing unit excluded."""
        cluster = Capability.CREATE | Capability.REMOVE

        assert Capability.exclude(cluster, Capability.MULTIPART) is cluster

    def test_exclusion_of_single_unit(self):
        """Single unit exclusion leaves all other units inside cluster."""
        cluster = Capability.CREATE | Capability.REMOVE

        assert Capability.exclude(cluster, Capability.CREATE) is Capability.REMOVE

    def test_multi_unit_exclusion(self):
        """Multiple units can be excluded at once."""
        cluster = Capability.CREATE | Capability.REMOVE | Capability.STREAM
        assert (
            Capability.exclude(cluster, Capability.REMOVE, Capability.CREATE)
            == Capability.STREAM
        )

    def test_exclusion_of_cluster(self):
        """The whole cluster can be excluded at once."""
        cluster = Capability.CREATE | Capability.REMOVE | Capability.STREAM

        empty = Capability.exclude(cluster, Capability.CREATE | Capability.STREAM)
        assert empty == Capability.REMOVE

    def test_can_single_capability(self):
        """Individual capabilites are identified in cluster."""
        cluster = Capability.CREATE | Capability.REMOVE
        assert cluster.can(Capability.CREATE)
        assert cluster.can(Capability.REMOVE)
        assert not cluster.can(Capability.STREAM)

    def test_can_cluster_capability(self):
        """Cluster capabilites are identified in cluster."""
        cluster = Capability.CREATE | Capability.REMOVE | Capability.STREAM

        assert cluster.can(Capability.CREATE | Capability.REMOVE)
        assert not cluster.can(Capability.CREATE | Capability.MOVE)


class TestParseFilesize:
    @pytest.mark.parametrize(
        ("value", "size"),
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
    def test_valid_sizes(self, value: str, size: int):
        """Human-readable filesize is parsed into number of bytes."""
        assert utils.parse_filesize(value) == size

    def test_empty_string(self):
        """Empty string causes an exception."""
        with pytest.raises(ValueError):  # noqa: PT011
            utils.parse_filesize("")

    def test_invalid_multiplier(self):
        """Empty string causes an exception."""
        with pytest.raises(ValueError):  # noqa: PT011
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
        assert isinstance(upload, shared.Upload)
        assert upload.stream.read() == b"hello"

    def test_str(self, faker: Faker):
        """Strings converted into Upload."""
        string: Any = faker.pystr()
        with pytest.raises(TypeError):
            utils.make_upload(string)

    def test_bytes(self, faker: Faker):
        """Bytes converted into Upload."""
        binary = faker.binary(100)
        upload = utils.make_upload(binary)

        assert isinstance(upload, shared.Upload)
        assert upload.stream.read() == binary

    def test_wrong_type(self):
        """Any unexpected value causes an exception."""
        with pytest.raises(TypeError):
            utils.make_upload(123)  # type: ignore
