#!/usr/bin/env python
# coding: UTF-8


"""
Auteur:

# Sonar 2.0
# Auteur initial: Bastien Ferland-Raymond
# Fichier de la refonte initiÃ©e par
# Sylvain Miron et Jean-FranÃ§ois Bourdon
# le 29 janvier 2019

# Outil 1


2021-04-08 - Migration de R en python pour QGIS par David Gauthier

Division des systemes d'information et du pilotage
Direction des inventaires forestiers
Ministere des Forets, de la Faune et des Parcs
Telephone: (418)-627-8669 poste 4322
Sans frais: 1-877-936-7397 poste 4322
Telecopieur: (418-646-1955
Courriel: david.gauthier@mffp.gouv.qc.ca


test de performance avec jeu de donneé SUB :
Couche en memoire avec index spatial : 1,89 minutes
Couche en memoire sans index spatial : 10,8 minutes

Couche gpkg local recré index spatial (meme si on dit que l'index spatial existe) : 2,09 minutes
Couche gpkg local en gardant l'index spatial des couches dans le gpkg : 10,62 minutes

test de performance avec jeu de donneé complet :
Couche en memoire avec index spatial : 16,85 minutes
Couche en memoire sans index spatial :

Couche gpkg local recré index spatial (meme si on dit que l'index spatial existe) :
Couche gpkg local en gardant l'index spatial des couches dans le gpkg :


"""
# Historique:
# 2021-04-08 -Création du script

from qgis.core import *
import processing
from processing.core.Processing import Processing
from qgis.analysis import QgsNativeAlgorithms
import time
import os
from random import randrange
from PyQt5.QtCore import QVariant
import csv
import ogr
import subprocess
import line_profiler
profile = line_profiler.LineProfiler()

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

def calculerChampSelection(layer, nomChamp, value):
    fields = layer.fields()
    indexChamp = fields.indexFromName(nomChamp)

    layer.startEditing()
    for feature in layer.selectedFeatures():
        layer.changeAttributeValue(feature.id(), indexChamp, value)

    layer.commitChanges()


