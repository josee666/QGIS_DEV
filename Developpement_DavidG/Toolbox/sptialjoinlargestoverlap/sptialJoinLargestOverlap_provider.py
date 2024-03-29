# -*- coding: utf-8 -*-

"""
/***************************************************************************
 sptialJoinLargestOverlap
                                 A QGIS plugin
 Join spatial permettant de recuperer les attributs ayant la plus grande proportion de superposition de la table ou classe d'entités join
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-08-21
        copyright            : (C) 2020 by David Gauthier MFFP,DIF
        email                : david.gauthier@mffp.gouv.qc.ca
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

__author__ = 'David Gauthier MFFP,DIF'
__date__ = '2020-08-21'
__copyright__ = '(C) 2020 by David Gauthier MFFP,DIF'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider
from .sptialJoinLargestOverlap_algorithm import sptialJoinLargestOverlapAlgorithm
from qgis.PyQt.QtGui import QIcon
import os

class sptialJoinLargestOverlapProvider(QgsProcessingProvider):

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
        self.addAlgorithm(sptialJoinLargestOverlapAlgorithm())
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'Join spatial plus grande superposition'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr('Jointure Spatiale Superposition')

    def icon(self):

        return QIcon(os.path.dirname(__file__) + '/image/Overlap2_large.png')

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
