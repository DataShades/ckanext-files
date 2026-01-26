import pytest
from faker import Faker
from responses import RequestsMock

from ckanext.files import shared


@pytest.mark.usefixtures("with_plugins")
class TestStorage:
    def test_url_is_kept_in_storage_data(self, faker: Faker):
        """Test that URL is kept in storage data.

        Given a link storage, when uploading a file with a URL,
        then the URL is kept in the storage data.
        """
        storage = shared.make_storage("test", {"type": "files:link"})

        location = shared.Location(faker.file_name())
        url = faker.url()

        with RequestsMock() as rsps:
            rsps.add("HEAD", url)
            data = storage.upload(location, shared.make_upload(url.encode()))

        assert data.location == location
        assert data.storage_data["url"] == url

    def test_permanent_link_returns_url(self, faker: Faker):
        """Test that permanent link returns the URL.

        Given a link storage, when getting the permanent link of a file,
        then the URL is returned.
        """
        storage = shared.make_storage("test", {"type": "files:link"})

        url = faker.url()
        data = shared.FileData(
            location=shared.Location(faker.file_name()),
            storage_data={"url": url},
        )

        permanent_link = storage.permanent_link(data)

        assert permanent_link == url

    def test_protocols_setting(self, faker: Faker):
        """Test that protocols setting is respected.

        Given a link storage with custom protocols, when uploading a file with a URL,
        then the URL is accepted only if it uses one of the allowed protocols.
        """
        storage = shared.make_storage("test", {"type": "files:link", "protocols": ["https"]})

        location = shared.Location("file.txt")

        url = faker.url(["http"])
        with RequestsMock() as rsps:
            rsps.add("HEAD", url)
            with pytest.raises(shared.exc.ContentError):
                storage.upload(location, shared.make_upload(url.encode()))

        url = faker.url(["https"])
        with RequestsMock() as rsps:
            rsps.add("HEAD", url)
            data = storage.upload(location, shared.make_upload(url.encode()))

        assert data.location == location
        assert data.storage_data["url"] == url

    def test_domains_setting(self, faker: Faker):
        """Test that domains setting is respected.

        Given a link storage with custom domains, when uploading a file with a URL,
        then the URL is accepted only if it uses one of the allowed domains.
        """
        allowed_domain = "example.com"
        storage = shared.make_storage("test", {"type": "files:link", "domains": [allowed_domain]})

        location = shared.Location("file.txt")

        url = f"https://notallowed.com/{faker.file_name()}"
        with RequestsMock() as rsps:
            rsps.add("HEAD", url)
            with pytest.raises(shared.exc.ContentError):
                storage.upload(location, shared.make_upload(url.encode()))

        url = f"https://{allowed_domain}/{faker.file_name()}"
        with RequestsMock() as rsps:
            rsps.add("HEAD", url)
            data = storage.upload(location, shared.make_upload(url.encode()))

        assert data.location == location
        assert data.storage_data["url"] == url
