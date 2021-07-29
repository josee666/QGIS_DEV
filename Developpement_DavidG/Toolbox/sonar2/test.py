# -*- coding: utf-8 -*-

import os
import subprocess

# faire un dissolve arcpy
path_us = r"E:\ADG\SONAR\1415CE\Intrants\US_1415CE.shp"
# path_us = r"C:\MrnMicro\temp\SONAR2_Intrants.gpkg\us"


path_arpyPy = os.path.dirname(__file__) + '/Arcpy_Dissolve_SONAR2.py {}'.format(path_us)

print(path_arpyPy)
subprocess.call("C:\Mrnmicro\Applic\python27\ArcGIS10.3\python.exe"+" "+path_arpyPy)