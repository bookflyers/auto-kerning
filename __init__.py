_needs_reload = 'bpy' in locals()

import bpy
from . import auto_kerning

if _needs_reload:
    import importlib
    auto_kerning = importlib.reload(auto_kerning)


def register():
    auto_kerning.register()


def unregister():
    auto_kerning.unregister()


if __name__ == '__main__':
    register()