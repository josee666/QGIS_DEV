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
import sys
import os
import subprocess
import time
import shutil
import os.path
from os import path
import glob
import pandas as pd
import pandas
import csv
from processing.tools import dataobjects




# Pour faire marcher GRASS en StandAlone script
# https://gis.stackexchange.com/questions/296502/pyqgis-scripts-outside-of-qgis-gui-running-processing-algorithms-from-grass-prov
from processing.algs.grass7.Grass7Utils import Grass7Utils
Grass7Utils.checkGrassIsInstalled()

# Chemin ou QGIS est installer
QgsApplication.setPrefixPath(r"C:\MrnMicro\OSGeo4W64\bin", True)

# Créer une reference à QgsApplication,
# Mettre le 2eme argument a faux pour desativer l'interface graphique de QGIS
qgs = QgsApplication([], False)

# initialiser QGIS
qgs.initQgis()

# Initialiser les outils qgis
Processing.initialize()

# sys.path.append(r'C:\MrnMicro\Applic\OSGeo4W64\apps\qgis-ltr\python\plugins\processing\algs\gdal')

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
        print(eSqlite.message)

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

def calculGeocodeOLD(ce, champ, whereclause =''):
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

    # index = len(list(layer.getFeatures()))

    # Si pas de clause
    if whereclause == '':
        feat = layer.getFeatures()
        geocode = []

        for features in feat:

            # coord = (features.geometry().centroid())
            coord = (features.geometry().pointOnSurface())
            geocode.append(str(round(coord.get().x(), 2)) + "+" + str(round(coord.get().y(), 2)))

    else:

        layer.selectByExpression(whereclause)
        selection = layer.selectedFeatures()
        geocode = []
        for features in selection:

            # coord = (features.geometry().centroid())
            coord = (features.geometry().pointOnSurface())
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
        attr_value = {indexChamp: geocode4[i]}  # Nouvelle valeure
        layer_provider.changeAttributeValues({id: attr_value})
        i+=1

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

