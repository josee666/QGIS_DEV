#!/usr/bin/env python
# coding: UTF-8


"""
Auteur:

Par David Gauthier \ Phillipe Leblanc\ Josée Martel\ Yahoo


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
import sys
import os
import subprocess
import time
import os.path
from os import path
import pandas
from processing.tools import dataobjects
from PyQt5.QtCore import QVariant
from serviceBdSqlite import *

from pandas import DataFrame

# librairies pour la fonction dissolve
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import fiona
import itertools
from operator import itemgetter
from geopandas import GeoSeries, GeoDataFrame
import geopandas as gpd
import pandas as pd
import rtree
from osgeo import gdal


# Pour faire marcher GRASS en StandAlone script
# https://gis.stackexchange.com/questions/296502/pyqgis-scripts-outside-of-qgis-gui-running-processing-algorithms-from-grass-prov
from processing.algs.grass7.Grass7Utils import Grass7Utils
Grass7Utils.checkGrassIsInstalled()

# Chemin ou QGIS est installer
QgsApplication.setPrefixPath(r"C:\Logiciels\OSGeo4W\bin", True)

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


def connec_sqlite(nombd):

    """ Fonction qui creer une connexion sur une BD SQLITE ou GEOPACKAGE et creer un curseur
    ARG: nombd(str): le nom de la bd avec chemin d'acces

    RETURN: nomconnection, nomcursor
    exemple d'appel: con, cur = connec_sqlite('E:/Python/projet/valid_acq/data/acq.sqlite')
    """
    import sqlite3
    nomconnection = None
    nomconnection = sqlite3.connect(nombd)
    nomconnection.enable_load_extension(True)
    nomconnection.load_extension("mod_spatialite")
    nomcursor = nomconnection.cursor()
    return nomconnection, nomcursor

def executeSQL(cursor, req, retour_cursor=True):

    """ JM 2016-03-10
    Fonction qui execute un SQL sur une BD
    ARGS:
        cursor(str) : Le curseur définie
        req(str) : Requete SQL a lancer
    Return: True/ si execution réussi, objet erreur si non réussi
    """
    import sqlite3
    try:
        cursor.execute(req)
        if retour_cursor:
            return cursor  #, True

    except sqlite3.Error as eSqlite:
        print(eSqlite)

        raise


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

            transfererCeGdbToGeoPackage(ce, gdb, gpkg)    """

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

    # Verifie si 'ce' est une string ou deja un vectorlayer de QGIS
    if isinstance(ce, str):
        layer = QgsVectorLayer(ce, 'lyr', 'ogr')
    else:
        layer = ce

    # Si pas de clause
    if whereclause == '':
        feat = layer.getFeatures()
        geocode = []

        for features in feat:
            coord = (features.geometry().pointOnSurface()) # point on surafce permet des faire le point  a linterieur du polygone
            geocode.append(str(round(coord.get().x(), 2)) + "+" + str(round(coord.get().y(), 2)))
    else:

        layer.selectByExpression(whereclause)
        selection = layer.selectedFeatures()
        geocode = []
        for features in selection:
            coord = (features.geometry().pointOnSurface())
            geocode.append(str(round(coord.get().x(), 2)) + "+" + str(round(coord.get().y(), 2)))

    # remplacer les . par des virgules
    for i in range(len(geocode)):
        row2 = geocode[i].replace(".", ",")
        geocode[i] = row2

        # Valeur des Y avec 2 decimales
        strRow = ''.join(geocode[i])
        tags = strRow.split('+')
        tags3 = str(tags[1]).split(',')
        if len(tags3[1]) == 1:
            row2 = tags[0] + "+" + tags[1] + "0"
            geocode[i] = row2

    for i in range(len(geocode)):
        strRow = ''.join(geocode[i])
        tags = strRow.split('+')
        # Valeur des X avec 2 decimales et ajout du signe + la ou les X sont positifs
        string = str(tags[0])
        substring = "-"
        tags2 = str(tags[0]).split(',')

        if substring in string:
            if len(tags2[1]) == 1:
                row4 = tags[0] + "0" + "+" + tags[1]
                geocode[i] = row4
            else:
                pass

        elif len(tags2[1]) == 1:
            row4 = "+" + tags[0] + "0" + "+" + tags[1]
            geocode[i] = row4
        else:
            tags[0] = "+" + str(tags[0])
            row2 = str(tags[0]) + "+" + tags[1]
            geocode[i] = row2


    # mettre a jour de la classe dentite avec la la liste geocode
    layer_provider = layer.dataProvider()
    if whereclause == '':
        feat = layer.getFeatures()
        layer.startEditing()
    else:
        layer.selectByExpression(whereclause)
        feat = layer.selectedFeatures()
        layer.startEditing()

    i=0
    for feature in feat:
        id = feature.id()
        # trouver l'index du champ
        fields = layer.fields()
        indexChamp = fields.indexFromName(champ)  # Index du champ
        attr_value = {indexChamp: geocode[i]}  # Nouvelle valeure
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

    # CREATE_NO_WINDOW = 0x08000000
    cmd = r"""ogr2ogr -f "FileGDB" {3} {0} -t_srs EPSG:32198 -lco FEATURE_DATASET={1} -lco XYTOLERANCE=0.02 -nln {2}""".format(ce,nomJeuClasseEntite,nomClasseEntite,outGDB)
    subprocess.call(cmd)

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

    # Dossier temp
    retrav = os.getenv('TEMP')

    # couches intermediaires
    gpkg = os.path.join(retrav, "temp.gpkg")
    CL = os.path.join(retrav, "CL.shp")
    CLgene = os.path.join(retrav, "CLgene.shp")
    transect = "{}|layername=transect".format(gpkg)


    print("Faire le CL")
    # Faire le centre ligne
    processing.run("grass7:v.voronoi.skeleton", {'input':ce, 'smoothness':0.25,'thin':-1,'-a':False,
                                                      '-s':True,'-l':False,'-t':False,'output':CL,
                                                      'GRASS_REGION_PARAMETER':None,'GRASS_SNAP_TOLERANCE_PARAMETER':-1,
                                                      'GRASS_MIN_AREA_PARAMETER':0,'GRASS_OUTPUT_TYPE_PARAMETER':0,
                                                      'GRASS_VECTOR_DSCO':'','GRASS_VECTOR_LCO':'','GRASS_VECTOR_EXPORT_NOCAT':False})
    print("Faire le CLgene")
    # generaliser le CL car il y a trop de vertex
    processing.run("grass7:v.generalize", {'input':CL,'type':[0,1,2],
                                           'cats':'','where':'','method':0,'threshold':1,'look_ahead':7,'reduction':50,'slide':0.5,
                                           'angle_thresh':3,'degree_thresh':0,'closeness_thresh':0,'betweeness_thresh':0,'alpha':1,
                                           'beta':1,'iterations':1,'-t':True,'-l':True,
                                           'output':CLgene,'error':'TEMPORARY_OUTPUT',
                                           'GRASS_REGION_PARAMETER':None,'GRASS_SNAP_TOLERANCE_PARAMETER':-1,
                                           'GRASS_MIN_AREA_PARAMETER':0.0001,'GRASS_OUTPUT_TYPE_PARAMETER':0,
                                           'GRASS_VECTOR_DSCO':'','GRASS_VECTOR_LCO':'','GRASS_VECTOR_EXPORT_NOCAT':False})


    print("Faire les transects")
    # Faire des transects de 10m  de chaque coté du sommet perpendiculaire au CL
    processing.run("native:transect", {'INPUT':CLgene,'LENGTH':10,'ANGLE':90,'SIDE':2,
                                       'OUTPUT':'ogr:dbname=\'{}\' table=\"transect\" (geom) sql='.format(gpkg)})


    print("Faire les Narrow")
    # Coupe les polygones avec les transect de 20 m qui traverse completement les polynones ecoforestiers.
    processing.run("native:splitwithlines", {'INPUT':ce,
                                             'LINES':transect,
                                             'OUTPUT':ceNarrow})


