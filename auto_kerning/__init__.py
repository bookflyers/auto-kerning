import bpy
from fontTools.ttLib import TTFont

from .reader import OTFKernReader

BLENDER_KERN_UNITS_PER_CHARACTER = 40


def apply_kerning(text_curve: bpy.types.TextCurve, font_path):
    """
    :param text_curve: bpy.types.TextCurve
    :param font_path: path to font file
    """
    font = TTFont(font_path)
    okr = OTFKernReader(font)
    cmap = font.getBestCmap()
    s = font.getGlyphSet()
    upm = font['head'].unitsPerEm

    pairs = [(text_curve.body[i], text_curve.body[i + 1]) for i in range(len(text_curve.body) - 1)]
    for i, p in enumerate(pairs):
        pc = (cmap.get(ord(p[0])), cmap.get(ord(p[1])))
        k = okr.kerningPairs.get(pc)
        c = cmap.get(ord(p[0]))
        c_w = s.get(c).width / upm if c in s else 1  # characters like \n do not have a glyph
        if k:
            text_curve.body_format[i].kerning = k * BLENDER_KERN_UNITS_PER_CHARACTER / (upm * c_w)


class TextObjectAutoKerning(bpy.types.Operator):
    """Apply font-defined kerning to text object"""
    bl_idname = 'object.auto_kerning'
    bl_label = 'Apply Kerning'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        text_curve = context.active_object.data
        apply_kerning(text_curve, text_curve.font.filepath)

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(TextObjectAutoKerning.bl_idname)


def register():
    bpy.utils.register_class(TextObjectAutoKerning)
    bpy.types.DATA_PT_paragraph_spacing.append(menu_func)


def unregister():
    bpy.utils.unregister_class(TextObjectAutoKerning)