def grilleSondage(us, reptrav,x, y):

    # """
    #  Permet de faire une grille aléatoire de X m par Y m et des placettes avec un pas de 125 metre
    #
    #                us = unité de sondage
    #                reptrav = dossier de travail
    #
    #                x = largeur de la tuile en metres
    #                y = hauteur de la tuile en metres
    #                ESPG (ne pas utiliser si votre classe d'entité (ce) est en 32198) = numéro ESPG de la projection
    #
    #            Exemple d'appel de la fonction:
    #
    #
    #            us = r"C:\MrnMicro\temp\us.shp
    #            reptrav = r"C:\MrnMicro\temp
    #            x = 10000
    #            y = 10000
    #
    #            creerGrille(ce, reptrav,us, x, y)
    #
    #       """



    # Couche
    gpkg = os.path.join(reptrav,"SONAR2_outil_1.gpkg")
    usCopy = "{0}|layername=ceCopy".format(gpkg)
    grille_tuiles = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=grille_tuiles'
    grille_placettes_tmp2 = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=grille_placettes_tmp2'
    grille_placettes = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=grille_placettes'


    # Copier l'US dans un geopackage
    processing.run("gdal:convertformat", {'INPUT':us,
                                          'OPTIONS':'-nln ceCopy','OUTPUT':gpkg})

    # trouver l'extend de l'US
    layer_usCopy = QgsVectorLayer(usCopy, 'lyr', 'ogr')
    ex = layer_usCopy.extent()


    # Permet de faire une grille aléatoire avec 1000 metre
    rand = randrange(1000)-500

    xmin = ex.xMinimum()+ rand
    xmax = ex.xMaximum()+ rand
    ymin = ex.yMinimum()+ rand
    ymax = ex.yMaximum()+ rand
    coords = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)

    ESPG = layer_usCopy.crs().authid()


    print("grille")

    # Créé une grille
    grille = processing.run("native:creategrid", {'TYPE':2,'EXTENT':coords,
                                         'HSPACING':x,'VSPACING':y,'HOVERLAY':0,'VOVERLAY':0,
                                         'CRS':QgsCoordinateReferenceSystem(ESPG),'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("native:createspatialindex", {'INPUT':grille})


    print("repair")

    # reparer les geometrie selon l'OGC
    repair_us = processing.run("native:fixgeometries", {'INPUT':us,
                                                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    processing.run("native:createspatialindex", {'INPUT':repair_us})


    print("grille_tuiles_tmp")

    # Extrire les tuiles avec le contour de l'US
    grille_tuiles_tmp = processing.run("native:extractbylocation", {'INPUT':grille,
                                                'PREDICATE':[0],'INTERSECT':repair_us,
                                                                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("native:createspatialindex", {'INPUT':grille_tuiles_tmp})


    print("grille_placettes_tmp")

    # créé les placettes dasn les tuiles avec une pas de 125m avec une degaements du perimetre de 62,5 metres
    grille_placettes_tmp = processing.run("qgis:regularpoints", {'EXTENT':grille_tuiles_tmp,'SPACING':125,'INSET':62.5,'RANDOMIZE':False,'IS_SPACING':True,
                                          'CRS':QgsCoordinateReferenceSystem(ESPG),'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    processing.run("native:createspatialindex", {'INPUT':grille_placettes_tmp})

    print("grille_placettes_tmp2")


    # Extraire les placettes qui intersect l'US
    processing.run("native:extractbylocation", {'INPUT':grille_placettes_tmp,
                                                'PREDICATE':[0],'INTERSECT':repair_us,
                                                'OUTPUT':'ogr:dbname=\'{0}\' table=\"grille_placettes_tmp2\" (geom) sql='.format(gpkg)})




    processing.run("native:createspatialindex", {'INPUT':grille_placettes_tmp2})

    print("grille_tuiles")
    # Garder les tuiles qui ont des placettes a l'interieur
    processing.run("native:extractbylocation", {'INPUT':grille_tuiles_tmp,'PREDICATE':[0],
                                                'INTERSECT':grille_placettes_tmp2,
                                                'OUTPUT':'ogr:dbname=\'{0}\' table=\"grille_tuiles\" (geom) sql='.format(gpkg)})


    processing.run("native:createspatialindex", {'INPUT':grille_tuiles})

    # ajouter un champ tuile_ID (pour grille_tuiles
    layer = QgsVectorLayer(grille_tuiles, 'lyr', 'ogr')

    champ = QgsField('tuile_ID', QVariant.String, '80')
    layer.dataProvider().addAttributes([champ])
    layer.updateFields()

    # Caluler le champ tuile_ID a l'aide su champ id et je pad avec des 0 (max 8) zeros apres le t avec zfill
    fields = layer.fields()
    indexChamp = fields.indexFromName('tuile_ID')

    layer.startEditing()
    for feature in layer.getFeatures():
        value = "t"+str(feature.id()).zfill(8)
        layer.changeAttributeValue(feature.id(), indexChamp, value)

    layer.commitChanges()

    # Supprimer les champs inutiles de grille_tuiles
    listChamp = ["left","top","right","bottom","id"]

    for li in listChamp:
        supprimerUnChamp(grille_tuiles, li)


    # Si la couche esrt en  memoire le champ se calcul pas. BIZ...
    # ajouter un champ plac_ID (pour grille_placettes)
    layer = QgsVectorLayer(grille_placettes_tmp2, 'lyr', 'ogr')

    champ = QgsField('plac_ID', QVariant.String, '80')
    layer.dataProvider().addAttributes([champ])
    layer.updateFields()

    # Caluler le champ plac_ID a l'aide su champ id et je pad avec des 0 (max 8) zeros apres le p avec zfill
    fields = layer.fields()
    indexChamp = fields.indexFromName('plac_ID')

    layer.startEditing()
    for feature in layer.getFeatures():
        value = "p"+str(feature.id()).zfill(8)
        layer.changeAttributeValue(feature.id(), indexChamp, value)

    layer.commitChanges()


    print("grille_placettes")
    # Faire un intersect avec grille_placettes_tmp2 et grille tuile pour aller chercher le tuile_ID
    processing.run("native:joinattributesbylocation", {'INPUT':grille_placettes_tmp2,'JOIN':grille_tuiles,'PREDICATE':[0],'JOIN_FIELDS':[],
                                                       'METHOD':0,'DISCARD_NONMATCHING':False,'PREFIX':'',
                                                       'OUTPUT':'ogr:dbname=\'{0}\' table=\"grille_placettes\" (geom) sql='.format(gpkg)})

    # Supprimer les champs inutiles de grille_tuiles
    listChamp = ["id","fid_2"]

    for li in listChamp:
        supprimerUnChamp(grille_placettes, li)


    return gpkg,grille_tuiles, grille_placettes,repair_us,ESPG


@profile
def main():

    # Dossier de travail temporaire
    reptrav = r"C:\MrnMicro\temp"


    # ParamÃ¨tres Ã  modifier manuellement ####
    # RÃ©pertoire de travail
    # Il est pris pour acquis que les sous-rÃ©pertoires "Code", "Intrants" et "Extrants" sont dÃ©jÃ  crÃ©Ã©s
    wd = "E:/ADG/SONAR/1415CE"
    # wd_code = "E:/ADG/SONAR/1415CE/Code"

    # NumÃ©ro de l'unitÃ© de sondage
    us = "1415CE"

    # AnnÃ©e de la prise de photo
    # Correspond Ã  ce qui n'apparaÃ®t pas encore dans la carte Ã©coforestiÃ¨re Ã  partir de cette annÃ©e-lÃ 
    annee_photo = 2012

    tempsDebut = time.time() # pour calculer le temps total de l'analyse

    # Sous-rÃ©pertoires de travail
    wd_intrants = os.path.join(wd, "Intrants") # Variable Ã©tait "dos.intrants"
    wd_extrants = os.path.join(wd, "Extrants") # Variable Ã©tait "dos.extrants"

    # Liste des chemins d'accÃ¨s pour les diffÃ©rents intrants
    path_us             = os.path.join(wd_intrants, "US_{0}.shp".format(us))
    # path_PeupForestiers = os.path.join(wd_intrants, "DDE_20K_PEU_FOR_ORI_TRV_VUE_SE_{0}.shp".format(us))



    path_PentesNum      = os.path.join(wd_intrants, "DDE_20K_CLA_PEN_VUE_SE_{0}.shp".format(us))
    path_chemins        = os.path.join(wd_intrants, "CHEMIN_SONAR_{0}.shp".format(us))
    path_geocodes       = os.path.join(wd_intrants, "LIST_GEOC_{0}.shp".format(us))
    path_HydroLin       = os.path.join(wd_intrants, "BDTQ_20K_HYDRO_LO_{0}.shp".format(us))
    path_ParamBuffers   = os.path.join(wd_intrants,  "Parametres", "BUFFER_template.csv")
    path_VoieFerree     = os.path.join(wd_intrants, "BDTQ_20K_VOIE_COMMU_LO_{0}.shp".format(us))
    path_PEP            = os.path.join(wd_intrants, "DDE_20K_PEP_VUE_PE_{0}.shp".format(us))
    path_ponc           = os.path.join(wd_intrants, "BDTQ_20K_BATIM_PO_{0}.shp".format(us))
    path_BatiLin        = os.path.join(wd_intrants, "BDTQ_20K_BATIM_LO_{0}.shp".format(us))
    path_BatiSur        = os.path.join(wd_intrants, "BDTQ_20K_BATIM_SO_{0}.shp".format(us))
    path_EquipPonc      = os.path.join(wd_intrants, "BDTQ_20K_EQUIP_PO_{0}.shp".format(us))
    path_EquipLin       = os.path.join(wd_intrants, "BDTQ_20K_EQUIP_LO_{0}.shp".format(us))
    path_EquipSur       = os.path.join(wd_intrants, "BDTQ_20K_EQUIP_SO_{0}.shp".format(us))
    path_AffecPonc      = os.path.join(wd_intrants, "DDE_UFZ_20K_USAGE_FOR_VUE_PE_{0}.shp".format(us))
    path_AffecLin       = os.path.join(wd_intrants, "DDE_UFZ_20K_USAGE_FOR_VUE_LE_{0}.shp".format(us))
    path_Feux           = os.path.join(wd_intrants, "DDE_20K_FEUX_MAJ_TRV_{0}.shp".format(us))
    path_PertMaj        = os.path.join(wd_intrants, "DDE_20K_AUTRE_PERTU_MAJ_TRV_{0}.shp".format(us))
    path_Interv         = os.path.join(wd_intrants, "INTERVENTION_{0}.shp".format(us))
    path_Planif         = os.path.join(wd_intrants, "PLAN_{0}.shp".format(us))
    path_BufferIn       = os.path.join(wd_intrants, "us_bufin_{0}_2025m.shp".format(us))
    path_masque         = os.path.join(wd_intrants, "MASQUE_{0}.shp".format(us))
    # path_SIP            = os.path.join(wd_intrants, "CFETBFEC_08664_SIP.shp")


    path_PeupForestiers = "E:/ADG/SONAR/1415CE/Intrants/DDE_20K_PEU_FOR_ORI_TRV_VUE_SE_SUBSET_1415CE.shp"
    # path_geocodes = "E:/ADG/SONAR/1415CE/Intrants/LIST_GEOC_SUBSET_1415CE.shp"
    path_ponc = "E:/ADG/SONAR/1415CE/Intrants/BDTQ_20K_BATIM_PO_SUBSET_1415CE.shp"


    # CrÃ©ation des grilles de tuiles et de placettes de 1000m x 1000m
    x = 1000
    y = 1000

    gpkg, grille_tuiles, grille_placettes, repair_us, ESPG = grilleSondage(path_us, reptrav, x, y)


    print("path_PeupForestiersFix")
    # Réparer les geometries de la couche forestieres
    # path_PeupForestiersFix = processing.run("native:fixgeometries", {'INPUT':path_PeupForestiers,
    #                                                              'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("native:fixgeometries", {'INPUT':path_PeupForestiers,
                                            'OUTPUT':'ogr:dbname=\'C:/MrnMicro/temp/SONAR2_outil_1.gpkg\' table=\"PeupForestiersFix\" (geom)'})

    path_PeupForestiersFix = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=PeupForestiersFix'




    processing.run("native:createspatialindex", {'INPUT':path_PeupForestiersFix})
    processing.run("native:createspatialindex", {'INPUT':grille_placettes})

    print("df_placettes_metadata_PeupForestiers")
    # faire le join avec QGIS au lieu de GEOPANDAS
    processing.run("native:joinattributesbylocation", {'INPUT':grille_placettes,'JOIN':path_PeupForestiersFix,
                                                       'PREDICATE':[0],
                                                       'JOIN_FIELDS':[],'METHOD':0,
                                                       'DISCARD_NONMATCHING':False,
                                                       'PREFIX':'',
                                                       'OUTPUT':'ogr:dbname=\'C:/MrnMicro/temp/SONAR2_outil_1.gpkg\' table=\"df_placettes_metadata_PeupForestiers\" (geom)',
                                                       'NON_MATCHING':'TEMPORARY_OUTPUT'})

    # Réparer les geometries de la US
    path_us = processing.run("native:fixgeometries", {'INPUT':path_us,'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    df_placettes_metadata_PeupForestiers = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=df_placettes_metadata_PeupForestiers'




    # Ajouter les valuers de de l'US pour les modes de gestions et autres a l'aide d'un join spatiale
    processing.run("native:joinattributesbylocation", {'INPUT':df_placettes_metadata_PeupForestiers,'JOIN':path_us,
                                                       'PREDICATE':[0],
                                                       'JOIN_FIELDS':[],'METHOD':0,
                                                       'DISCARD_NONMATCHING':False,
                                                       'PREFIX':'',
                                                       'OUTPUT':'ogr:dbname=\'C:/MrnMicro/temp/SONAR2_outil_1.gpkg\' table=\"df_placettes_metadata_PeupForestiers_US\" (geom)',
                                                       'NON_MATCHING':'TEMPORARY_OUTPUT'})

    df_placettes_metadata_PeupForestiers_US = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=df_placettes_metadata_PeupForestiers_US'

    # Supprimer les champs inutiles de df_placettes_metadata_PeupForestiers
    # listChamp = []
    #
    # print("liste champ")
    # for field in layer_df_placettes_metadata_PeupForestiers.fields():
    #     listChamp.append(field.name())
    #
    # listChampAgarder = ["plac_ID","tuile_ID","GEOC_FOR","ORIGINE","CO_TER","ET1_HAUT","CL_PENT"]
    #
    # listChampAsupprimer = list(set(listChamp).difference(listChampAgarder))
    #
    #
    # print("supprime champ")
    #
    # for li in listChampAsupprimer:
    #     supprimerUnChamp(df_placettes_metadata_PeupForestiers, li)

    path_PentesNumFix = processing.run("native:fixgeometries", {'INPUT':path_PentesNum,
                                                                     'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("native:createspatialindex", {'INPUT':path_PentesNumFix})


    print("join_QGIS")
    # faire le join avec QGIS au lieu de GEOPANDAS
    processing.run("native:joinattributesbylocation", {'INPUT':df_placettes_metadata_PeupForestiers_US,'JOIN':path_PentesNumFix,
                                                       'PREDICATE':[0],
                                                       'JOIN_FIELDS':[],'METHOD':1,
                                                       'DISCARD_NONMATCHING':False,
                                                       'PREFIX':'',
                                                       'OUTPUT':'ogr:dbname=\'C:/MrnMicro/temp/SONAR2_outil_1.gpkg\' table=\"df_placettes_metadata_PeupForestiersPenteNum\" (geom)',
                                                       'NON_MATCHING':'TEMPORARY_OUTPUT'})


    # Création de la couche des infranchissables (pente F et S et CO_TER est EAU ou INO
    layer_path_PeupForestiers = QgsVectorLayer(path_PeupForestiers, 'lyr', 'ogr')
    layer_path_PentesNum = QgsVectorLayer(path_PentesNum, 'lyr', 'ogr')

    processing.run("qgis:selectbyexpression", {'INPUT':layer_path_PeupForestiers,
                                               'EXPRESSION':' \"CO_TER\"  IN (\'EAU\', \'INO\')','METHOD':0})

    # copîe
    processing.run("native:saveselectedfeatures", {'INPUT':layer_path_PeupForestiers,
                                                   'OUTPUT':'ogr:dbname=\'{0}\' table=\"CO_TER_EAU_INO\" (geom) sql='.format(gpkg)})

    processing.run("qgis:selectbyexpression", {'INPUT':layer_path_PentesNum,
                                               'EXPRESSION':' \"CL_PENT\"  IN (\'F\', \'S\')','METHOD':0})

    # ajout a la selection courante
    processing.run("native:saveselectedfeatures", {'INPUT':layer_path_PentesNum,
                                                   'OUTPUT':'ogr:dbname=\'{0}\' table=\"PENTNUM_F_S\" (geom) sql='.format(gpkg)})

    CO_TER_EAU_INO = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=CO_TER_EAU_INO'
    PENTNUM_F_S = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=PENTNUM_F_S'

    # Combiner les selections des 2 couches pour faire les infranchissables
    processing.run("native:mergevectorlayers", {'LAYERS':[CO_TER_EAU_INO, PENTNUM_F_S],
                                                'CRS':QgsCoordinateReferenceSystem(ESPG),
                                                'OUTPUT':'ogr:dbname=\'{0}\' table=\"infranchissable\" (geom) sql='.format(gpkg)})

    df_placettes_metadata_PeupForestiersPenteNum = 'C:/MrnMicro/temp/SONAR2_outil_1.gpkg|layername=df_placettes_metadata_PeupForestiersPenteNum'
    layerdf_placettes_metadata_PeupForestiersPenteNum = QgsVectorLayer(df_placettes_metadata_PeupForestiersPenteNum, 'lyr', 'ogr')

    # Ajouter une liste de champ qui sont nécessaires pour les Compilations
    MG_ex = QgsField('MG_ex', QVariant.String, '1')
    UFZ_ex = QgsField('UFZ_ex', QVariant.String, '1')
    PENFRT = QgsField('PENFRT', QVariant.String, '1')
    NONFOR = QgsField('NONFOR', QVariant.String, '1')
    P7M = QgsField('P7M', QVariant.String, '1')
    us_ex = QgsField('us_ex', QVariant.String, '1')
    mesurable = QgsField('mesurable', QVariant.String, '1')

    layerdf_placettes_metadata_PeupForestiersPenteNum.dataProvider().addAttributes([MG_ex,UFZ_ex,PENFRT,NONFOR,P7M,us_ex,mesurable])
    layerdf_placettes_metadata_PeupForestiersPenteNum.updateFields()


    # Mettre la valeur O (oui) ou N (Non) dans le champ MG_ex
    # Selection
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':'\"MODE_GEST\" IN (\'01\', \'09\',\'10\',\'28\')',
                                               'METHOD':0})

    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'MG_ex', 'N')
    layerdf_placettes_metadata_PeupForestiersPenteNum.invertSelection()
    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'MG_ex', 'O')


    # Mettre la valeur O (oui) ou N (Non) dans le champ UFZ_ex
    # Selection
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':'\"IPF_UFZ\" IN (\'01\', \'02\',\'03\',\'04\',\'05\',\'06\')',
                                               'METHOD':0})

    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'UFZ_ex', 'O')
    layerdf_placettes_metadata_PeupForestiersPenteNum.invertSelection()
    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'UFZ_ex', 'N')


    # Mettre la valeur O (oui) ou N (Non) dans le champ PENFRT
    # Selection
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"CL_PENT\" = \'S\'','METHOD':0})
    # Ajout
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"CL_PENT_2\"  IN (\'F\', \'S\')','METHOD':1})

    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'PENFRT', 'O')
    layerdf_placettes_metadata_PeupForestiersPenteNum.invertSelection()
    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'PENFRT', 'N')


    # Mettre la valeur O (oui) ou N (Non) dans le champ NONFOR
    # Selection
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':'\"CO_TER\"  IS NULL',
                                               'METHOD':0})

    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'NONFOR', 'N')
    layerdf_placettes_metadata_PeupForestiersPenteNum.invertSelection()
    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'NONFOR', 'O')


    # Mettre la valeur O (oui) ou N (Non) dans le champ P7M
    # Selection
    # Je met la valeur du champ en entier et non string. Sinon  ca marche pas
    ET1_HAUT_NUM= QgsField('ET1_HAUT_NUM', QVariant.Int, '3')
    layerdf_placettes_metadata_PeupForestiersPenteNum.dataProvider().addAttributes([ET1_HAUT_NUM])
    layerdf_placettes_metadata_PeupForestiersPenteNum.updateFields()

    # # Selectionne de touts les entité
    # layerdf_placettes_metadata_PeupForestiersPenteNum.selectAll()

    print('Calcul')
    # # Je calcul le champ ET1_HAUT_NUM avec les valuers de ET1_HAUT
    field = "ET1_HAUT_NUM"
    expression = "feature['ET1_HAUT']"
    # # Cette focntion prend 80 % du temps total sur un gros jeu de donnée
    calculateAttributes(layerdf_placettes_metadata_PeupForestiersPenteNum, field, expression)

    # fields = layerdf_placettes_metadata_PeupForestiersPenteNum.fields()
    # indexChamp = fields.indexFromName(field)
    # expression = "feature['ET1_HAUT']"
    #
    # layerdf_placettes_metadata_PeupForestiersPenteNum.startEditing()
    # for feature in layerdf_placettes_metadata_PeupForestiersPenteNum.getFeatures():
    #     layerdf_placettes_metadata_PeupForestiersPenteNum.changeAttributeValue(feature.id(), indexChamp, expression)
    #
    # layerdf_placettes_metadata_PeupForestiersPenteNum.commitChanges()
    print('Fin Calcul')




    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"ET1_HAUT_NUM\"  < 7  OR  \"ET1_HAUT_NUM\"  IS NULL',
                                               'METHOD':0})

    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'P7M', 'N')
    layerdf_placettes_metadata_PeupForestiersPenteNum.invertSelection()
    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'P7M', 'O')


    # Faire une liste des geocode de liste geocode provenant des compilations
    layer_path_geocodes = QgsVectorLayer(path_geocodes, 'lyr', 'ogr')

    GEOC_FOR = ""
    for feature in layer_path_geocodes.getFeatures():
        GEOC_FOR += "'" + feature["GEOC_FOR"]+"'"+","

    # faire une selection des GEOCOFOR
    clause = "GEOC_FOR IN ({})".format(GEOC_FOR[:-1])
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':clause,'METHOD':0})


    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'us_ex', 'N')
    layerdf_placettes_metadata_PeupForestiersPenteNum.invertSelection()
    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'us_ex', 'O')


    # Selctionne de toutes les entité
    layerdf_placettes_metadata_PeupForestiersPenteNum.selectAll()


    # Maintenant je vais enlever toutes les VALEURS exclu du plan de sondage champ par champ
    # MG_ex
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"MG_ex\" = \'O\' ','METHOD':2})

    # UFZ_ex
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"UFZ_ex\" = \'O\' ','METHOD':2})

    # PENFRT
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"PENFRT\" = \'O\' ','METHOD':2})

    # NONFOR
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"NONFOR\" = \'O\' ','METHOD':2})

    # P7M
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"P7M\" = \'N\' ','METHOD':2})

    # us_ex
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"us_ex\" = \'O\' ','METHOD':2})


    # Je calcul les placettes mesurables. Par la suite il faut enlever les autres excluions tel les chemin, hydro, batiment ,etc...
    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'mesurable', 'O')
    layerdf_placettes_metadata_PeupForestiersPenteNum.invertSelection()
    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'mesurable', 'N')

   #  Lire le csv pour les paramnetre des buffer
    with open(path_ParamBuffers, 'r') as read_obj:
        csv_reader = csv.reader(read_obj)
        data = list(csv_reader)

    # buffer general
    line2 = data[1]
    bufgene = line2[2]

    # buffer cheminE1
    line4 = data[3]
    cheminE1 = line4[2]

    # buffer cheminE2
    line5 = data[4]
    cheminE2 = line5[2]

    # buffer cheminE3
    line6 = data[5]
    cheminE3 = line6[2]

    # buffer cheminE4
    line7 = data[6]
    cheminE4 = line7[2]

    # buffer cheminE5
    line8 = data[7]
    cheminE5 = line8[2]

    # buffer cheminE6
    line9 = data[8]
    cheminE6 = line9[2]

    # buffer cheminEH
    line10 = data[9]
    cheminEH = line10[2]

    # buffer PEP
    line11 = data[10]
    bufPEP = line11[2]

    # buffer batiment
    line12 = data[11]
    bufbatiment = line12[2]

    # buffer equipement
    line13 = data[12]
    bufequipement = line13[2]

    # buffer affecP
    line14 = data[13]
    bufaffecP = line14[2]

    # buffer affecL
    line15 = data[14]
    bufaffecL = line15[2]


    # Faire les différents buffer
    # Chemins
    listeChemin = ['E1','E2','E3','E4','E5','E6','EH']
    listBufferchemin = [cheminE1,cheminE2,cheminE3,cheminE4,cheminE5,cheminE6,cheminEH]

    lyrpathChemin = QgsVectorLayer(path_chemins, 'lyrchemin', 'ogr')

    i=0
    for li in listeChemin:
        processing.run("qgis:selectbyexpression", {'INPUT':lyrpathChemin,
                                                   'EXPRESSION':' \"SONAR2\"  = \'{0}\''.format(li),'METHOD':0})
        # copier la selection en memoire
        buf = processing.run("native:saveselectedfeatures", {'INPUT': lyrpathChemin, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},)["OUTPUT"]

        # Emprise de 20m plus le buffer general
        buffer_ch =int(listBufferchemin[i])+int(bufgene)

        processing.run("native:buffer", {'INPUT':buf,'DISTANCE':buffer_ch,'SEGMENTS':5,
                                         'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                         'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,(li+"_buf"))})
        i+=1



   # Hydro lineraires
   #  Garder seulement les codes suivants
    lyrpathhydro = QgsVectorLayer(path_HydroLin, 'lypathhydro', 'ogr')
    processing.run("qgis:selectbyexpression", {'INPUT':lyrpathhydro,
                                               'EXPRESSION':' \"HYD_CODE_I\" IN (\'1010050000\',\'1010050000\',\'1020002000\',\'1020050000\','
                                                            '\'1200000000\',\'1200000004\',\'1200050000\',\'1010000000\')','METHOD':0})

    # copier la selection en memoire
    buf = processing.run("native:saveselectedfeatures", {'INPUT': lyrpathhydro, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},)["OUTPUT"]
    processing.run("native:buffer", {'INPUT':buf,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"hydro_buf")})

   # Voie férée
    lyrVoieFerree = QgsVectorLayer(path_VoieFerree, 'lypathhydro', 'ogr')
    processing.run("qgis:selectbyexpression", {'INPUT':lyrVoieFerree,
                                               'EXPRESSION':' \"VCO_DESCR\" =\'Voie ferrée\'','METHOD':0})
    # copier la selection en memoire
    buf = processing.run("native:saveselectedfeatures", {'INPUT': lyrVoieFerree, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},)["OUTPUT"]

    processing.run("native:buffer", {'INPUT':buf,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"Voie_feree_buf")})

   # PEP
    lyrPEP = QgsVectorLayer(path_PEP, 'lypath_PEP', 'ogr')
    processing.run("qgis:selectbyexpression", {'INPUT':lyrPEP,
                                               'EXPRESSION':' \"NO_PE\" IN (\'01\',\'02\')','METHOD':0})
    # copier la selection en memoire
    buf = processing.run("native:saveselectedfeatures", {'INPUT': lyrPEP, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},)["OUTPUT"]

    processing.run("native:buffer", {'INPUT':buf,'DISTANCE':bufPEP,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"PEP_buf")})

   # batiment ponctuel
    lyrbatimentP = QgsVectorLayer(path_ponc, 'lyrbatimentP', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrbatimentP,'DISTANCE':bufbatiment,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"BatimentPonc_buf")})

   # batiment lineaire
    lyrbatimentL = QgsVectorLayer(path_BatiLin, 'lyrbatimentP', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrbatimentL,'DISTANCE':bufbatiment,'SEGMENTS':5,
                                 'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                 'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"BatimentLin_buf")})


    # batiment surfacique
    lyrbatimentS = QgsVectorLayer(path_BatiSur, 'lyrbatimentS', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrbatimentS,'DISTANCE':bufbatiment,'SEGMENTS':5,
                                 'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                 'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"BatimentSurf_buf")})


   # equipement ponc
    lyrpath_EquipPonc = QgsVectorLayer(path_EquipPonc, 'lyrpath_EquipPonc', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrpath_EquipPonc,'DISTANCE':bufequipement,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"EquipementPonc_buf")})


   # equipement lineaire
    lyrpath_EquipLin = QgsVectorLayer(path_EquipLin, 'lyrpath_EquipLin', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrpath_EquipLin,'DISTANCE':bufequipement,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"EquipementLin_buf")})


   # equipement surfacique
    lyrpath_EquipSurf = QgsVectorLayer(path_EquipSur, 'lyrpath_EquipSur', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrpath_EquipSurf,'DISTANCE':bufequipement,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"EquipementSurf_buf")})


   # affection ponctuelles
    lyrpath_AffecPonc = QgsVectorLayer(path_AffecPonc, 'lyrpath_EquipSur', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrpath_AffecPonc,'DISTANCE':bufaffecP,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"AffecPonc_buf")})


    # affectation linéaires
    lyrpath_AffecLin = QgsVectorLayer(path_AffecLin, 'lyrpath_AffecLin', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrpath_AffecLin,'DISTANCE':bufaffecL,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"AffecLin_buf")})


   # couches feux selon l'années de prise de vue. annee_photo sera a changé toutes les années
    lyrpath_Feux = QgsVectorLayer(path_Feux, 'lypath_Feux', 'ogr')

    #TODO valider si le champ est bon et focntionne bien en string, car j'ai un différent de R... Faire un chmap numériue avec FMJ_EXERC
    processing.run("qgis:selectbyexpression", {'INPUT':lyrpath_Feux,
                                           'EXPRESSION':' \"FMJ_EXERC\" >= \'{0}\''.format(annee_photo),'METHOD':0})

    # copier la selection en memoire
    buf = processing.run("native:saveselectedfeatures", {'INPUT': lyrpath_Feux, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},)["OUTPUT"]

    processing.run("native:buffer", {'INPUT':buf,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"Feux_buf")})


   # couches des perturbation selon l'années de prise de vue .annee_photo sera a changé toutes les années
    lyrpath_PertMaj = QgsVectorLayer(path_PertMaj, 'lypath_PertMaj', 'ogr')

    #TODO valider si le champ est bon et focntionne bien en string, car j'ai un différent de R... Faire un chmap numériue avec APM_EXERC
    processing.run("qgis:selectbyexpression", {'INPUT':lyrpath_PertMaj,
                                               'EXPRESSION':' \"APM_EXERC\" >= \'{0}\''.format(annee_photo),'METHOD':0})
    # copier la selection en memoire
    buf = processing.run("native:saveselectedfeatures", {'INPUT': lyrpath_PertMaj, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},)["OUTPUT"]

    processing.run("native:buffer", {'INPUT':buf,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"PertMaj_buf")})


   # couches des intervention des rapports AECA
    lyrpath_Interv = QgsVectorLayer(path_Interv, 'lyrpath_Interv', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrpath_Interv,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"Interv_buf")})


   #  interventions planifiés
    lyrpath_Planif = QgsVectorLayer(path_Planif, 'lyrpath_Planif', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrpath_Planif,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"Planif_buf")})


    print("buf 7m")
   # peup moins de 7m
    # TODO avec cette requete je n'ai pas a faire celle de R qui correcpond a : Va chercher la combinaison origines non égal à NA et ET1_haut égal à NA
    lyrpath_PeupForestiersFix = QgsVectorLayer(path_PeupForestiersFix, 'lypath_PeupForestiersFix', 'ogr')
    ET1_HAUT_NUM= QgsField('ET1_HAUT_NUM', QVariant.Int, '3')
    lyrpath_PeupForestiersFix.dataProvider().addAttributes([ET1_HAUT_NUM])
    lyrpath_PeupForestiersFix.updateFields()

    field = "ET1_HAUT_NUM"
    expression = "feature['ET1_HAUT']"
    calculateAttributes(lyrpath_PeupForestiersFix, field, expression)

    processing.run("qgis:selectbyexpression", {'INPUT':lyrpath_PeupForestiersFix,
                                               'EXPRESSION':' \"ET1_HAUT_NUM\"  < 7  OR  \"ET1_HAUT_NUM\"  IS NULL','METHOD':0})
    # copier la selection en memoire
    buf = processing.run("native:saveselectedfeatures", {'INPUT': lyrpath_PeupForestiersFix, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},)["OUTPUT"]

    processing.run("native:buffer", {'INPUT':buf,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"PM7M_buf")})

    print("buf NONFOR")
   # Non forestier
    lyrpath_PeupForestiersFix = QgsVectorLayer(path_PeupForestiersFix, 'lypath_PeupForestiersFix', 'ogr')
    processing.run("qgis:selectbyexpression", {'INPUT':lyrpath_PeupForestiersFix,
                                               'EXPRESSION':'\"CO_TER\"  IS NOT NULL',
                                               'METHOD':0})

    # copier la selection en memoire
    buf = processing.run("native:saveselectedfeatures", {'INPUT': lyrpath_PeupForestiersFix, 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT},)["OUTPUT"]

    processing.run("native:buffer", {'INPUT':buf,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"Non_FOR_buf")})

    print("buf masque")
   # Masque
    lyrpath_masque = QgsVectorLayer(path_masque, 'lyrpath_masque', 'ogr')
    processing.run("native:buffer", {'INPUT':lyrpath_masque,'DISTANCE':bufgene,'SEGMENTS':5,
                                     'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,
                                     'DISSOLVE':False,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"masque_buf")})
    print("buf aipf")
   # TODO Pas sur de faire la bonne chose
   #  Peuplement nonAIPF. Je vasi utiliser les peuplement NON AIPF pour les exclures du plan de sondage.
    # Pas de buffer a faire meme si j'appele la couche en sorti NONAIPF_buf
    lyrpath_PeupForestiersFix = QgsVectorLayer(path_PeupForestiersFix, 'lypath_PeupForestiersFix', 'ogr')
    processing.run("qgis:selectbyexpression", {'INPUT':lyrpath_PeupForestiersFix,
                                               'EXPRESSION':' \"IN_NAIPF\"  <> \'O\'','METHOD':0})
    # copier la selection
    processing.run("native:saveselectedfeatures", {'INPUT': lyrpath_PeupForestiersFix,
                                                   'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"NONAIPF_buf")})

   #  Liste de tous les buffers dans le geopackage
    layers = [l.GetName() for l in ogr.Open(gpkg)]
    listBuf =[]
    for layer in layers:
        if layer.endswith('_buf'):
            listBuf.append(gpkg+"|layername="+ layer)


    # Buffer_in,path_SIP sont des couches fournies. Il n'y a pas de buffer a faire. Donc je vais l'ajouter dasn ma liste du merge final du buffer
    # listBuf.append(path_SIP)
    listBuf.append(path_BufferIn)


    # Faire une selection par location avec chaque element de la liste avec la "fonction ajouter a la selection courante" 'METHOD':1
    for li in listBuf:
        processing.run("native:selectbylocation", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,'PREDICATE':[0],
                                                                                        'INTERSECT':li,'METHOD':1})

    calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'mesurable', 'N')


    # TODO Supprimer les champs non necessaires
    listChamp = []

    print("liste champ")
    for field in layerdf_placettes_metadata_PeupForestiersPenteNum.fields():
        listChamp.append(field.name())

    listChampAsupprimer = ["fid_2","ORIG_FID", "JOIN_FID", "CO_IMP", "IPF_ZMI", "IPF_UFZ", "MODE_GEST",
                           "DOMANIALIT", "NO_TDA", "NO_AGENCE", "US_FOR",
                           "UPE", "IPF_US", "SONDAGE", "SUPERFICIE_2",
                           "FEUILLET", "IN_SOMMET", "NOG", "SUPERFICIE_3",
                           "INDICATIF", "ID_GEO", "SHAPE_Leng_2","ET1_HAUT_NUM"]

    print("supprime champ")

    for li in listChampAsupprimer:
        supprimerUnChamp(df_placettes_metadata_PeupForestiersPenteNum, li)

    # ## Autre methode en faisant un merge, mais c'est plus long qu'une serie de selection
    # print("merge")
    # # Faire le merge de tous les buffers et autres
    # processing.run("native:mergevectorlayers", {'LAYERS':listBuf,
    #                                             'CRS':None,'OUTPUT':'ogr:dbname=\'{0}\' table=\"{1}\" (geom) sql='.format(gpkg,"Merge_TOTAL_buf")})
    # #
    # # Faire une selection par location du Merge TOTAL su rles placettes potetiel
    # #  afin de toruver les placettes qui tombent a l'interieur du MERGE
    # # Les placettes a l'interieur auront la valeur 'N' dans le champ mesurable, c'est a dire non mesurable
    # Merge_TOTAL_buf = 'C:/MrnMicro/temp/grille.gpkg|layername=Merge_TOTAL_buf'
    # lyrMerge_TOTAL_buf = QgsVectorLayer(Merge_TOTAL_buf, 'lyrMerge_TOTAL_buf', 'ogr')
    #
    # print("selection final")
    # processing.run("native:selectbylocation", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,'PREDICATE':[0],
    #                                            'INTERSECT':lyrMerge_TOTAL_buf,'METHOD':0})
    #
    # calculerChampSelection(layerdf_placettes_metadata_PeupForestiersPenteNum, 'mesurable', 'N')


    # #  Liste de tous les layer dans le geopackage
    # layers = [l.GetName() for l in ogr.Open(gpkg)]
    # li_elem_a_supprimer =[]
    # for layer in layers:
    #     li_elem_a_supprimer.append(layer)
    #
    # li_elem_a_supprimer.remove('df_placettes_metadata_PeupForestiersPenteNum')
    # li_elem_a_supprimer.remove('infranchissable')


    # # Supprimer les layers indesirable
    # for elem in li_elem_a_supprimer:
    #
    #     CREATE_NO_WINDOW = 0x08000000
    #     cmd = r"""ogrinfo {0} -sql "drop table {1}""".format(gpkg,elem)
    #     subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)

    # renommer la couche final des placettes par grille_plac
    
    CREATE_NO_WINDOW = 0x08000000
    cmd = r"""ogrinfo {0} -sql "ALTER TABLE df_placettes_metadata_PeupForestiersPenteNum RENAME TO grille_plac""".format(gpkg)
    subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)

    stream = open(r'C:\MrnMicro\temp\outil1.txt', 'w')
    profile.print_stats(stream=stream)

    temps_final = time.time()
    temp_tot = round((temps_final - tempsDebut) / 60, 2)
    print("Le temps total de traitement est de : {} minutes".format(temp_tot))



if __name__ == '__main__':

    main()

