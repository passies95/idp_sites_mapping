# -*- coding: utf-8 -*-

"""
/***************************************************************************
 IDPSiteMapping
                                 A QGIS plugin
 Plugin to Help with mapping of Internally Displaced Persons Structures
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-07-24
        copyright            : (C) 2024 by pascal ogola
        email                : pascaladongo@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'pascal ogola'
__date__ = '2024-07-24'
__copyright__ = '(C) 2024 by pascal ogola'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider
from .configure import configureTOOLS
from .BilateralFiltering import BilateralFiltering
from .computed_ranges import RasterClassificationUsingComputedRanges
from .compute_threshold_Otsu import ThresholdUsingOtsuAlgorithm
from .Segment_with_Thresholding import SegmentationUsingThresholding
from .BuiltUP_Areas_Extraction import TentExtraction
from .BuiltUP_Areas_Extraction_for_Known_Areas import TentExtractionForKnownAreas


class IDPSiteMappingProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(configureTOOLS())
        # processing tools
        self.addAlgorithm(BilateralFiltering())
        self.addAlgorithm(RasterClassificationUsingComputedRanges())
        self.addAlgorithm(ThresholdUsingOtsuAlgorithm())
        self.addAlgorithm(SegmentationUsingThresholding())
        # Segmentation Tools
        self.addAlgorithm(TentExtraction())
        self.addAlgorithm(TentExtractionForKnownAreas())
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        return 'IDP_Sites_Mapping'

    def name(self):
        return self.tr('IDP Sites Mapping')

    def icon(self):
        return QgsProcessingProvider.icon(self)

    def longName(self):
        return self.name()