def separerJeuClasseEntite(ce, reptrav, x, y, ESPG = 32198):

    """
     Permet de de faire des jeux de données a partir d'une classe d'entité avec une grille de X metre (x) par X metre (y).
     Le résultat sera des tuiles numérotés dans un GEOPACKAGE nommé "JeuClasseEntite.gpkg" situé dans le dossier de travail que vous aurez choisi.
     La grille est en projection en Quebec Lambert (32198). Donc, si votre classe d'entité a un autre projection il faut defenir le ESPG


               Args:
                   ce : classe d'entité
                   reptrav = dossier de travail
                   x = largeur de la tuile en metres
                   y = hauteur de la tuile en metres
                   ESPG (ne pas utiliser si votre classe d'entité (ce) est en 32198) = numéro ESPG de la projection

               Exemple d'appel de la fonction:

               ce = r"C:\MrnMicro\temp\ecofor.shp"
               reptrav = r"C:\MrnMicro\temp
               x = 10000
               y = 10000
               ESPG (ne pas utiliser si votre classe d'entité (ce) est en 32198) = 2949

               separerJeuClasseEntite(ce, reptrav, x, y, ESPG)

                    ou (avec la projection Quebec Lambert par defaut)

               separerJeuClasseEntite(ce, reptrav, x, y)

        """

    # Copier la ce dasn un geopackage
    gpkg = os.path.join(reptrav,"JeuClasseEntite.gpkg")
    processing.run("gdal:convertformat", {'INPUT':ce,
                                          'OPTIONS':'-nln ceCopy','OUTPUT':gpkg})

    ceCopy = "{0}|layername=ceCopy".format(gpkg)


    # trouver l'extend de la couche ceCopy
    layer_ceCopy = QgsVectorLayer(ceCopy, 'lyr', 'ogr')
    ex = layer_ceCopy.extent()

    xmin = ex.xMinimum()
    xmax = ex.xMaximum()
    ymin = ex.yMinimum()
    ymax = ex.yMaximum()
    coords = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)

    # Faire une grille de X x X avec l'extend avec un projection LAMBERT par default
    processing.run("native:creategrid", {'TYPE':2,'EXTENT':coords,
                                         'HSPACING':x,'VSPACING':y,'HOVERLAY':0,'VOVERLAY':0,
                                         'CRS':QgsCoordinateReferenceSystem('EPSG:{0}'.format(ESPG)),'OUTPUT':'ogr:dbname=\'{0}\' table=\"grille\" (geom) sql='.format(gpkg)})

    grille = "{0}|layername=grille".format(gpkg)

    # Faire une selection par location en boucle avec la colonne id de la grille, copier la selection et effacer la selection dans la ce copier
    # Faire une liste des valeurs du champ "id" de la grille
    listId = []
    layer = QgsVectorLayer(grille, 'lyr', 'ogr')
    for feature in layer.getFeatures():
        listId.append(feature["id"])


    # faire des layer avant les selections
    grille = QgsVectorLayer(grille, 'lyr', 'ogr')
    ceCopy = QgsVectorLayer(ceCopy, 'lyr', 'ogr')

    # faire une boucle pour separer la classe d'entité en jeu de données
    for i in listId:

        # faire un selection par attribut sur le id de la grille
        whereclause = ' \"id\"={}'.format(i)
        print (whereclause)

        processing.run("qgis:selectbyexpression", {'INPUT':grille,'EXPRESSION':whereclause,'METHOD':0})

        # copier la selection en memoire
        select = processing.run("native:saveselectedfeatures", {'INPUT': grille, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT}),["OUTPUT"]

        # faire une selection location intersect avec la grille sur la ce
        processing.run("native:selectbylocation", {'INPUT':ceCopy,
                                               'PREDICATE':[0],'INTERSECT':select,'METHOD':0})

        # Copier la tuile si il y a une selection
        selection = ceCopy.selectedFeatures()
        count = ceCopy.selectedFeatureCount()
        if count > 0:

            processing.run("native:saveselectedfeatures", {'INPUT': ceCopy, 'OUTPUT': 'ogr:dbname=\'{0}\' table=\"tuile_{1}\" (geom) sql='.format(gpkg,i)})

            # Effacer de la selection dans ceCopy afin de ne pas reprendre les polygones en double
            with edit(ceCopy):
                for feature in selection:
                    ceCopy.deleteFeature(feature.id())

    # Effacer les couches grille et ceCopy du gpkg avec GDAL
    # path de GDAL
    sys.path.append(r"\\Sef1271a\F1271g\OutilsProdDIF\modules_communs\gdal\gdal2.3.2")

    CREATE_NO_WINDOW = 0x08000000
    cmd = r"""ogrinfo {0} -sql "drop table grille""".format(gpkg)
    subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)

    cmd = r"""ogrinfo {0} -sql "drop table ceCopy""".format(gpkg)
    subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)

