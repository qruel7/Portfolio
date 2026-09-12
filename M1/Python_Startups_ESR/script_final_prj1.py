################################################################################################
############################### Programmation Python Avancée ###################################
################################################################################################


                                    #### PROJET 1 ####
### Étude sur les liens entre start-ups et structures d'enseignement supérieur de recherche ###



                        ### SOMMAIRE ###
                        
## Importation et préparation des données ------------ ligne 20   ##
## Traitement des données ---------------------------- ligne 141  ##
## Programme d'affichage interactif ------------------ ligne 450  ##
## Appel du programme -------------------------------- ligne 1389 ##



##############################################
### IMPORTATION ET PREPARATION DES DONNEES ###
##############################################


# importation de tous les packages requis pour la compilation du programme :
    
# packages généraux :
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd

# packages pour les rapports au format PDF :
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
import tempfile
import os



# 1.
# importation de la base de données depuis l'URL de téléchargement
df=pd.read_csv("https://www.data.gouv.fr/api/1/datasets/r/8129ef0f-ea7a-4a75-9f78-f882c7a3fbce",sep=";")



# 2.
temp=df.head(10)  # DataFrame temporaire pour avoir un apperçu de la forme de df et de ses colonnes

# modification des noms de colonnes pour faciliter leur manipulation
df.columns=["siren","nom","date_crea","actifs","esr_nom","esr_id","incub_nom","incub_id","date_accompagnement","statut","date_fermeture","date_obs","site_internet","id_crunchbase","id_dealroom","code_postal","commune","depart_char","region_char","code_commune","depart_num","region_num","code_iso"]

print(df.dtypes)  # affichage des différents types pour toutes les colonnes de df


# modification des colonnes contenant une date en datetime, afin de pouvoir faire des opérations avec
df["date_crea"]=pd.to_datetime(df["date_crea"],format="%Y-%m-%d",errors="coerce")
df["date_fermeture"]=pd.to_datetime(df["date_fermeture"],format="%Y-%m",errors="coerce")
df["date_obs"]=pd.to_datetime(df["date_obs"],format="%d-%m-%Y",errors="coerce")


df["statut"].unique()  # affichage de toutes les valeurs que peut prendre la colonne "statut"
df["statut"]=df["statut"].map({"active":True,"inactive":False})  # mappage de la colonne pour remplacer les valeurs par True ou False (et laisser les na tels quels)
df["statut"] = df["statut"].astype("boolean")  # conversion en booléen


df.loc[df["depart_num"].isin(["2A","2B"]), "depart_num"]="20"  # modification des valeurs problématiques empêchant la conversion de la colonne en numeric. Il s'agit des 2 départements de la Corse, que nous avons regroupé ensemble en tant que 20, comme c'était le cas à l'époque
df[["siren","code_postal","depart_num","region_num"]]=df[["siren","code_postal","depart_num","region_num"]].astype("Int64")  # conversion des colonnes en Int64, qui gère le type nullable.


df[["actifs","region_char","code_iso"]]=df[["actifs","region_char","code_iso"]].astype("category")  # conversion des colonnes en category


# conversion des colonnes en string (chaîne de caractères)
df[["nom","esr_nom","esr_id","incub_nom","incub_id",
    "site_internet","id_crunchbase","id_dealroom","commune","depart_char"]]=df[["nom","esr_nom","esr_id","incub_nom","incub_id",
                                                                                "site_internet","id_crunchbase","id_dealroom","commune","depart_char"]].astype("string")



# 3.
print(df.dtypes)  # affichage du résumé technique de df



# 4.
# définition d'une fonction renvoyant toutes les valeurs possibles que peut prendre une colonne spécifiée
# en prenant en compte les cellules multi-valuées
def ensemble_valeurs(df,col):
    ensemble=set()  # création d'un ensemble vide
    
    for cellule in df[col]:  # on va tester pour chaque cellule de df[col] si elle est vide 
        if pd.notna(cellule):
            elements=cellule.split(",")  # si elle n'est pas vide, on récupère les éléments qui la contiennent, en précisant "," comme séparateur
            
            for e in elements:
                ensemble.add(e.strip())  # pour chaque element de la cellule, on l'ajoute à l'ensemble créé plus tôt
    return ensemble  # retourne l'ensemble contenant toutes les valeurs possibles de "col"
        
    



# 5.
# récupération de toutes las valeurs possibles des colonnes suivantes stockées dans un ensemble :
    
# esr_id :
ens_esr_id=ensemble_valeurs(df,"esr_id")

# actifs :
ens_actifs=ensemble_valeurs(df,"actifs")

# esr_nom :
ens_esr_nom=ensemble_valeurs(df,"esr_nom")

# incub_id :
ens_incub_id=ensemble_valeurs(df,"incub_id")

# date_accompagnement :
ens_date_accompagnement=ensemble_valeurs(df,"date_accompagnement")




# 6.
# on ne garde que les colonnes utiles pour la suite du programme pour alléger df et optimiser l'exécution
df=df.drop(columns=["incub_nom","incub_id","date_accompagnement","date_obs","site_internet","id_crunchbase","id_dealroom","code_postal","commune","code_commune","depart_num","region_num","code_iso"])

print(df.columns)  # affichage des colonnes restantes

# exportation de la base de données nettoyée dans un fichier csv
df.to_csv("dataclean.csv",index=False)





##############################
### TRAITEMENT DES DONNEES ###
##############################


## Organisation des partenariats ##
    
# 1.
# définition de la fonction qui renvoie le dataframe des start-ups liées à la structure ESR passée en argument
def startups_liees(df,nom_structure):
        tri=[] # on définit un vecteur vide
        
        # on va tester la correspondance de nom pour chaque ligne, en découpant les cellules en elements s'il y a une virgule
        for cellule in df["esr_nom"]:
            correspondance=False
            if pd.notna(cellule):
                elements=str(cellule).split(",")
                for e in elements:
                    if e.strip()==nom_structure:
                        correspondance=True
                        break
                        # si la condition est validée, càd si on trouve un element de cellule égal à nom on arrête de tester les éléments de cette cellule, et on affecte True à correspondance
                  
            # pour chaque ligne de df on ajoute True si correspondance, ou False si non-correspondance 
            # tri est donc un vecteur booléen de taille len(df)
            # il permettra de trier les lignes à restituer dans le df de sortie de fonction, càd seulement les lignes pour lesquelles la startup est liée à la structure ESR indiquée en argument
            tri.append(correspondance)
            
        return df[tri] # ça va return le df dont les startups sont liées à la structure ESR en argument


test2=startups_liees(df, "Centre national de la recherche scientifique")



# 2.
# définition de la fonction qui renvoie l'ensemble des structures ESR partenaires d'une start-up liée avec la structure donnée en argument
def st_partenaires(df,nom_structure):
    df_filtre=startups_liees(df,nom_structure)  # on récupère l'ensemble des start-ups liées à nom_structure
    ensemble=ensemble_valeurs(df_filtre,"esr_nom")  # à partir de df_filtre, on met dans un ensemble toutes les valeurs possibles de "esr_nom"
    ensemble.discard(nom_structure)  # on retire de l'ensemble le nom de structure ESR passée en argument 
    return ensemble  # retourne l'ensemble voulu


test3=st_partenaires(df,"Aix-Marseille Université")
    
    
    
    
## Implantation géographique ##

# 3.
# définition de la fonction qui renvoie le nombre de start-ups par lieu (précisé en argument de la fonction) sous forme de Series
def nb_par_lieu(df,nom_col):
    series_comptage=df.groupby(nom_col,observed=True)["siren"].nunique()  # regroupe les observations de df par les valeurs possibles de "nom_col", qui ne sont pas valeurs manquantes et compte le nombre de numéro siren unique pour chaque groupe
                                                                          # ça renvoie une serie indexée par "nom_col"
    series_comptage=series_comptage.rename("effectif")  # renomme la colonne de comptage de façon plus parlante
    return series_comptage  # retourne la Series voulue
  
  
