from .appveyor import Appveyor
from .github import GitHubActions
from .manylinux import Manylinux
from .poetry_pyproject import PoetryPyProject, PoetryPyProjectPythonRequires
from .setup_py import SetupClassifiers, SetupPythonRequires
from .tox import Tox
from .travis import Travis


# The order here is only mildly important: it's used for presentation.
# Note that SetupPythonRequires.title assumes it's included right after
# SetupClassifiers!
ALL_SOURCES = [
    SetupClassifiers,
    SetupPythonRequires,
    PoetryPyProject,
    PoetryPyProjectPythonRequires,
    Tox,
    Travis,
    GitHubActions,
    Appveyor,
    Manylinux,
]
