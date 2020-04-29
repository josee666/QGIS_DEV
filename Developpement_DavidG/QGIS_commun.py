#!/usr/bin/env python
# coding: UTF-8


"""
Auteur:

Par David Gauthier

Division des systemes d'information et du pilotage
Direction des inventaires forestiers
Ministere des Forets, de la Faune et des Parcs
Telephone: (418)-627-8669 poste 4322
Sans frais: 1-877-936-7397 poste 4322
Telecopieur: (418-646-1955
Courriel: david.gauthier@mffp.gouv.qc.ca

"""
# Historique:
# 2020-03-22 -Création du QGIS commun

from qgis.core import *
import processing
from processing.core.Processing import Processing
from qgis.analysis import QgsNativeAlgorithms

from PyQt5.QtCore import QVariant
from random import randrange
import os
from os import path
import subprocess


# Chemin ou QGIS est installer
QgsApplication.setPrefixPath(r"C:\MrnMicro\Applic\OSGeo4W64\bin", True)

# Créer une reference à QgsApplication,
# Mettre le 2eme argument a faux pour desativer l'interface graphique de QGIS
qgs = QgsApplication([], False)

# initialiser QGIS
qgs.initQgis()

# Initialiser les outils qgis
Processing.initialize()

# Permet d'utiliser les algorithmes "natif" ecrit en c++
# https://gis.stackexchange.com/questions/279874/using-qgis3-processing-algorithms-from-standalone-pyqgis-scripts-outside-of-gui
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

def transfererCeGdbToGeoPackage(ce, gdb, gpkg):
    """Permet de transferer une classe d'entité provenant d'une .gdb dans un Geopackage existant ou inexistant'.
            Args:
                ce : classse d'entité que l'on veut transférer
                gdb : gdb contenenant les classes d'entités
                gpkg : gpkg ou la classe d'entité sera transferer


            Exemples d'appel de la fonction:
            ce = 'ForS5_fus'
            gdb = "E:\Temp\geotraitement_QGIS\SharedFiles\ForOri08.gdb"
            gpkg = "E:\Temp\geotraitement_QGIS\SharedFiles\ForOri08.gpkg"

            transfererCeGdbToGeoPackage(ce, gdb, gpkg)
    """

    # Classe dentité dans la gdb
    feature = gdb + '|' + 'layername=' + ce

    # faire un layer avec la string feature
    layer = QgsVectorLayer(feature, ce, 'ogr')

    # Option de sauvegarde
    options = QgsVectorFileWriter.SaveVectorOptions()


    # Si le Geopackage existe
    if path.isfile(gpkg):

        # J'enleve l'extension car il est créé plus bas
        gpkg = gpkg.replace(".gpkg", "")
        # permet de copier dans un GPKG existant
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        options.driverName = 'GPKG'
        options.layerName = ce

        # Transférer la ce de la gdb vers le GeoPackage
        QgsVectorFileWriter.writeAsVectorFormat(layer, gpkg, options)

    # Si le Geopackage n'existe pas
    else:
        # J'enleve l'extension car il est créé plus bas
        gpkg = gpkg.replace(".gpkg", "")

        options.driverName = 'GPKG'
        options.layerName = ce

        # Transférer la ce de la gdb vers le GeoPackage
        QgsVectorFileWriter.writeAsVectorFormat(layer, gpkg, options)

