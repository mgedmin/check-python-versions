from .appveyor import Appveyor
from .manylinux import Manylinux
from .setup_py import SetupClassifiers, SetupPythonRequires
from .tox import Tox
from .travis import Travis
from .github import GitHubActions


# The order here is only mildly important: it's used for presentation.
# Note that SetupPythonRequires.title assumes it's included right after
# SetupClassifiers!
ALL_SOURCES = [
    SetupClassifiers,
    SetupPythonRequires,
    Tox,
    Travis,
    GitHubActions,
    Appveyor,
    Manylinux,
]
