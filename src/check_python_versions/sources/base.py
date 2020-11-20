import typing
from typing import Callable, Optional

from ..utils import FileLines, FileOrFilename
from ..versions import SortedVersionList


ExtractorFn = Callable[[FileOrFilename], Optional[SortedVersionList]]
UpdaterFn = Callable[[FileOrFilename, SortedVersionList], Optional[FileLines]]


class Source(typing.NamedTuple):
    title: str
    filename: str
    extract: ExtractorFn
    update: Optional[UpdaterFn] = None