def updateCursor(ce, champ, valeur, nouvelleValeur):
    """Permet de changer une valeure specifique dans un champ specifique avec une nouvelle valeur'.
               Args:
                   ce : classe d'entité
                   champ : Nom du champ
                   valeur : valeur que l'on veut modifier dans le champ
                   nouvelleValeur : Nouvelle valeure que l'on veut mettre dans le champ

               Exemples d'appel de la fonction:

                ce = "E:/Temp/geotraitement_QGIS/acq4peei.shp"
                            ou
                dans un geopackage:

                ce ="E:\Temp\geotraitement_QGIS\SharedFiles\ForOri08.gpkg|layername=ForS5_fus
                champ = 'ORIGINE'
                ancienneValeure = 'CT'
                nouvelleValeure = 'P'

               updateCursor(ce, champ, valeur, nouvelleValeur):
       """

    layer = QgsVectorLayer(ce, 'lyr', 'ogr')


    layer_provider = layer.dataProvider()
    layer.startEditing()
    for feature in layer.getFeatures():
        if feature[champ] == valeur:
            id = feature.id()
            # trouver l'index du champ
            fields = layer.fields()
            indexChamp = fields.indexFromName(champ) # Index du champ
            attr_value = {indexChamp: nouvelleValeur} # Nouvelle valeure
            layer_provider.changeAttributeValues({id: attr_value})
        layer.commitChanges()

def calculGeocode(ce, champ, whereclause =''):
    """Permet de calculer un GEOCODE sur toute la couche ou sur une selection'.
                Args:
                    ce : classse d'entité ou lon veut calculer un GEOCODE
                    champ : le champ ou le calcul de GEOCODE sera fait
                    whereclause : Expression sql pour faire une selection sur la classe d'entité

                Exemples d'appel de la fonction:
                ce = "E:/Temp/geotraitement_QGIS/acq4peei.shp"
                champ = 'GEOCODE' ou'GEOC_FOR' ou 'GEOC_MAJ' etc... (il faut que le champ existe)
                whereclause(optionnel) = "\"GES_CO\" = 'ENEN'"

                calculGeocode(ce, champ, whereclause)
        """
    # Si pas de clause, je selectionne tout les objectid de la couche
    if whereclause == '':
        whereclause = ' \"OBJECTID\" is not null'

    # Verifie si 'ce' est une string ou deja un vectorlayer de QGIS
    if isinstance(ce, str):
        layer = QgsVectorLayer(ce, 'lyr', 'ogr')
    else:
        layer = ce


    layer.selectByExpression(whereclause)
    selection = layer.selectedFeatures()
    geocode = []
    for features in selection:
        coord = (features.geometry().centroid())
        geocode.append(str(round(coord.get().x(), 2)) + "+" + str(round(coord.get().y(), 2)))

    # Mettre la valeur de Geocode dans la champ en remplacant les . par des virgules
    geocode2 = []
    i = 0
    for row in geocode:
        row2 = geocode[i].replace(".", ",")
        geocode2.append(row2)
        i += 1

    # Valeur des Y avec 2 decimales
    geocode3 = []
    for row in geocode2:
        strRow = ''.join(row)
        tags = strRow.split('+')
        tags3 = str(tags[1]).split(',')
        if len(tags3[1]) == 1:
            row2 = tags[0] + "+" + tags[1] + "0"
            geocode3.append(row2)
        else:
            geocode3.append(row)

    # Valeur des X avec 2 decimales et ajout du signe + la ou les X sont positifs
    geocode4 = []
    for row in geocode3:
        strRow = ''.join(row)
        tags = strRow.split('+')

        string = str(tags[0])
        substring = "-"
        tags2 = str(tags[0]).split(',')

        if substring in string:
            geocode4.append(row)
        elif len(tags2[1]) == 1:
            row4 = "+" + tags[0] + "0" + "+" + tags[1]
            geocode4.append(row4)
        else:
            tags[0] = "+" + str(tags[0])
            row2 = str(tags[0]) + "+" + tags[1]
            geocode4.append(row2)

    # mettre a jour la selection de la classe dentite avec la la liste geocode4
    layer_provider = layer.dataProvider()
    layer.selectByExpression(whereclause)
    selection = layer.selectedFeatures()
    layer.startEditing()

    i=0
    for feature in selection:
        id = feature.id()
        # trouver l'index du champ
        fields = layer.fields()
        indexChamp = fields.indexFromName(champ)  # Index du champ
        attr_value = {indexChamp: geocode4[i]}  # Nouvelle valeure
        layer_provider.changeAttributeValues({id: attr_value})
        i+=1
    layer.commitChanges()


