@echo off
call "E:\OSGeo4W64\bin\o4w_env.bat"
call "E:\OSGeo4W64\bin\qt5_env.bat"
call "E:\OSGeo4W64\bin\py3_env.bat"

@echo on
pyrcc5 -o resources.py resources.qrc