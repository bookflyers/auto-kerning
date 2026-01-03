"""
From https://github.com/adobe-type-tools/kern-dump
"""
__ALL__ = ['OTFKerningReader']

import logging

from fontTools import ttLib

class LeftClass:
    def __init__(self):
        self.glyphs = []
        self.class1Record = 0

class RightClass:
    def __init__(self):
        self.glyphs = []
        self.class2Record = 0


def collect_unique_kern_lookup_indexes(featureRecord):
    unique_kern_lookups = []
    for featRecItem in featureRecord:
        # GPOS feature tags (e.g. kern, mark, mkmk, size) of each ScriptRecord
        if featRecItem.FeatureTag == 'kern':
            feature = featRecItem.Feature

            for featLookupItem in feature.LookupListIndex:
                if featLookupItem not in unique_kern_lookups:
                    unique_kern_lookups.append(featLookupItem)

    return unique_kern_lookups


class OTFKernReader(object):

    def __init__(self, font: str | ttLib.TTFont):
        self.font = ttLib.TTFont(font) if isinstance(font, str) else font
        self.kerningPairs = {}
        self.singlePairs = {}
        self.classPairs = {}
        self.pairPosList = []
        self.allLeftClasses = {}
        self.allRightClasses = {}
        self.output = []

        assert 'GPOS' in self.font, 'Font requires a Glyph Positioning table to read kerning information'
        self.analyzeFont()
        self.findKerningLookups()
        self.getPairPos()
        self.getSinglePairs()
        self.getClassPairs()
        self.output = self.make_output()

    def make_output(self):
        pair_value_list = []
        for pair, value in self.kerningPairs.items():
            pair_value_list.append(f'{pair[0]} {pair[1]} {value}')
        pair_value_list.sort()
        return pair_value_list

    def analyzeFont(self):
        self.gposTable = self.font['GPOS'].table
        self.scriptList = self.gposTable.ScriptList
        self.featureList = self.gposTable.FeatureList
        self.featureCount = self.featureList.FeatureCount
        self.featureRecord = self.featureList.FeatureRecord

        self.unique_kern_lookups = collect_unique_kern_lookup_indexes(self.featureRecord)

    def findKerningLookups(self):
        """
        Lookup types:
        1   Single adjustment           Adjust position of a single glyph
        2   Pair adjustment             Adjust position of a pair of glyphs
        3   Cursive attachment          Attach cursive glyphs
        4   MarkToBase attachment       Attach a combining mark to a base glyph
        5   MarkToLigature attachment   Attach a combining mark to a ligature
        6   MarkToMark attachment       Attach a combining mark to another mark
        7   Context positioning         Position one or more glyphs in context
        8   Chained Context positioning Position one or more glyphs in chained context
        9   Extension positioning       Extension mechanism for other positionings
        10+ Reserved for future use
        """

        assert len(self.unique_kern_lookups), 'Font has no kerning lookups'

        self.lookup_list = self.gposTable.LookupList
        self.lookups = []
        for kern_lookup_index in sorted(self.unique_kern_lookups):
            lookup = self.lookup_list.Lookup[kern_lookup_index]

            # Confirm this is a GPOS LookupType 2; or
            # using an extension table (GPOS LookupType 9):

            if lookup.LookupType not in [2, 9]:
                logging.info(
                    f'Info: GPOS LookupType {lookup.LookupType} found. '
                    'This type is neither a pair adjustment positioning '
                    'lookup (GPOS LookupType 2), nor using an extension table '
                    '(GPOS LookupType 9), which are the only ones supported.')
                continue
            self.lookups.append(lookup)

    def getPairPos(self):
        for lookup in self.lookups:
            for subtableItem in lookup.SubTable:

                if subtableItem.LookupType == 9:  # extension table
                    if subtableItem.ExtensionLookupType == 8:  # contextual
                        logging.info('Contextual Kerning not supported.')
                        continue
                    elif subtableItem.ExtensionLookupType == 2:
                        subtableItem = subtableItem.ExtSubTable

                if subtableItem.Format not in [1, 2]:
                    logging.warning(f'Coverage format {subtableItem.Coverage.Format} is not yet supported.')

                if subtableItem.ValueFormat1 not in [0, 4, 5]:
                    logging.warning(f'ValueFormat1 format {subtableItem.ValueFormat1} is not yet supported.')

                if subtableItem.ValueFormat2 not in [0]:
                    logging.warning(f'ValueFormat2 format {subtableItem.ValueFormat2} is not yet supported.')

                self.pairPosList.append(subtableItem)

                # Each glyph in this list will have a corresponding PairSet
                # which will contain all the second glyphs and the kerning
                # value in the form of PairValueRecord(s)
                # self.firstGlyphsList.extend(subtableItem.Coverage.glyphs)

    def getSinglePairs(self):
        for pairPos in self.pairPosList:
            if pairPos.Format == 1:
                # single pair adjustment

                firstGlyphsList = pairPos.Coverage.glyphs

                # This iteration is done by index so we have a way
                # to reference the firstGlyphsList:
                for ps_index, pair_set in enumerate(pairPos.PairSet):
                    for pairValueRecordItem in pair_set.PairValueRecord:
                        firstGlyph = firstGlyphsList[ps_index]
                        secondGlyph = pairValueRecordItem.SecondGlyph
                        pair = firstGlyph, secondGlyph
                        valueFormat = pairPos.ValueFormat1

                        if valueFormat == 5:  # RTL kerning
                            x_placement = pairValueRecordItem.Value1.XPlacement
                            x_advance = pairValueRecordItem.Value1.XAdvance
                            kernValue = f'<{x_placement} 0 {x_advance} 0>'
                        elif valueFormat == 0:  # RTL pair with value <0 0 0 0>
                            kernValue = "<0 0 0 0>"
                        elif valueFormat == 4:  # LTR kerning
                            kernValue = pairValueRecordItem.Value1.XAdvance
                        else:
                            logging.info(f'ValueFormat1 = {valueFormat}')
                            continue  # skip the rest

                        self.kerningPairs[pair] = kernValue
                        self.singlePairs[pair] = kernValue

    def getClassPairs(self):
        for index, pairPos in enumerate(self.pairPosList):
            if pairPos.Format == 2:

                leftClasses = {}
                rightClasses = {}

                # Find left class with the Class1Record index="0".
                # This first class is mixed into the "Coverage" table
                # (e.g. all left glyphs) and has no class="X" property
                # that is why we have to find the glyphs in that way.

                lg0 = LeftClass()

                # list of all glyphs kerned to the left of a pair:
                allLeftGlyphs = pairPos.Coverage.glyphs

                singleGlyphs = []
                classGlyphs = []

                for gName, classID in pairPos.ClassDef1.classDefs.items():
                    if classID == 0:
                        singleGlyphs.append(gName)
                    else:
                        classGlyphs.append(gName)
                # coverage glyphs minus glyphs in real class (without class 0)
                lg0.glyphs = list(set(allLeftGlyphs) - set(classGlyphs))

                lg0.glyphs.sort()
                leftClasses[lg0.class1Record] = lg0
                className = f"class_{index}_{lg0.class1Record}"
                self.allLeftClasses[className] = lg0.glyphs

                # Find all the remaining left classes:
                for leftGlyph in pairPos.ClassDef1.classDefs:
                    class1Record = pairPos.ClassDef1.classDefs[leftGlyph]

                    if class1Record != 0:  # this was the crucial line.
                        lg = LeftClass()
                        className = f"class_{index}_{class1Record}"
                        lg.class1Record = class1Record
                        leftClasses.setdefault(
                            class1Record, lg).glyphs.append(leftGlyph)
                        self.allLeftClasses.setdefault(className, lg.glyphs)

                # Same for the right classes:
                for rightGlyph in pairPos.ClassDef2.classDefs:
                    class2Record = pairPos.ClassDef2.classDefs[rightGlyph]
                    rg = RightClass()
                    rg.class2Record = class2Record
                    className = f"class_{index}_{class2Record}"
                    rightClasses.setdefault(
                        class2Record, rg).glyphs.append(rightGlyph)
                    self.allRightClasses.setdefault(className, rg.glyphs)

                for record_l in leftClasses:
                    for record_r in rightClasses:
                        if pairPos.Class1Record[record_l].Class2Record[record_r]:
                            valueFormat = pairPos.ValueFormat1

                            if valueFormat in [4, 5]:
                                kernValue = pairPos.Class1Record[record_l].Class2Record[record_r].Value1.XAdvance
                            elif valueFormat == 0:
                                # valueFormat zero is caused by a value of <0 0 0 0> on a class-class pair; skip these
                                continue
                            else:
                                logging.info(f'\tValueFormat1 = {valueFormat}')
                                continue  # skip the rest

                            if kernValue != 0:
                                leftClassName = f'class_{index}_{leftClasses[record_l].class1Record}'
                                rightClassName = f'class_{index}_{rightClasses[record_r].class2Record}'
                                self.classPairs[(leftClassName, rightClassName)] = kernValue

                                for g_left in leftClasses[record_l].glyphs:
                                    for g_right in rightClasses[record_r].glyphs:
                                        if (g_left, g_right) in self.kerningPairs:
                                            # if the kerning pair has already been assigned in pair-to-pair kerning
                                            continue
                                        else:
                                            if valueFormat == 5:  # RTL kerning
                                                x_placement = pairPos.Class1Record[record_l].Class2Record[
                                                    record_r].Value1.XPlacement
                                                x_advance = pairPos.Class1Record[record_l].Class2Record[
                                                    record_r].Value1.XAdvance
                                                kernValue = f"<{x_placement} 0 {x_advance} 0>"

                                            self.kerningPairs[(g_left, g_right)] = kernValue

                        else:
                            logging.error('ERROR')