def conversionFormatVersGDB(ce, nomJeuClasseEntite, nomClasseEntite, outGDB):

    """Permet de convertir une classe d'entité et la mettre dans une gdb esri avec un jeu de classe d'entité
         avec une tolerance xy de 0.02m en utilisant QGIS.

               Args:
                   ce : classe d'entité
                   nomJeuClasseEntite = nom du jeu de classe d'entité
                   nomClasseEntite = nom de la classe d'entité en sortie dans la gdb
                   outGDB = nom de la gdb crée

               Exemples d'appel de la fonction:

               ce = r"C:\MrnMicro\temp\Racc_dif.shp"
               nomJeuClasseEntite = "TOPO"
               nomClasseEntite = "CorS5"
               outGDB = r"C:\MrnMicro\temp\ForOri.gdb"

               conversionFormatVersGDB(ce, nomJeuClasseEntite, nomClasseEntite, outGDB)
        """

    processing.run("gdal:convertformat", {'INPUT':ce,
                                          'OPTIONS':'-lco FEATURE_DATASET={0} -lco XYTOLERANCE=0.02 -nln {1}'.format(nomJeuClasseEntite, nomClasseEntite),
                                          'OUTPUT':outGDB})

def conversionFormatVersGDBCMD(ce, nomJeuClasseEntite, nomClasseEntite, outGDB):

    """Permet de convertir une classe d'entité et la mettre dans une gdb esri avec un jeu de classe d'entité
         avec une tolerance xy de 0.02m en utilisant en ligne de commande.

               Args:
                   ce : classe d'entité
                   nomJeuClasseEntite = nom du jeu de classe d'entité
                   nomClasseEntite = nom de la classe d'entité en sortie dans la gdb
                   outGDB = nom de la gdb crée

               Exemples d'appel de la fonction:

               ce = r"C:\MrnMicro\temp\Racc_dif.shp"
               nomJeuClasseEntite = "TOPO"
               nomClasseEntite = "CorS5"
               outGDB = r"C:\MrnMicro\temp\ForOri.gdb"

               conversionFormatVersGDBCMD(ce, nomJeuClasseEntite, nomClasseEntite, outGDB)
        """

    CREATE_NO_WINDOW = 0x08000000
    cmd = r"""ogr2ogr -f "FileGDB" {3} {0} -t_srs EPSG:32198 -lco FEATURE_DATASET={1} -lco XYTOLERANCE=0.02 -nln {2}""".format(ce,nomJeuClasseEntite,nomClasseEntite,outGDB)
    subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)

