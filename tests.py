import check_python_versions as cpv


def test_get_versions_from_classifiers():
    assert cpv.get_versions_from_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ]) == ['2.7', '3.6', '3.7', 'PyPy']


def test_get_versions_from_classifiers_major_only():
    assert cpv.get_versions_from_classifiers([
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ]) == ['2', '3']


def test_get_versions_from_classifiers_with_only_suffix():
    assert cpv.get_versions_from_classifiers([
        'Programming Language :: Python :: 2 :: Only',
    ]) == ['2']


def test_get_versions_from_classifiers_with_trailing_whitespace():
    # I was surprised too that this is allowed!
    assert cpv.get_versions_from_classifiers([
        'Programming Language :: Python :: 3.6 ',
    ]) == ['3.6']


def test_parse_python_requires_empty():
    assert cpv.parse_python_requires('') == []


def test_parse_python_requires_greater_than(monkeypatch):
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 8)
    assert cpv.parse_python_requires('>= 3.6') == ['3.6', '3.7', '3.8']


def test_parse_python_requires_greater_than_with_exceptions(monkeypatch):
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 3)
    assert cpv.parse_python_requires('>= 2.7, != 3.0.*, != 3.1.*') == [
        '2.7', '3.2', '3.3'
    ]