test4=nb_par_lieu(df,"region_char") 




# 4.
# définition de la fonction qui renvoie le nombre de start-ups partenaires de la structure ESR (précisée en argument) par lieu (précisé en argument) sous forme de Series
def impl_partenaires(df,nom_structure,nom_col):
    df_filtre=startups_liees(df,nom_structure)  # on récupère le dataframe des start-ups partenaires de "nom_structure"
    comptage=nb_par_lieu(df_filtre,nom_col)  # on créé la Series qui va compter le nombre de start-ups partenaires par "nom_col"
    return comptage.sort_values(ascending=False)  # retourne la Series voulue, triée par ordre décroissant pour une meilleure lisibilité


test5=impl_partenaires(df, "Université de Tours", "depart_char")




## Startups ayant cessé leur activité ##

# 5.
# définition de la fonction qui renvoie le dataframe des start-ups ayant fermé, avec une nouvelle colonne prenant comme valeur la durée de vie de ces start-ups
def startups_fermees(df):
    df_filtre=df[df["statut"]==False].copy()  # récupère le dataframe contenant toutes les start-ups qui ont fermé
                                              # le .copy() permet d'éviter un warning dans la console
    df_filtre=df_filtre.dropna(subset=["date_fermeture"])  # on retire les lignes pour lesquelles "date_fermeture" est valeur manquante pour éviter les problèmes lors du calcul de "duree_de_vie"
    df_filtre["duree_de_vie"]=df["date_fermeture"]-df["date_crea"]  # création de la colonne "duree_de_vie"
    df_filtre=df_filtre[df_filtre["duree_de_vie"]>=pd.Timedelta(0)]  # on retire les lignes pour lesquelles "duree_de_vie" est négative car cela n'a pas de sens et fausserait les calculs de moyenne par exemple
    return df_filtre  # retourne le dataframe voulu


test6=startups_fermees(df)
print(test6.dtypes)  # on a bien duree_de_vie de type timedelta64



# 6.
# définition de la fonction qui renvoie la base des start-ups (partenaires de la structure passée en arguments) qui ont cessé leur activité
def partenaires_fermees(df,nom_structure):
    df_filtre=startups_fermees(df)  # création du dataframe contenant toutes les start-ups ayant fermé, avec la colonne "duree_de_vie"
    return startups_liees(df_filtre,nom_structure)  # retourne le dataframe voulu


test7=partenaires_fermees(df, "Centre national de la recherche scientifique")



# 7.
# définition de la fonction qui renvoie le nombre de start-ups fermé par région
def nb_fermees_region(df):
    df_filtre=startups_fermees(df)  
    comptage=nb_par_lieu(df_filtre,"region_char")  # créé la Series donnant le nombre de start-ups fermées par région
    return comptage  # retourne la Series créée


test8=nb_fermees_region(df)

    

# 8.
# création de la variable prenant comme valeur la durée de vie moyenne des start-ups fermées
df_fermees=startups_fermees(df)
duree_vie_moy_fermees=df_fermees["duree_de_vie"].mean()
print(duree_vie_moy_fermees)


# création des 15 variables prenant comme valeur la durée de vie moyenne des start-ups fermées pour chaque région
regions=df_fermees["region_char"].dropna().unique()  # création d'un vecteur contenant toutes les valeurs possibles de "region_char"
print(regions)    
    
for region in regions:
    df_filtre=df_fermees[df_fermees["region_char"]==region]  # on filtre selon la région
    ddvm=df_filtre["duree_de_vie"].mean()  # calcul de la durée de vie moyenne
    
    nom_var="ddvm_"+region.replace(" ","_").replace("-","_").replace("'","_")  # création des noms variables, qui seront sous la forme "ddvm_'region_char'". 
                                                                               # les .replace() permettent de remplacer les caractères qui seraient problématiques.
    globals()[nom_var]=ddvm  # création des variables globales s'appelant nom_var créé plus tôt et valant la durée de vie moyenne calculée
    
    
    
# alternative dictionnaire, plus optimisée
ddvm_par_region={}  # création d'un dictionnaire vide
for region in regions:
    df_filtre=df_fermees[df_fermees["region_char"]==region]
    ddvm_par_region[region]=df_filtre["duree_de_vie"].mean()  # region est la clé du dictionnaire, et la durée de vie moyenne calculée est sa valeur
    
print(ddvm_par_region)    





## Actifs produits par les entreprises ##
    
# 9.
# définition de la fonction qui renvoie le dataframe des entreprises en possession du type d'actif passé en argument
def avec_actif(df,nom_actif):
    tri=[] # on définit un vecteur vide
    
    # on va tester la correspondance de nom_actif pour chaque ligne, en découpant les cellules en elements s'il y a une virgule
    for cellule in df["actifs"]:
        correspondance=False
        if pd.notna(cellule):
            elements=str(cellule).split(",")
            for e in elements:
                if e.strip()==nom_actif:
                    correspondance=True
                    break
                    # si la condition est validée, càd si on trouve un element de cellule égal à nom_actif on arrête de tester les éléments de cette cellule, et on affecte True à correspondance
              
        # pour chaque ligne de df on ajoute True si correspondance, ou False si non-correspondance 
        # tri est donc un vecteur booléen de taille len(df)
        # il permettra de trier les lignes à restituer dans le df de sortie de fonction, càd seulement les lignes pour lesquelles la startup possède le type d'actif indiqué en argument
        tri.append(correspondance)
    
    df_filtre=df[tri].set_index("siren")  # met la colonne "siren" en index
    return df_filtre  # retourne le dataframe voulu

    
test9=avec_actif(df,"Brevet")
    
    
    
    
# 10.
# définition de la fonction qui renvoie un dataframe contenant les nombre d'occurence de chaque élément de l'ensemble passé en argument
def nb_par_categorie(df,nom_col,ensemble):
    dico={}  # création d'un dictionnaire vide
    for e in ensemble:
        compteur=0  # on initie la variable de comptage à 0 pour chaque élément de l'ensemble
        for cellule in df[nom_col]:
            if pd.notna(cellule):
                elements=cellule.split(",")
                for x in elements:
                    if x.strip()==e:
                        compteur+=1  # si on trouve une correspondance entre l'élément de l'ensemble précisé en argument qui est testé 
                                     # avec un des éléments de la cellule de df[nom_col], on ajoute +1 à la variable de comptage
                        break  # arrête de chercher une correspondance si il y en a une qui a été trouvée
        dico[e]=compteur  # ajoute la clé "e" au dictionnaire, dont la valeur vaut "compteur"
        
    df_compte=pd.DataFrame.from_dict(dico, orient="index", columns=["nombre"])  # création du dataframe indexé par les clés de dico contenant une colonne "nombre" valant le nombre d'occurence de chaque clé
    return df_compte  # retourne le dataframe voulu


test10=nb_par_categorie(df,"actifs",{"Brevet","Savoir-faire secret","Logiciel"})




# 11.
# création de la fonction qui renvoie le nombre d'entreprises possédant le type d'actif donné en argument
def nb_startup_actif(df,actif):
    df_filtre=avec_actif(df,actif)
    nb_startup=len(df_filtre)  # récupère le nombre de lignes du df filtré, qui correspond au nombre de start-ups ayant l'actif passé en argument
    return nb_startup  # retourne le résultat souhaité


test11=nb_startup_actif(df, "Brevet")




# 12.
df_with_actif=df[df["actifs"].notna()]  # on créé le dataframe qui contient toutes les start-ups ayant au moins un actif
type_actif=ensemble_valeurs(df_with_actif,"actifs")  # on stocke dans un ensemble toutes les valeurs possibles de "actifs"

