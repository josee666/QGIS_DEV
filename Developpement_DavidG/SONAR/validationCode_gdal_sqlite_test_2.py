#!/usr/bin/env python
# -*- coding: latin-1 -*-

# Auteur: Sylvain Miron 2021-03-22
# validateur sonar2

# NB: Vous devez avoir GDAL installer sur votre poste


#import string
import subprocess, os
import sqlite3
import sys
reload(sys)
##sys.setdefaultencoding('Latin-1')
sys.setdefaultencoding('UTF-8')
import arcpy
import arcgisscripting
import tkMessageBox
from arcpy import env

def lancement_cmd(cmd, return_output=False):
    """ SM 2021-01-19
    Fonction quon appelle pour lancer une commande par l'invite de commande
    Pour OGR-GDAL
    """
    try:
        if isinstance(cmd, str):
            cmdDecode = cmd
        else:
           cmdDecode = cmd.encode('UTF-8')  # on convertie unicode en STR

        output = subprocess.check_output(cmdDecode, stdin=None, stderr=subprocess.STDOUT,
                                         shell=True, universal_newlines=True)

        if output[:5] == "ERROR" or "FAILURE" in output:

            if "ERROR 6: No translation for Mercator_Auxiliary_Sphere" in output:
                # erreur select ogrinfo sur un certain shp. mais info voulue y est tout de meme donc ok pas erreur
                return output

            if "index" and "already exists" not in output:
                message = "Probleme lancement CMD = {}".format(cmd)
                # print(message + "-" + output)

                if "lock" in output:
                    mess = "La couche est ouverte, veuillez la fermer et relancer le traitement"
                    messStr = mess.encode('UTF-8')
                    raise ValueError(messStr)
                else:
                    raise Exception(message + "\n\n" + output)

        if return_output:
            return output

    except Exception as e:

        print("probleme dans lancement cmd GDAL : ", e, cmd)
        raise



def lancement_importation_donnees(sqliteTravail, grille_plac_dans_tuile_sel, grille_tuile_sel, depart_potentiel):
    ##############
    #  1: conversion GDB tab code ou shape en SQLITE
    ############

    commandeCoversion = " ogr2ogr -f sqlite {0} {1} -dsco spatialite=yes ".format(sqliteTravail, grille_plac_dans_tuile_sel)


    output = lancement_cmd(commandeCoversion)
    print(output)


    ################
    # 2 - ajouter dans la sqlite la table donnee a valider
    ################
    GrilleTuileSel = " ogr2ogr -f sqlite -append {0} {1} -nln grille_tuile_sel -dsco spatialite=yes ".format(sqliteTravail, grille_tuile_sel)

    output = lancement_cmd(GrilleTuileSel)
    print(output)


    DepartPotentiel = " ogr2ogr -f sqlite -append {0} {1} -nln depart_potentiel -dsco spatialite=yes ".format(sqliteTravail, depart_potentiel)


    output = lancement_cmd(DepartPotentiel)
##    output1 = lancement_cmd(commandeAjoutTabDonnee1)
    print(output)


def lancement_validation_donnees(path_fichier_erreurs):
    #####################
    #####
    # 3 - Valider les shp grille_plac_dans_tuile_sel, grille_tuile_sel et depart_potentiel
    ######
    ##############
    # connection sur la BD

    try:
        connexion = sqlite3.connect(sqliteTravail)
        curseur = connexion.cursor()
    except:
        print("probleme lors de connexion sqlite")
        raise


    Erreurs_grille_plac_dans_tuile_sel = """alter table grille_plac_dans_tuile_sel add erreurs_valeurs_manquantes varchar(100)"""
    curseur.execute(Erreurs_grille_plac_dans_tuile_sel)
    connexion.commit()

    DepartPotentiel = """alter table depart_potentiel add erreur varchar(100)"""
    curseur.execute(DepartPotentiel)
    connexion.commit()

    DepartPotentiel = """alter table depart_potentiel add erreur1 varchar(100)"""
    curseur.execute(DepartPotentiel)
    connexion.commit()



