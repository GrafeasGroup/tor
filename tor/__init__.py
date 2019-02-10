import glob
import os

__version__ = "3.7.0"

# list all modules so we can `from tor import *`
__all__ = [
    os.path.basename(f if not f.endswith(".py") else f[:-3])
    for f in glob.glob(os.path.join(os.path.dirname(__file__), "*"))
    if (os.path.isfile(f) and f.endswith(".py") and not f.endswith("__init__.py"))
    or (os.path.isdir(f) and os.path.exists(os.path.join(f, "__init__.py")))
]
