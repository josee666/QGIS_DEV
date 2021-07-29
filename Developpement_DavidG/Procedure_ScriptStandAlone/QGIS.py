#!/usr/bin/env python
# coding: utf-8


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
# 2020-03-20 -Création du script


from qgis.core import *
import processing
from processing.core.Processing import Processing
from qgis.analysis import QgsNativeAlgorithms
from PyQt5.QtCore import QVariant
import sys
import os
import subprocess
import geopandas as gpd
import shapely
from shapely.geometry import Polygon

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

def copyCeToGpkg(ce, gpkg, nomCouche):

    # faire un layer avec la string ce
    couche = QgsVectorLayer(ce, "lyr", 'ogr')

    # Option de sauvegarde
    options = QgsVectorFileWriter.SaveVectorOptions()

    # J'enleve l'extension
    gpkg = gpkg.replace(".gpkg", "")

    options.driverName = 'GPKG'
    options.layerName = nomCouche

    # Transférer la ce de la gdb vers le GeoPackage
    QgsVectorFileWriter.writeAsVectorFormat(couche, gpkg, options)

    sortie = gpkg + ".gpkg" + '|' + 'layername=' + nomCouche

    return sortie


def dissolvedGeopandasGPKG(gpkg, namefc, nameoutfc, fields = None):

    """
    Permet de faire un dissolve avec Geopandas dans un geopackage
    Geopandas ne gere pas encore les valeur Null lors du dissole. C'est pour ca que je rempli
    les valeurs Null pas une string "null"

              Args:
                  gpkg : geopackage
                  namefc : nom de la classe d'entité
                  nameoutfc : nom de la classe d'entité en sortie
                  fields : champ

              Exemple d'appel de la fonction:

              gpkg = r"C:\MrnMicro\temp\test_dissolve_fiona\HISTO_MAJF_2018.gpkg"
              ce ='HISTO_MAJF_2018_Repair'
              out = 'HISTO_MAJF_2018_diss'
              fields = 'CO_TER'

              dissolvedGeopandasGPKG(gpkg, ce, out, fields)

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



if __name__ == '__main__':



    gpkg = os.path.join(R"C:\MrnMicro\temp","SONAR2_Intrants.gpkg")
    us = gpd.read_file(gpkg, layer='us')
    print('fill')
    filled_shape = Polygon(us.exterior)
    print('tetet')
    new = gpd.GeoDataFrame(crs=us.crs, geometry=[filled_shape])
    print('tetghhhhet')
    new.to_file(gpkg, layer='us_filled', driver="GPKG")




    # # copie l'us dans le geopackage
    # # Copie des peuplement dan sle GPKG
    # us_gpkg = 'us'
    # path_us_gpkg = copyCeToGpkg(path_us, gpkg, us_gpkg)
    #
    # print("dissolve")
    # # faire un dissolve de l'US
    # us_gpkg_dissolve = 'us_gpkg_dissolve'
    # dissolvedGeopandasGPKG(gpkg, us_gpkg, us_gpkg_dissolve, fields = None)




# Écrire les algorithmes que l'on veut appeler.

# ce = 'C:/MrnMicro/temp/Racc_dif.shp'
# output = 'C:/MrnMicro/temp/test.shp'
# param = {'INPUT':input,'ROUND_TO':0,'OUTPUT':output}

# # faire un layer avec ce
# if isinstance(ce, str):
#     layer = QgsVectorLayer(ce, 'lyr', 'ogr')
# else:
#     layer = ce

# ajouter un champ SUP
# https://qgis.org/pyqgis/3.2/core/Field/QgsField.html
# https://gis.stackexchange.com/questions/174971/how-to-define-the-number-of-decimals-when-adding-a-new-field-as-double-to-an-att

# champ = QgsField('test', QVariant.Double,'double',100,2 )
# layer.dataProvider().addAttributes([champ])
# layer.updateFields()
#
# feat = layer.getFeatures()
# layer_provider = layer.dataProvider()
#
# # caluler la superficie en m carrée
# for features in feat:
#     id = features.id()
#     # trouver l'index du champ
#     fields = layer.fields()
#     indexChamp = fields.indexFromName('test')  # Index du champ
#
#     sup =str(round(features.geometry().area(),2))
#     attr_value = {indexChamp: sup}  # calculer area
#     layer_provider.changeAttributeValues({id: attr_value})
#
# layer.commitChanges()


# permet de sortir l'extent d'une couche
# processing.run("qgis:polygonfromlayerextent", param)

# ce='C:/MrnMicro/temp/Racc_dif.shp'
# nomJeuClasseEntite="TOPO"
# nomClasseEntite="test"
# outGDB='C:/MrnMicro/temp/sdfss.gdb'
#
# processing.run("gdal:convertformat", {'INPUT':ce,
#                                       'OPTIONS':'-lco FEATURE_DATASET={0} -lco XYTOLERANCE=0.02 -nln {1}'.format(nomJeuClasseEntite, nomClasseEntite),
#                                       'OUTPUT':outGDB})

# processing.run("gdal:convertformat", {'INPUT':ce,'OPTIONS':'','OUTPUT':outGDB})

# processing.run("gdal:convertformat", {'INPUT':'Q:/Dtxp_Carto/Trm_pre/2020/07/Perm5pre.shp','OPTIONS':'','OUTPUT':'C:/MrnMicro/temp/test.gdb'})


# CREATE_NO_WINDOW = 0x08000000
# cmd = r"""ogr2ogr -f "FileGDB" {3} {0} -t_srs EPSG:32198 -lco FEATURE_DATASET={1} -lco XYTOLERANCE=0.02 -nln {2}""".format(ce,nomJeuClasseEntite,nomClasseEntite,outGDB)
# subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)
#


# input = 'E:/Temp/geotraitement_QGIS/sub.shp'
# output = 'E:/Temp/geotraitement_QGIS/sommet.shp'
# param = {'INPUT':input,'OUTPUT':output}
#
# # permet d'extraire les sommets d'une couche
# processing.run("native:extractvertices", param)


# cmd = r"""ogr2ogr -f "FileGDB" C:\MrnMicro\temp\coversion_GDAL\EcoForS5_Ori_Prov.gdb C:\MrnMicro\temp\coversion_GDAL\EcoForS5_Ori_Prov.gpkg EcoForS5_ORI_PROV -lco FEATURE_DATASET=TOPO -lco XYTOLERANCE=0.02 -nln allo"""
# subprocess.call(cmd, shell=False)
#
# CREATE_NO_WINDOW = 0x08000000
# cmd = r"""ogr2ogr -f "FileGDB" C:\MrnMicro\temp\coversion_GDAL\EcoForS5_Ori_Prov.gdb C:\MrnMicro\temp\coversion_GDAL\EcoForS5_Ori_Prov.gpkg EcoForS5_ORI_PROV -lco FEATURE_DATASET=TOPO -lco XYTOLERANCE=0.02 -nln EcoForS5_ORI_PROV"""
# subprocess.call(cmd, creationflags=CREATE_NO_WINDOW)

# os.system(cmd)

# Fermer QGIS, vide la memoire....
qgs.exitQgis()