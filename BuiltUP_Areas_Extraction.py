"""
Name : Tent Extraction
Group : model
"""

import os
from qgis.core import QgsProcessing, QgsRasterLayer, QgsProcessingUtils
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis import processing


class TentExtraction(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer('satellite_image', 'Satellite Image', defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('sample_bare_areas', 'Sample Bare Areas', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Structures', 'Structures', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        steps = 26
        feedback = QgsProcessingMultiStepFeedback(steps, model_feedback)
        results = {}
        outputs = {}

        # split raster bands
        # Split the Raster Image into Single Bands
        # Generate temporary filenames to save split bands
        # blueBand = QgsProcessingUtils.generateTempFilename('blue.tif')
        # greenBand = QgsProcessingUtils.generateTempFilename('green.tif')
        # redBand = QgsProcessingUtils.generateTempFilename('red.tif')

        alg_params = {
            'GRASS_RASTER_FORMAT_META': '',
            'GRASS_RASTER_FORMAT_OPT': '',
            'GRASS_REGION_CELLSIZE_PARAMETER': 0,
            'GRASS_REGION_PARAMETER': None,
            'input': parameters['satellite_image'],
            # Since these are Grass Algorithmn using Temporary Output produces wrong resuts
            # Save to temporary filename instead
            'blue': QgsProcessingUtils.generateTempFilename('blue.tif'),
            'green': QgsProcessingUtils.generateTempFilename('green.tif'),
            'red': QgsProcessingUtils.generateTempFilename('red.tif')
        }

        feedback.pushInfo("Running algorithm: Split Raster Bands")

        outputs['SplitRasterBands'] = processing.run('grass7:r.rgb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}
        
        # Compute F1 Layer
        #######################################################################################################################################
        # Write the Red, Green and Blue Bands to a new layer
        blueBand = QgsRasterLayer(outputs['SplitRasterBands']['blue'], 'blue')
        greenBand= QgsRasterLayer(outputs['SplitRasterBands']['green'], 'green')
        redBand = QgsRasterLayer(outputs['SplitRasterBands']['red'], 'red')

        print('name:', blueBand.bandName(1))
        print('name:', greenBand.bandName(1))
        print('name:', redBand.bandName(1))

        # Check if layer is valid
        if not blueBand.isValid() or not greenBand.isValid() or not redBand.isValid():
            print("One or more raster layers are not valid.")
            exit()
        
        # compute g

        alg_params = {
            'CELLSIZE': 0,
            'CRS': None,
            'EXPRESSION': '"green@1" /  ( "red@1" + "green@1" + "blue@1" ) ',
            'EXTENT': None,
            'LAYERS': [outputs['SplitRasterBands']['red'],
                       outputs['SplitRasterBands']['green'],
                       outputs['SplitRasterBands']['blue']],
            'OUTPUT': QgsProcessingUtils.generateTempFilename('g.tif')
        }

        feedback.pushInfo("Running algorithm: compute G edge")

        outputs['ComputeG'] = processing.run('qgis:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        # feedback.pushInfo(f"Raster calculation result saved to: {outputs['ComputeG']['OUTPUT']}")
        
        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}
        
        # compute r
        alg_params = {
            'CELLSIZE': 0,
            'CRS': None,
            'EXPRESSION': '"red@1" /  ( "red@1" + "green@1" + "blue@1" ) ',
            'EXTENT': None,
            'LAYERS': [outputs['SplitRasterBands']['red'],
                       outputs['SplitRasterBands']['green'],
                       outputs['SplitRasterBands']['blue']],
            'OUTPUT': QgsProcessingUtils.generateTempFilename('r.tif')
        }

        feedback.pushInfo("Running algorithm: Compute r edge")

        outputs['ComputeR'] = processing.run('qgis:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # compute absolute difference Green
        # retrieve the calculated layer g
        g = QgsRasterLayer(outputs['ComputeG']['OUTPUT'], 'g')
        alg_params = {
            'CELLSIZE': 0,
            'CRS': None,
            'EXPRESSION': 'abs("g@1" - "green@1")',
            'EXTENT': outputs['SplitRasterBands']['green'],
            'LAYERS': [outputs['SplitRasterBands']['green'],outputs['ComputeG']['OUTPUT']],
            'OUTPUT': QgsProcessingUtils.generateTempFilename('absG.tif')
        }

        feedback.pushInfo("Running algorithm: Compute Absolute Difference Green")

        outputs['ComputeAbsoluteDifferenceGreen'] = processing.run('qgis:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # # compute absolute difference Red
        # Retrieve the computed layer r
        r = QgsRasterLayer(outputs['ComputeR']['OUTPUT'], 'r')
        alg_params = {
            'CELLSIZE': 0,
            'CRS': None,
            'EXPRESSION': 'abs("r@1" - "red@1")',
            'EXTENT': outputs['SplitRasterBands']['red'],
            'LAYERS': [outputs['SplitRasterBands']['red'],outputs['ComputeR']['OUTPUT']],
            'OUTPUT': QgsProcessingUtils.generateTempFilename('absR.tif')
        }

        feedback.pushInfo("Running algorithm: Compute Absolute Difference Red")

        outputs['ComputeAbsoluteDifferenceRed'] = processing.run('qgis:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}
        
        # # compute f1
        # Retrieve absolute difference red and Green
        absG = QgsRasterLayer(outputs['ComputeR']['OUTPUT'], 'absG')
        absR = QgsRasterLayer(outputs['ComputeR']['OUTPUT'], 'absR')
        alg_params = {
            'CELLSIZE': 0,
            'CRS': None,
            'EXPRESSION': ' ( "absR@1" + "absG@1" )  / 2',
            'EXTENT': None,
            'LAYERS': [outputs['ComputeAbsoluteDifferenceRed']['OUTPUT'],outputs['ComputeAbsoluteDifferenceGreen']['OUTPUT']],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Compute F1 B")

        outputs['ComputeF1B'] = processing.run('qgis:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # f1 layer statistics
        alg_params = {
            'BAND': 1,
            'INPUT': outputs['ComputeF1B']['OUTPUT']
        }

        feedback.pushInfo("Running algorithm: Compute F1 Layer Statistics")

        outputs['F1LayerStatistics'] = processing.run('native:rasterlayerstatistics', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}
        
        # Normalize f1
        alg_params = {
            'BAND': 1,
            'FUZZYHIGHBOUND': outputs['F1LayerStatistics']['MAX'],
            'FUZZYLOWBOUND': outputs['F1LayerStatistics']['MIN'],
            'INPUT': outputs['ComputeF1B']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Normalize F1")

        outputs['NormalizeF1'] = processing.run('native:fuzzifyrasterlinearmembership', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # #################################################################################################
        # # Compute f3 Layer
        # #################################################################################################0
        
        # compute f3 part a
        alg_params = {
            'CELLSIZE': 0,
            'CRS': None,
            'EXPRESSION': '("green@1" -  min("red@1","blue@1"))',
            'EXTENT': None,
            'LAYERS': [outputs['SplitRasterBands']['red'],
                       outputs['SplitRasterBands']['green'],
                       outputs['SplitRasterBands']['blue']],
            'OUTPUT': QgsProcessingUtils.generateTempFilename('f3A.tif')
        }

        feedback.pushInfo("Running algorithm: compute f3 part a")

        outputs['ComputeF3PartA'] = processing.run('qgis:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # # compute f3 part b
        # Retrieve f3 A layer
        f3A = QgsRasterLayer(outputs['ComputeF3PartA']['OUTPUT'], 'f3A')
        alg_params = {
            'CELLSIZE': 0,
            'CRS': None,
            'EXPRESSION': '( ("f3A@1" < 0 )  * 0) +  (( "f3A@1">= 0) * "f3A@1")',
            'EXTENT': None,
            'LAYERS': outputs['ComputeF3PartA']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Compute f3 part b")

        outputs['ComputeF3PartB'] = processing.run('qgis:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # f3 layer statistics
        alg_params = {
            'BAND': 1,
            'INPUT': outputs['ComputeF3PartB']['OUTPUT']
        }

        feedback.pushInfo("Running algorithm: Compute F3 Layer Statistics")

        outputs['F3LayerStatistics'] = processing.run('native:rasterlayerstatistics', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}
        
        # Normalize f3
        alg_params = {
            'BAND': 1,
            'FUZZYHIGHBOUND': outputs['F3LayerStatistics']['MAX'],
            'FUZZYLOWBOUND': outputs['F3LayerStatistics']['MIN'],
            'INPUT': outputs['ComputeF3PartB']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Normalize F3")

        outputs['NormalizeF3'] = processing.run('native:fuzzifyrasterlinearmembership', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # ###################################################################################################
        # # Compute Bare Areas Layer
        # ###################################################################################################

        # Compute Soil Brightness
        alg_params = {
            'channels.blue': 3,
            'channels.green': 2,
            'channels.mir': None,
            'channels.nir': None,
            'channels.red': 1,
            'in': parameters['satellite_image'],
            'list': 'Soil:BI',  # Soil:BI
            'outputpixeltype': 5,  # float
            'out': QgsProcessingUtils.generateTempFilename('soilBI.tif')
        }

        # Log current step and run the algorithm
        feedback.pushInfo("Running algorithm: Compute Soil Brightness")

        outputs['ComputeSoilBrightness'] = processing.run('otb:RadiometricIndices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # Sample Soil BI
        alg_params = {
            'COLUMN_PREFIX': 'BI',
            'INPUT': parameters['sample_bare_areas'],
            'RASTERCOPY': outputs['ComputeSoilBrightness']['out'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Sample Soil Brightness")

        outputs['SampleSoilBi'] = processing.run('native:rastersampling', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}

        # Bare Areas Statistics
        alg_params = {
            'FIELD_NAME': 'BI1',
            'INPUT_LAYER': outputs['SampleSoilBi']['OUTPUT']
        }

        feedback.pushInfo("Running algorithm: Compute Bare Area Statistics")

        outputs['BareAreasStatistics'] = processing.run('qgis:basicstatisticsforfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(15)
        if feedback.isCanceled():
            return {}

        # Compute Bare Areas
        alg_params = {
            'INPUT': outputs['ComputeSoilBrightness']['out'],
            'MAXIMUM_VALUE': outputs['BareAreasStatistics']['THIRDQUARTILE'],
            'MINIMUM_VALUE': outputs['BareAreasStatistics']['MIN'],
            'CLASSIFIED_RASTER': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Compute Bare Areas")

        outputs['ComputeBareAreas'] = processing.run('IDP_Sites_Mapping:rasterclassificationusingcomputedranges', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}
        
        # Invert BareAreas
        alg_params = {
            'BAND_A': 1,
            'BAND_B': None,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': '1-A',
            'INPUT_A': outputs['ComputeBareAreas']['CLASSIFIED_RASTER'],
            'INPUT_B': None,
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'PROJWIN': None,
            'RTYPE': 0,  # Byte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Compute Bare Areas Inverse")

        outputs['InvertBareareas'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}
        
        # ##################################################################################################
        # # Threshold and Segment f1, f3 and Compute Built Up Areas
        # ##################################################################################################

        # Compute f1 Threshold
        alg_params = {
            'INPUT': outputs['NormalizeF1']['OUTPUT']
        }

        feedback.pushInfo("Running algorithm: Compute F1 Threshold")

        outputs['ComputeF1Threshold'] = processing.run('IDP_Sites_Mapping:computethresholdwithotsu', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}

        # Segment f1
        alg_params = {
            'Adaptive Method': 0,  # gaussian
            # Convert the threshold value to a float from the numpy.float
            'Block Size': float(outputs['ComputeF1Threshold']['OUTPUT_THRESHOLD']),
            'Invert Image': False,
            'Modal Blurring': 0,
            'Percent': 0.05,
            'Raster': outputs['NormalizeF1']['OUTPUT'],
            'Thresholding Method': 0,  # otsu
            'Output Raster': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Segment F1")

        outputs['SegmentF1'] = processing.run('IDP_Sites_Mapping:segmentationusingthresholding', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}

        # Compute f3 Threshold
        alg_params = {
            'INPUT': outputs['NormalizeF3']['OUTPUT'],
            'OUTPUT_HTML': None
        }

        feedback.pushInfo("Running algorithm: Compute F3 Threshold")

        outputs['ComputeF3Threshold'] = processing.run('IDP_Sites_Mapping:computethresholdwithotsu', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(20)
        if feedback.isCanceled():
            return {}

        # Segment f3
        alg_params = {
            'Adaptive Method': 0,  # gaussian
            # Convert the threshold to a float
            'Block Size': float(outputs['ComputeF3Threshold']['OUTPUT_THRESHOLD']),
            'Invert Image': False,
            'Modal Blurring': 0,
            'Percent': 0.05,
            'Raster': outputs['NormalizeF3']['OUTPUT'],
            'Thresholding Method': 0,  # otsu
            'Output Raster': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Segment F3")

        outputs['SegmentF3'] = processing.run('IDP_Sites_Mapping:segmentationusingthresholding', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(21)
        if feedback.isCanceled():
            return {}

        # Compute Built Areas
        alg_params = {
            'BAND_A': 1,
            'BAND_B': 1,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': 'logical_and(A==1,B==1)*0*A+logical_and(A==1,B==0)',
            'INPUT_A': outputs['SegmentF3']['Output Raster'],
            'INPUT_B': outputs['SegmentF1']['Output Raster'],
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'PROJWIN': None,
            'RTYPE': 0,  # Byte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Compute Built Up Areas")

        outputs['ComputeBuiltAreas'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(22)
        if feedback.isCanceled():
            return {}

        # Built Up Soils Difference
        alg_params = {
            'BAND_A': 1,
            'BAND_B': 1,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': 'A*B',
            'INPUT_A': outputs['ComputeBuiltAreas']['OUTPUT'],
            'INPUT_B': outputs['InvertBareareas']['OUTPUT'],
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'PROJWIN': None,
            'RTYPE': 0,  # Byte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Compute Built Up Soils Difference")

        outputs['BuiltUpSoilsDifference'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(23)
        if feedback.isCanceled():
            return {}

        # IDP Camp Binary
        # builtUpBinary = QgsRasterLayer(outputs['BuiltUpSoilsDifference']['OUTPUT'], 'builtUpBinary')
        alg_params = {
            'in': outputs['BuiltUpSoilsDifference']['OUTPUT'],
            'out': QgsProcessingUtils.generateTempFilename('builtUpBinary.tif'),
            'channel': 1,
            'structype': 'box',
            'xradius': 1,
            'yradius': 1,
            'filter': 'opening',
            'filter.opening.foreval': 1,
            'filter.opening.backval': 0,
            'outputpixeltype': 5  # float
        }

        feedback.pushInfo("Running algorithm: Compute Binary Morphological Operation on the IDP Binary")

        outputs['IdpCampBinary'] = processing.run('otb:BinaryMorphologicalOperation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(24)
        if feedback.isCanceled():
            return {}

        # Polygonize Structures
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'EXTRA': '',
            'FIELD': 'DN',
            'INPUT': outputs['IdpCampBinary']['out'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        feedback.pushInfo("Running algorithm: Polygonize Built Up Areas Layer")

        outputs['PolygonizeStructures'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(25)
        if feedback.isCanceled():
            return {}

        # Extract by attribute
        alg_params = {
            'FIELD': 'DN',
            'INPUT': outputs['PolygonizeStructures']['OUTPUT'],
            'OPERATOR': 0,  # =
            'VALUE': '1',
            'OUTPUT': parameters['Structures']
        }

        feedback.pushInfo("Running algorithm: Extract the Built Up Areas by Attribute")

        outputs['ExtractByAttribute'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}
        
        feedback.pushInfo("Running algorithm: Writing Final Layer")

        results['Structures'] = outputs['ExtractByAttribute']['OUTPUT']
        return results

    def name(self):
        return 'Tent Extraction'

    def displayName(self):
        return 'Tent Extraction'

    def group(self):
        return 'Segmentation'

    def groupId(self):
        return 'segmentation'

    def shortHelpString(self):
        return """<html><body><p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.25pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Algorithmn is implemented based on the procedure defined in the paper titled https://www.researchgate.net/publication/360952641_A_BUILDING_CHANGE_DETECTION_METHOD_BASED_ON_A_SINGLE_ALS_POINT_CLOUD_AND_A_HRS_IMAGE</p></body></html></p>
<h2>Input parameters</h2>
<h3>Satellite Image</h3>
<p>An RGB True color channel Satellite Imagery to be used for classifiication. Due to the processing time,smaller tiles are preffered for efficient processing.</p>
<h3>Sample Bare Areas</h3>
<p>A point layer containing bare areas that have been sampled representatively across the image to be analayzed. Given the image variablity, bare areas with varying characterisitcs should be sampled. At least 80 points across an image. The image should not have any other attribute besides the id. Each image should have only the bare areas sampled on that specific image as there can be great variations between images and this will result to misleading information.</p>
<h2>Outputs</h2>
<h3>Structures</h3>
<p>This is apolygon layer that represents that tented areas and the structure. Some post processing should be undertaken to eliminate other structures. Use the rectanglify tool to clean the polygons and make them representative of the tents. One post processing is to compute a difference with then known IDP Camp areas. However care should be taken to only use this approach if/when the IDP camps have already been updated. If not, then a manual cleaning would be prefereable.</p>
<style type="text/css">
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.25pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Todo</p></body></html></p><br><p align="right">Algorithm author: Pascal Ogola</p><p align="right">Help author: Pascal Ogola</p><p align="right">Algorithm version: v1</p></body></html>"""

    def createInstance(self):
        return TentExtraction()
