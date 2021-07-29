# -*- coding: utf-8 -*-

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


import arcpy
from os import sys


def dissolve(intrant):


    dissolve = r"C:\MrnMicro\temp\dissolve.shp"

    if arcpy.Exists(dissolve):
        arcpy.Delete_management(dissolve)

    arcpy.Dissolve_management(in_features=intrant, out_feature_class=dissolve,
                              dissolve_field="", statistics_fields="",
                              multi_part="SINGLE_PART", unsplit_lines="DISSOLVE_LINES")

if __name__ == '__main__':

    intrant = sys.argv[1]
    dissolve(intrant)