dict_actif={}  # on créée un dictionnaire vide
for actif in type_actif:
    compte=nb_startup_actif(df_with_actif,actif)  # comptage du nombre de start-up ayant l'actif testé dans la boucle for
    proportion=round(compte/len(df_with_actif) *100,1)  # calcul de la proportion en %
    dict_actif[actif]=proportion  # ajoute la clé "actif" au dictionnaire, dont la valeur vaut "proportion"




# 13.
# création de la fonction qui créé un histogramme représentant la répartition des types d'actifs parmi toutes les start-ups en possédant au moins un
def tracer_rep_actifs(df):
    df_with_actif=df[df["actifs"].notna()]
    type_actif=ensemble_valeurs(df_with_actif,"actifs")

    dict_actif={}
    for actif in type_actif:
        compte=nb_startup_actif(df_with_actif,actif)
        proportion=compte/len(df_with_actif) *100
        dict_actif[actif]=proportion
        
    actifs=sorted(dict_actif,key=dict_actif.get,reverse=True)  # on trie le dictionnaire par rapport à la valeur proportion (en décroissant) pour une meilleure lisibilité graphique
    proportion=[dict_actif[actif] for actif in actifs]
    
    
    plt.figure(figsize=(12,6))  # gère la taille du graphique généré
    barres=plt.bar(actifs,proportion,color="coral",edgecolor="firebrick")  # initiation des différentes barres de l'histogramme
    
    # valeurs au dessus des barres :
    for barre in barres:
        hauteur=barre.get_height()  # on récupère la hauteur de chaque barre
        plt.text(barre.get_x()+barre.get_width()/ 2,hauteur+0.5,f"{hauteur:.1f}%",ha="center")  # on affiche la proportion au dessus de la barre
    
    plt.ylabel("Proportion (en %)",fontsize=12)
    plt.title("Répartition des actifs parmi les start-ups\n(pour celles possédant au moins un actif)",fontweight="bold",fontsize=15)
    plt.xticks(rotation=45,ha="right")  # on tourne à 45° la légende sur l'axe des x (donc les types d'actifs) pour une bonne visibilité
    plt.show()


tracer_rep_actifs(df) 
    
    
    
# variante de la fonction précédente, pour voir la répartition des types d'actifs en fonction d'une structure ESR renseignée (qu'on va réutiliser plus tard)    
def tracer_rep_actifs_choix(df,nom_structure):
    df_choix=startups_liees(df, nom_structure)
    df_with_actif=df_choix[df_choix["actifs"].notna()]
    
    
    type_actif=ensemble_valeurs(df_with_actif,"actifs")

    dict_actif={}
    for actif in type_actif:
        compte=nb_startup_actif(df_with_actif,actif)
        proportion=compte/len(df_with_actif) *100
        dict_actif[actif]=proportion
        
    actifs=sorted(dict_actif,key=dict_actif.get,reverse=True)
    proportion=[dict_actif[actif] for actif in actifs]
    
    
    plt.figure(figsize=(12,6))
    barres=plt.bar(actifs,proportion,color="coral",edgecolor="firebrick")
    
    # valeurs au dessus des barres :
    for barre in barres:
        hauteur=barre.get_height()
        plt.text(barre.get_x()+barre.get_width()/ 2,hauteur+0.5,f"{hauteur:.1f}%",ha="center")
    
    plt.ylabel("Proportion (en %)",fontsize=12)
    plt.title(f"Répartition des actifs parmi les start-ups partenaires de {nom_structure}\n(pour celles possédant au moins un actif)",fontweight="bold",fontsize=15)
    plt.xticks(rotation=45,ha="right")
    plt.show()  
    
    
tracer_rep_actifs_choix(df, "Université d'Orléans")   
    
    
    
    
    


########################################
### PROGRAMME D'AFFICHAGE INTERACTIF ###
########################################


## Définition de fonctions utiles pour le programme ##

# fonction pour afficher le menu :
def menu(choix):
    print(f"Vous avez choisi {choix}.\n")
    print("Veuillez sélectionner l'action à effectuer :")
    print("   1- Partenariats de la structure ESR")
    print("   2- Implantation géographique des partenariats")
    print("   3- Étude sur les start-ups partenaires fermées")
    print("   4- Actifs produits par les start-ups partenaires")
    print("   5- Rapport complet")
    print("   6- Sélectionner une autre structure ESR")
    print("   Autre- Quitter\n")