def identifyNarrowPolygon(ce, ceNarrow):

    """
     Version BETA 20200429. J'aimerais enlever les 2 premiers et 2 derniers vertex du Centreligne

     Permet de recréer l'algorithme de ESRI 'identifyNarrowPolygon' permettant de couper les polygones ayant des retrecissements (Appendices)
     de moins de 20 metre.

               Args:
                   ce : classe d'entité
                   ceNarrow = sortie avec les polygones coupés


               Exemples d'appel de la fonction:

               ce = r"C:\MrnMicro\temp\ecofor.shp"
               ceNarrow = r"C:\MrnMicro\temp\ecoforNarrow.shp"

               identifyNarrowPolygon(ce, ceNarrow)
        """

    # Faire le centre ligne
    CL = processing.run("grass7:v.voronoi.skeleton", {'input':ce,
                                                 'smoothness':0.25,'thin':-1,'-a':False,'-s':True,'-l':False,'-t':False,
                                                 'output':QgsProcessing.TEMPORARY_OUTPUT,'GRASS_REGION_PARAMETER':None,
                                                 'GRASS_SNAP_TOLERANCE_PARAMETER':-1,'GRASS_MIN_AREA_PARAMETER':0,
                                                 'GRASS_OUTPUT_TYPE_PARAMETER':0,'GRASS_VECTOR_DSCO':'','GRASS_VECTOR_LCO':'',
                                                 'GRASS_VECTOR_EXPORT_NOCAT':False})["OUTPUT"]


    # generaliser le CL car il y a trop de vertex
    CLgene = processing.run("grass7:v.generalize", {'input':CL,'type':[0,1,2],
                                           'cats':'','where':'','method':0,'threshold':1,'look_ahead':7,'reduction':50,'slide':0.5,
                                           'angle_thresh':3,'degree_thresh':0,'closeness_thresh':0,'betweeness_thresh':0,'alpha':1,
                                           'beta':1,'iterations':1,'-t':True,'-l':True,
                                           'output':QgsProcessing.TEMPORARY_OUTPUT,'error':'TEMPORARY_OUTPUT',
                                           'GRASS_REGION_PARAMETER':None,'GRASS_SNAP_TOLERANCE_PARAMETER':-1,
                                           'GRASS_MIN_AREA_PARAMETER':0.0001,'GRASS_OUTPUT_TYPE_PARAMETER':0,
                                           'GRASS_VECTOR_DSCO':'','GRASS_VECTOR_LCO':'','GRASS_VECTOR_EXPORT_NOCAT':False})["OUTPUT"]



    # Faire des transects de 10m  de chaque coté du sommet perpendiculaire au CL
    transect = processing.run("native:transect", {'INPUT':CLgene,
                                       'LENGTH':10,'ANGLE':90,'SIDE':2,'OUTPUT':QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    # Coupe les polygones avec les transect de 20 m qui traverse completement les polynones ecoforestiers.
    processing.run("native:splitwithlines", {'INPUT':ce,
                                             'LINES':transect,
                                             'OUTPUT':ceNarrow})

if __name__ == '__main__':
    # ce = 'ForS5_fus'
    # gdb = r"E:\Temp\geotraitement_QGIS\SharedFiles\ForOri08.gdb"
    # gpkg = r"E:\Temp\geotraitement_QGIS\SharedFiles\ForOri08.gpkg"

    # transfererCeGdbToGeoPackage(ce, gdb, gpkg)

    # ce = "E:/Temp/geotraitement_QGIS/acq4peei.shp"
    # champ = 'CDE_CO'
    # ancienneValeure = 'A'
    # nouvelleValeure = 'Z'

    # updateCursor(ce, champ, ancienneValeure, nouvelleValeure)

    # ce = "E:/Temp/geotraitement_QGIS/acq4peei_GEOC_FOR.shp"
    # selection = 'GEOC_FOR'
    # # # whereclause = " \"GES_CO\" = '{}' ".format("ENEN")
    # whereclause= ' \"OBJECTID\" <= 30'
    # # whereclause = ""
    # calculGeocode(ce, selection, whereclause)



    # ce = r"C:\MrnMicro\temp\Racc_dif.shp"
    # nomJeuClasseEntite = "TOPO"
    # nomClasseEntite = "CorS5"
    # outGDB = r"C:\MrnMicro\temp\ForOri.gdb"
    #
    # cmd = r"""ogr2ogr -f "FileGDB" C:\MrnMicro\temp\ForOri.gdb C:\MrnMicro\temp\Racc_dif.shp -lco FEATURE_DATASET=TOPO -lco XYTOLERANCE=0.02 -nln CorS5"""
    # subprocess.call(cmd)
    # conversionFormatVersGDB(ce, nomJeuClasseEntite, nomClasseEntite, outGDB)
    ce = r"C:\MrnMicro\temp\Appendice2020\sub.shp"
    ceNarrow = r"C:\MrnMicro\temp\Appendice2020\subNarrow.shp"

    identifyNarrowPolygon(ce, ceNarrow)