### Liste des noms complets des champs inscrit dans le fichier texte pour les donnees en erreur
#    liste_champ = ["Erreur ou donnees manquantes dans le champ groupe de grille_plac_dans_tuile_sel", "Donnees manquantes dans depart_potentiel",
#                   "Une seule valeur par groupe champ acces de Depart_potentiel","Moins de 4 placettes dans placettes_potentielles"]
#    "Unite de paysage regional",


### Requetes sql. La première est une validation des dates de mise a jour les deux suivsntes valident les champs
    # qui servitont a faire les cles. Les autres requetes
    # font la comparaisons de champs entre la table a valider et les tables de codes oracle a partir de
    # combinaisons (cles) entre la table a valider et la table de codes oracle. Les champs a valider sont le domaine
    # bioclimatique, le sous domaine bioclimatique, la region ecologique, la sous region ecologique, le nom du district,
    # la zone de vegetation et la sous zone de vegetation.


### ajouter un champ erreur et update pour identifier les erreurs possibles


    Erreurs_grille_plac_dans_tuile_sel = """update grille_plac_dans_tuile_sel set erreurs_valeurs_manquantes = "erreurs donnees manquantes ou null" where rowid in 
                                             (select rowid from grille_plac_dans_tuile_sel where groupe is null or groupe = '' or groupe = 'g0' or groupe = 'g1' or groupe = 'g2' or 
                                             groupe = 'g3')"""
    curseur.execute(Erreurs_grille_plac_dans_tuile_sel)
    connexion.commit()


    Erreurs_depart_potentiel = """update depart_potentiel set erreur = "erreur donnees manquantes ou différentes de C et V" where rowid in (select rowid from depart_potentiel 
                                  where groupe is null or groupe = '' or groupe = 'g0' or acces not in ('C', 'V'))"""
    curseur.execute(Erreurs_depart_potentiel)
    connexion.commit()


    Erreurs_depart_potentiel2 = """update depart_potentiel set erreur1 = "erreur combinaison tuile groupe acces" where ("tuil_id" || "groupe") in 
                                  (select "tuil_id" || "groupe" from (SELECT  "tuil_id", "groupe", "acces", count(*) as nb FROM depart_potentiel group by "tuil_id", "groupe", 
                                  "acces") group by "tuil_id", "groupe" HAVING COUNT(*) > 1)"""
    curseur.execute(Erreurs_depart_potentiel2)
    connexion.commit()


    connexion.close()


    ### Liste des noms complets des champs inscrit dans le fichier texte pour les donnees en erreur
    liste_champ = ["Erreurs_grille_plac_dans_tuile_sel", "Erreurs_depart_potentiel", "Erreurs_depart_potentiel2"]
    #    "Unite de paysage regional",

    file = open(path_fichier_erreurs, "w")
    count = 0



### Liste des requetes
    liste_requetes = [Erreurs_grille_plac_dans_tuile_sel, Erreurs_depart_potentiel, Erreurs_depart_potentiel2]

        #, Donnees_manquantes_depart]

                      #Valid_une_seule_valeur, Valid_moins_de_quatre_placettes]


### Boucle qui sert à passer ligne par ligne les tables comparees selon les champs cibles et detecter les erreurs pour les inscrire
    # dans un ficher texte selon l'identifiant unique (OBJECTID)
    for requete in liste_requetes:

        bon_champ = liste_champ[count]

        file.write("\n\n")
        file.write("Non conforme {}".format(bon_champ))
        file.write("\n\n")
        # ici plutot que select *, aller chercher seulement votre champ cle et le champ valide, serait mieux.
        #        for i in liste_requeteSQL:
        curseur.execute(requete)
        rows = curseur.fetchall()


        for row in rows:
            str_erreur = ""
            for i in row:
                str_erreur = str_erreur + " OBJECTID " + str(i)
        # print("probleme avec le code dans cette ligne: {} ".format(row) )
        #            print()
        #            erreur_str = '-'.join(row)
        #            erreur_str = str.join(map(str, row))
            file.write(str_erreur)
            file.write("\n")
        count = count + 1
    file.write("\n\n")

    file.close()
    connexion.close()




