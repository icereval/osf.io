from blinker import ANY
from urlparse import urlparse
from contextlib import contextmanager
from addons.osfstorage import settings as osfstorage_settings


def create_test_file(node, user, filename='test_file', create_guid=True):
    osfstorage = node.get_addon('osfstorage')
    root_node = osfstorage.get_root()
    test_file = root_node.append_file(filename)

    if create_guid:
        test_file.get_guid(create=True)

    test_file.create_version(user, {
        'object': '06d80e',
        'service': 'cloud',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': 1337,
        'contentType': 'img/png'
    }).save()
    return test_file


def urlparse_drop_netloc(url):
    url = urlparse(url)
    if url[4]:
        return url[2] + '?' + url[4]
    return url[2]


@contextmanager
def disconnected_from_listeners(signal):
    """Temporarily disconnect all listeners for a Blinker signal."""
    listeners = list(signal.receivers_for(ANY))
    for listener in listeners:
        signal.disconnect(listener)
    yield
    for listener in listeners:
        signal.connect(listener)