def spatialJoinLargestOverlap(target_features, join_features):

    # faire des layer
    if isinstance(target_features, str):
        target_layer = QgsVectorLayer(target_features, 'lyr', 'ogr')
    else:
        target_layer = target_features


    # # ajouter un champ SUP1 au target et caluler la superficie
    # champ = QgsField('SUP1', QVariant.Double,'double',100,2 )
    # target_layer.dataProvider().addAttributes([champ])
    # target_layer.updateFields()

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


    if isinstance(join_features, str):
        join_layer = QgsVectorLayer(join_features, 'lyr', 'ogr')
    else:
        join_layer = join_features


    # faire un intersect
    intersect = processing.run("native:intersection", {'INPUT':target_layer,'OVERLAY':join_layer,'INPUT_FIELDS':['OBJECTID','SUP1'],
                                           'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    # calculer la nouvelle superficie des polygones
    sup2 = processing.run("qgis:fieldcalculator", {'INPUT':intersect,'FIELD_NAME':'SUP2','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':2,
                                            'NEW_FIELD':True,'FORMULA':'round($area,2)','OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    # Geopackage temporaire
    gpkg = os.path.join(r"C:\MrnMicro\temp","temp.gpkg")


    # calculer la proportion de la superficie SUP2 et SUP1
    processing.run("qgis:fieldcalculator", {'INPUT':sup2,'FIELD_NAME':'prop','FIELD_TYPE':0,'FIELD_LENGTH':100,
                                                                  'FIELD_PRECISION':2,'NEW_FIELD':False,'FORMULA':'( \"SUP2\"  /  \"SUP1\" ) * 100',
                                                                    'OUTPUT':'ogr:dbname=\'{0}\' table=\"prop\" (geom) sql='.format(gpkg)})


    # classe d'entité contenant les proportion de l'intersect
    prop = "{0}|layername=prop".format(gpkg)
    prop = QgsVectorLayer(prop, 'lyr', 'ogr')


    # faire une liste de l'identifiant unique de la couhe en entrée
    OBJECTID = []

    for feature in prop.getFeatures():
        OBJECTID.append(feature["OBJECTID"])

    # supprimer les doublons de la liste
    OBJECTID = list(dict.fromkeys(OBJECTID))


    # faire une copie de prop et tout efacer pour utiliser comme source vide
    tempLayer = "{0}|layername=tempLayer".format(gpkg)
    processing.run("native:fixgeometries", {'INPUT': prop, 'OUTPUT':'ogr:dbname=\'{0}\' table=\"tempLayer\" (geom) sql='.format(gpkg)})

    Layer = QgsVectorLayer(tempLayer, 'lyr', 'ogr')
    with edit(Layer):
        for feature in Layer.getFeatures():
            Layer.deleteFeature(feature.id())

    # faire une selection en boucle avec la liste sur la couche prop afin d'extraire par la suite les proportion les plus grande par OBJECTID
    for i in OBJECTID:


        # print(i)

        # faire un selection par attribut
        whereclause = ' \"OBJECTID\"={}'.format(i)
        selectByExpression(prop, whereclause, method=0)

        ## Lorsque das un geopackage, les tuiles ne passe pas toutes contrairement a un shp......
        # processing.run("native:saveselectedfeatures", {'INPUT': prop, 'OUTPUT': 'ogr:dbname=\'{0}\' table=\"tuile_{1}\" (geom) sql='.format(gpkg,i)})
        # temp = "{0}|layername=tuile_{1}".format(gpkg,i)

        # temp = r"C:\MrnMicro\temp\tuile_{}.shp".format(i)
        # processing.run("native:saveselectedfeatures", {'INPUT': prop, 'OUTPUT': temp})

        # temp = QgsVectorLayer(temp, 'lyr', 'ogr')

        # temp = processing.run("native:saveselectedfeatures", {'INPUT': prop, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

        # faire une liste avec les proportions

        propMax = []
        for feature in prop.selectedFeatures():
            propMax.append(feature["prop"])

            propMax.sort(reverse=True)

        # # faire une liste avec les proportions
        # for feature in temp.getFeatures():
        #     propMax.append(feature["prop"])
        #
        #     propMax.sort(reverse=True)


        # expression avec la plus grande proportion
        # whereclause = ' \"prop\"={}'.format(propMax[0])


        # selectByExpression(temp, whereclause, method=0)
        #
        # selection = temp.selectedFeatures()
        # for feature in selection:
        #     Layer.dataProvider().addFeatures([feature])
        #     Layer.commitChanges()


        propMaxFinal = str(propMax[0])
        propMaxFinal = (propMaxFinal[:5])

        whereclause = ' \"OBJECTID\"  = {0} AND \"prop\">= {1}'.format(i, propMaxFinal)

        # print(whereclause)
        selectByExpression(prop, whereclause, method=0)

        selection = prop.selectedFeatures()
        for feature in selection:
            Layer.dataProvider().addFeatures([feature])
            Layer.commitChanges()

# 99.99992847029067



        a = 'test'


def spatialJoinLargestOverlapCSV(target_features, join_features):

    # faire des layer
    if isinstance(target_features, str):
        target_layer = QgsVectorLayer(target_features, 'lyr', 'ogr')
    else:
        target_layer = target_features


    # # ajouter un champ SUP1 au target et caluler la superficie
    # champ = QgsField('SUP1', QVariant.Double,'double',100,2 )
    # target_layer.dataProvider().addAttributes([champ])
    # target_layer.updateFields()

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


    if isinstance(join_features, str):
        join_layer = QgsVectorLayer(join_features, 'lyr', 'ogr')
    else:
        join_layer = join_features


    # faire un intersect
    intersect = processing.run("native:intersection", {'INPUT':target_layer,'OVERLAY':join_layer,'INPUT_FIELDS':['OBJECTID','SUP1'],
                                                       'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    # calculer la nouvelle superficie des polygones
    sup2 = processing.run("qgis:fieldcalculator", {'INPUT':intersect,'FIELD_NAME':'SUP2','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':2,
                                                   'NEW_FIELD':True,'FORMULA':'round($area,2)','OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    # Geopackage temporaire
    gpkg = os.path.join(r"C:\MrnMicro\temp","temp.gpkg")


    # calculer la proportion de la superficie SUP2 et SUP1
    processing.run("qgis:fieldcalculator", {'INPUT':sup2,'FIELD_NAME':'prop','FIELD_TYPE':0,'FIELD_LENGTH':100,
                                            'FIELD_PRECISION':2,'NEW_FIELD':False,'FORMULA':'( \"SUP2\"  /  \"SUP1\" ) * 100',
                                            'OUTPUT':'ogr:dbname=\'{0}\' table=\"prop\" (geom) sql='.format(gpkg)})


    # classe d'entité contenant les proportion de l'intersect
    prop = "{0}|layername=prop".format(gpkg)
    prop = QgsVectorLayer(prop, 'lyr', 'ogr')


    # faire une liste de l'identifiant unique de la couhe en entrée
    OBJECTID = []

    for feature in prop.getFeatures():
        OBJECTID.append(feature["OBJECTID"])

    # supprimer les doublons de la liste
    OBJECTID = list(dict.fromkeys(OBJECTID))

    # faire un csv avec prop

    csvProp = r'C:\MrnMicro\temp\prop.csv'
    options_CSV = QgsVectorFileWriter.SaveVectorOptions()
    options_CSV.driverName = "CSV"

    QgsVectorFileWriter.writeAsVectorFormatV2(prop,csvProp , QgsCoordinateTransformContext(), options_CSV)

    csvProp = QgsVectorLayer(csvProp, 'lyr', 'ogr')

    # dossier des csv
    resultCsv = r"C:\MrnMicro\temp\resultcsv"
    os.mkdir(resultCsv)

    # faire une selection en boucle avec la liste sur la couche prop afin d'extraire par la suite les proportion les plus grande par OBJECTID
    for i in OBJECTID:

        # faire un selection par attribut
        whereclause = ' \"OBJECTID\"={}'.format(i)
        selectByExpression(csvProp, whereclause, method=0)


        # faire une liste avec les proportions
        propMax = []
        for feature in csvProp.selectedFeatures():
            propMax.append(feature["prop"])

            propMax.sort(reverse=True)


        propMaxFinal = str(propMax[0])
        propMaxFinal = (propMaxFinal[:5])

        whereclause = ' \"OBJECTID\"= {0} AND \"prop\">= {1}'.format(i, propMaxFinal)
        # whereclause = "select * from csvProp where OBJECTID = {0} ".format(i, propMaxFinal)

        print(whereclause)

        # print(whereclause)
        # selectByExpression(csvProp, whereclause, method=0)
        csvPropTemp = processing.run("native:extractbyexpression", {'INPUT':csvProp,
                                                      'EXPRESSION':whereclause,'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]



        # faire des csv unique que l'on va combiner apres
        csvPropUnique = os.path.join(resultCsv,"{0}.csv").format(i)
        options_CSV = QgsVectorFileWriter.SaveVectorOptions()
        options_CSV.driverName = "CSV"
        QgsVectorFileWriter.writeAsVectorFormatV2(csvPropTemp, csvPropUnique, QgsCoordinateTransformContext(), options_CSV)


    # Combiner les cvs en un seul
    # repertoire des csv
    os.chdir(resultCsv)
    extension = 'csv'
    all_filenames = [i for i in glob.glob('*.{}'.format(extension))]
    #combine all files in the list
    combined_csv = pd.concat([pd.read_csv(f) for f in all_filenames ])
    #export to csv
    csvResult = r"C:\MrnMicro\temp\result.csv"
    combined_csv.to_csv(csvResult, index=False, encoding='utf-8-sig')

def spatialJoinLargestOverlapSQL(target_features, join_features, outfc, Pente = False):


    # faire des layer
    if isinstance(target_features, str):
        target_layer = QgsVectorLayer(target_features, 'lyr', 'ogr')
    else:
        target_layer = target_features


    # # ajouter un champ SUP1 au target et caluler la superficie
    # champ = QgsField('SUP1', QVariant.Double,'double',100,2 )
    # target_layer.dataProvider().addAttributes([champ])
    # target_layer.updateFields()

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


    if isinstance(join_features, str):
        join_layer = QgsVectorLayer(join_features, 'lyr', 'ogr')
    else:
        join_layer = join_features


    # permet d'ignorer les geometries non valide
    context = dataobjects.createContext()
    context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)


    # faire un intersect
    intersect = processing.run("native:intersection", {'INPUT':target_layer,'OVERLAY':join_layer,'INPUT_FIELDS':['OBJECTID','SUP1'],
                                                       'OVERLAY_FIELDS':[],'OVERLAY_FIELDS_PREFIX':'','OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    # calculer la nouvelle superficie des polygones
    sup2 = processing.run("qgis:fieldcalculator", {'INPUT':intersect,'FIELD_NAME':'SUP2','FIELD_TYPE':0,'FIELD_LENGTH':10,'FIELD_PRECISION':2,
                                                   'NEW_FIELD':True,'FORMULA':'round($area,2)','OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    # Geopackage temporaire
    gpkg = os.path.join(r"C:\MrnMicro\temp","temp.gpkg")

    if os.path.exists(gpkg):
        os.remove(gpkg)
    else:
        pass


    # calculer la proportion de la superficie SUP2 et SUP1
    processing.run("qgis:fieldcalculator", {'INPUT':sup2,'FIELD_NAME':'prop','FIELD_TYPE':0,'FIELD_LENGTH':100,
                                            'FIELD_PRECISION':2,'NEW_FIELD':False,'FORMULA':'( \"SUP2\"  /  \"SUP1\" ) * 100',
                                            'OUTPUT':'ogr:dbname=\'{0}\' table=\"prop\" (geom) sql='.format(gpkg)})

    # classe d'entité contenant les proportion de l'intersect
    prop = "{0}|layername=prop".format(gpkg)
    prop = QgsVectorLayer(prop, 'lyr', 'ogr')


    # creer un champ unique qui sera utilisé pour les pentes
    proptemp = processing.run("qgis:fieldcalculator", {'INPUT':prop,
                                            'FIELD_NAME':'New_Id','FIELD_TYPE':2,'FIELD_LENGTH':35,
                                            'FIELD_PRECISION':3,'NEW_FIELD':True,'FORMULA':' concat(  \"OBJECTID\" , \"CL_PENT\" )',
                                                       'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    # faire un csv avec prop
    csvProp = r'C:\MrnMicro\temp\prop.csv'
    options_CSV = QgsVectorFileWriter.SaveVectorOptions()
    options_CSV.driverName = "CSV"

    # Ecrire le CSV
    QgsVectorFileWriter.writeAsVectorFormatV2(proptemp, csvProp , QgsCoordinateTransformContext(), options_CSV)

    # faire une bd sqlite pour faire une requet SQL
    input_files = r"C:\MrnMicro\temp\prop.csv"

    # faire la connection avec la bd
    nomconnection, nomcursor = connec_sqlite(gpkg)

    # copier avec panda le csv dans la bd
    df = pandas.read_csv(input_files)
    df.to_sql("Proportion", nomconnection, if_exists='append', index=False)

    if Pente is False:

            # requete SQL qui permet de grouper les objectid avec la plus grande proportion de superposition. cette valeur est dans le champ prop
            req = "create table resultFinal as select * from Proportion GROUP BY OBJECTID having prop = max(prop)"

            # excecuter la requete
            executeSQL(nomcursor, req, retour_cursor=True)
    else:

        # TODO faire une requete si c'est pour les pentes
        # permet de faire une somme des proportion par classe de pente par OBJECTID
        req = "create table SelectionPente as select *, SUM(prop) SUMProp from Proportion GROUP BY New_id"

        # excecuter la requete
        executeSQL(nomcursor, req, retour_cursor=True)

        # permet de prendre le maximum des proportion par OBECTID afin d'avoir la pente le plus représentée
        req = "create table resultFinal as select * from SelectionPente GROUP BY OBJECTID having SUMProp = max(SUMProp)"

        # excecuter la requete
        executeSQL(nomcursor, req, retour_cursor=True)


    # # faire un csv
    # csvResult = r"C:\MrnMicro\temp\result.csv"
    # # fetchall permet de faire une liste avec l'objet selection
    # rows = selection.fetchall()
    # fp = open(csvResult, 'w')
    # myFile = csv.writer(fp)
    # myFile.writerows(rows)
    # fp.close()
    #
    # # récupérer les noms de colonnes de la table prop.csv
    # with open (csvProp) as csvfile:
    #     csv_reader = csv.reader(csvfile)
    #     csv_headings = next(csv_reader)
    #
    #     # TODO si pente faire ceci:
    #     csv_headings.append("SUM")
    #
    # # met les valeur du csv en memoire
    # with open(csvResult,newline='') as f:
    #     r = csv.reader(f)
    #     data = [line for line in r]
    #
    # # Ajout des noms de colonnes dans le csv final
    # with open(csvResult,'w',newline='') as f:
    #     w = csv.writer(f)
    #     w.writerow(csv_headings)
    #     w.writerows(data)
    #
    #
    #
    # # enleve les lignes vides avec panda
    # csvResultFinal = r"C:\MrnMicro\temp\resultFinal.csv"
    # df = pd.read_csv(csvResult)
    # df.dropna(axis=0, how='all',inplace=True)
    # df.to_csv(csvResultFinal, index=False)
    #
    # # copier le csv dans le geopakage
    # input_files = r"C:\MrnMicro\temp\resultFinal.csv"
    #
    #
    #
    # # faire la connection avec la bd
    # nomconnection, nomcursor = connec_sqlite(gpkg)
    #
    # # copier avec panda le csv dans la bd
    # df = pandas.read_csv(input_files)
    # df.to_sql("resultFinal", nomconnection, if_exists='append', index=False)

    resultaFinalGpkg = "C:/MrnMicro/temp/temp.gpkg|layername=resultFinal"

    # enlever le champ OBJECTID_2 pour que le join ne decalle pas dasn les colonnes...
    result = QgsVectorLayer(resultaFinalGpkg, 'lyr', 'ogr')
    layer_provider = result.dataProvider()
    fields = result.fields()
    indexChamp = fields.indexFromName('OBJECTID_2')  # Index du champ

    print(indexChamp)
    layer_provider.deleteAttributes([indexChamp])
    result.updateFields()


    # faire le join avec le csv et target_layer
    processing.run("native:joinattributestable", {'INPUT':target_layer,'FIELD':'OBJECTID',
                                                  'INPUT_2':result,
                                                  'FIELD_2':'OBJECTID','FIELDS_TO_COPY':[],'METHOD':1,
                                                  'DISCARD_NONMATCHING':False,'PREFIX':'','OUTPUT':outfc})



    os.remove(csvProp)




if __name__ == '__main__':

    tempsDebut = time.time()

    target_features = r'C:\MrnMicro\temp\For_sub_2.shp'
    join_features = r'C:\MrnMicro\temp\Pente_clip_repairSP.shp'
    outfc = r'C:\MrnMicro\temp\join.shp'


    # target_features = "C:/MrnMicro/temp/ForOri07.gdb|layername=ForS5_fus"
    # join_features = "C:/MrnMicro/temp/CARTE_ECOLOGIQUE_5E.gdb|CARTE_ECOLOGIQUE_5E"
    # #
    # outfc = "C:/MrnMicro/temp/temp.gpkg|layername=join"
    # bd = r"C:\MrnMicro\temp\temp.gpkg"
    #
    # # faire la connection avec la bd
    # nomconnection, nomcursor = connec_sqlite(bd)
    #
    # # requete SQL qui permet de grouper les objectid avec la plus grande proportion de superposition. cette valeur est dans le champ prop
    # req = "select * from prop GROUP BY OBJECTID having prop = max(prop)"
    #
    # # excecuter la requete
    # selection = executeSQLite(nomcursor, req, retour_cursor=True)


    spatialJoinLargestOverlapSQL(target_features, join_features,outfc)


    # input_files = r"C:\MrnMicro\temp\prop.csv"
    # bd_sqlite = r"C:\MrnMicro\temp\Proportion.sqlite"
    # nomconnection, nomcursor = connec_sqlite(bd_sqlite)
    # # df = pandas.read_csv(input_files)
    # # df.to_sql("Proportion", nomconnection, if_exists='append', index=False)
    #
    # req = "CREATE TABLE test"
    # selection = executeSQLite(nomcursor, req, retour_cursor=True)

    # req = "INSERT INTO Proportion.TABLE SELECT * FROM resultat.TABLE"
    # executeSQLite(selection, req, retour_cursor=True)




    # liste = list(selection.fetchall())
    # print(liste)


    # executeSQLite(selection, req, retour_cursor=True)







    # layer = QgsVectorLayer(target_features, 'lyr', 'ogr')
    # options_CSV = QgsVectorFileWriter.SaveVectorOptions()
    # options_CSV.driverName = "CSV"
    #
    # QgsVectorFileWriter.writeAsVectorFormatV2(layer, r'C:\MrnMicro\temp\xyz.csv', QgsCoordinateTransformContext(), options_CSV)

    timeTot = time.time()
    temp_tot = round((timeTot - tempsDebut) / 60, 4)
    print(temp_tot)

    # initialiserQGIS()

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

    # x = 100000
    # y = 100000
    # ce = "C:/MrnMicro/temp/Appendice2020/ce_ecofor_territoire_a_taiter.shp"
    # reptrav = r"C:\MrnMicro\temp"
    # separerJeuClasseEntite(ce, reptrav, x, y)