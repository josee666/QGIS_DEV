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


Migration de R en python pour QGIS par David Gauthier

Division des systemes d'information et du pilotage
Direction des inventaires forestiers
Ministere des Forets, de la Faune et des Parcs
Telephone: (418)-627-8669 poste 4322
Sans frais: 1-877-936-7397 poste 4322
Telecopieur: (418-646-1955
Courriel: david.gauthier@mffp.gouv.qc.ca

"""
# Historique:
# 2021-04-08 -Création du script

from qgis.core import *
import processing
from processing.core.Processing import Processing
from qgis.analysis import QgsNativeAlgorithms
import time
import os
import geopandas as gpd
from geopandas import GeoDataFrame
import pandas as pd
from random import randrange
from PyQt5.QtCore import QVariant
from osgeo import ogr
from QGIS_commun import supprimerUnChamp
from geopandas.tools import sjoin, overlay


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


    gpkg = os.path.join(reptrav,"grille.gpkg")
    usCopy = "{0}|layername=ceCopy".format(gpkg)
    # repair_us = 'C:/MrnMicro/temp/grille.gpkg|layername=repair_us'
    # grille = 'C:/MrnMicro/temp/grille.gpkg|layername=grille'
    # grille_tuiles_tmp = 'C:/MrnMicro/temp/grille.gpkg|layername=grille_tuiles_tmp'
    grille_tuiles = 'C:/MrnMicro/temp/grille.gpkg|layername=grille_tuiles'
    # grille_placettes_tmp = 'C:/MrnMicro/temp/grille.gpkg|layername=grille_placettes_tmp'
    grille_placettes_tmp2 = 'C:/MrnMicro/temp/grille.gpkg|layername=grille_placettes_tmp2'
    grille_placettes = 'C:/MrnMicro/temp/grille.gpkg|layername=grille_placettes'


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

    # Faire une grille de X x Y avec l'extend
    # processing.run("native:creategrid", {'TYPE':2,'EXTENT':coords,
    #                                      'HSPACING':x,'VSPACING':y,'HOVERLAY':0,'VOVERLAY':0,
    #                                      'CRS':QgsCoordinateReferenceSystem(ESPG),'OUTPUT':'ogr:dbname=\'{0}\' table=\"grille\" (geom) sql='.format(gpkg)})


    print("grille")
    grille = processing.run("native:creategrid", {'TYPE':2,'EXTENT':coords,
                                         'HSPACING':x,'VSPACING':y,'HOVERLAY':0,'VOVERLAY':0,
                                         'CRS':QgsCoordinateReferenceSystem(ESPG),'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("native:createspatialindex", {'INPUT':grille})


    # Réparer les geometries
    # processing.run("native:fixgeometries", {'INPUT':us,
    #                                         'OUTPUT':'ogr:dbname=\'{0}\' table=\"repair_us\" (geom) sql='.format(gpkg)})


    print("repair")
    repair_us = processing.run("native:fixgeometries", {'INPUT':us,
                                                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    processing.run("native:createspatialindex", {'INPUT':repair_us})

    # Extraire la grille qui intersect seulement l'US
    # processing.run("native:extractbylocation", {'INPUT':grille,
    #                                             'PREDICATE':[0],'INTERSECT':repair_us,
    #                                             'OUTPUT':'ogr:dbname=\'{0}\' table=\"grille_tuiles_tmp\" (geom) sql='.format(gpkg)})

    print("grille_tuiles_tmp")
    grille_tuiles_tmp = processing.run("native:extractbylocation", {'INPUT':grille,
                                                'PREDICATE':[0],'INTERSECT':repair_us,
                                                                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("native:createspatialindex", {'INPUT':grille_tuiles_tmp})

    # Faire les placettes avec un pas de 125m
    # processing.run("qgis:regularpoints", {'EXTENT':grille_tuiles_tmp,'SPACING':125,'INSET':62.5,'RANDOMIZE':False,'IS_SPACING':True,
    #                                       'CRS':QgsCoordinateReferenceSystem(ESPG),'OUTPUT':'ogr:dbname=\'{0}\' table=\"grille_placettes_tmp\" (geom) sql='.format(gpkg)})


    print("grille_placettes_tmp")
    grille_placettes_tmp = processing.run("qgis:regularpoints", {'EXTENT':grille_tuiles_tmp,'SPACING':125,'INSET':62.5,'RANDOMIZE':False,'IS_SPACING':True,
                                          'CRS':QgsCoordinateReferenceSystem(ESPG),'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]


    processing.run("native:createspatialindex", {'INPUT':grille_placettes_tmp})

    print("grille_placettes_tmp2")

    # # Extraire les placettes qui intersect l'US
    # processing.run("native:extractbylocation", {'INPUT':grille_placettes_tmp,
    #                                             'PREDICATE':[0],'INTERSECT':repair_us,
    #                                             'OUTPUT':'ogr:dbname=\'{0}\' table=\"grille_placettes_tmp2\" (geom) sql='.format(gpkg)})



    # grille_placettes_tmp2 = processing.run("native:extractbylocation", {'INPUT':grille_placettes_tmp,
    #                                             'PREDICATE':[0],'INTERSECT':repair_us,
    #                                                                     'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

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


def main():

    # Dossier de travail temporaire
    reptrav = r"C:\MrnMicro\temp"


    # ParamÃ¨tres Ã  modifier manuellement ####
    # RÃ©pertoire de travail
    # Il est pris pour acquis que les sous-rÃ©pertoires "Code", "Intrants" et "Extrants" sont dÃ©jÃ  crÃ©Ã©s
    wd = "E:/ADG/SONAR/1415CE"
    wd_code = "E:/ADG/SONAR/1415CE/Code"

    # NumÃ©ro de l'unitÃ© de sondage
    us = "1415CE"

    # AnnÃ©e de la prise de photo
    # Correspond Ã  ce qui n'apparaÃ®t pas encore dans la carte Ã©coforestiÃ¨re Ã  partir de cette annÃ©e-lÃ 
    annee_photo = "2012"

    # Pour des fins de dÃ©veloppement, la graine du gÃ©nÃ©rateur de nombres alÃ©atoire est fixÃ©e
    #seed <- .Random.seed # Lors de la phase de production, la valeur pourrait Ãªtre conservÃ©e de cette faÃ§on pour fins de dÃ©bogage
    # set.seed(99999)
    tempsDebut = time.time() # pour calculer le temps total de l'analyse


    # Sous-rÃ©pertoires de travail
    wd_intrants = os.path.join(wd, "Intrants") # Variable Ã©tait "dos.intrants"
    wd_extrants = os.path.join(wd, "Extrants") # Variable Ã©tait "dos.extrants"

    # Liste des chemins d'accÃ¨s pour les diffÃ©rents intrants
    path_us             = os.path.join(wd_intrants, "US_{0}.shp".format(us))
    path_PeupForestiers = os.path.join(wd_intrants, "DDE_20K_PEU_FOR_ORI_TRV_VUE_SE_{0}.shp".format(us))



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
    path_BufferIn       = os.path.join(wd_intrants, "us_bufin_{0}.shp".format(us))
    path_masque         = os.path.join(wd_intrants, "MASQUE_{0}.shp".format(us))
    path_SIP            = os.path.join(wd_intrants, "CFETBFEC_08664_SIP.shp")


    # seulement pour le dÃ©veloppement et Ã©viter ainsi de charger une couche trop grande
    # qui prend des dizaines de minutes Ã  charger
    # path_PeupForestiers = "E:/ADG/SONAR/1415CE/Intrants/DDE_20K_PEU_FOR_ORI_TRV_VUE_SE_SUBSET_1415CE.shp"
    # path_geocodes = "E:/ADG/SONAR/1415CE/Intrants/LIST_GEOC_SUBSET_1415CE.shp"
    # path_ponc = "E:/ADG/SONAR/1415CE/Intrants/BDTQ_20K_BATIM_PO_SUBSET_1415CE.shp"



    ## Accronymes Ã  saveur forestiÃ¨re
    # ZAMI  => Zones d'application des modalitÃ©s d'intervention
    # US    => UnitÃ© de sondage
    # UA    => UnitÃ© d'amÃ©nagement
    # UFZ   => Usage forestier
    # MTM   => Mercator transverse modifiÃ©e


    # CrÃ©ation des grilles de tuiles et de placettes
    x = 1000
    y = 1000

    gpkg, grille_tuiles, grille_placettes, repair_us, ESPG = grilleSondage(path_us, reptrav, x, y)

    # BLOC DE VALIDATION
    # ###############################################################################
    # Jointure spatiale entre les placettes potentielles et l'unitÃ© de sondage
    # afin de leur attribuer les informations liÃ©es aux modes de gestion, aux affectations
    # et aux zones d'application des modalitÃ©s d'intervention (ZAMI)

    # dfgrille_placettes = gpd.read_file(gpkg, layer="grille_placettes")
    # dfrepair_us = gpd.read_file(gpkg, layer="repair_us")
    # df_placettes_metadata_us = sjoin(dfgrille_placettes, dfrepair_us, how="left", op='intersects')
    # df_placettes_metadata_us.to_file(gpkg, layer="df_placettes_metadata_us", driver="GPKG")
    #
    # # Conservation des champs mentionnÃ©s uniquement (retrait des champs superflus)
    # df_placettes_metadata_us <- df_placettes_metadata_us[,c("US_FOR", "MODE_GEST", "IPF_UFZ", "SONDAGE")]
    #
    # #cmtJFB Modifier la section pour rendre plus robuste selon le choix
    # # On devra modifier la sÃ©lection, si on fait une agence, on veut "20", et Ã  anticosti on veut "05"
    #
    # #cmtJFB Regarder si je ne pourrais pas conserver les exclusions en valeurs boolÃ©ennes
    # # Identification des placettes tombant Ã  l'extÃ©rieur d'un territoire constituant une unitÃ© d'amÃ©nagement (UA)
    # # oÃ¹ 0 = inclus et 1 = exclus
    # vec_exclus_ModeGestion <- as.numeric(!(df_placettes_metadata_us$MODE_GEST %in% c("01", "09", "10", "28")))
    #
    # # Identification des placettes tombant dans un territoire ayant un usage forestier (IPF_UFZ) spÃ©cifique
    # # oÃ¹ 0 = inclus et 1 = exclus   #cmtJFB Obtenir une liste des codes de correspondance et que veut dire IPF?
    # vec_exclus_UsageForestier <- as.numeric(df_placettes_metadata_us$IPF_UFZ %in% c("01", "02", "03", "04", "05", "06"))
    #
    # vec_bool_inclus <- !as.logical(vec_exclus_ModeGestion + vec_exclus_UsageForestier)
    # vec_bool_sondage <- ifelse(df_placettes_metadata_us$SONDAGE == "N", FALSE, TRUE)
    #
    # # Validation que les zones Ã  sonder correspondent bien. #cmtJFB Ã reformuler, pas sÃ»r de comprendre?
    # if (!all(vec_bool_inclus == vec_bool_sondage)){
    # message(paste0("Le champ 'SONDAGE' crÃ©Ã© par R n'est pas identique Ã  celui fourni dans la couche us_XXXXX.shp.",
    # "\n Veuillez vÃ©rifier la liste des modes de gestion, affectations et ZAMI exclus."))
    # }
    ##################################################################################################################
    # FIN


    # # # Jointure spatiale entre les placettes potentielles et la couche forestiÃ¨re
    # # df_placettes_metadata_PeupForestiers <- grille_placettes %over% spdf_PeupForestiers

    # # GEOPOANDAS JOIN SPATIAL
    # dfgrille_placettes = gpd.read_file(gpkg, layer="grille_placettes")
    # dfpath_PeupForestiers = gpd.read_file(path_PeupForestiers)
    # df_placettes_metadata_PeupForestiers = sjoin(dfgrille_placettes, dfpath_PeupForestiers, how="inner", op='intersects')
    # df_placettes_metadata_PeupForestiers.to_file(gpkg, layer="df_placettes_metadata_PeupForestiers", driver="GPKG")

    ## Conservation des variables dÃ©sirÃ©es uniquement
    # spdf_PeupForestiers@data <- spdf_PeupForestiers@data[,c("GEOC_FOR","ORIGINE","CO_TER","ET1_HAUT","CL_PENT")]


    print("path_PeupForestiersFix")
    # Réparer les geometries de la couche forestieres
    path_PeupForestiersFix = processing.run("native:fixgeometries", {'INPUT':path_PeupForestiers,
                                                                 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("native:createspatialindex", {'INPUT':path_PeupForestiersFix})
    processing.run("native:createspatialindex", {'INPUT':grille_placettes})

    print("df_placettes_metadata_PeupForestiers")
    # faire le join avec QGIS au lieu de GEOPANDAS
    processing.run("native:joinattributesbylocation", {'INPUT':grille_placettes,'JOIN':path_PeupForestiersFix,
                                                       'PREDICATE':[0],
                                                       'JOIN_FIELDS':[],'METHOD':1,
                                                       'DISCARD_NONMATCHING':False,
                                                       'PREFIX':'',
                                                       'OUTPUT':'ogr:dbname=\'C:/MrnMicro/temp/grille.gpkg\' table=\"df_placettes_metadata_PeupForestiers\" (geom)',
                                                       'NON_MATCHING':'TEMPORARY_OUTPUT'})

    # processing.run("native:intersection", {'INPUT':grille_placettes,'OVERLAY':path_PeupForestiersFix,
    #                                        'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],
    #                                        'OVERLAY_FIELDS_PREFIX':'',
    #                                        'OUTPUT':'ogr:dbname=\'C:/MrnMicro/temp/grille.gpkg\' table=\"df_placettes_metadata_PeupForestiers\" (geom)'})



    df_placettes_metadata_PeupForestiers = 'C:/MrnMicro/temp/grille.gpkg|layername=df_placettes_metadata_PeupForestiers'


    # Supprimer les champs inutiles de df_placettes_metadata_PeupForestiers
    layer_df_placettes_metadata_PeupForestiers = QgsVectorLayer(df_placettes_metadata_PeupForestiers, 'lyr', 'ogr')

    listChamp = []

    print("liste champ")
    for field in layer_df_placettes_metadata_PeupForestiers.fields():
        listChamp.append(field.name())

    listChampAgarder = ["plac_ID","tuile_ID","GEOC_FOR","ORIGINE","CO_TER","ET1_HAUT","CL_PENT"]

    listChampAsupprimer = list(set(listChamp).difference(listChampAgarder))


    print("supprime champ")
    layer_provider = layer_df_placettes_metadata_PeupForestiers.dataProvider()
    fields = layer_df_placettes_metadata_PeupForestiers.fields()

    for li in listChampAsupprimer:

        print(li)
        indexChamp = fields.indexFromName(li)  # Index du champ
        layer_provider.deleteAttributes([indexChamp])

    # layer_df_placettes_metadata_PeupForestiers.updateFields()
    layer_df_placettes_metadata_PeupForestiers.commitChanges()

        # supprimerUnChamp(df_placettes_metadata_PeupForestiers, li)


    # print("geopandas")
    # # GEOPOANDAS JOIN SPATIAL
    # # Joindre les pente numérique avec les placettes (df_placettes_metadata_PeupForestiers)
    # df_placettes_metadata_PeupForestiers = gpd.read_file(gpkg, layer="df_placettes_metadata_PeupForestiers")
    # dfpath_PentesNum = gpd.read_file(path_PentesNum)
    # df_placettes_metadata_PeupForestiersPenteNum = sjoin(df_placettes_metadata_PeupForestiers, dfpath_PentesNum, how="inner", op='intersects')
    # df_placettes_metadata_PeupForestiersPenteNum.to_file(gpkg, layer="df_placettes_metadata_PeupForestiersPenteNum", driver="GPKG")


    path_PentesNumFix = processing.run("native:fixgeometries", {'INPUT':path_PentesNum,
                                                                     'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT})["OUTPUT"]

    processing.run("native:createspatialindex", {'INPUT':path_PentesNumFix})


    print("join_QGIS")
    # faire le join avec QGIS au lieu de GEOPANDAS
    processing.run("native:joinattributesbylocation", {'INPUT':df_placettes_metadata_PeupForestiers,'JOIN':path_PentesNumFix,
                                                       'PREDICATE':[0],
                                                       'JOIN_FIELDS':[],'METHOD':1,
                                                       'DISCARD_NONMATCHING':False,
                                                       'PREFIX':'',
                                                       'OUTPUT':'ogr:dbname=\'C:/MrnMicro/temp/grille.gpkg\' table=\"df_placettes_metadata_PeupForestiersPenteNum\" (geom)',
                                                       'NON_MATCHING':'TEMPORARY_OUTPUT'})


    # processing.run("native:createspatialindex", {'INPUT':df_placettes_metadata_PeupForestiers})
    #
    # processing.run("native:intersection", {'INPUT':df_placettes_metadata_PeupForestiers,'OVERLAY':path_PentesNumFix,
    #                                        'INPUT_FIELDS':[],'OVERLAY_FIELDS':[],
    #                                        'OVERLAY_FIELDS_PREFIX':'',
    #                                        'OUTPUT':'ogr:dbname=\'C:/MrnMicro/temp/grille.gpkg\' table=\"df_placettes_metadata_PeupForestiersPenteNum\" (geom)'})
    #
    #



# # DÃ©termination des placettes forestiÃ¨res
    # #cmtJFB Pourquoi CO_TER est Ã  NA lorsque c'est forestier?
    # vec_bool_NonForestier <- !is.na(df_placettes_metadata_PeupForestiers[,"CO_TER"])
    #
    # # DÃ©termination des placettes de >7m
    # vec_bool_Plus7m <- as.numeric(df_placettes_metadata_PeupForestiers[,"ET1_HAUT"]) >= 7
    # vec_bool_Plus7m[is.na(vec_bool_Plus7m)] <- FALSE
    #
    # # DÃ©termination des placettes qui ne sont pas sur des sommets
    # vec_bool_Sommet <- df_placettes_metadata_PeupForestiers[,"CL_PENT"] == "S"
    # vec_bool_Sommet[is.na(vec_bool_Sommet)] <- FALSE


    # Création de la couche des infranchissables (pente F et S et CO_TER est EAU ou INO
    layer_path_PeupForestiers = QgsVectorLayer(path_PeupForestiers, 'lyr', 'ogr')
    layer_path_PentesNum = QgsVectorLayer(path_PentesNum, 'lyr', 'ogr')

    processing.run("qgis:selectbyexpression", {'INPUT':layer_path_PeupForestiers,
                                               'EXPRESSION':' \"CO_TER\"  IN (\'EAU\', \'INO\')','METHOD':0})

    processing.run("native:saveselectedfeatures", {'INPUT':layer_path_PeupForestiers,
                                                   'OUTPUT':'ogr:dbname=\'{0}\' table=\"CO_TER_EAU_INO\" (geom) sql='.format(gpkg)})

    processing.run("qgis:selectbyexpression", {'INPUT':layer_path_PentesNum,
                                               'EXPRESSION':' \"CL_PENT\"  IN (\'F\', \'S\')','METHOD':0})

    processing.run("native:saveselectedfeatures", {'INPUT':layer_path_PentesNum,
                                                   'OUTPUT':'ogr:dbname=\'{0}\' table=\"PENTNUM_F_S\" (geom) sql='.format(gpkg)})

    CO_TER_EAU_INO = 'C:/MrnMicro/temp/grille.gpkg|layername=CO_TER_EAU_INO'
    PENTNUM_F_S = 'C:/MrnMicro/temp/grille.gpkg|layername=PENTNUM_F_S'


    # Combiner les 2 couches pour faire les infranchissables
    processing.run("native:mergevectorlayers", {'LAYERS':[CO_TER_EAU_INO, PENTNUM_F_S],
                                                'CRS':QgsCoordinateReferenceSystem(ESPG),
                                                'OUTPUT':'ogr:dbname=\'{0}\' table=\"infranchissable\" (geom) sql='.format(gpkg)})

    # Séries de selection afin de garder les placettes réellement sondable
    df_placettes_metadata_PeupForestiersPenteNum = 'C:/MrnMicro/temp/grille.gpkg|layername=df_placettes_metadata_PeupForestiersPenteNum'
    layerdf_placettes_metadata_PeupForestiersPenteNum = QgsVectorLayer(df_placettes_metadata_PeupForestiersPenteNum, 'lyr', 'ogr')


    # Selection des CO_TER non null
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':'\"CO_TER\"  IS NULL','METHOD':0})

    # Enlever de la selection les etage <7 m et NULL
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"ET1_HAUT\"  < 7  OR  \"ET1_HAUT\"  IS NULL',
                                               'METHOD':2})

    # Enlever de la selection les PENTES S venant de la carte originale
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                               'EXPRESSION':' \"CL_PENT_left\" = \'S\'','METHOD':2})


    # Enlever de la selection les PENTES F et S venant de la couche de pente numérique
    processing.run("qgis:selectbyexpression", {'INPUT':layerdf_placettes_metadata_PeupForestiersPenteNum,
                                                                  'EXPRESSION':' \"CL_PENT_right\"  IN (\'F\', \'S\')','METHOD':2})

    print("fin")
    # ## Gestion des pentes fortes
    # # C hargement de la couche de pentes numÃ©riques polygonales
    # spdf_PentesNum <- load_intrant(path_PentesNum, crs_us)
    #
    # # Conservation des pentes "F" et "S" uniquement
    # spdf_PentesNum <- spdf_PentesNum[spdf_PentesNum@data[,"CL_PENT"] %in% c("F", "S"),]

    #
    # # RenumÃ©rotation des polygones restants
    # spdf_PentesNum <- spChFIDs(spdf_PentesNum, paste("p", 1:nrow(spdf_PentesNum), sep="_"))
    #
    # # Jointure spatiale entre les placettes potentielles et les pentes numÃ©riques polygonales
    # df_placettes_metadata_PentesNum <- grille_placettes %over% spdf_PentesNum
    # vec_bool_PentesFortes <- df_placettes_metadata_PentesNum[,"CL_PENT"] %in% c("F", "S")
    # vec_bool_PentesFortes[is.na(vec_bool_PentesFortes)] <- FALSE
    #
    # # RÃ©Ã©criture des attributs aux placettes potentielles
    # grille_placettes@data <- data.frame(grille_placettes@data,
    #                                     GEOC_FOR   = df_placettes_metadata_PeupForestiers[,"GEOC_FOR"],
    # MODE_GEST = df_placettes_metadata_us[,"MODE_GEST"],
    # IPF_UFZ   = df_placettes_metadata_us[,"IPF_UFZ"],
    # MG_ex     = vec_exclus_ModeGestion,
    #             UFZ_ex    = vec_exclus_UsageForestier,
    #                         PENFRT    = as.numeric(vec_bool_PentesFortes),
    #                                        NONFOR    = as.numeric(vec_bool_NonForestier),
    #                                                       P7M       = as.numeric(vec_bool_Plus7m),
    #                                                                      SOMM      = as.numeric(vec_bool_Sommet),
    #                                                                                     stringsAsFactors = FALSE)
    #
    # # Extraction des infranchissables de la couche forestiÃ¨re en raison du code de terrain
    # vec_bool_inf <- spdf_PeupForestiers$CO_TER %in% c("EAU", "INO")
    # spdf_inf_ct <- spdf_PeupForestiers[vec_bool_inf,]
    #
    # # RenumÃ©rotation des polygones infranchissables en raison du code de terrain
    # spdf_inf_ct <- spChFIDs(spdf_inf_ct, paste("ct", 1:nrow(spdf_inf_ct), sep="_"))
    #
    # #cmtJFB Je ne comprends pas pourquoi il y a un nÃ©gatif, pour retirer tous les attributs? Si oui, Ã§a pourrait
    # #       Ãªtre fait plus proprement
    # spdf_inf_ct@data <- data.frame(spdf_inf_ct@data[, -(1:ncol(spdf_inf_ct@data))],
    # type = "codeterrain",
    #        stringsAsFactors = FALSE)
    #
    # # Copie des polygones de pentes
    # #cmtJFB Je ne comprends pas pourquoi il y a un nÃ©gatif, pour retirer tous les attributs? Si oui, Ã§a pourrait
    # #       Ãªtre fait plus proprement
    # spdf_inf_pentes <- spdf_PentesNum
    # spdf_inf_pentes@data <- data.frame(spdf_inf_pentes@data[,-(1:ncol(spdf_inf_pentes@data))],
    # type = "pente",
    #        stringsAsFactors = FALSE)
    #
    # # Combinaison des infranchissables de code de terrain et de pentes
    # spdf_inf_combine <- rbind(spdf_inf_ct, spdf_inf_pentes)
    #
    # # Identification des polygones contiguÃ«s
    # #cmtJFB NÃ©cessaire de clarifier ce qui se passe vraiment
    # ls_inf_contigues <- spdep::poly2nb(spdf_inf_combine)
    # vec_inf_index_contigues <- spdep::n.comp.nb(ls_inf_contigues)$comp.id
    #
    # # Union des couches infranchissables
    # #cmtJFB NÃ©cessaire de clarifier ce qui se passe vraiment, car ce n'est une union vraiment, car
    # #       il y a encore des superpositions entre les polygones
    # #cmtJFB writeOGR(spdf_inf_combine, "F:/SONAR_dev", "union", driver="ESRI Shapefile")
    # #cmtJFB retirer le [1:10,] et [1:10] que j'ai ajoutÃ© seulement parce que sinon la transformation
    # #SpatialDataFramePolygons en SpatialPolygons rendait certaines gÃ©omÃ©tries invalides
    # spdf_inf_combine <- maptools::unionSpatialPolygons(spdf_inf_combine[1:10,],
    #                                                    vec_inf_index_contigues[1:10],
    #                                                    threshold=NULL)
    #
    # spdf_inf_combine <- SpatialPolygonsDataFrame(spdf_inf_combine,
    #                                              data.frame(ID=1:length(spdf_inf_combine@polygons)))
    #
    # writeOGR(spdf_inf_combine, file.path(wd_extrants, "Couche GIS"), "infranchissable",
    #          driver="ESRI Shapefile", check_exists=TRUE, overwrite_layer=TRUE)
    #










    # #cmtJFB Devrait faire l'object d'une autre section, on n'est plus dans les infranchissables
    # # Chargement de la couche de chemins ####
    # spdf_chemins <- load_intrant(path_chemins, crs_us)
    #
    # # Conservation du champ SONAR2 qui sera converti en emprise et qui identifie la classe de chemin
    # #cmtJFB On devrait demander plutÃ´t quel champ comprend la classe de chemin plutÃ´t que de chercher
    # #       un nom de colonne en particulier qui n'est pas normalement dans une couche de chemins
    # spdf_chemins_terrestre <- spdf_chemins[,"SONAR2"]
    # spdf_chemins_terrestre@data <- data.frame(emprise=spdf_chemins_terrestre@data[, "SONAR2"],
    # stringsAsFactors=FALSE)
    #
    #
    # # Chargement de couche de points correspondant aux gÃ©ocode des polygones de la couche de peuplements forestiers
    # #cmtJFB Ne devrait-on pas plutÃ´t utiliser directement les coordonnÃ©es des gÃ©ocodes qui sont dÃ©jÃ  dans la couche
    # #       de peuplements forestiers? Ãa Ã©viterait un intrant supplÃ©mentaire et une occasion de plus de boguer.
    # #       De ce que je comprends, LIST_GEOC_ ne comprend que les gÃ©ocodes qui sont situÃ©s Ã  l'intÃ©rieur du contour
    # #       de l'unitÃ© de sondage. La couche de peuplements peut-elle avoir des gÃ©ocodes Ã  l'extÃ©rieur? Il serait
    # #       peut-Ãªtre mieux alors de retirer ces polygones dÃ¨s le chargement initial s'ils ne servent Ã  rien.
    # spdf_geocodes <- load_intrant(path_geocodes, crs_us)
    #
    # #cmtJFB writeOGR(grille_placettes, "F:/SONAR_dev", "grille_placettes", driver="ESRI Shapefile")
    # # Identifie les placettes qui tombent dans un polygone dont le gÃ©ocode est Ã  l'extÃ©rieur de l'unitÃ© de sondage
    # vec_geocodes_exclus <- as.numeric(!grille_placettes@data[,"GEOC_FOR"] %in% spdf_geocodes@data[,"GEOC_FOR"])
    # grille_placettes@data[,"us_ex"] <- vec_geocodes_exclus
    #
    # # Chargement des paramÃ¨tres pour les tailles de buffers
    # df_ParamBuffers <- read.csv(path_ParamBuffers, sep=",", header=TRUE, stringsAsFactors=FALSE)
    #
    # # Extraction de la valeur du buffer gÃ©nÃ©ral
    # taille_BufferGen <- df_ParamBuffers[df_ParamBuffers[,"categorie"] == "general", "largeur"]
    #
    #
    # ## Buffer chemins ####
    # # Identification des types d'emprises de chemins possibles
    # vec_emprises_valides <- names(table(spdf_chemins_terrestre@data[,"emprise"]))
    #
    # # Identifie les placettes potentielles tombant Ã  l'intÃ©rieur du buffer des chemins
    # for (str_emprise in vec_emprises_valides){
    #     spdf_buffer <- gBuffer(spdf_chemins_terrestre[spdf_chemins_terrestre@data[,"emprise"] == str_emprise,],
    # width = taille_BufferGen + df_ParamBuffers[df_ParamBuffers[,"emprise"] == str_emprise, "largeur"],
    # byid = TRUE)
    #
    # # Jointure spatiale avec les placettes potentielles
    # df_InsideBuffer <- grille_placettes %over% spdf_buffer
    # df_InsideBuffer[!is.na(df_InsideBuffer[,1]), 1] <- 1
    # df_InsideBuffer[is.na(df_InsideBuffer[,1]), 1] <- 0
    # grille_placettes@data[,str_emprise] <- df_InsideBuffer[,1]
    # }
    #
    #
    # ## Buffer hydro linÃ©aire ####
    # # Vecteur des indicatifs pour lesquels des buffers sont nÃ©cessaires
    # #cmtJFB Est-ce seulement des permanents? Ã quoi correspondent-ils au juste?
    # vec_value_kept <- c("1010050000",
    #                     "1020001000",
    #                     "1020002000",
    #                     "1020050000",
    #                     "1200000000",
    #                     "1200000004",
    #                     "1200050000",
    #                     "1010000000")
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # spdf_HydroLin <- load_intrant(path_HydroLin, crs_us)
    # grille_placettes@data[,"BUF_HL"] <- evaluateBuffer(grille_placettes,
    #                                                    spdf_HydroLin,
    #                                                    taille_BufferGen,
    #                                                    "HYD_CODE_I", vec_value_kept)
    #
    #
    # ## Buffer voie ferrÃ©e ####
    # spdf_VoieFerree <- load_intrant(path_VoieFerree, crs_us)
    #
    # # Conservation des Ã©lÃ©ments correspondant uniquement aux voies ferrÃ©es
    # # Il y a substr() pour Ã©viter tout problÃ¨me avec les accents. ProblÃ¨me absent si une GDB est utilisÃ©e
    # #cmtJFB Ã mon avis, il serait mieux d'utiliser le champ VCO_CODE_INDIC avec la valeur 2020001000
    # #       puisque Ã§a Ã©viterait tout problÃ¨me liÃ© au texte de la mÃªme maniÃ¨re que pour HydroLin
    # spdf_VoieFerree <- spdf_VoieFerree[substr(spdf_VoieFerree@data[,"VCO_DESCR"], 0, 9) == "Voie ferr",]
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # #cmtJFB La taille de buffer dans le code original Ã©tait codÃ© dur Ã  25m
    # grille_placettes@data[,"VF"] <- evaluateBuffer(grille_placettes,
    #                                                spdf_VoieFerree,
    #                                                taille_BufferGen)
    #
    #
    # ## Buffer placettes permanentes (PEP) ####
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # taille_BufferPEP <- df_ParamBuffers[df_ParamBuffers[,"categorie"] == "PEP", "largeur"]
    #
    # # Vecteur des indicatifs pour lesquels des buffers sont nÃ©cessaires
    # #cmtJFB Ã quoi correspond vraiment "NO_PE", Ã§a peut vraiment Ãªtre des points de dÃ©part et d'arrivÃ©e?
    # vec_value_kept <- c("01","02")
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # spdf_PEP <- load_intrant(path_PEP, crs_us)
    # grille_placettes@data[,"PEP"] <- evaluateBuffer(grille_placettes,
    #                                                 spdf_PEP,
    #                                                 taille_BufferPEP,
    #                                                 "NO_PE", vec_value_kept)
    #
    #
    # ## Buffer bÃ¢timents ####
    # # Chargement de la valeur de buffer
    # taille_BufferBati <- df_ParamBuffers[df_ParamBuffers[,"categorie"] == "Batiment", "largeur"]
    #
    # ## Buffer bÃ¢timents ponctuels ####
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # spdf_BatiPonc <- load_intrant(path_ponc, crs_us)
    # grille_placettes@data[,"BUF_BAT_PO"] <- evaluateBuffer(grille_placettes,
    #                                                        spdf_BatiPonc,
    #                                                        taille_BufferBati)
    #
    #
    # ## Buffer bÃ¢timents linÃ©aires ####
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # spdf_BatiLin <- load_intrant(path_BatiLin, crs_us)
    # grille_placettes@data[,"BUF_BAT_LO"] <- evaluateBuffer(grille_placettes,
    #                                                        spdf_BatiLin,
    #                                                        taille_BufferBati)
    #
    #
    # ## Buffer bÃ¢timents surfaciques ####
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # spdf_BatiSur <- load_intrant(path_BatiSur, crs_us)
    # grille_placettes@data[,"BUF_BAT_SO"] <- evaluateBuffer(grille_placettes,
    #                                                        spdf_BatiSur,
    #                                                        taille_BufferBati)
    #
    #
    # ## Buffer Ã©quipements ####
    # # Chargement de la valeur de buffer
    # taille_BufferEquip <- df_ParamBuffers[df_ParamBuffers[,"categorie"] == "Equipement", "largeur"]
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # spdf_EquipPonc <- load_intrant(path_EquipPonc, crs_us)
    # grille_placettes@data[,"BUF_EQ_PO"] <- evaluateBuffer(grille_placettes,
    #                                                       spdf_EquipPonc,
    #                                                       taille_BufferEquip)
    #
    #
    # ## Buffer Ã©quipements linÃ©aires ####
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # spdf_EquipLin <- load_intrant(path_EquipLin, crs_us)
    # grille_placettes@data[,"BUF_EQ_LO"] <- evaluateBuffer(grille_placettes,
    #                                                       spdf_EquipLin,
    #                                                       taille_BufferEquip)
    #
    #
    # ## Buffer Ã©quipements surfaciques ####
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©es de superposition
    # spdf_EquipSur <- load_intrant(path_EquipSur, crs_us)
    # grille_placettes@data[,"BUF_EQ_SO"] <- evaluateBuffer(grille_placettes,
    #                                                       spdf_EquipSur,
    #                                                       taille_BufferEquip)
    #
    #
    # ## Buffer affectations ponctuelles ####
    # # Chargement des valeurs de buffer
    # taille_AffecPonc <- df_ParamBuffers[df_ParamBuffers[,"categorie"] == "Affectation" &
    # df_ParamBuffers[,"emprise"] == "ponctuelles",
    #                                "largeur"]
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©s de superposition
    # spdf_AffecPonc <- load_intrant(path_AffecPonc, crs_us)
    # grille_placettes@data[,"BUF_UFZ_PO"] <- evaluateBuffer(grille_placettes,
    #                                                        spdf_AffecPonc,
    #                                                        taille_AffecPonc)
    #
    #
    # ## Buffer affectations linÃ©aires ####
    # # Chargement des valeurs de buffer
    # taille_AffecLin <- df_ParamBuffers[df_ParamBuffers[,"categorie"] == "Affectation" &
    # df_ParamBuffers[,"emprise"] == "lineaire",
    #                                "largeur"]
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©s de superposition
    # spdf_AffecLin <- load_intrant(path_AffecLin, crs_us)
    # grille_placettes@data[,"BUF_UFZ_LO"] <- evaluateBuffer(grille_placettes,
    #                                                        spdf_AffecLin,
    #                                                        taille_AffecLin)
    #
    #
    # ## Buffer feux ####
    # #  Notes originale: il faudra peut-Ãªtre faire un code qui Ã©limine les polygones de feu de 2010
    # #  qui sont dÃ©jÃ  photo-interprÃ©tÃ©s, c'est-Ã -dire qui ont une origine == annee_photo
    #
    # # Chargement de la couche de feux
    # spdf_Feux <- load_intrant(path_Feux, crs_us)
    #
    # # Sous-sÃ©lection des feux aprÃ¨s la prise de photos
    # #cmtJFB Pas sÃ»r si j'ai bien modifiÃ© et compris ce bout-lÃ 
    # post_photo <- as.numeric(as.character(spdf_Feux@data[,"FMJ_ANNEE_"])) >= annee_photo |
    # as.numeric(as.character(spdf_Feux@data[,"FMJ_ANNEE1"])) >= annee_photo
    # post_photo[is.na(post_photo)] <- FALSE
    #
    # # garder la bonne date
    # spdf_Feux <- spdf_Feux[post_photo,]
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©s de superposition
    # grille_placettes@data[,"FEU"] <- evaluateBuffer(grille_placettes,
    #                                                 spdf_Feux,
    #                                                 taille_BufferGen)
    #
    #
    # ## Buffer perturbations ####
    # #  Notes originales: il faudra peut-Ãªtre faire un code qui Ã©limine les polygones de perturbations
    # #  de 2010 qui sont dÃ©jÃ  photo-interprÃ©tÃ©s, c'est-Ã -dire qui ont une origine == annee_photo
    #
    # # Chargement de la couche de perturbations
    # spdf_PertMaj <- load_intrant(path_PertMaj, crs_us)
    #
    # # Sous-sÃ©lection des perturbations aprÃ¨s la prise de photos
    # #cmtJFB Pas sÃ»r si j'ai bien modifiÃ© et compris ce bout-lÃ 
    # post_photo <- as.numeric(as.character(spdf_PertMaj@data[,"APM_ANNEE_"])) >= annee_photo |
    # as.numeric(as.character(spdf_PertMaj@data[,"APM_ANNEE1"])) >= annee_photo
    # post_photo[is.na(post_photo)] <- FALSE
    #
    # if (sum(post_photo) != 0){
    # # garder la bonne date
    # spdf_PertMaj <- spdf_PertMaj[post_photo,]
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©s de superposition
    # grille_placettes@data[,"PERT"] <- evaluateBuffer(grille_placettes,
    # spdf_PertMaj,
    # taille_BufferGen)
    # }
    #
    #
    # ## Buffer interventions des rapports (AECA) ####
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©s de superposition
    # spdf_Interv <- load_intrant(path_Interv, crs_us)
    # grille_placettes@data[,"INT_REL"] <- evaluateBuffer(grille_placettes,
    #                                                     spdf_Interv,
    #                                                     taille_BufferGen)
    #
    #
    # ## Buffer interventions planifiÃ©es ####
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©s de superposition
    # spdf_Planif <- load_intrant(path_Planif, crs_us)
    # grille_placettes@data[,"INT_PLA"] <- evaluateBuffer(grille_placettes,
    #                                                     spdf_Planif,
    #                                                     taille_BufferGen)
    #
    #
    # ## Buffer moins de 7 mÃ¨tres ####
    # #cmtJFB Partie Ã  retravailler complÃ¨tement, je ne suis pas sÃ»r de bien comprendre alors
    # #       j'ai seulement aÃ©rÃ© le code
    #
    # # Transformation du champ ET1_HAUT en numÃ©rique. NOTE: Pour Ã©viter de mettre des patchs comme
    # # (as.numeric), il faudra vÃ©rifier et s'assurer que les chiffres et les nombres sont en numÃ©rique
    # plus_petit_7m <- as.numeric(spdf_PeupForestiers@data[,"ET1_HAUT"]) < 7
    #
    # # Identifie les NA comme faux
    # plus_petit_7m[is.na(plus_petit_7m)] <- FALSE
    #
    # if (any(plus_petit_7m)){
    # # Fait un buffer sur les plus petits que 7 mÃ¨tres
    # buf_Et1 <- gBuffer(spdf_PeupForestiers[plus_petit_7m,],
    # width=taille_BufferGen,
    # byid=TRUE)
    # }
    #
    # SpP_buf_Et1 <- as(buf_Et1, "SpatialPolygons")
    #
    # # Va chercher la combinaison origines non Ã©gal Ã  NA et ET1_haut Ã©gal Ã  NA
    # ori_haut <- !is.na(spdf_PeupForestiers@data[,"ORIGINE"]) &
    # is.na(spdf_PeupForestiers@data[,"ET1_HAUT"])
    #
    # if (any(ori_haut)){
    # buf_Et2 <- gBuffer(spdf_PeupForestiers[ori_haut,],
    # width=taille_BufferGen,
    # byid=TRUE)
    # }
    #
    # SpP_buf_Et2= as(buf_Et2, "SpatialPolygons")
    #
    # # Changer les ID de tous les buffers
    # # plus_petit_7m
    # ID <- sapply(SpP_buf_Et1@polygons, function(x) x@ID)
    # SpP_buf_Et1 <- spChFIDs(SpP_buf_Et1, paste0("BAP_", ID))
    #
    # # ori_haut
    # ID <- sapply(SpP_buf_Et2@polygons, function(x) x@ID)
    # SpP_buf_Et2 <- spChFIDs(SpP_buf_Et2, paste0("BAL_", ID))
    #
    # # Combine tous les buffers d'infrastructures
    # buf_moins_7m <- rbind(SpP_buf_Et1, SpP_buf_Et2)
    #
    # # Plaquer les placettes potentielles sur les moins de 7 mÃ¨tres
    # moins_7m <- grille_placettes %over% buf_moins_7m
    #
    # # Remplacer par des 1 ceux qui ont une correspondance par 0 ceux qui n'en ont pas
    # moins_7m[!is.na(moins_7m)] <- 1
    # moins_7m[is.na(moins_7m)] <- 0
    #
    # # Ajouter la colonne joint au data des placettes potentielles
    # grille_placettes@data[,"BUF_M7M"] <- moins_7m
    #
    #
    # ## Buffer intÃ©rieur unitÃ© de sondage ####
    # # fait le buffer in
    # bufin <- readOGR(path_BufferIn, stringsAsFactors=FALSE)
    #
    # ### Faire le joint du buffer d'intÃ©rieur d'US avec placettes potentielles
    # joint_temp <- grille_placettes %over% bufin
    # joint_temp[!is.na(joint_temp$UPE), "UPE"] <- 0
    # joint_temp[is.na(joint_temp$UPE), "UPE"] <- 1
    # #grille_placettes@data$LIM_US <- joint_temp
    # grille_placettes@data$LIM_US <- as.numeric(joint_temp$UPE)
    #
    #
    # ## Buffer non forestier ####
    # #cmtJFB Autre section Ã  valider. Je ne suis pas sÃ»r de la sÃ©lection initiale effectuÃ©e
    # # Extraction du non forestier de la couche de peuplements forestiers
    # spdf_NonFor <- spdf_PeupForestiers[!is.na(spdf_PeupForestiers@data[,"CO_TER"]),]
    #
    # # Ãvaluation de la position des placettes potentielles en fonction des entitÃ©s de superposition
    # grille_placettes@data[,"BUF_NF"] <- evaluateBuffer(grille_placettes,
    #                                                    spdf_NonFor,
    #                                                    taille_BufferGen)
    #
    #
    # ## Peuplements non-NAIPF ####
    # #cmtJFB Ã retravailler, je n'ai rien changÃ©.
    # if (any(df_PeupForestiers$IN_NAIPF != 'O')){
    # peu.non.naipf <- spdf_PeupForestiers[-grep("AIPF", df_PeupForestiers$VER_PRG),]
    # peu.non.naipf <- SpatialPolygons(slot(peu.non.naipf, "polygons"),
    # proj4string=CRS(proj4string(peu.non.naipf)))
    #
    # ## Faire le joint des peuplements non-NAIPF avec placettes potentielles
    # joint_temp1 <- grille_placettes %over% peu.non.naipf
    # joint_temp1[!is.na(joint_temp1)] <- 1
    # joint_temp1[is.na(joint_temp1)] <- 0
    # grille_placettes@data[,"INITIAL"] <- joint_temp1
    # }
    #
    # ## Sites d'intÃ©rÃªt particulier (SIP) ####
    # #cmtJFB Ã retravailler, je n'ai rien changÃ©. La couche en entrÃ©e pourrait Ãªtre
    # #       au format polygonal, mais aussi linÃ©aire et/ou ponctuel. Ajuster le
    # #       code en consÃ©quence pour Ãªtre flexible
    # couche_SIP <- load_intrant(path_SIP, crs_us)
    #
    # couche_SIP <- SpatialPolygons(slot(couche_SIP, "polygons"),
    #                               proj4string=CRS(proj4string(couche_SIP)))
    #
    # ## Faire le joint des SIP avec placettes potentielles
    # joint_temp <- grille_placettes %over% couche_SIP
    # joint_temp[!is.na(joint_temp)] <- 1
    # joint_temp[is.na(joint_temp)] <- 0
    #
    # #  Le nom de la colonne est fait pour Ãªtre confondant
    # grille_placettes@data$PdesA <- joint_temp
    #
    #
    # ## Masque ####
    # #cmtJFB Ã retravailler, je n'ai rien changÃ© de particulier. Masque permettant de couvrir les zones cadastrÃ©es
    # #       et autres contraintes non dÃ©finie. Couche fourre-tout. Toujours sous forme de polygones.
    # couche_autre <- load_intrant(path_masque, crs_us)
    #
    # couche_autre <- SpatialPolygons(slot(couche_autre, "polygons"),
    #                                 proj4string=CRS(proj4string(couche_autre)))
    #
    # buf_masque <- gBuffer(couche_autre, width=taille_BufferGen, byid=T)
    # SpP_buf_masque= as(buf_masque, "SpatialPolygons")
    #
    # ## Faire le joint des interventions planifiÃ©es avec placettes potentielles
    # joint_temp <- grille_placettes %over% SpP_buf_masque
    # joint_temp[!is.na(joint_temp)]    <- 1
    # joint_temp[is.na(joint_temp)]     <- 0
    # grille_placettes@data$Aut <- joint_temp
    #
    #
    # ## DÃ©termination des placettes mesurables ####
    # #cmtJFB Ã retravailler, je n'ai rien changÃ© de particulier sauf
    # #       une passe assez brute pour forcer toutes les valeurs en numÃ©rique
    # toutes_var_bin <- c("vec_exclus_ModeGestion",
    #                     "vec_exclus_UsageForestier",
    #                     "PENFRT_BDTQ",
    #                     "PENFRT",
    #                     "NONFOR",
    #                     "SOMM",
    #                     "E1", "E2", "E3", "E4", "E5", "E6", "EH",
    #                     "BUF_HL", "PEP", "VF", "BUF_BAT_PO", "BUF_BAT_LO", "BUF_BAT_SO",
    #                     "BUF_EQ_PO", "BUF_EQ_LO", "BUF_EQ_SO", "BUF_UFZ_PO", "BUF_UFZ_LO",
    #                     "FEU", "PERT", "INT_REL", "INT_PLA", "BUF_M7M", "BUF_NF", "LIM_US",
    #                     "INITIAL", "PdesA", "us_ex", "Aut")
    #
    # tbl_exclusion = grille_placettes@data[, colnames(grille_placettes@data) %in% toutes_var_bin]
    # tbl_exclusion = data.frame(lapply(tbl_exclusion, function(x){as.numeric(x)}))
    # mesurable <- as.numeric(rowSums(tbl_exclusion) == 0)
    #
    # grille_placettes@data[,"mesurable"] <- mesurable
    #
    # megatable <- merge(grille_placettes@data, df_PeupForestiers, by="GEOC_FOR",
    #                    all.x=TRUE, all.Y=FALSE)
    #
    # megatable[is.na(megatable)] <- ""
    #
    # writeOGR(grille_placettes, file.path(wd_extrants, "Couche GIS"), "grille_plac",
    #          driver="ESRI Shapefile", check_exists=TRUE, overwrite_layer=TRUE)
    #
    # save(megatable, file=file.path(wd_extrants, "table_plac_pot_compile.RData"))
    #
    # donn_carte <- df_PeupForestiers

    temps_final = time.time()
    temp_tot = round((temps_final - tempsDebut) / 60, 2)
    print("Le temps total de traitement est de : {} minutes".format(temp_tot))



if __name__ == '__main__':

    tempsDebut = time.time()

    main()