def calculerSuperficieAlbers(ce):

    """
     Permet de caluler le champs SUPERFICIE en Canada_Albers_Equal_Area_Conic (ESRI:102001)

               Args:
                   ce : classe d'entité

               Exemple d'appel de la fonction:

               ce = r"C:\MrnMicro\temp\ecofor.shp"

               calculerSuperficieAlbers(ce)

        """

    # faire un layer avec ce
    if isinstance(ce, str):
        layer = QgsVectorLayer(ce, 'lyr', 'ogr')
    else:
        layer = ce

    layerReproject = processing.run("native:reprojectlayer", {'INPUT':layer,'TARGET_CRS':QgsCoordinateReferenceSystem('ESRI:102001'),'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},
                             )["OUTPUT"]

    # ajouter un champ SUPERFICIE
    # # https://qgis.org/pyqgis/3.2/core/Field/QgsField.html
    # # https://gis.stackexchange.com/questions/174971/how-to-define-the-number-of-decimals-when-adding-a-new-field-as-double-to-an-att
    #
    # champ = QgsField('SUPERFICIE', QVariant.Double,'double',30, 1 )
    # layer.dataProvider().addAttributes([champ])
    # layer.updateFields()

    # calculer la superficie de la couche reprojeté en Albers et mettre le tout dans une liste
    feat = layerReproject.getFeatures()
    superficie = []

    for features in feat:
        sup =round((features.geometry().area())/ 10000,1)
        superficie.append(sup)

    # mettre a jour la superficie de la couche original avec la liste des superficies de la couche reprojetée
    feat = layer.getFeatures()
    layer_provider = layer.dataProvider()

    i=0
    for features in feat:
        id = features.id()
        # trouver l'index du champ
        fields = layer.fields()
        indexChamp = fields.indexFromName('SUPERFICIE')
        attr_value = {indexChamp: superficie[i]}
        layer_provider.changeAttributeValues({id: attr_value})
        i+=1

    layer.commitChanges()
def selectByExpression(layer, expression, method=0):

    """Permet de sélectionner une couche par expression (selon les attributs).
            Args:
                layer : classe d'entité que l'on veut sélectionner
                expression : expression sql de la sélection
                method : méthode de sélection. La valeur par défaut est 0 (0=Créer une nouvelle sélection, 1=Ajouter a la sélection courante, 2=Enlever de la sélection actuelle, 3=Sélection au sein de la sélection courante)


            Exemples d'appel de la fonction:

            table = r"C:\MrnMicro\temp\Couche_annuelle\TableCodesVP.gdb|layername=DDE_PRO_SOU_VP_VUE"
            layer = QgsVectorLayer(table, 'lyr', 'ogr')
            expression = '\"PRS_IN_MJF\" = "O"'
            method = 3
            selectByExpression(layer, expression, method)
    """

    if method == 0:
        behavior = QgsVectorLayer.SetSelection
    elif method == 1:
        behavior = QgsVectorLayer.AddToSelection
    elif method == 2:
        behavior = QgsVectorLayer.RemoveFromSelection
    elif method == 3:
        behavior = QgsVectorLayer.IntersectSelection

    layer.selectByExpression(expression, behavior)
    return layer.selectedFeatures()


def calculateAttributes(layer, field, expression, selection=False):

    """Permet de calculer un champ.
            Args:
                layer : classe d'entité que l'on veut calculer
                field : champ que l'on veut calculer
                expression : expression qui permet de déterminer la valeur calculée (Si on veut copier la valeur d'un autre champ, il faut inscrire : feature['FIELD'].
                selection : Si la valuer est True, le calcul est fait sur les entités selectionnées . La valeur par defaut est False.


            Exemples d'appel de la fonction:

            gpkg_path = f"C:/MrnMicro/temp/Couche_annuelle/geotraitement/foret.gpkg|layername=territoire"
            layer = QgsVectorLayer(gpkg_path, 'lyr', 'ogr')
            field = "NOMAJ_PEE"
            expression = "feature['OBJECTID'] + 1"
            calculateAttributes(layer, field, expression)
    """

    if not selection:
        with edit(layer):
            for feature in layer.getFeatures():

                feature.setAttribute(feature.fieldNameIndex(field), eval(expression))
                layer.updateFeature(feature)
    elif selection:
        with edit(layer):
            for feature in layer.getSelectedFeatures():

                feature.setAttribute(feature.fieldNameIndex(field), eval(expression))
                layer.updateFeature(feature)


def convertListForSqlQuery(list):

    """Permet de convertir une liste python pour être inclus dans une requête SQL. Les crochets deviennent des parenthèses.
            Args:
                list : liste python

            Exemples d'appel de la fonction:

            list_error = ['RADIOO', 'LOS', 'RTG']
            selectByExpression(layer, f"NOMAJ_PEE" IN {convertListForSqlQuery(list_error)}"
    """
    elements = (', '.join("'{0}'".format(x) for x in list))
    sql_list = f"({elements})"
    return sql_list


def supprimerUnChamp(fc, champ):

    """
    Permet de supprimer un champ

              Args:
                  ce : classe d'entité
                  champ : nom du champ

              Exemple d'appel de la fonction:

              ce = r"C:\MrnMicro\temp\ecofor.shp"
              champ : "SUPERFICIE"

              calculerSuperficieAlbers(ce,champ)

       """

    layer_fc = QgsVectorLayer(fc, 'lyr', 'ogr')
    layer_provider = layer_fc.dataProvider()
    fields = layer_fc.fields()

    indexChamp = fields.indexFromName(champ)  # Index du champ
    layer_provider.deleteAttributes([indexChamp])
    layer_fc.updateFields()


def spatialJoinLargestOverlap(target_features, join_features, outfc, Pente = False):

    """
   Permet de faire un intersect entre 2 classe d'entité et de garder les valeurs attributaires du "join_features"
   qui sont représenté avec la plus grande superpostion.

   Je dois mieux documenter la description de la fonction

             Args:
                 ce : classe d'entité
                 champ : nom du champ

             Exemple d'appel de la fonction:

             ce = r"C:\MrnMicro\temp\ecofor.shp"
             champ : "SUPERFICIE"

             calculerSuperficieAlbers(ce,champ)

      """
    
    # Geopackage temporaire
    gpkg = os.path.join(r"C:\MrnMicro\temp","temp.gpkg")

    if os.path.exists(gpkg):
        os.remove(gpkg)
    else:
        pass

    # il faut toujours travailler dans un GEOPACKAGE, car si je prends un shape et un layer dans un GEOPACKAGE,
    #  les outils comme intersect ne fonctionne pas bien

    # Je copie les 2 intrants (target_features et join_features) dans le GEOPACKAGE temporaire
    # J'enleve l'extension car il est créé plus bas
    gpkg = gpkg.replace(".gpkg", "")


    options_GPKG = QgsVectorFileWriter.SaveVectorOptions()
    options_GPKG.driverName = "GPKG"
    options_GPKG.layerName ="target_features"

    # faire un layer si c un string
    if isinstance(target_features, str):
        target_features = QgsVectorLayer(target_features, 'target_layer', 'ogr')
    else:
        pass

    # Ecrire le fichier dans le gpkg
    QgsVectorFileWriter.writeAsVectorFormatV2(target_features, gpkg, QgsCoordinateTransformContext(), options_GPKG)

    target_features_gpkg = "{0}|layername=target_features".format(gpkg+".gpkg")
    target_features = target_features_gpkg


    # permet de copier dans un GPKG existant
    options_GPKG.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    options_GPKG.layerName ="join_features"

    # faire un layer si c un string
    # faire un layer
    if isinstance(join_features, str):
        join_features = QgsVectorLayer(join_features, 'lyr', 'ogr')
    else:
        pass


    # Ecrire le fichier dans le gpkg
    QgsVectorFileWriter.writeAsVectorFormatV2(join_features, gpkg , QgsCoordinateTransformContext(), options_GPKG)

    join_features_gpkg = "{0}|layername=join_features".format(gpkg+".gpkg")
    join_features = join_features_gpkg


    gpkg = os.path.join(r"C:\MrnMicro\temp","temp.gpkg")

    # faire des layer
    if isinstance(target_features, str):
        target_layer = QgsVectorLayer(target_features, 'target_layer', 'ogr')
    else:
        target_layer = target_features


    # ajouter un champ SUP1 au target et caluler la superficie
    champ = QgsField('SUP1', QVariant.Double,'double',100,2 )
    target_layer.dataProvider().addAttributes([champ])
    target_layer.updateFields()

    feat = target_layer.getFeatures()
    layer_provider = target_layer.dataProvider()

    # caluler la superficie en m carrée
    for features in feat:
        id = features.id()
        # trouver l'index du champ
        fields = target_layer.fields()
        indexChamp = fields.indexFromName('SUP1')  # Index du champ

        sup =str(round(features.geometry().area(),2))
        attr_value = {indexChamp: sup}  # calculer area
        layer_provider.changeAttributeValues({id: attr_value})

    target_layer.commitChanges()

    # creer un champ unique qui servira pour le join final
    layer_provider=target_layer.dataProvider()
    layer_provider.addAttributes([QgsField("UNIQ",QVariant.String)])
    target_layer.updateFields()


    # Calculer la valeur unique avec la fonction pour calculer les geocodes
    calculGeocode(target_layer, "UNIQ", whereclause ='')

    if isinstance(join_features, str):
        join_layer = QgsVectorLayer(join_features, 'join_layer', 'ogr')
    else:
        join_layer = join_features


    # permet d'ignorer les geometries non valide
    context = dataobjects.createContext()
    context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)


    # faire un intersect
    # intersect = processing.run("native:intersection", {'INPUT':target_layer,'OVERLAY':join_layer,'INPUT_FIELDS':[],
    #                                                    'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    processing.run("native:intersection", {'INPUT':target_layer,'OVERLAY':join_layer,
                                           'INPUT_FIELDS':['fid', 'UNIQ','SUP1'],'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'',
                                           'OUTPUT':'ogr:dbname=\'{0}\' table=\"intersect\" (geom) sql='.format(gpkg)})


    intersect = "C:/MrnMicro/temp/temp.gpkg|layername=intersect"
    intersect = QgsVectorLayer(intersect, 'lyr', 'ogr')

    # # calculer la nouvelle superficie des polygones
    # sup2 = processing.run("qgis:fieldcalculator", {'INPUT':intersect,'FIELD_NAME':'SUP2','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':2,
    #                                                'NEW_FIELD':True,'FORMULA':'round($area,2)','OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("qgis:fieldcalculator", {'INPUT':intersect,'FIELD_NAME':'SUP2','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':2,
                                                   'NEW_FIELD':True,'FORMULA':'round($area,2)',
                                            'OUTPUT':'ogr:dbname=\'{0}\' table=\"sup2\" (geom) sql='.format(gpkg)})

    sup2 = "C:/MrnMicro/temp/temp.gpkg|layername=sup2"
    sup2 = QgsVectorLayer(sup2, 'lyr', 'ogr')



    # calculer la proportion de la superficie SUP2 et SUP1
    processing.run("qgis:fieldcalculator", {'INPUT':sup2,'FIELD_NAME':'prop','FIELD_TYPE':0,'FIELD_LENGTH':100,
                                            'FIELD_PRECISION':2,'NEW_FIELD':False,'FORMULA':'( \"SUP2\"  /  \"SUP1\" ) * 100',
                                            'OUTPUT':'ogr:dbname=\'{0}\' table=\"prop\" (geom) sql='.format(gpkg)})

    # classe d'entité contenant les proportion de l'intersect
    prop = "{0}|layername=prop".format(gpkg)
    prop = QgsVectorLayer(prop, 'lyr', 'ogr')


    if Pente is False:

        # faire un csv avec prop
        csvProp = r'C:\MrnMicro\temp\prop.csv'
        options_CSV = QgsVectorFileWriter.SaveVectorOptions()
        options_CSV.driverName = "CSV"

        # Ecrire le CSV
        QgsVectorFileWriter.writeAsVectorFormatV2(prop, csvProp , QgsCoordinateTransformContext(), options_CSV)

    else:

        # creer un champ unique qui sera utilisé pour les pentes
        proptemp = processing.run("qgis:fieldcalculator", {'INPUT':prop,
                                                           'FIELD_NAME':'New_Id','FIELD_TYPE':2,'FIELD_LENGTH':35,
                                                           'FIELD_PRECISION':3,'NEW_FIELD':True,'FORMULA':' concat(  \"UNIQ\" , \"CL_PENT\" )',
                                                           'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

        # faire un csv avec proptemp
        csvProp = r'C:\MrnMicro\temp\prop.csv'
        options_CSV = QgsVectorFileWriter.SaveVectorOptions()
        options_CSV.driverName = "CSV"

        # Ecrire le CSV
        QgsVectorFileWriter.writeAsVectorFormatV2(proptemp, csvProp , QgsCoordinateTransformContext(), options_CSV)


    input_files = r"C:\MrnMicro\temp\prop.csv"

    # faire la connection avec la bd
    nomconnection, nomcursor = connec_sqlite(gpkg)

    # copier avec panda le csv dans la bd
    df = pandas.read_csv(input_files)
    df.to_sql("Proportion", nomconnection, if_exists='append', index=False)

    if Pente is False:

        # requete SQL qui permet de grouper les UNIQ avec la plus grande proportion de superposition. cette valeur est dans le champ prop.
        # la table resultFinal sera cree dan le gpkg
        req = "create table resultFinal as select * from Proportion GROUP BY UNIQ having prop = max(prop)"

        # excecuter la requete
        executeSQL(nomcursor, req, retour_cursor=True)

    else:

        # faire une requete pour les pentes
        # permet de faire une somme des proportions par classes de pente a l'aide du champ New_id.
        #  la table SelectionPente sera cree dans le gpkg avec le champ TotalProp
        req = "create table SelectionPente as select *, SUM(prop) TotalProp from Proportion GROUP BY New_id"

        # excecuter la requete
        executeSQL(nomcursor, req, retour_cursor=True)

        # permet de prendre le maximum des proportions par UNIQ dans le champ TotalProp afin d'avoir la pente le plus représentée.
        #  la table resultFinal sera cree dans le gpkg
        req = "create table resultFinal as select * from SelectionPente GROUP BY UNIQ having TotalProp = max(TotalProp)"

        # excecuter la requete
        executeSQL(nomcursor, req, retour_cursor=True)


    resultaFinalGpkg = "C:/MrnMicro/temp/temp.gpkg|layername=resultFinal"

    # faire un layer avec resultFinal
    result = QgsVectorLayer(resultaFinalGpkg, 'lyr', 'ogr')

    # faire le join avec la table resultFinal et target_layer
    processing.run("native:joinattributestable", {'INPUT':target_layer,'FIELD':'UNIQ',
                                                  'INPUT_2':result,
                                                  'FIELD_2':'UNIQ','FIELDS_TO_COPY':[],'METHOD':1,
                                                  'DISCARD_NONMATCHING':False,'PREFIX':'','OUTPUT':outfc})

    # Supprimer les champs inutiles du join
    supprimerUnChamp(outfc, "UNIQ")
    supprimerUnChamp(outfc, "UNIQ_2")
    supprimerUnChamp(outfc, "SUP1_2")
    supprimerUnChamp(outfc, "SUP1")
    supprimerUnChamp(outfc, "SUP2")

    if Pente is False:
         pass
    else:
        supprimerUnChamp(outfc, "prop")
        supprimerUnChamp(outfc, "New_Id")


    # jeter le csv prop.csv
    os.remove(csvProp)


def convertirFGDBtoGPKGogr(pathGDB):

    """
    Permet de convertir des FGDB de ESRI en Geopackage avec GDAL

              Args:
                  pathGDB : chemin ou se trouve les FGDB


              Exemple d'appel de la fonction:

              pathGDB = r"C:\MrnMicro\temp"

              convertirFGDBtoGPKGogr(pathGDB)

       """

    listGDB = os.listdir(pathGDB)

    try :

        for fgdb in listGDB:

            print("Traitement de la GDB : {}".format(fgdb))

            gpkg = fgdb.replace('.gdb', '.gpkg')
            outdb= os.path.join(pathGDB, gpkg)

            gdb = os.path.join(pathGDB,fgdb)

            cmd = r"""ogr2ogr -append -f GPKG {0} {1}""".format(outdb, gdb)
            subprocess.call(cmd)

    except :
        pass

# def dissolveFiona(gpkg, nomInput, nomOutput, fields):
#
#     layer = gpd.read_file(gpkg, layer=nomInput)
#     layer.fillna('null')
#     with fiona.open(gpkg, layer='{0}'.format(nomInput)) as input:
#         with fiona.open(gpkg, 'w', layer='{0}'.format(nomOutput), **input.meta) as output:
#             grouper = itemgetter(*fields)
#             key = lambda k: grouper(k['properties'])
#             for k, group in itertools.groupby(sorted(input, key=key), key):
#                 properties, geom = zip(*[(feature['properties'], shape(feature['geometry'])) for feature in group])
#                 output.write({'geometry': mapping(unary_union(geom)), 'properties': properties[0]})
#
# # marche juste avec 1 champ
# def dissolveGDAL(input, output, fields):
#     cmd = r"""ogr2ogr {1} {0} -dialect sqlite -sql "SELECT ST_Union(geometry), {2} FROM {0} GROUP BY {2}""".format(input, output, fields)
#     subprocess.call(cmd)


# https://geopandas.org/io.html
def dissolvedGeopandasGPKG(gpkg, namefc, nameoutfc, fields = None, singlepart = False):

    """
    Permet de faire un dissolve avec Geopandas dans un geopackage
    Geopandas ne gere pas encore les valeur Null lors du dissole. C'est pour ca que je rempli
    les valeurs Null pas une string "null"

              Args:
                  gpkg : geopackage
                  namefc : nom de la classe d'entité
                  nameoutfc : nom de la classe d'entité en sortie
                  fields : champ
                  singlepart = faire un multi part ou single part


              Exemple d'appel de la fonction:

              gpkg = r"C:\MrnMicro\temp\test_dissolve_fiona\HISTO_MAJF_2018.gpkg"
              ce ='HISTO_MAJF_2018_Repair'
              out = 'HISTO_MAJF_2018_diss'
              fields = 'CO_TER'
              singlepart = False

              dissolvedGeopandasGPKG(gpkg, ce, out, fields, singlepart)


       """


    if fields is None:
        layer = gpd.read_file(gpkg, layer=namefc)
        gdfu = layer.unary_union
        new = gpd.GeoDataFrame(crs=layer.crs, geometry=[gdfu])
        new.to_file(gpkg, layer=nameoutfc, driver="GPKG")

    else:
        layer = gpd.read_file(gpkg, layer=namefc)
        filled = layer.fillna('null')

        dissolved = filled.dissolve(by=fields, aggfunc = 'last', as_index=False)

        dissolved.to_file(gpkg, layer=nameoutfc, driver="GPKG")

    if singlepart:
        outputSP = nameoutfc+"SP"
        multi2single(gpkg, nameoutfc, outputSP)

    else:
        pass

def remplace_None_par_null(layer):

    with edit(layer):
        for feat in layer.getFeatures():
            for field in feat.fields().names():
                if feat[field] == None:
                    feat[field] = 'null'
            layer.updateFeature(feat)

def remplace_null_par_None(layer):

    with edit(layer):
        for feat in layer.getFeatures():
            for field in feat.fields().names():
                if feat[field] == 'null':
                    feat[field] = None
            layer.updateFeature(feat)

def multi2single(gpkg,ce,outputSP):

    """
   Permet de faire un multipart to single part avec Geopandas

             Args:
                 gpkg : geopackage
                 ce : classe d'entité
                 outputSP : sortie


             Exemple d'appel de la fonction:

             gpkg = r"C:\MrnMicro\temp\test_dissolve_fiona\HISTO_MAJF_2018.gpkg"
             ce ='HISTO_MAJF_2018'
             outputSP = 'HISTO_MAJF_2018_sp'

             multi2single(gpkg,ce,outputSP)

      """

    gpdf = gpd.read_file(gpkg, layer=ce)
    gpdf_singlepoly = gpdf[gpdf.geometry.type == 'Polygon']
    gpdf_multipoly = gpdf[gpdf.geometry.type == 'MultiPolygon']

    for i, row in gpdf_multipoly.iterrows():
        Series_geometries = pd.Series(row.geometry)
        df = pd.concat([gpd.GeoDataFrame(row, crs=gpdf_multipoly.crs).T]*len(Series_geometries), ignore_index=True)
        df['geometry']  = Series_geometries
        gpdf_singlepoly = pd.concat([gpdf_singlepoly, df])

    gpdf_singlepoly.reset_index(inplace=True, drop=True)
    gpdf_singlepoly.to_file(gpkg, layer=outputSP, driver="GPKG")


def dissolvePyqgis(ce, gpkg, nomDissolved, fields):

    """
    Permet de faire un dissolve avec QGIS


              Args:
                  ce : nom de la classe d'entité
                  gpkg : geopackage
                  nomDissolved : nom de la classe d'entité en sortie
                  fields : champ


              Exemple d'appel de la fonction:

              ce = 'input'
              gpkg = r"C:\MrnMicro\temp\test_dissolve_fiona\test_dissolve_fiona.gpkg"
              out = 'dissolved'
              fields = 'DEP_SUR'

              dissolvePyqgis(ce, gpkg, out, fields)


       """


    if isinstance(input, str):
        input = QgsVectorLayer(input, 'ce', 'ogr')
    else:
        input = input

    processing.run("native:dissolve", {'INPUT':ce,'FIELD':fields,
                                       'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg, nomDissolved)})

# def intersect():
#     layergrille_placettes = QgsVectorLayer(grille_placettes, 'lyr', 'ogr')
#     layerrepair_us = QgsVectorLayer(repair_us, 'lyr', 'ogr')
#
#     print("index")
#     QgsSpatialIndex(layergrille_placettes.getFeatures())
#     QgsSpatialIndex(layerrepair_us.getFeatures())
#
#     print("intersect")
#     for f in layergrille_placettes.getFeatures():
#         for a in layerrepair_us.getFeatures():
#             if a.geometry().intersects(f.geometry()):
#                 df_placettes_metadata_us = a.geometry().intersection(f.geometry())





if __name__ == '__main__':

    tempsDebut = time.time()


    reptrav = r"C:\MrnMicro\temp"
    # gpkg = os.path.join(reptrav,"grilleCopie.gpkg")
    gpkg = os.path.join(reptrav,"out.sqlite")

    serviceBD = ServiceBdSqlite(gpkg, mode_spatialite = True)
    serviceBD.sqlite3_etablir_connexion()

    # # Ca crée un dissolve
    # req = "CREATE Table Dissolve as " \
    #       "Select ST_Union(geom) as geometry, CO_TER, SREG_ECO " \
    #       "FROM CO_TER_EAU_INO " \
    #       "GROUP BY CO_TER, SREG_ECO"

    # # Permet d'ajouter dasn la table gpkg_contents du GEOPAKAGE une ligne avec le dissolve fait
    # # Nous allons copier les valeurs de CO_TER_EAU_INO
    # req = """ insert into gpkg_contents select 'Dissolve', data_type, 'Dissolve', description, last_change, min_x, min_y, max_x, max_y, srs_id
    #         from gpkg_contents where table_name = 'CO_TER_EAU_INO'
    #         """
    # serviceBD.executeRequete(req, commit=True)
    #
    # # Permet d'ajouter dasn la table gpkg_geometry_columns du GEOPAKAGE une ligne avec le dissolve fait
    # # Nous allons copier les valeurs de CO_TER_EAU_INO
    # req = """ insert into gpkg_geometry_columns
    #         select 'Dissolve', column_name, geometry_type_name, srs_id, z, m
    #         from gpkg_geometry_columns where table_name = 'CO_TER_EAU_INO'
    #         """
    #
    #
    # serviceBD.executeRequete(req, commit=True)


    # Ca crée un intersect

    # req = "CREATE Table grille_placettes_pente as " \
    #       "Select * " \
    #       "FROM grille_placettes, DDE_20K_CLA_PEN_VUE_SE_1415CE " \
    #       "WHERE st_intersects(grille_placettes.geom, DDE_20K_CLA_PEN_VUE_SE_1415CE.geom)" \
    #
    # req = "CREATE Table grille_placettes_FOR_sub4 as "\
    #       "select a.plac_ID, a.geom, b.GEOC_FOR " \
    #       "from grille_placette_sub a, Peuplement_for_sub b "\
    #       "where ST_Intersects(a.geom , b.geom) " \


    req = "CREATE Table grille_placettes_FOR_TOT as " \
          "select a.plac_ID, a.geom, b.GEOC_FOR " \
          "from grille_placettes a, Peuplement_FOR b " \
          "where ST_Intersects(a.geom , b.geom) " \

    # req = "CREATE Table grille_placettes_FOR_TOT as " \
    #       "Select * " \
    #       "FROM vgpkg_grille_placettes, vgpkg_Peuplement_FOR " \
    #       "WHERE st_intersects(vgpkg_grille_placettes.geom, vgpkg_Peuplement_FOR.geom)" \


    # req = "CREATE Table grille_placettes_FOR_TOT as " \
    #       "select a.fid, a.geom from vgpkg_grille_placette_sub a " \
    #       "INNER JOIN vgpkg_Peuplement_for_sub b " \
    #       "ON (ST_Intersects(a.geom , b.geom))"


    serviceBD.executeRequete(req, commit=True)


    # Permet d'ajouter dasn la table gpkg_contents du GEOPAKAGE une ligne avec le grille_placettes_pente fait
    # Nous allons copier les valeurs de grille_placettes
    req = """ insert into gpkg_contents select 'grille_placettes_FOR_TOT', data_type, 'grille_placettes_FOR_TOT', description, last_change, min_x, min_y, max_x, max_y, srs_id
            from gpkg_contents where table_name = 'grille_placette_sub'
            """
    serviceBD.executeRequete(req, commit=True)

    # Permet d'ajouter dasn la table gpkg_contents du GEOPAKAGE une ligne avec le grille_placettes_pente fait
    # Nous allons copier les valeurs de grille_placettes
    req = """ insert into gpkg_geometry_columns
            select 'grille_placettes_FOR_TOT', column_name, geometry_type_name, srs_id, z, m
            from gpkg_geometry_columns where table_name = 'grille_placette_sub'
            """


    serviceBD.executeRequete(req, commit=True)






    print('afs')



    # x = 1000
    # y = 1000
    # us = r"E:\ADG\SONAR\1415CE\Intrants\US_1415CE.shp"
    # reptrav = r"C:\MrnMicro\temp"
    # grille_tuiles, grille_placettes = grilleSondage(us, reptrav, x, y)

    # input = os.path.join(r"C:\MrnMicro\temp\test_dissolve_fiona","input.shp" )
    # dissolved = os.path.join(r"C:\MrnMicro\temp\test_dissolve_fiona","input_dissolved.shp")
    # fields = 'CO_TER'

    # dissolveGDAL(input, dissolved, fields)

    # gpkg = r"C:\MrnMicro\temp\test_dissolve_fiona\HISTO_MAJF_2018.gpkg"
    # ce ='HISTO_MAJF_2018_Repair'
    # out = 'HISTO_MAJF_2018_diss'
    # fields = 'CO_TER'
    #
    #
    #
    # # gpkg = (r"C:\MrnMicro\temp\test_dissolve_fiona\test_dissolve_fiona.gpkg")
    # # ce = 'input'
    # # out = 'dissolved'
    # # fields = 'DEP_SUR'
    #
    #
    # # dissolveFiona(gpkg, ce, out, fields)
    #
    # dissolvedGeopandasGPKG(gpkg, ce, out, fields, singlepart = False)
    #
    # # dissolvePyqgis(ce, gpkg, out, fields)
    #
    # target_features = r"C:\MrnMicro\temp\test_join\FOR_repair.shp"
    # join_features =r"C:\MrnMicro\temp\test_join\Pente_repair.shp"
    # outfc =r"C:\MrnMicro\temp\test_join\join.shp"
    #
    # spatialJoinLargestOverlap(target_features, join_features, outfc, Pente = True)


    temps_final = time.time()
    temp_tot = round((temps_final - tempsDebut) / 60, 2)
    print("Le temps total de traitement est de : {} minutes".format(temp_tot))




    # pet4 = r"C:\Users\gaudaf\Desktop\Nouveau dossier\pee4_gdb_exportArcMap.shp"
    #
    # # fields = "SUPERFICIE"
    # # with arcpy.da.SearchCursor(pet4, fields) as cursor:
    # #     for row in cursor:
    # #         sup = row[0]
    # #         print(sup)
    #
    # layer = QgsVectorLayer(pet4, 'lyr', 'ogr')
    # field = "SUPERFCIE"
    #
    # features = layer.getFeatures()
    #
    # for ft in features:
    #     attrs = ft.attributes()
    #     print (attrs)
    #






    #
    # tempsDebut = time.time()
    #
    # target_features = r'C:\MrnMicro\temp\For_sub_2.shp'
    # # target_features = 'C:/MrnMicro/temp/ForOri07.gpkg|layername=For_sub_2'
    # # join_features = r'C:\MrnMicro\temp\For_sub_3.shp'
    # # join_features = r'C:\MrnMicro\temp\ecologie_sub.shp'
    # join_features = 'C:/MrnMicro/temp/pente.gpkg|layername=Pente_clip_RepairSP'
    # outfc = r'C:\MrnMicro\temp\join.shp'
    #
    #
    #
    # Pente = True
    # spatialJoinLargestOverlap(target_features, join_features,outfc, Pente)
    #
    #
    # timeTot = time.time()
    # temp_tot = round((timeTot - tempsDebut) / 60, 4)
    # print(temp_tot)


    # https://www.sqlitetutorial.net/
    #
    # # Ce que j’ai essayé pour la mise à jour d’un champ
    # import sqlite3
    # bd1 = r"\\Sef1271a\f1271g\Fdif\Transit\bouj1a\David_Gauthier_aka_Gandalf\ecoulements_bruts_ZM_confiance.gpkg"
    # bd2 = r"\\Sef1271a\f1271g\Fdif\Transit\bouj1a\David_Gauthier_aka_Gandalf\ecoulements_bd2.gpkg"
    # conn = sqlite3.connect(bd2)
    # cursor = conn.cursor()
    #
    # # req = " ".join([
    # #     "UPDATE tbl_copy",
    # #     "SET caract='BLA'"
    # # ])
    #
    #
    # req = "ALTER TABLE tbl_copy ADD BLA varchar(255)"
    #
    # cursor.execute(req)
    # conn.commit()
    # conn.close()

    #
    # import sqlite3
    # bd1 = r"\\Sef1271a\f1271g\Fdif\Transit\bouj1a\David_Gauthier_aka_Gandalf\ecoulements_bruts_ZM_confiance.gpkg"
    # bd2 = r"\\Sef1271a\f1271g\Fdif\Transit\bouj1a\David_Gauthier_aka_Gandalf\ecoulements_bd2.gpkg"
    #
    #
    # # req = " ".join([
    # #     "UPDATE tbl_copy",
    # #     "SET caract='BLA'"
    # # ])
    #
    #
    # # faire la connection avec la bd
    # nomconnection, nomcursor = connec_sqlite(bd1)
    #
    # # req = "ALTER TABLE tbl_copy ADD BLA varchar(12)" # Si je mets varchar(xxxx), QGIS ne voit pas le champ, mais ESRI oui......
    # # req = "ALTER TABLE tbl_copy ADD BLA"
    # req = "UPDATE tableJoin SET col_int = 1"
    #
    # # excecuter la requete
    # executeSQL(nomcursor, req, retour_cursor=True)



    # # Ce que j’ai essayé pour un joint de table
    # bd1 = r"\\Sef1271a\f1271g\Fdif\Transit\bouj1a\David_Gauthier_aka_Gandalf\ecoulements_bruts_ZM_confiance.gpkg"
    # bd2 = r"\\Sef1271a\f1271g\Fdif\Transit\bouj1a\David_Gauthier_aka_Gandalf\ecoulements_bd2.gpkg"
    #
    # conn = sqlite3.connect(bd1)
    # conn.execute("ATTACH DATABASE '" + bd2 + "' AS data2")
    #
    #
    # req = " ".join([
    #     "UPDATE ecoulements as SELECT * from ecoulements",
    #     "LEFT JOIN data2.tbl_copy",
    #     "ON ecoulements.fid = data2.tbl_copy.fid"
    # ])
    #
    # req = "create table tableJoin as select * from ecoulements LEFT JOIN data2.tbl_copy on ecoulements.fid = data2.tbl_copy.fid"

    # conn.execute(req)
    # conn.commit()
    # conn.close()
    #
    #
    #
    # # Pour supprimer une table
    # bd1 = r"\\Sef1271a\f1271g\Fdif\Transit\bouj1a\David_Gauthier_aka_Gandalf\ecoulements_bruts_ZM_confiance.gpkg"
    # conn = sqlite3.connect(bd1)
    # conn.execute("DROP TABLE ecoulements_bruts_ZM")
    # conn.commit()
    # conn.close()



# cmd = r"""ogr2ogr -append -F SQLITE C:\MrnMicro\temp\CLASSI_ECO_IEQM.sqlite C:\MrnMicro\temp\CLASSI_ECO_IEQM.gdb -dsco spatialite=yes -preserve_fid"""
    # subprocess.call(cmd)

    # ce = 'ForS5_fus'

    # from datetime import datetime
    # start=datetime.now()

    # gdb = r"C:\MrnMicro\temp\ForOri07.gdb"
    # gpkg = r"C:\MrnMicro\temp\ForOri07.gpkg"
    #
    # # transfererCeGdbToGeoPackage(ce, gdb, gpkg)


    # ce = r"C:\MrnMicro\temp\ForOri07.gpkg|layername=ForS5_fus"
    # champ = 'ORIGINE'
    # ancienneValeure = 'CPR'
    # nouvelleValeure = 'ttt'

    # transfererCeGdbToGeoPackage(ce, gdb, gpkg)
    #
    # updateCursor(ce, champ, ancienneValeure, nouvelleValeure)

    # ce = r"C:\MrnMicro\temp\ForOri07.gpkg|layername=ForS5_fus"
    # ce = r"C:\MrnMicro\temp\Racc_dif.shp"
    # nomJeuClasseEntite = "TOPO"
    # nomClasseEntite = "ForS5_fus"
    # outGDB = r"C:\MrnMicro\temp\ForOritest.gdb"
    #
    # conversionFormatVersGDB(ce, nomJeuClasseEntite, nomClasseEntite, outGDB)

    # calculerSuperficieAlbers(ce)

    # print(datetime.now()-start)

    # ce = "C:/MrnMicro/temp/Export_Output.shp"
    # ce ="C:/MrnMicro/temp/EcoForS5_Ori_Prov.gdb|layername=EcoForS5_ORI_PROV"
    # selection = 'UUID'
    # # whereclause = " \"GES_CO\" = '{}' ".format("ENEN")
    # whereclause= ' \"OBJECTID\" <= 30'
    # whereclause=' \"VER_PRG\"  = "AIPF2019"'
    # whereclause = ""
    # calculGeocode(ce, selection, whereclause)

    # calculerSuperficie(ce)

    # ce = r"C:\MrnMicro\temp\Appendice2020\sub.shp"
    # nomJeuClasseEntite = "TOPO"
    # nomClasseEntite = "CorS5"
    # outGDB = r"C:\MrnMicro\temp\ForOri.gdb"

    # cmd = r"""ogr2ogr -f "FileGDB" C:\MrnMicro\temp\ForOri.gdb C:\MrnMicro\temp\Racc_dif.shp -lco FEATURE_DATASET=TOPO -lco XYTOLERANCE=0.02 -nln CorS5"""
    # subprocess.call(cmd)
    # conversionFormatVersGDB(ce, nomJeuClasseEntite, nomClasseEntite, outGDB)



    # debut = datetime.datetime.now()
    # # ce = r"C:/MrnMicro/temp/Appendice2020/appendice_qgis.gpkg|layername=territoire_a_traiter"
    # ce = "C:/MrnMicro/temp/Appendice2020/ce_ecofor_territoire_a_taiter_sub1000.shp"
    # ceNarrow =r"C:\MrnMicro\temp\Appendice2020\ce_ecofor_territoire_a_taiterNarrow.shp"

    # print(datetime.datetime.now())

    # identifyNarrowPolygon(ce, ceNarrow)

    # tempsTot = datetime.datetime.now() - debut
    # print("temps pour la durée du traitement: {}".format(tempsTot))

