from typing import Callable, Optional

from ..utils import FileLines, FileOrFilename
from ..versions import SortedVersionList


ExtractorFn = Callable[[FileOrFilename], Optional[SortedVersionList]]
UpdaterFn = Callable[[FileOrFilename, SortedVersionList], Optional[FileLines]]


class Source:

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        filename: str,
        extract: ExtractorFn,
        update: Optional[UpdaterFn] = None,
    ) -> None:
        self.title = title or filename
        self.filename = filename
        self.extract = extract
        self.update = update

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
            pathname=pathname,
            versions=versions,
        )
        return source


class SourceFile(Source):

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        filename: str,
        extract: ExtractorFn,
        update: Optional[UpdaterFn] = None,
        pathname: str,
        versions: SortedVersionList,
    ) -> None:
        super().__init__(
            title=title, filename=filename, extract=extract, update=update)
        self.pathname = pathname
        self.versions = versions
