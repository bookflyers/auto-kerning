import os
from typing import Optional

import bpy
from fontTools.ttLib import TTFont

from .reader import OTFKernReader

BLENDER_KERN_UNITS_PER_CHARACTER = 40
SUPPORTED_FILE_EXTS = {'.otf', '.ttf'}


class FontKernInfo:

    def __init__(self, font_path: str):
        self.font = TTFont(font_path)
        self.kerningPairs = OTFKernReader(self.font).kerningPairs
        self.cmap = self.font.getBestCmap()
        self.gs = self.font.getGlyphSet()

    def cmap_lookup(self, c: str):
        return self.cmap.get(ord(c))

    def calc_kerning(self, c1: str, c2: str):
        c = self.cmap_lookup(c1)
        k = self.kerningPairs.get((c, self.cmap_lookup(c2)))
        if k is None or c not in self.gs:
            return None

        return k * BLENDER_KERN_UNITS_PER_CHARACTER / self.gs[c].width

    @classmethod
    def from_path(cls, path: str) -> Optional['FontKernInfo']:
        if path is not None \
                and os.path.exists(path) \
                and os.path.splitext(path)[-1].lower() in SUPPORTED_FILE_EXTS:
            return cls(path)
        return None


def apply_kerning(
        text_curve: bpy.types.TextCurve,
        font_path: str,
        font_bold_path: Optional[str] = None,
        font_italic_path: Optional[str] = None,
        font_bold_italic_path: Optional[str] = None,
):
    """
    :param text_curve: bpy.types.TextCurve
    :param font_path: path to font file
    :param font_bold_path:
    :param font_italic_path:
    :param font_bold_italic_path:
    """
    info_regular = FontKernInfo.from_path(font_path)
    info_bold = FontKernInfo.from_path(font_bold_path)
    info_italic = FontKernInfo.from_path(font_italic_path)
    info_bold_italic = FontKernInfo.from_path(font_bold_italic_path)

    for i in range(len(text_curve.body) - 1):
        if text_curve.body_format[i].use_bold and text_curve.body_format[i].use_italic:
            info = info_bold_italic
        elif text_curve.body_format[i].use_bold:
            info = info_bold
        elif text_curve.body_format[i].use_italic:
            info = info_italic
        else:
            info = info_regular

        if not info:
            continue

        c1, c2 = text_curve.body[i], text_curve.body[i + 1]
        k = info.calc_kerning(c1, c2)
        if k:
            text_curve.body_format[i].kerning = k


class TextObjectAutoKerning(bpy.types.Operator):
    """Apply font-defined kerning to text object"""
    bl_idname = 'object.auto_kerning'
    bl_label = 'Apply Kerning'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        text_curve = context.active_object.data
        apply_kerning(
            text_curve,
            text_curve.font.filepath,
            text_curve.font_bold.filepath,
            text_curve.font_italic.filepath,
            text_curve.font_bold_italic.filepath,
        )

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(TextObjectAutoKerning.bl_idname)


def register():
    bpy.utils.register_class(TextObjectAutoKerning)
    bpy.types.DATA_PT_paragraph_spacing.append(menu_func)


def unregister():
    bpy.utils.unregister_class(TextObjectAutoKerning)
