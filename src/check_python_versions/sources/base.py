from typing import Callable, Optional

from ..utils import FileLines, FileOrFilename
from ..versions import SortedVersionList


ExtractorFn = Callable[[FileOrFilename], Optional[SortedVersionList]]
UpdaterFn = Callable[[FileOrFilename, SortedVersionList], Optional[FileLines]]


class Source:
    """Source for information about supported Pythons.

    Examples of sources are: setup.py, CI configuration files.

    A source has a ``title``, a typical ``filename`` (which can be a
    glob pattern).

    A source knows how to extract the list of supported Python versions
    from a file, and it can know how to update the list of versions.

    A source knows whether it's possible/typical to include PyPy support
    for packages that want to support PyPy.
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        filename: str,
        extract: ExtractorFn,
        update: Optional[UpdaterFn] = None,
        check_pypy_consistency: bool,
        has_upper_bound: bool,
    ) -> None:
        self.title = title or filename
        self.filename = filename
        self.extract = extract
        self.update = update
        self.check_pypy_consistency = check_pypy_consistency
        self.has_upper_bound = has_upper_bound

    def for_file(
        self,
        pathname: str,
        versions: SortedVersionList,
        relpath: str,
    ) -> 'SourceFile':
        title = relpath if self.title == self.filename else self.title
        source = SourceFile(
            title=title,
            filename=self.filename,
            extract=self.extract,
            update=self.update,
            check_pypy_consistency=self.check_pypy_consistency,
            has_upper_bound=self.has_upper_bound,
            pathname=pathname,
            versions=versions,
        )
        return source


class SourceFile(Source):
    """A concrete source file with  information about supported Pythons.

    Some sources (GitHub Actions) can have multiple files matching a
    glob pattern.  Each of those gets its own ``SourceFile`` instance.
    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        filename: str,
        extract: ExtractorFn,
        update: Optional[UpdaterFn] = None,
        check_pypy_consistency: bool,
        has_upper_bound: bool,
        pathname: str,
        versions: SortedVersionList,
    ) -> None:
        super().__init__(
            title=title, filename=filename, extract=extract, update=update,
            check_pypy_consistency=check_pypy_consistency,
            has_upper_bound=has_upper_bound)
        self.pathname = pathname
        self.versions = versions
