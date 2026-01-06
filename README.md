# Auto Kerning for Blender

## About
Automatic kerning for text objects in Blender.

With one click, this add-on automatically kerns the selected text object's contents,
using the kerning information from the object's font files.

![Animation of kerning applied to the words "Kern Your Text"](./images/auto-kerning-demo.webp)

## Use
When a text object is selected, the "Apply Kerning" button appears under Paragraph > Spacing
in the Data tab of the Properties Editor.

![Screenshot of the "Apply Kerning" button in the Blender UI](./images/auto-kerning-screenshot.png)

## Limitations
- Supports left-to-right fonts in TTF or OTF format
- If the text value is changed, auto-kerning needs to be re-applied
- Does not kern text created with the _String to Curves_ node
- Has no effect on the built-in Blender font

## Acknowledgments
This add-on uses:
- https://github.com/adobe-type-tools/kern-dump
- https://github.com/fonttools/fonttools