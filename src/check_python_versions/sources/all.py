from .appveyor import Appveyor
from .github import GitHubActions
from .manylinux import Manylinux
from .pyproject import PyProject, PyProjectPythonRequires
from .setup_py import SetupClassifiers, SetupPythonRequires
from .tox import Tox
from .travis import Travis


# The order here is only mildly important: it's used for presentation.
# Note that SetupPythonRequires.title assumes it's included right after
# SetupClassifiers!
ALL_SOURCES = [
    SetupClassifiers,
    SetupPythonRequires,
    PyProject,
    PyProjectPythonRequires,
    Tox,
    Travis,
    GitHubActions,
    Appveyor,
    Manylinux,
]