if __name__ == '__main__':

### Operations manuelles
    grille_plac_dans_tuile_sel = "E:/SONAR2/OutilDeValidationTest/grille_plac_dans_tuile_sel.shp" # couche a valider
    grille_tuile_sel = "E:/SONAR2/OutilDeValidationTest/grille_tuile_sel.shp" # couche a valider
    depart_potentiel = "E:/SONAR2/OutilDeValidationTest/depart_potentiel.shp" # couche a valider
    sqliteTravail = "E:/SONAR2/OutilDeValidationTest" + "\\travail.sqlite"# endroit ou la base sqlite sera deposee
    path_fichier_erreurs = "E:/SONAR2/OutilDeValidationTest" + "\\Rapport_erreurs_SONAR2.txt"# endroit ou le fichier d'erreurs sera depose


### Interface de commande
#    grille_plac_dans_tuile_sel = sys.argv[1] # couche a valider
#    grille_tuile_sel = sys.argv[2] # couche a valider
#    depart_potentiel = sys.argv[3] # couche a valider
#    sqliteTravail = sys.argv[4] + "\\travail.sqlite"# endroit ou la base sqlite sera deposee
#    path_fichier_erreurs = sys.argv[5] + "\\Rapport_erreurs_SONAR2.txt"# endroit ou le fichier d'erreurs sera depose


    if os.path.exists(sqliteTravail):
        os.remove(sqliteTravail)


    print ("Etape1: importation des donnees")
    lancement_importation_donnees(sqliteTravail, grille_plac_dans_tuile_sel, grille_tuile_sel, depart_potentiel)
    print ("Fin etape 1")

    print ("Etape2: validation des donnees")
    lancement_validation_donnees(path_fichier_erreurs)
    print ("Fin etape 2")

print ("Fin du programme")





### Creation des cles qui serviront a faire les validations entre les champs des donnees a valider et les tables oracle
#dde_dis_eco = u"Alter table {0} ADD COLUMN {1} CHAR(7)".format(dde_dis_eco_vp_vue, "UPR_NDE")
#curseur.execute(dde_dis_eco)
#concat = u"""UPDATE "dde_dis_eco_vp_vue" SET "UPR_NDE" = UPR_CO_UPR || NDE_CO_NDE"""
#curseur.execute(concat)
#connexion.commit()


#dde_reg_eco = u"Alter table {0} ADD COLUMN {1} CHAR(7)".format(dde_reg_eco_vp_vue, "DOM_REG")
#curseur.execute(dde_reg_eco)
#concat = u"""UPDATE "dde_reg_eco_vp_vue" SET "DOM_REG" = DOB_CO_DOB || REC_CO_REC"""
#curseur.execute(concat)
#connexion.commit()


#donne_a_valider = u"Alter table {0} ADD COLUMN {1} CHAR(2)".format("table_donnee", "DOM_REG_verif")
#curseur.execute(donne_a_valider)
#concat = u"""UPDATE "table_donnee" SET "DOM_REG_verif" = dom_bio_p || reg_eco_p"""
#curseur.execute(concat)
#connexion.commit()


#donne_a_valider = u"Alter table {0} ADD COLUMN {1} CHAR(7)".format("table_donnee", "UPR_NDE_verif")
#curseur.execute(donne_a_valider)
#concat = u"""UPDATE "table_donnee" SET "UPR_NDE_verif" = upays_reg_ || dis_eco_p"""
#curseur.execute(concat)
#connexion.commit()