import os.path

__version__ = '0.2.0'
__resource_path__ = os.path.join(os.path.split(__file__)[0], "resources")

from .psg import PSG
del psg
