# -*- coding: utf-8 -*-

"""
/***************************************************************************
 FaireRaccDif
                                 A QGIS plugin
 Faire un racc dif
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-03-24
        copyright            : (C) 2020 by David Gauthier - MFFP (DIF)
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

__author__ = 'David Gauthier - MFFP (DIF)'
__date__ = '2020-03-24'
__copyright__ = '(C) 2020 by David Gauthier - MFFP (DIF)'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import *
import shutil
import os
from shutil import ignore_patterns
from ClassSecurite import Securite_pde
from PyQt5.QtCore import QVariant
from qgis.PyQt.QtGui import QIcon


from PyQt5.QtCore import QFile, QFileInfo

import processing
from processing.core.Processing import Processing
from qgis.analysis import QgsNativeAlgorithms
host = "Ulysse1"
import subprocess

class TransmissionpreliminaireAcq5peeiprel(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    # Vous pouvez donner les noms que vous voulez.
    # Il faut les utiliser ici bas dans  "def initAlgorithm" et "processAlgorithm"

    INPUT_perm5pre = 'INPUT_perm5pre'


    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # parametre 1 INPUT FeatureSource
        self.addParameter(QgsProcessingParameterFeatureSource( self.INPUT_perm5pre,  self.tr('Périmetre préliminaire (perm5pre.shp)'),
                [QgsProcessing.TypeVectorAnyGeometry]))



    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        ###### Parametres ###############################################################################

        # mettre le premier parametre (vector layer) comme input dans un object
        perm5pre = self.parameterAsVectorLayer(parameters, self.INPUT_perm5pre, context)

        environnement_acceptation = False
        if environnement_acceptation is True:
            suffix_env = 'A'
            genUsername = 'Intranet\ADL-Sief-DoffD'
            genPassword = "66uhdf2011feis!"
        else:
            suffix_env = ''
            genUsername = "Intranet\ADL-Sief-DoffP"
            genPassword = 'RRTuijfeis2011!'

        # Dossier temp
        retrav = os.getenv('TEMP')

        # Faire un dossier pour les .shp qui seront transférés dans le doissier trm_pre
        trm_pre_tansfert = os.path.join(retrav, "trm_pre_transfert")
        out = os.path.join(retrav, "trm_pre_transfert", "MTM")

        if not os.path.exists(trm_pre_tansfert):
            os.mkdir(trm_pre_tansfert)
        else:
            pass
        if not os.path.exists(out):
            os.mkdir(out)
        else:
            pass

        # connection au serveur ulysse1
        obj_connec_doff = Securite_pde(environnement_acceptation, genUsername, genPassword, temps_attente=2,host=host)
        obj_connec_doff.connect_serveur()


        # Path  ===============================================================
        path_adg = r"\\{0}\PDE{1}\ADG".format(host, suffix_env)
        path_adg_EcoForOri_prov = os.path.join(path_adg, "EcoForS5_ORI_Prov")
        folder = os.listdir(path_adg_EcoForOri_prov)

        # trouve le nom de la classe d'entité en QGIS
        valid = perm5pre.name()

        if valid != "Perm5pre":

            msg = u"\nERREUR : La couche doit se nommer Perm5pre\n"
            feedback.reportError(msg)

        else:

            ###################################################################################################

            # GDB et shp ===============================================================
            for f in folder:
                if (f.startswith("Ass")):
                    path_adg_EcoForOri_provGDB = os.path.join(f, "EcoFor_Ori_Prov.gdb")

            GDB_EcoForOri = os.path.join(path_adg_EcoForOri_prov, path_adg_EcoForOri_provGDB)


            msg = u"\n1. Copie GDB localement"
            feedback.pushInfo(msg)

            # Copie de la carte ecoforestiere et struture vide
            if os.path.exists(os.path.join(retrav, "EcoFor_Ori_Prov.gdb")):
                shutil.rmtree(os.path.join(retrav, "EcoFor_Ori_Prov.gdb"))


            shutil.copytree(GDB_EcoForOri, os.path.join(retrav, "EcoFor_Ori_Prov.gdb"),
                            ignore=ignore_patterns('*.lock'))

            # GDB ecofor ===============================================================
            GDB_EcoForOriLoc = os.path.join(retrav, "EcoFor_Ori_Prov.gdb")
            gpk_EcoForOriLoc = os.path.join(retrav, "EcoFor_Ori_Prov.gpkg")


            # msg = u"\n1.1 Transferer le carte ecofor dans un Geopackage"
            # feedback.pushInfo(msg)
            #
            # # Transférer la couche EcoFor_ORI_PROV de EcoFor_Ori_Prov.gdb dans un GeoPackages avec GDAL
            # CREATE_NO_WINDOW = 0x08000000
            # cmd = r"""ogr2ogr -f GPKG {0} {1} -t_srs EPSG:32198""".format(gpk_EcoForOriLoc,GDB_EcoForOriLoc)
            # subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)

            # ce Local dans un GeoPackage ou GDB ===============================================================
            # ceCarteEcofor = "{}|layername=EcoFor_ORI_PROV".format(gpk_EcoForOriLoc)
            ceCarteEcoforstring = '{}|layername=EcoFor_ORI_PROV'.format(GDB_EcoForOriLoc)
            Acq5peei_prel = os.path.join(trm_pre_tansfert, "Acq5peei_prel.shp")

            # Faire un layer avec la carte ecofor
            ceCarteEcofor = QgsVectorLayer(ceCarteEcoforstring, "ceCarteEcofor", "ogr")


            # # test ajouter un champ dans une GDB CA MARCHE
            #
            # champ = "test"
            # # permet d'ajouter un champ double
            # layer_provider = ceCarteEcofor.dataProvider()
            # layer_provider.addAttributes([QgsField(champ, QVariant.Double)])
            # ceCarteEcofor.updateFields()
            #


            msg = u"\n2. Creation de la couche Acq5peei_prel"
            feedback.pushInfo(msg)

            # faire un buffer de 500 m
            Perm5preBuf = processing.run("native:buffer",
                                       {'INPUT': perm5pre, 'DISTANCE': 500, 'SEGMENTS': 5,
                                        'END_CAP_STYLE': 1, 'JOIN_STYLE': 0, 'MITER_LIMIT': 2, 'DISSOLVE': False,
                                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT}, feedback=feedback)["OUTPUT"]


            msg = u"\n2.0 Selection dans la carte ecoforestiere"
            feedback.pushInfo(msg)

            # faire une selection location intersect avec perimetre sur la carte ecofor prov
            processing.run("native:selectbylocation",
                       {'INPUT': ceCarteEcofor,
                        'PREDICATE': [0], 'INTERSECT': Perm5preBuf, 'METHOD': 0}, feedback=feedback)


            msg = u"\n2.1 Sauvegarde de la selection"
            feedback.pushInfo(msg)

            # copier la selection en memoire
            ce_ecofor_select = processing.run("native:saveselectedfeatures", {'INPUT': ceCarteEcofor, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},
                                   feedback=feedback)["OUTPUT"]


            msg = u"\n2.2 Réparer les géométries"
            feedback.pushInfo(msg)

            repair = processing.run("native:fixgeometries", {'INPUT':ce_ecofor_select,'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},
                                    feedback=feedback)["OUTPUT"]


            msg = u"\n2.3 Dissolve de la selection"
            feedback.pushInfo(msg)

            # Un dissolve de ma selection et apres je vais suppirmer les trous a l'interieur du dissolve.
            dissolve = processing.run("native:dissolve", {'INPUT': repair, 'FIELD': [], 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},
                              feedback=feedback)["OUTPUT"]

            # suppirmer les trous a l'interieur du dissolve
            newPerm5pre = processing.run("native:deleteholes", {'INPUT':dissolve,'MIN_AREA':999999999,'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT},
                                 feedback=feedback)["OUTPUT"]

            # refaire une selection WITHIN avec le nouveau perimetre pas de trou
            processing.run("native:selectbylocation", {'INPUT': ceCarteEcofor, 'PREDICATE': [6],'INTERSECT': newPerm5pre, 'METHOD': 0},
                            feedback=feedback)

            # Copier en .shp la prel localement
            processing.run("native:saveselectedfeatures", {'INPUT': ceCarteEcofor, 'OUTPUT': Acq5peei_prel},
                       feedback=feedback)

            #####################################################
            msg = u"\n3. Projection de la couche"
            feedback.pushInfo(msg)

            # trouver le path d'une couche en Input dans QGIS (c une string)
            pathINPUT = self.parameterDefinition('INPUT_perm5pre').valueAsPythonString(parameters['INPUT_perm5pre'], context)

            # Enleve "/Perm5pre.shp" de la string pour avoir seulement le path du shp
            pathINPUT = pathINPUT.replace("/Perm5pre.shp", "")

            fus = os.path.basename(pathINPUT)
            fus = fus.replace("'","")

            if fus == '04':
                proj = 'EPSG:32184'
            elif fus == '05':
                proj = 'EPSG:32185'
            elif fus == '06':
                proj = 'EPSG:32186'
            elif fus == '07':
                proj = 'EPSG:32187'
            elif fus == '08':
                proj = 'EPSG:32188'
            elif fus == '09':
                proj = 'EPSG:32189'
            elif fus == '10':
                proj = 'EPSG:32110'
            else:
                raise QgsProcessingException("\nLe dossier parent du Perm5pre.shp ne contient pas de # de fuseau\n")

            # for file in os.listdir(trm_pre_tansfert):
            #     if file.endswith(".shp"):
            #         outfc = os.path.join(out, file)

            processing.run("native:reprojectlayer", {'INPUT':Acq5peei_prel,
                                                             'TARGET_CRS':QgsCoordinateReferenceSystem(proj),
                                                             'OUTPUT':os.path.join(out, "Acq5peei_prel.shp")},feedback=feedback)
            trm_pre = pathINPUT
            trm_pre = trm_pre.replace("'","")

            msg = u"\n4. Transfert de la couche dans le dossier : {0}".format(trm_pre)
            feedback.pushInfo(msg)

            # copier les données dans le dossier trm_pre
            for file in os.listdir(out):
                shutil.copy(os.path.join(out, file), trm_pre)

            msg = u"\n5. Fin du programme"
            feedback.pushInfo(msg)


        return {self.INPUT_perm5pre: 'INPUT_perm5pre'}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return '1 - Transmission préliminaire (Acq5peei_prel)'

    def icon(self):

        return QIcon(os.path.dirname(__file__) + '/image/1.png')

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ''

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return TransmissionpreliminaireAcq5peeiprel()
