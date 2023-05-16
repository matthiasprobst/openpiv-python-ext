"""version information for openpiv"""


def read_from_setup_file():
    import re
    with open('setup.py', 'r') as f:
        contents = f.read()
        version_match = re.search(r"version=['\"]([^'\"]*)['\"]", contents)
        if version_match:
            return version_match.group(1)
        else:
            raise ValueError("Version not found in setup.py")


try:  # only works with python>=3.8
    from importlib.metadata import version as _version

    __version__ = _version('openpiv')
except ImportError as e:
    __version__ = read_from_setup_file()