# fonction pour générer le rapport général en PDF :
def generer_pdf(df, comptage_all, df_carte, regions, st_fermees, ddvm_par_region, dict_actif_trie, dict_compte, st_actifs):
    
    tmp_dir = tempfile.gettempdir()
    nom_fichier = "rapport_global_startups.pdf" # nom du fichier final
    
    # on récupère les styles reportLab par défaut
    doc = SimpleDocTemplate(nom_fichier, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()     
    
    style_analyse = ParagraphStyle('Analyse', parent=styles['Normal'], spaceAfter=6, spaceBefore=6)
    
    style_titre = ParagraphStyle('TitreSouligne', parent=styles['Title'],
                                  underline=True, textDecoration='underline') # titre principal souligné
    
    style_stats = ParagraphStyle('StatsGenerales', parent=styles['Heading1'],
                                  fontSize=14, alignment=TA_CENTER, spaceAfter=10) # on centre au mieux 
    style_section = ParagraphStyle('Section', parent=styles['Heading2'],
                                    fontSize=12, underline=True, textDecoration='underline',
                                    spaceBefore=10, spaceAfter=8)
    style_liste = ParagraphStyle('Liste', parent=styles['Normal'],
                                  leftIndent=0.5*cm, spaceAfter=0.1,fontSize=9)
    
    style_justifie = ParagraphStyle('Justifie', parent=styles['Normal'],
                                     alignment=4, spaceAfter=6, spaceBefore=6)   # affichage du texte en justifié
    
    story = []     # On crée une liste vide qui contiendra les éléments à ajouter au PDF

    # ===================== TITRE =====================
    story.append(Paragraph("<u>Analyse des données des start-ups liées à l'ESR français</u>", style_titre))
    story.append(Spacer(1, 20))

    # ===================== STATS GÉNÉRALES =====================
    story.append(Paragraph("Statistiques générales", style_stats))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Notre base de données répertorie les informations de <b>{len(df)}</b> start-ups françaises, "
        f"parmi lesquelles <b>{len(st_fermees)}</b> ont fermé.", style_analyse
    ))
    story.append(Spacer(1, 8))

    # ===================== RÉPARTITION PAR RÉGION ====================
    # liste par région le nombre de start-ups + combien ont fermé
    
    story.append(Paragraph("<u>Répartition géographique par région</u>", style_section))
    for region in comptage_all.index:
        nb = comptage_all.loc[region, "effectif"]
        fermees = comptage_all.loc[region, "nb_fermees"]
        if pd.notna(fermees):
            txt = f"• {region} : {nb} (dont {int(fermees)} {'a fermé' if fermees == 1 else 'ont fermé'})"
        else:
            txt = f"• {region} : {nb}" # si on ne connait pas le nb de fermées, on affiche juste l'effectif

        story.append(Paragraph(txt, style_liste))
    story.append(Spacer(1, 10))

    # ===================== CARTES CÔTE À CÔTE =====================
    # on génère 2 cartes (effectif + taux de fermeture)
    carte1_path = os.path.join(tmp_dir, "carte1.png")
    carte2_path = os.path.join(tmp_dir, "carte2.png")
    
    # --- Carte 1 : effectifs ---
    
    fig, ax = plt.subplots(1, 1, figsize=(6, 6))
    regions.plot(column="effectif", cmap="YlOrRd", legend=True, edgecolor="black",
                 linewidth=0.5, ax=ax, legend_kwds={'label': "Nombre de start-ups", 'shrink': 0.6})
    
    ax.set_title("Répartition globale du nombre\nde start-ups par région", fontsize=10, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(carte1_path, dpi=150, bbox_inches="tight") # on save
    plt.close() #on close pour éviter que ça s'accumule en mémoire 
    
# --- Carte 2 : proportion de fermées ---

    fig, ax = plt.subplots(1, 1, figsize=(6, 6))
    regions.plot(column="prop_fermees", cmap="YlOrRd", legend=True, edgecolor="black",
                 linewidth=0.5, ax=ax, legend_kwds={'label': "Taux de fermeture (%)", 'shrink': 0.6})
    
    ax.set_title("Part de start-ups ayant fermé\npar région", fontsize=10, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(carte2_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    # on crée 2 images à partir des PNG générés
    
    img1 = Image(carte1_path, width=8.5*cm, height=8.5*cm)
    img2 = Image(carte2_path, width=8.5*cm, height=8.5*cm)
    
    carte_table = Table([[img1, img2]]) # met les 2 images sur la meme ligne 
    carte_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                      ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story.append(carte_table)
    story.append(Spacer(1, 10))
    
    
    # --- Commentaire d'analyse ---
     
    
    story.append(Paragraph(
        "Sans surprise, l'Île-de-France s'impose comme la région privilégiée des start-ups : "
        "elle concentre à elle seule près d'un quart des effectifs de notre base de données. "
        "À l'inverse, les régions Centre-Val de Loire et la Corse sont beaucoup moins représentées "
        "dans cet écosystème, et semblent donc peu attractives concernant les start-ups.", style_justifie
    ))
    story.append(Paragraph(
        "En analysant le taux de fermeture par région, nous remarquons que 4 d'entre elles sont "
        "particulièrement touchées : la Nouvelle-Aquitaine, la Normandie, la Corse et le Centre-Val de Loire.",
        style_justifie
    ))
    
    
    # ===================== DURÉE DE VIE =====================
    # on passe à une nouvelle page et on donne une durée de vie moyennes des start-ups fermées 
    
    story.append(PageBreak()) #on passe à la page suivante
    story.append(Paragraph("<u>Durée de vie des start-ups ayant fermé</u>", style_section))
    story.append(Paragraph(
        f"La durée de vie moyenne des start-ups ayant fermé est de "
        f"<b>{st_fermees['duree_de_vie'].mean().days} jours</b>.", style_analyse
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Durée de vie moyenne par région :", styles['Normal']))
    
    
    for region, duree in ddvm_par_region.items(): #ddvm = durée de vie moyenne 
        story.append(Paragraph(f"• {region} : {duree.days} jours", style_liste))
    story.append(Spacer(1, 10))

    # ===================== ACTIFS =====================
    # on affiche ici les stats sur les actifs (combien de start-ups ont au moins un actif) réparti par type + un histogramme
    
    story.append(Paragraph("<u>Répartition des actifs</u>", style_section))
    story.append(Paragraph(
        f"Parmi nos {len(df)} start-ups, <b>{len(st_actifs)}</b> sont en possession d'au moins un actif "
        f"(soit {round(len(st_actifs)/len(df)*100,1)}% d'entre elles).", style_analyse
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Répartition des actifs parmi ces start-ups :", styles['Normal']))
    
    for actif, prop in dict_actif_trie.items(): # actif déjà trié
        story.append(Paragraph(f"• {actif} : {prop}% | {dict_compte[actif]} start-ups", style_liste))
    story.append(Spacer(1, 10))
    
    # --- Histogramme des actifs ---
    histo_path = os.path.join(tmp_dir, "histogramme_actifs.png")
    
    fig, ax = plt.subplots(figsize=(10, 5)) #on prend assez large pour faire tenir les labels 
    
    ax.barh(list(dict_actif_trie.keys()), list(dict_actif_trie.values()), color="coral", edgecolor="black")
    ax.set_xlabel("Proportion (%)")
    ax.set_title("Répartition des actifs parmi les start-ups", fontweight="bold")
    ax.invert_yaxis()   # pour avoir le plus grand en haut (plus “naturel” à lire si dict trié décroissant)
    plt.tight_layout()
    plt.savefig(histo_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    # insertion de l’histogramme dans le PDF
    story.append(Image(histo_path, width=14.6*cm, height=6.25*cm))
    
    story.append(Spacer(1, 10))
    
    # interprétation des résultats
    story.append(Paragraph(
        "L'analyse de ces données révèle que la détention d'actifs n'est pas une norme : "
        "à peine une start-up sur cinq (19,6 %) fait le choix de protéger ses innovations de cette manière.",
        style_justifie
    ))
    story.append(Paragraph(
        "Parmi ces entreprises, on observe une très forte asymétrie dans la répartition des actifs, "
        "très largement dominée par le brevet. Ce dernier s'impose comme l'outil de protection de référence, "
        "possédé par plus de trois quarts d'entre elles (77,4 %). "
        "Derrière le brevet, les logiciels (16,1 %) et le savoir-faire secret (9,8 %) représentent "
        "tout de même une part significative des stratégies de protection. "
        "En revanche, le recours à toutes les autres catégories d'actifs (APP, droits d'auteur, "
        "bases de données, matériel biologique, etc.) s'avère purement anecdotique.",
        style_justifie
    ))
    
    # ===================== BUILD =====================
    
    doc.build(story)
    return nom_fichier # compile et écrit le pdf 




# seconde fonction pour générer le rapport de la structure ESR renseignée par l'utilisateur :
    # on veut générer un pdf "ciblé" sur une structure ESR que l'utilisateur choisira 
    
def generer_pdf_structure(df, choix, df_choix, df_fermees_choix, structures_partenaires,
                          repart_all, df_carte, departements, ddvm_par_depart,
                          df_actif_choix, dict_actif_trie, dict_compte, type_actif):
    
    tmp_dir = tempfile.gettempdir() # on crée un dossier temporaire pour stocker les images 
    nom_fichier = f"rapport_{choix.replace(' ','_')}.pdf"
    
    # mise en page 
    doc = SimpleDocTemplate(nom_fichier, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm) 
    
    # on définit les styles de texte pour chaque partie du pdf 
    
    styles = getSampleStyleSheet()
    style_analyse = ParagraphStyle('Analyse', parent=styles['Normal'], spaceAfter=6, spaceBefore=6)
    style_titre = ParagraphStyle('TitreSouligne', parent=styles['Title'],
                                  underline=True, textDecoration='underline')
    style_section = ParagraphStyle('Section', parent=styles['Heading2'],
                                    fontSize=12, underline=True, textDecoration='underline',
                                    spaceBefore=10, spaceAfter=8)
    style_liste = ParagraphStyle('Liste', parent=styles['Normal'],
                                  leftIndent=0.5*cm, spaceAfter=0, fontSize=9, leading=11)
    
    story = [] 

    # ===================== TITRE =====================
    story.append(Paragraph(f"<u>Rapport complet sur {choix}</u>", style_titre))
    story.append(Spacer(1, 20))

    # ===================== 1. PARTENARIATS =====================
    # combien de start-ups sont liées + combien ont fermé
    story.append(Paragraph("<u>1. Partenariats de la structure ESR</u>", style_section))
    story.append(Paragraph(
        f"Nombre de start-ups liées : <b>{len(df_choix)}</b>, parmi lesquelles "
        f"<b>{len(df_fermees_choix)}</b> ont fermé.", style_analyse
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Liste des start-ups partenaires :", styles['Normal']))
    liste_closed = ensemble_valeurs(df_fermees_choix, "nom") # on récupère la liste des noms des start-ups fermées
    
    # Construire la liste des noms
    noms = []
    for startup in df_choix["nom"].sort_values(): #tri alphabétique des noms
        if startup in liste_closed:
            noms.append(f"• {startup} (qui a fermé)")
        else:
            noms.append(f"• {startup}")
    
    # Répartir sur 2 colonnes (plus lisible si liste longue)
    moitie = (len(noms) + 1) // 2
    col1 = noms[:moitie]
    col2 = noms[moitie:]
    
    # Compléter si nombre impair
    while len(col2) < len(col1):
        col2.append("")
    
    # Créer le tableau
    table_data = []
    
    # on transforme chaque texte en Paragraph pour garder le style 
    for g, d in zip(col1, col2):
        table_data.append([Paragraph(g, style_liste), Paragraph(d, style_liste)])
    
    t = Table(table_data, colWidths=[9*cm, 9*cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t)  # permet d'afficher la liste sur 2 colonnes pour optimiser l'espace sur le pdf
    story.append(Spacer(1, 8))
    
    # affichage des structures ESR partenaires
    
    story.append(Paragraph(
        f"Nombre de structures ESR liées : <b>{len(structures_partenaires)}</b>.", style_analyse
    ))
    story.append(Paragraph("Liste des structures ESR partenaires :", styles['Normal']))
    noms_structures = [f"• {structure}" for structure in sorted(structures_partenaires)] # sorted pour que ça soit plus propre (ordre alphabétique)
    
    moitie = (len(noms_structures) + 1) // 2
    col1 = noms_structures[:moitie]
    col2 = noms_structures[moitie:]
    
    while len(col2) < len(col1):
        col2.append("")
    
    table_data = []
    for g, d in zip(col1, col2):
        table_data.append([Paragraph(g, style_liste), Paragraph(d, style_liste)])
    
    t = Table(table_data, colWidths=[9*cm, 9*cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t)  # permet d'afficher la liste sur 2 colonnes pour optimiser l'espace sur le pdf
    story.append(Spacer(1, 10))

    # ===================== 2. IMPLANTATION GÉOGRAPHIQUE ====================
    # répartition par département + cartes des départements
    
    story.append(Paragraph("<u>2. Implantation géographique des partenariats</u>", style_section))
    story.append(Paragraph(
        f"Répartition des {len(df_choix)} start-ups partenaires par département :", style_analyse
    ))

    for departement in repart_all.index: # repart_all = tableau des effectifs par département 
        nb = repart_all.loc[departement, "effectif"] # nb de start ups dans ce département 
        fermees = repart_all.loc[departement, "nb_fermees"]  #nb de fermées
        if pd.notna(fermees):
            txt = f"• {departement} : {nb} (dont {int(fermees)} {'a fermé' if fermees == 1 else 'ont fermé'})"
        else:
            txt = f"• {departement} : {nb}"
        story.append(Paragraph(txt, style_liste))
    story.append(Spacer(1, 10))

    # Carte par département
    # on veut générer une carte en PNG puis l'insérer dans le PDF 
    
    carte_path = os.path.join(tmp_dir, "carte_departements.png")
    # missing_kwds : on met du gris clair pour les départements sans données pour plus de visibilité
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    departements.plot(column="effectif", cmap="YlOrRd", legend=True, edgecolor="black",
                      linewidth=0.5, ax=ax, legend_kwds={'label': "Nombre de start-ups partenaires", 'shrink': 0.6},missing_kwds={'color': 'lightgray', 'edgecolor': 'black', 'linewidth': 0.5})
    
    ax.set_title(f"Répartition globale du nombre de start-ups\npartenaires de {choix}\npar département", fontsize=10, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(carte_path, dpi=150, bbox_inches="tight")
    plt.close()

    story.append(Image(carte_path, width=12*cm, height=12*cm)) # insertion dans le pdf
    story.append(Spacer(1, 10))

    # ===================== 3. START-UPS FERMÉES =====================
    # on analyse uniquement les startups partenaires qui ont fermés 
    
    story.append(Paragraph("<u>3. Étude sur les start-ups partenaires fermées</u>", style_section))

    if df_fermees_choix.empty:
        story.append(Paragraph("Aucune start-up partenaire n'a fermé.", style_analyse))
    else:
        story.append(Paragraph(
            f"Parmi les {len(df_fermees_choix)} start-ups partenaires ayant fermé, la durée de vie moyenne "
            f"est de <b>{df_fermees_choix['duree_de_vie'].mean().days} jours</b>.", style_analyse
        )) #on prend la durée moyenne
        story.append(Spacer(1, 6))
        
        story.append(Paragraph("Durée de vie moyenne par département :", styles['Normal']))
        
        for departement, duree in ddvm_par_depart.items():
            story.append(Paragraph(f"• {departement} : {duree.days} jours", style_liste))
    story.append(Spacer(1, 10))

    # ===================== 4. ACTIFS =====================
    # vérifit si les start-ups partenaires ont des actfis 
    
    story.append(Paragraph("<u>4. Actifs produits par les start-ups partenaires</u>", style_section))
    
    # on regarde si la start-up partenaire a au moins un actif ou non 
    if df_actif_choix.empty:
        story.append(Paragraph("Aucune des start-ups partenaires n'est en possession d'un actif.", style_analyse))
    else:
        story.append(Paragraph(
            f"Part des start-ups partenaires en possession d'au moins un actif : "
            f"<b>{round(len(df_actif_choix)/len(df_choix)*100,1)}%</b>.", style_analyse
        ))
        story.append(Spacer(1, 6))
        
        story.append(Paragraph(
            f"Répartition des actifs parmi les {len(df_actif_choix)} start-ups partenaires en possédant au moins un :",
            styles['Normal']
        ))
        for actif, prop in dict_actif_trie.items():
            story.append(Paragraph(f"• {actif} : {prop}% | {dict_compte[actif]} start-ups", style_liste))
        story.append(Spacer(1, 10))

        # --- Histogramme des actifs ---
        
        histo_path = os.path.join(tmp_dir, "histogramme_actifs_choix.png")
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.barh(list(dict_actif_trie.keys()), list(dict_actif_trie.values()), color="coral", edgecolor="black")
        ax.set_xlabel("Proportion (%)")
        ax.set_title(f"Répartition des actifs parmi les start-ups partenaires de {choix}", fontweight="bold")
        ax.invert_yaxis()
        plt.tight_layout()
        plt.savefig(histo_path, dpi=150, bbox_inches="tight")
        plt.close()

        story.append(Image(histo_path, width=14*cm, height=7*cm))

    # ===================== BUILD =====================
    doc.build(story)
    return nom_fichier







# définition d'une fonction programme qui comporte l'ensemble du rapport pour faciliter son appel
def programme():
    
    # ================== Rapport Global =======================
    # le but est d'afficher une analyse globale sur les start-ups de notre base de données, 
    # avant de rentrer dans une analyse plus détaillée en fonction des structures ESR.
    print("\n\nAnalyse des données des start-ups liées à l'ESR français\n\n")
    
    print("-"*60)
    print("Statistiques générales")
    
    # --- calcul préliminaire des variables qui vont nous servir par la suite ---
    
    st_fermees=startups_fermees(df)
    comptage_st_fermees=nb_par_lieu(st_fermees,"region_char").rename("nb_fermees")  # nb de fermées par région 
    comptage=nb_par_lieu(df, "region_char").sort_values(ascending=False)  # nb total par région dans l'ordre décroissant 
    comptage_all=pd.concat([comptage,comptage_st_fermees],axis=1)  # axis 1 pour concaténer en colonne
    st_actifs=df[df["actifs"].notna()]      # start-ups  qui ont au moins actif 
    type_actif=ensemble_valeurs(st_actifs,"actifs")  # ensemble des types d'actifs présents
    
    # --- résumé global ---
    print(f"\nNotre base de données répertorie les informations de {len(df)} start-ups françaises, parmi lesquelles {len(st_fermees)} ont fermé.")
    print("\nLeur répartition géographique par région est la suivante :")
    
    # afficher région par région (effectif + fermées si dispo), avec un pluriel propre
    for region in comptage_all.index:
        if pd.notna(comptage_all.loc[region,"nb_fermees"]):
            if comptage_all.loc[region,"nb_fermees"]==1:
                print(f' - {region} : {comptage_all.loc[region,"effectif"]} (dont {int(comptage_all.loc[region,"nb_fermees"])} a fermé)')
            else:
                print(f' - {region} : {comptage_all.loc[region,"effectif"]} (dont {int(comptage_all.loc[region,"nb_fermees"])} ont fermé)')
        else:
            print(f' - {region} : {comptage_all.loc[region,"effectif"]}')
    
    
    #====================== Création des Cartes =====================
    
    #le but des de construire 2 cartes : effectifs par région + taux de fermeture par région
    
    # préparation d'un dataframe regroupant les infos à montrer sur les cartes 
    df_carte=comptage_all.reset_index()  # région devient une colonne (plus simple pour merge)
    df_carte["prop_fermees"]=round(df_carte["nb_fermees"]/df_carte["effectif"]*100,1)
    
        
    # chargement d'une base de données permettant d'afficher une carte de la France optimisée par région
    url="https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions.geojson"
    regions=gpd.read_file(url)
        
        
    # jointure de notre df_carte avec la base de données chargée regions
    regions = regions.merge(df_carte,left_on="nom",right_on="region_char",how="left")
        
    
    # création et affichage des cartes
    
    # --- Carte 1 ---
    
    # répartition globale des start-ups par région : 
    fig,ax=plt.subplots(1,1,figsize=(10, 10))
    regions.plot(column="effectif",
                 cmap="YlOrRd",        # jaune > orange > rouge
                 legend=True,
                 edgecolor="black",
                 linewidth=0.5,
                 ax=ax,
                 legend_kwds={'label': "Nombre de start-ups"})
    ax.set_title("Répartition globale du nombre de start-ups\npar région en France métropolitaine",fontsize=14,fontweight="bold")
    ax.axis("off") #p as d'axes sur la carte
    plt.show()
    
    # --- Carte 2 ---
    
    # part des start-ups qui ont fermé par région 
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    regions.plot(column="prop_fermees",
                 cmap="YlOrRd",        # jaune > orange > rouge
                 legend=True,
                 edgecolor="black",
                 linewidth=0.5,
                 ax=ax,
                 legend_kwds={'label': "Taux de fermeture (%)"})
    ax.set_title("Part de start-ups ayant fermé\npar région en France métropolitaine",fontsize=14,fontweight="bold")
    ax.axis("off")
    plt.show()
    
    # commentaire 
    
    print('\nVous trouverez dans la fenêtre "Graphes" une carte montrant la répartition globale des start-ups par région en France métropolitaine, ainsi qu\'une seconde carte illustrant la part des start-ups ayant fermé par région.')
    print("\nSans surprise, l'Île-de-France s'impose comme la région privilégiée des start-ups : elle concentre à elle seule près d'un quart des effectifs de notre base de données."
          " À l'inverse', les régions Centre-Val de Loire et la Corse sont beaucoup moins représentées dans cet écosystème, et semblent donc peu attractives concernant les start-ups.")
    print("\nEn analysant le taux de fermeture par région, nous remarquons que 4 d'entre elles sont particulièrement touchées :"
          " la Nouvelle-Aquitaine, la Normandie, la Corse et le Centre-Val de Loire.")
    
    
    #========================================= Durée de vie Global ==========================
    #on veut calculer la durée de vie moyenne des start-ups fermées 
    
    print(f"\n\nLa durée de vie moyenne des start-ups ayant fermé est de {st_fermees['duree_de_vie'].mean().days} jours.")
    print("\nSi on regarde leur durée de vie moyenne par région, nous avons :")
    ddvm_par_region={}
    for region in comptage_st_fermees.index: # on filtre sur la région puis on fait moyenne
        ddvm_par_region[region]=st_fermees[st_fermees["region_char"]==region]["duree_de_vie"].mean()
        print(f" - {region} : {ddvm_par_region[region].days} jours")
    
    #===================================== Actifs ===========================
    # on calcule pour chaque nom d'actif le nombre de start-ups + la proportion 
    
    dict_actif={}   # dictionnaire vide  
    dict_compte={}  # dictionnaire vide
    
    for actif in type_actif:
        compte=nb_startup_actif(st_actifs,actif)  # compte combien de start-ups ont cet actif 
        proportion=round(compte/len(st_actifs) *100,1)  # proportion parmi celles qui ont au moins un actif 
        dict_actif[actif]=proportion  # ajoute "actif" en clé, et a pour valeur la proportion calculée
        dict_compte[actif]=compte  # ajoute "actif" en clé, et a pour valeur le compte calculé
    
    # on fait un tri décroissant par proportion 
    
    dict_actif_trie=dict(sorted(dict_actif.items(),reverse=True,key=lambda x: x[1]))
    print(f"\n\nParmi nos {len(df)} start-ups, {len(st_actifs)} sont en possession d'au moins un actif (soit {round(len(st_actifs)/len(df)*100,1)}% d'entre elles).")
    print("\nRépartition des actifs parmi ces start-ups :")
    for actif, prop in dict_actif_trie.items():
        print(f" - {actif} : {prop}% | {dict_compte[actif]} start-ups")
        
    tracer_rep_actifs(df) # histogramme de la répartition des actifs
    
    # rapport 
    print("\nL'analyse de ces données révèle que la détention d'actifs n'est pas une norme : à peine une start-up sur cinq (19,6 %) fait le choix de protéger ses innovations de cette manière.")
    print("Parmi ces entreprises, on observe une très forte asymétrie dans la répartition des actifs, très largement dominée par le brevet. Ce dernier s'impose comme l'outil de protection de référence, "
          "possédé par plus de trois quarts d'entre elles (77,4 %)."
          " Derrière le brevet, les logiciels (16,1 %) et le savoir-faire secret (9,8 %) représentent tout de même une part significative des stratégies de protection."
          " En revanche, le recours à toutes les autres catégories d'actifs (APP, droits d'auteur, bases de données, matériel biologique, etc.) s'avère purement anecdotique.")
    
    print('\nOuvrez la fenêtre "Graphes" afin de visualiser la répartition des actifs sous forme d\'histogramme.\n\n')
    
    
    print("-"*60)
    
    
    #================================== export PDF =====================
    # on veut proposer à l'utilisateur d'exporter le rapport global en PDF
    
    while True:
        print('Souhaitez-vous exporter ce rapport global portant sur l\'ensemble des start-ups au format PDF ? Tapez "OUI" ou "NON".\n')
        reponse=input("Votre réponse : ")
        if reponse.upper().strip()=="OUI": # fonctionne peu importe la casse et les espaces 
            nom_fichier = generer_pdf(df, comptage_all, df_carte, regions,
                                      st_fermees, ddvm_par_region,
                                      dict_actif_trie, dict_compte, st_actifs)   
            
            print(f"\nLe rapport PDF a été généré : {nom_fichier}")
            break
        
        elif reponse.upper().strip()=="NON":
            print("\nTrès bien. Pas de PDF généré.")
            break
        
        else:
            print('\nRéponse invalide, veuillez taper "OUI" ou "NON".\n')  # tant que la réponse n'est pas "OUI" ou "Non", le programme reposera la question
            
    print("-"*60)
    print("\n\n")
    
    #============================= choix structure ESR =======================================
    # # affiche les structures ESR disponibles, demande un choix valide, puis entre dans le menu d'actions.
    
    ens_structures_esr=sorted(ensemble_valeurs(df,"esr_nom"))  # liste triée par ordre alphabétique de toute les structures ESR
    while True:
        
        print(f"Voici les {len(ens_structures_esr)} structures ESR répertoriées dans la base de données :\n")
        for e in ens_structures_esr:
            print(f" - {e}")
        
        print("\nVeuillez taper le nom de la structure que vous souhaitez analyser.\n")
        choix=input("Votre choix : ")
        
        # permet de forcer un choix existant 
        
        choix_possibles=ensemble_valeurs(df, "esr_nom")
        while choix not in choix_possibles:
            print("\n\nChoix invalide, veuillez réessayer en faisant attention à la casse et aux espaces.")
            print(f"\n\nVoici les {len(ens_structures_esr)} structures ESR répertoriées dans la base de données :\n")
            for e in ens_structures_esr:
                print(f" - {e}")
        
            print("\nVeuillez taper le nom de la structure que vous souhaitez analyser.\n")
            choix=input("Votre choix : ")
        
    
        # --- calcul préliminaire des variables qui vont nous servir par la suite ---
        
        df_choix=startups_liees(df,choix)  # starups liées à la structure
        structures_partenaires=sorted(st_partenaires(df,choix))   # autres structures ESR en partenariat
        df_fermees_choix=startups_fermees(df_choix)               # start-ups liées qui ont fermé
        
        liste_closed=ensemble_valeurs(df_fermees_choix,"nom") # lensemble des noms des start-ups fermées
        liste_fermees=nb_par_lieu(df_fermees_choix,"depart_char").rename("nb_fermees") # liste du nombre de fermées par département
        df_actif_choix=df_choix[df_choix["actifs"].notna()]  #start-ups partenaires avec actifs
        type_actif=ensemble_valeurs(df_actif_choix,"actifs") # type d'actif présent pour cette structure 
        
        
        print("\n")
        quitter=False # initiation de la variable qui va permettre de quitter le programme si elle vaut True
        
        #==================================== Menu d'action ===================================
        #boucle principal, l'utilisateur doit choisir une action sur la structure séléctionnée
        while True :
            print("-"*60)
            menu(choix) # permet d'afficher les options possibles pour l'utilisateur
            action=input("Votre choix : ")  # l'utilisateur rentre son choix
            print("-"*60)
            
            
            
            # --- Action 1 : Partenariats ---
            
            if action=="1":
                print(f"\nNombre de start-ups liées : {len(df_choix)}, parmi lesquelles {len(df_fermees_choix)} ont fermé.\n")
                print("Liste des start-ups partenaires :")
                for startup in df_choix["nom"].sort_values():  # permet un affichage dans l'ordre alphabétique
                    if startup in liste_closed:   # =si le nom de la start-up est dans la liste des start-up ayant fermé (liste_closed)
                        print(f" - {startup} (qui a fermé)") 
                    else:
                        print(f" - {startup}")
                        
                print(f"\n\nNombre de structures ESR liées : {len(structures_partenaires)}.\n")
                print("Liste des structures ESR partenaires :")
                for structure in structures_partenaires:
                    print(f" - {structure}")
                
                print("\n")
                
                
                
            # --- Action 2 : implantation géographique ---
            
            elif action=="2":
                print(f"\nRépartition des {len(df_choix)} start-ups partenaires par département :")
                repart_choix=impl_partenaires(df,choix, "depart_char") # effectif par département 
            
                # on fusionne par colonne le total des startups et le nombre de strcutures fermées
                repart_all=pd.concat([repart_choix,liste_fermees],axis=1) 
            
            # affiche le total par département et le nombre de start-ups fermées (si il y en a)
    
                for departement in repart_all.index:
                    if pd.notna(repart_all.loc[departement,"nb_fermees"]):
                        if repart_all.loc[departement,"nb_fermees"]==1:
                            print(f" - {departement} : {repart_all.loc[departement,'effectif']} (dont {int(repart_all.loc[departement,'nb_fermees'])} a fermé)")
                        else:
                            print(f" - {departement} : {repart_all.loc[departement,'effectif']} (dont {int(repart_all.loc[departement,'nb_fermees'])} ont fermé)")
                    else:
                        print(f" - {departement} : {repart_all.loc[departement,'effectif']}")
                    
                        
                
                # préparation d'un dataframe regroupant les infos à montrer sur les cartes 
                
                df_carte=repart_all.reset_index().fillna(0)  # NaN -> 0 pour éviter des trous dans les calculs
                df_carte["prop_fermees"]=round(df_carte["nb_fermees"]/df_carte["effectif"]*100,1)
                
                # chargement d'une base de données permettant d'afficher une carte de la France optimisée par département
                url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements.geojson"
                departements=gpd.read_file(url)
                
                # jointure de notre df_carte avec la base de données chargée departements
                departements = departements.merge(df_carte, left_on="nom", right_on="depart_char", how="left")
                departements["effectif"]=departements["effectif"]
        
                #--- création et affichage des cartes ---
        
                # carte illustrant la répartition globale des start-ups partenaires par départements : 
                fig, ax = plt.subplots(1, 1,figsize=(10, 10))
                departements.plot(
                    column="effectif",
                    cmap="YlOrRd",        # jaune > orange > rouge
                    legend=True,
                    edgecolor="black",
                    linewidth=0.5,
                    ax=ax,
                    legend_kwds={'label':"Nombre de start-ups partenaires"},
                    missing_kwds={'color':'lightgray','edgecolor':'black','linewidth': 0.5}  # on met les valeurs manquantes en gris pour une meilleure lecture de carte
                )
                ax.set_title(f"Répartition globale du nombre de start-ups\npartenaires de {choix}\npar département en France métropolitaine",fontsize=14,fontweight="bold")
                ax.axis("off")
                plt.show()
                
                print(f'\nOuvrez la fenêtre "Graphes" afin de visualiser une carte illustrant la répartition des start-ups partenaires de {choix} en France métropolitaine.')
                
                print("\n")
                
                
                
            # --- Action 3 : stratups fermées ---
                
            elif action=="3":
                if df_fermees_choix.empty:
                    print("\n\nAucune start-up partenaire n'a fermé.")
                
                else:
                    print(f"\n\nParmi les {len(df_fermees_choix)} start-ups partenaires ayant fermé, la durée de vie moyenne est de {df_fermees_choix['duree_de_vie'].mean().days} jours.")
                    print("\nSi on s'intéresse aux durées de vie moyenne par département, nous avons :")
                    ddvm_par_depart={}
                    for departement in liste_fermees.index:
                        ddvm_par_depart[departement]=df_fermees_choix[df_fermees_choix["depart_char"]==departement]["duree_de_vie"].mean()
                        print(f" - {departement} : {ddvm_par_depart[departement].days} jours")
                
                print("\n")
                
                
            # --- action 4 : actif ---    
            
            elif action=="4":
                if df_actif_choix.empty:
                    print("\n\nAucune des start-ups partenaire n'est en possession d'un actif.")
                
                else:
                    # recalcule les répartitions d'actifs pour cette structure
                    dict_actif={}
                    dict_compte={}
                    for actif in type_actif:
                        compte=nb_startup_actif(df_actif_choix,actif)
                        proportion=round(compte/len(df_actif_choix) *100,1)
                        dict_actif[actif]=proportion
                        dict_compte[actif]=compte
            
                    dict_actif_trie=dict(sorted(dict_actif.items(),reverse=True,key=lambda x: x[1]))
            
                    print(f"\n\nPart des start-ups partenaires en possession d'au moins un actif : {round(len(df_actif_choix)/len(df_choix)*100,1)}%.")
                    print(f"\nRépartition des actifs parmi les {len(df_actif_choix)} start-ups partenaires en possédant au moins un :")
                    for actif, prop in dict_actif_trie.items():
                        print(f" - {actif} : {prop}% | {dict_compte[actif]} start-ups")
                        
                    tracer_rep_actifs_choix(df,choix) # histogramme de répartition des actifs adapté à la structure
                    
                    print('\nOuvrez la fenêtre "Graphes" afin de visualiser la répartition des actifs sous forme d\'histogramme.')
        
                print("\n")
                
                
                
            # --- Action 5 : rapport complet ---
            # Combiner  les actions 1-4 en mode "rapport" puis proposer un export PDF
                
            elif action=="5":
                
                print(f"\n\nRapport complet sur {choix}")
                
                # partenariats
                
                print("\n\n 1. Partenariats de la structure ESR")
                print(f"\nNombre de startups liées : {len(df_choix)}, parmi lesquelles {len(df_fermees_choix)} ont fermé.\n")
                print("Liste des start-ups partenaires :")
                for startup in df_choix["nom"].sort_values():
                    if startup in liste_closed:
                        print(f" - {startup} (qui a fermé)")
                    else:
                        print(f" - {startup}")
                        
                print(f"\n\nNombre de structures ESR liées : {len(structures_partenaires)}.\n")
                print("Liste des structures ESR partenaires :")
                for structure in structures_partenaires:
                    print(f" - {structure}")
                    
                    
                    
               # implantation
               
                print("\n\n 2. Implantation géographique des partenariats")
                print(f"\nRépartition des {len(df_choix)} start-ups partenaires par département :")
                repart_choix=impl_partenaires(df, choix, "depart_char")
                repart_all=pd.concat([repart_choix,liste_fermees],axis=1)
            
                for departement in repart_all.index:
                    if pd.notna(repart_all.loc[departement,"nb_fermees"]):
                        if repart_all.loc[departement,"nb_fermees"]==1:
                            print(f" - {departement} : {repart_all.loc[departement,'effectif']} (dont {int(repart_all.loc[departement,'nb_fermees'])} a fermé)")
                        else:
                            print(f" - {departement} : {repart_all.loc[departement,'effectif']} (dont {int(repart_all.loc[departement,'nb_fermees'])} ont fermé)")
                    else:
                        print(f" - {departement} : {repart_all.loc[departement,'effectif']}")
                
                # préparation d'un dataframe regroupant les infos à montrer sur les cartes 
                
                df_carte=repart_all.reset_index().fillna(0)
                df_carte["prop_fermees"]=round(df_carte["nb_fermees"]/df_carte["effectif"]*100,1)
                
                # chargement d'une base de données permettant d'afficher une carte de la France optimisée par département
                
                url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements.geojson"
                departements=gpd.read_file(url)
                
                # jointure de notre df_carte avec la base de données chargée departements
                departements = departements.merge(df_carte,left_on="nom",right_on="depart_char",how="left")
                departements["effectif"]=departements["effectif"]
        
                # création et affichage des cartes
        
                # carte illustrant la répartition globale des start-ups partenaires par départements : 
                fig,ax=plt.subplots(1,1,figsize=(10, 10))
                departements.plot(
                    column="effectif",
                    cmap="YlOrRd",        # jaune > orange > rouge
                    legend=True,
                    edgecolor="black",
                    linewidth=0.5,
                    ax=ax,
                    legend_kwds={'label':"Nombre de start-ups partenaires"},
                    missing_kwds={'color':'lightgray','edgecolor':'black','linewidth':0.5}  # on met les valeurs manquantes en gris pour une meilleure lecture de carte
                )
                ax.set_title(f"Répartition globale du nombre de start-ups\npartenaires de {choix}\npar département en France métropolitaine",fontsize=14,fontweight="bold")
                ax.axis("off")
                plt.show()
                
                print(f'\nOuvrez la fenêtre "Graphes" afin de visualiser une carte illustrant la répartition des start-ups partenaires de {choix} en France métropolitaine.')
        
                # fermées
                
                print("\n\n 3. Étude sur les start-ups partenaires fermées")
                
                ddvm_par_depart={}   # initialisation du dictionnaire hors de la condition pour ne pas empêcher la création du pdf
                if df_fermees_choix.empty:
                    print("\nAucune start-up partenaire n'a fermé.")
                    
                else:
                    print(f"\nParmi les {len(df_fermees_choix)} start-ups partenaires ayant fermé, la durée de vie moyenne est de {df_fermees_choix['duree_de_vie'].mean().days} jours.")
                    print("\nSi on s'intéresse aux durées de vie moyenne par département, nous avons :")
                    for departement in liste_fermees.index:
                        ddvm_par_depart[departement]=df_fermees_choix[df_fermees_choix["depart_char"]==departement]["duree_de_vie"].mean()
                        print(f" - {departement} : {ddvm_par_depart[departement].days} jours")
                    
                # actifs     
                    
                    
                print("\n\n 4. Actifs produits par les start-ups partenaires")
                
                dict_actif={}   # initialisation des dictionnaires hors de la condition pour ne pas empêcher la création du pdf 
                dict_compte={}
                if df_actif_choix.empty:
                    print("\nAucune des start-ups partenaire n'est en possession d'un actif.")
                
                else:  
                    
                # calcule, pour chaque actif, le nombre de start-ups concernées et leur part
                    
                    for actif in type_actif:
                        compte=nb_startup_actif(df_actif_choix,actif)
                        proportion=round(compte/len(df_actif_choix) *100,1)
                        dict_actif[actif]=proportion
                        dict_compte[actif]=compte
                    
                    # trie les actifs du plus représenté au moins représenté
                    
                    dict_actif_trie=dict(sorted(dict_actif.items(),reverse=True,key=lambda x: x[1]))
                    
                    
                    
                    print(f"\nPart des start-ups partenaires en possession d'au moins un actif : {round(len(df_actif_choix)/len(df_choix)*100,1)}%.")
                    print(f"\nRépartition des actifs parmi les {len(df_actif_choix)} start-ups partenaires en possédant au moins un :")
                    for actif, prop in dict_actif_trie.items():
                        print(f" - {actif} : {prop}% | {dict_compte[actif]} start-ups")
                        
                    tracer_rep_actifs_choix(df,choix)  # Affiche l'histogramme de répartition des actifs
                    
                    print('\nOuvrez la fenêtre "Graphes" afin de visualiser la répartition des actifs sous forme d\'histogramme.')
                
                
                
                print("\n\n --- FIN DU RAPPORT ---")
                
                # --- Export pdf du rapport ---
                while True:
                    print('\n\nSouhaitez-vous une version PDF de ce rapport ? Tapez "OUI" ou "NON".\n')
                    reponse=input("Votre réponse : ")
                    
                    # Si OUI : génère le PDF puis quitte la boucle
                    
                    if reponse.upper().strip()=="OUI":
                        nom_fichier=generer_pdf_structure(df, choix, df_choix, df_fermees_choix, structures_partenaires,
                                                            repart_all, df_carte, departements, ddvm_par_depart,
                                                            df_actif_choix, dict_actif_trie, dict_compte, type_actif)
                        print(f"\nLe rapport PDF a été généré : {nom_fichier}\n\n")
                        break
                    # Si NON : pas de PDF, puis quitte la boucle
                    
                    elif reponse.upper().strip()=="NON":
                        print("\nTrès bien. Pas de PDF généré.\n\n")
                        break 
                    # si réponse invalide on redemande 
                    else:
                        print('\nRéponse invalide, veuillez taper "OUI" ou "NON".') 
                        
                        
            # --- Action 6 : changer de structure ---             
             # on revient au choix ESR 
            elif action=="6":
                print("\nRetour à la sélection d'une structure ESR.\n\n")
                break  # permet de quitter la seconde boucle while, et de retourner au choix de la structure ESR  
                
            # --- autre : quitter le programmme ---
                
            else:
                print("\nAu revoir !")
                print("\n\n --- FIN DU PROGRAMME ---")
                quitter=True  # affecte True à quitter afin de vérifier la condition d'arrêt de la première boucle while
                break  # permet de quitter la seconde boucle while
        
        # si utilisateur demande à quitter on casse aussi la boucle de séléction ESR 
        if quitter==True:
            break # on sort de la première boucle while -> fin du programme
    
            




##########################
### APPEL DU PROGRAMME ###
##########################

# appel de la fonction programme() définie précédemment, afin de simplifier la compilation pour l'utilisateur
# (il n'a pas à sélectionner tout le code de la ligne 881 à 1388 afin d'exécuter le programme)

programme()




                    #####     --- FIN DU SCRIPT ---     #####


#####################################################################################
#                                                                                   #
#            ### Script rédigé par Quentin RUEL et Olivier Baudouin ###             #
#                                                                                   #
#####################################################################################
