# Projet 3 : Préparation, analyse et prédiction

# Réalisé par Quentin RUEL et Olivier BAUDOUIN


# ANALYSE ET PREDICTION DES VALEURS MARCHANDES DES GARDIENS 
# DES 5 GRANDS CHAMPIONNATS SUR LES SAISONS DE 2018 à 2023


# Sources de données :
# - Stats des gardiens : FBref, Github
# - Valeurs marchandes et infos complémentaires : dcaribou (transfermarkt-datasets), Github



# mise en place des packages requis pour la compilation :
import pandas as pd
import numpy as np
import requests
import io
import gzip
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_absolute_error, r2_score



### 2.1 Préparation des données 

# Définition de fonctions utiles pour l'importation et la manipulation des données :

# Charge un fichier CSV compressé
def charger_csv_gz(url):
    response=requests.get(url)
    donnees= gzip.decompress(response.content)
    return pd.read_csv(io.BytesIO(donnees))


# Convertit l'âge du format 'années-jours' (comme '31-168') en nombre décimal
def convertir_age(valeur):
    if "-" in str(valeur):
        parties=str(valeur).split("-")
        return int(parties[0])+int(parties[1])/365
    return float(valeur)


# Détermine la saison correspondant à une date donnée
def attribuer_saison(date,bornes_saisons):
    for saison, (debut,fin) in bornes_saisons.items():
        if debut<=date<fin:
            return saison
    return None


# Importation des données :
    
# Base stats gardiens 
URL_STATS_2018_2023=("https://raw.githubusercontent.com/hadjdeh/football-data-analysis/main/Scraping_fbref_static_data/data/old_seasons/top5_leagues_keeper_2018_2019__2022_2023.csv")

# Petit nettoyage
df_fbref =pd.read_csv(URL_STATS_2018_2023)
df_fbref["age"]=df_fbref["age"].apply(convertir_age)
df_fbref=df_fbref.drop(["Unnamed: 0"],axis=1)
df_fbref["league_name"]=df_fbref["league_name"].str.removesuffix("-Stats")


# Bases valeurs marchandes et infos complémentaires
URL_VALUATIONS ="https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/player_valuations.csv.gz"
URL_PLAYERS="https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/players.csv.gz"

df_valuations=charger_csv_gz(URL_VALUATIONS)
df_players=charger_csv_gz(URL_PLAYERS)

# Filtrage pour garder les gardiens des 5 grands championnats
df_gardiens=df_players[
    (df_players["sub_position"]=="Goalkeeper") &
    (df_players["current_club_domestic_competition_id"].isin(["GB1","ES1", "IT1","L1","FR1"])) &
    (df_players["last_season"]>2017)]



# Jointure des valeurs marchandes avec infos gardiens
df_gk_valuations=df_valuations.merge(df_gardiens,on="player_id",how="inner")

df_gk_valuations=df_gk_valuations[df_gk_valuations["name"].isin(df_fbref["player"].unique())]

# Petit nettoyage
df_gk_valuations= df_gk_valuations[["date","market_value_in_eur_x","name","foot","height_in_cm","contract_expiration_date","international_caps"]].copy()
df_gk_valuations["date"]=pd.to_datetime(df_gk_valuations["date"])


# Attribution d'une valorisation par saison pour chaque gardien
BORNES_SAISONS={"2018-2019": (pd.Timestamp("2018-08-01"), pd.Timestamp("2019-08-01")),
                 "2019-2020": (pd.Timestamp("2019-08-01"), pd.Timestamp("2020-08-01")),
                 "2020-2021": (pd.Timestamp("2020-08-01"), pd.Timestamp("2021-08-01")),
                 "2021-2022": (pd.Timestamp("2021-08-01"), pd.Timestamp("2022-08-01")),
                 "2022-2023": (pd.Timestamp("2022-08-01"), pd.Timestamp("2023-08-01"))}

df_gk_valuations["saison"]=df_gk_valuations["date"].apply(
    lambda d: attribuer_saison(d, BORNES_SAISONS))
df_gk_valuations=df_gk_valuations.dropna(subset=["saison"])

# On garde la dernière valorisation de chaque gardien pour chaque saison
df_val_par_saison = (df_gk_valuations.sort_values("date").groupby(["name","saison"]).last().reset_index())



# Construction du dataframe principal 
df_all=df_fbref.merge(df_val_par_saison,left_on=["player","season"],right_on=["name","saison"],how="inner").drop(["name","saison"],axis=1)

df_all=df_all.sort_values(["player","season"]).copy()



# Features engineering

# on fill les valeurs manquantes avec 0
df_all["international_caps"]=df_all["international_caps"].fillna(0)

# Mois de contrat restants à la fin de la saison
df_all =df_all.dropna(subset=["contract_expiration_date"]).copy()
df_all["contract_expiration_date"]=pd.to_datetime(df_all["contract_expiration_date"])
df_all["fin_saison"]=pd.to_datetime(df_all["season"].str[-4:]+ "-06-30")
df_all["mois_contrat_restants"]=((df_all["contract_expiration_date"]-df_all["fin_saison"]).dt.days/30).round().astype(int)

# regroupement des nationalités peu représentées
top_nationalites=df_all["nationality"].value_counts().head(10).index
df_all["nationality_grouped"]=df_all["nationality"].apply(lambda x: x if x in top_nationalites else "OTHER")

# Ajout de variables pertinentes
df_all["win_pct"]=df_all["gk_wins"]/df_all["gk_games"].replace(0,1)
df_all["saves_per90"]=df_all["gk_saves"]/df_all["minutes_90s"].replace(0,1)

# Valeur marchande de la saison précédente
df_all["market_value_prev"]= df_all.groupby("player")["market_value_in_eur_x"].shift(1)

# on retire quelques colonnes
df_all.drop(["fin_saison","date","contract_expiration_date"],axis=1)



# Séparation des données en échantillon Train/Test :
# On va utiliser les données des saisons 2018-2019 à 2021-2022 pour le Train, soit 4 saisons complètes
# Et les données de la saison 2022-2023 pour le Test.

saisons_train=["2018-2019","2019-2020","2020-2021","2021-2022"]
saison_test="2022-2023"

df_train=df_all[df_all["season"].isin(saisons_train)].copy()
df_test=df_all[df_all["season"]==saison_test].copy()






### 2.2 Analyse et visualisation

# Analyse 1 : Evolution de la valeur marchande moyenne par ligue

def analyse_valeur_par_ligue(df):
    tableau=df.groupby(["season","league_name"])["market_value_in_eur_x"].mean().reset_index()
    tableau["market_value_in_eur_x"]=tableau["market_value_in_eur_x"]/1000000
    return tableau.pivot(index="season",columns="league_name",values="market_value_in_eur_x")

def afficher_valeur_par_ligue(tableau_plot):
    plt.figure(figsize=(10, 6))
    for ligue in tableau_plot.columns:
        plt.plot(tableau_plot.index,tableau_plot[ligue], marker="o",linewidth=2,label=ligue)
    plt.title("Évolution de la valeur marchande moyenne des gardiens par ligue", fontsize=14)
    plt.xlabel("Saison")
    plt.ylabel("Valeur marchande moyenne (M€)")
    plt.legend(loc="center left")
    plt.grid(True,alpha=0.3)
    plt.tight_layout()
    plt.show()
    


# Analyse 2 : Corrélation entre stats de performance et valeur marchande

# Matrice de corréltion
def analyse_correlations(df):
    colonnes_stats = ["age", "gk_save_pct","gk_clean_sheets_pct", "gk_goals_against_per90",
                      "gk_psxg_net_per90","gk_crosses_stopped_pct", "win_pct","gk_pct_passes_launched", 
                      "gk_def_actions_outside_pen_area_per90","international_caps","mois_contrat_restants", 
                      "market_value_in_eur_x"]
    return df[colonnes_stats].corr()

# sous forme de heatmap pour bien visualiser
def afficher_correlations(matrice):
    noms_courts = {"age":"Âge",
                   "gk_save_pct":"% arrêts",
                   "gk_clean_sheets_pct":"% clean sheets",
                   "gk_goals_against_per90":"Buts encaissés/90",
                   "gk_psxg_net_per90":"PSxG net/90",
                   "gk_crosses_stopped_pct":"% centres arrêtés",
                   "win_pct":"% victoires",
                   "gk_pct_passes_launched":"% passes longues",
                   "gk_def_actions_outside_pen_area_per90":"Actions déf hors surface/90",
                   "international_caps":"Sélections internationales",
                   "mois_contrat_restants":"Mois contrat restants",
                   "market_value_in_eur_x":"Valeur marchande"}
    matrice_plot=matrice.rename(index=noms_courts,columns=noms_courts)

    plt.figure(figsize=(12, 10))
    sns.heatmap(matrice_plot,annot=True, fmt=".2f",cmap="RdBu_r",center=0,vmin=-1,vmax=1,square=True,linewidths=0.5)
    plt.title("Corrélation entre stats de gardien et valeur marchande",fontsize=14)
    plt.tight_layout()
    plt.show()



# Analyse 3 : Comparaison top 20% et bottom 20%

def analyse_top_vs_bottom(df):
    seuil_haut=df["market_value_in_eur_x"].quantile(1-0.2)
    seuil_bas=df["market_value_in_eur_x"].quantile(0.2)

    top=df[df["market_value_in_eur_x"]>=seuil_haut]
    bottom= df[df["market_value_in_eur_x"]<=seuil_bas]

    colonnes = ["age", "gk_save_pct", "gk_clean_sheets_pct", "gk_goals_against_per90","gk_psxg_net_per90", 
                "win_pct", "international_caps","mois_contrat_restants", "gk_crosses_stopped_pct","gk_def_actions_outside_pen_area_per90"]
    return pd.DataFrame({"Top 20%":top[colonnes].mean(),"Bottom 20%": bottom[colonnes].mean()})


# Graphique en barre pour les stats en % et tableau récap
def afficher_top_vs_bottom(comparaison):
    noms_courts = {"age":"Âge",
                   "gk_save_pct":"% arrêts",
                   "gk_clean_sheets_pct":"% clean sheets",
                   "gk_goals_against_per90":"Buts enc./90",
                   "gk_psxg_net_per90":"PSxG net/90",
                   "win_pct":"% victoires",
                   "international_caps":"Sélections int.",
                   "mois_contrat_restants":"Mois contrat",
                   "gk_crosses_stopped_pct":"% centres arrêtés",
                   "gk_def_actions_outside_pen_area_per90":"Actions hors surf./90"}
    comparaison_plot=comparaison[["Top 20%","Bottom 20%"]].rename(index=noms_courts)
    comparaison_plot.loc["% victoires"]=comparaison_plot.loc["% victoires"]*100

    # Graphique en barre
    stats_a_afficher=["% arrêts","% clean sheets","% victoires","% centres arrêtés"]
    data_plot=comparaison_plot.loc[stats_a_afficher]
    x=range(len(data_plot))

    fig, ax=plt.subplots(figsize=(10,6))
    ax.bar([i- 0.35/2 for i in x],data_plot["Top 20%"],0.35,label="Top 20%",color="limegreen")
    ax.bar([i+ 0.35/2 for i in x],data_plot["Bottom 20%"],0.35, label="Bottom 20%",color="firebrick")
    ax.set_xticks(x)
    ax.set_xticklabels(data_plot.index,fontsize=11)
    ax.set_ylabel("Valeur (%)")
    ax.set_title("Profil des gardiens : Top 20% vs Bottom 20% par valeur marchande",fontsize=14)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3,axis="y")
    
    for i, stat in enumerate(data_plot.index):
        ax.text(i- 0.35/2, data_plot["Top 20%"][stat]+0.5,f"{data_plot['Top 20%'][stat]:.1f}",ha="center",fontsize=9)
        ax.text(i+ 0.35/2, data_plot["Bottom 20%"][stat]+0.5,f"{data_plot['Bottom 20%'][stat]:.1f}",ha="center",fontsize=9)
    plt.tight_layout()
    plt.show()

    # Tableau récapitulatif
    fig2, ax2=plt.subplots(figsize=(10,5))
    ax2.axis("off")
    table_data=comparaison_plot.round(2).reset_index()
    table_data.columns= ["Statistique", "Top 20%", "Bottom 20%"]
    table= ax2.table(cellText=table_data.values,colLabels=table_data.columns,cellLoc="center",loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2,1.8)
    
    for j in range(3):
        table[0,j].set_facecolor("lightgray")
        table[0,j].set_text_props(fontweight="bold")
    ax2.set_title("Comparaison détaillée Top 20% vs Bottom 20%",fontsize=14,pad=20)
    plt.tight_layout()
    plt.show()




### 2.3 Prédiction et classification

# Préparation des variables :

variables_cat = ["foot","league_name","nationality_grouped"]

variables_num = ["age", "height_in_cm","international_caps", "mois_contrat_restants","gk_games_starts", "minutes_90s", 
                 "win_pct","gk_goals_against_per90","saves_per90","gk_save_pct","gk_clean_sheets_pct","gk_pens_save_pct",
                 "gk_psxg_net_per90","gk_psnpxg_per_shot_on_target_against","gk_pct_passes_launched", "gk_passes_length_avg",
                 "gk_pct_goal_kicks_launched","gk_goal_kick_length_avg","gk_crosses_stopped_pct","gk_def_actions_outside_pen_area_per90","gk_avg_distance_def_actions"]

target="market_value_in_eur_x"

encoder=OneHotEncoder(sparse_output=False, handle_unknown="ignore")
encoded_train=encoder.fit_transform(df_train[variables_cat])
encoded_test=encoder.transform(df_test[variables_cat])
encoded_cols=list(encoder.get_feature_names_out(variables_cat))

all_features=variables_num + encoded_cols

X_train=pd.concat([df_train[variables_num].reset_index(drop=True),pd.DataFrame(encoded_train,columns=encoded_cols)],axis=1)

X_test= pd.concat([df_test[variables_num].reset_index(drop=True),pd.DataFrame(encoded_test,columns=encoded_cols)],axis=1)

# on passe la cible en log car la distribution est très asymétrique
y_train=np.log1p(df_train[target].reset_index(drop=True))
y_test=df_test[target].reset_index(drop=True)



# Avant de passer à la modélisation du modèle, on va faire une sélection de variables avec la méthode forward
# à chaque étape, on ajoute la variable qui maximise le R². On arrête quand l'amélioration est nulle ou < à 0.005
def selection_forward(X, y,features_candidates,n_max=10,cv=5):
    selected=[]
    scores=[]
    remaining=list(features_candidates)

    print("Sélection forward en cours...")
    print(f"{'Étape':<8} {'Variable ajoutée':<45} {'R² CV moyen':<12}")
    print("-"*65)

    for step in range(n_max):
        best_score=-np.inf
        best_feature= None

        for feature in remaining:
            test_features= selected+[feature]
            model=GradientBoostingRegressor(n_estimators=200,max_depth=4, learning_rate=0.05,subsample=0.8,random_state=42)
            cv_scores=cross_val_score(model, X[test_features], y, cv=cv, scoring="r2")
            mean_score=cv_scores.mean()
            if mean_score>best_score:
                best_score=mean_score
                best_feature=feature

        if scores and (best_score-scores[-1]<0.005):
            print(f"\n  Arrêt : l'ajout de '{best_feature}' n'améliore le R² que de "
                  f"{best_score - scores[-1]:.4f} (< 0.005)")
            break

        selected.append(best_feature)
        remaining.remove(best_feature)
        scores.append(best_score)
        print(f"{step + 1:<8} {best_feature:<45} {best_score:.4f}")

    return selected,scores


# Graphique de l'évolution du R² avec l'ajout de variables
def afficher_selection(selected,scores,couleur, titre=""):
    plt.figure(figsize=(10,6))
    plt.plot(range(1,len(scores)+1),scores,marker="o",linewidth=2,color=couleur)
    plt.xticks(range(1,len(scores)+1), selected,rotation=45,ha="right")
    plt.xlabel("Variable ajoutée")
    plt.ylabel("R² moyen (validation croisée)")
    plt.title(f"Sélection forward : évolution du R²{' - ' + titre if titre else ''}")
    plt.grid(True,alpha=0.3)
    plt.tight_layout()
    plt.show()



# MODELE SANS market_value_prev :

# Dans un premier temps, on essaie de prédire la valeur marchande des gardiens basé uniquement sur leurs performances et caractéristiques
selected_v1, scores_v1=selection_forward(X_train,y_train,all_features)

model_v1=GradientBoostingRegressor(n_estimators=500,max_depth=4,learning_rate=0.05,subsample=0.8, random_state=42)
model_v1.fit(X_train[selected_v1], y_train)
y_pred_v1=np.expm1(model_v1.predict(X_test[selected_v1]))

# df qui compare les valeurs réelles avec celles prédite du modèle 1
comparaison_v1=pd.DataFrame({"Gardien":df_test["player"].values,"Valeur réelle":y_test.values,"Valeur prédite": y_pred_v1.round().astype(int)})

# montre le poids des variables explicatives
importances_v1=pd.Series(model_v1.feature_importances_,index=selected_v1)


# MODELE AVEC market_value_prev :

# Comme les résultats n'étaient pas concluants sans market_value_prev, on l'ajoute pour voir si le meilleur indicateur 
# pour prédire la valeur marchande des gardiens à date est leur valeur précédente
df_train_v2=df_train.dropna(subset=["market_value_prev"]).copy()
df_test_v2= df_test.dropna(subset=["market_value_prev"]).copy()

encoded_train_v2=encoder.fit_transform(df_train_v2[variables_cat])
encoded_test_v2=encoder.transform(df_test_v2[variables_cat])
encoded_cols_v2=list(encoder.get_feature_names_out(variables_cat))

variables_num_v2=variables_num + ["market_value_prev"]
all_variables_v2=variables_num_v2 + encoded_cols_v2

X_train_v2= pd.concat([df_train_v2[variables_num_v2].reset_index(drop=True),pd.DataFrame(encoded_train_v2,columns=encoded_cols_v2)],axis=1)

X_test_v2= pd.concat([df_test_v2[variables_num_v2].reset_index(drop=True),pd.DataFrame(encoded_test_v2,columns=encoded_cols_v2)],axis=1)

y_train_v2=np.log1p(df_train_v2[target].reset_index(drop=True))
y_test_v2=df_test_v2[target].reset_index(drop=True)

selected_v2, scores_v2 = selection_forward(X_train_v2,y_train_v2,all_variables_v2)

model_v2=GradientBoostingRegressor(n_estimators=500,max_depth=4,learning_rate=0.05,subsample=0.8, random_state=42)
model_v2.fit(X_train_v2[selected_v2],y_train_v2)
y_pred_v2=np.expm1(model_v2.predict(X_test_v2[selected_v2]))

comparaison_v2=pd.DataFrame({"Gardien": df_test_v2["player"].values,"Valeur réelle":y_test_v2.values,"Valeur prédite": y_pred_v2.round().astype(int)})

importances_v2=pd.Series(model_v2.feature_importances_,index=selected_v2)


# Comparaison visuelle des prédictions des deux modèles grâce à un nuage de points :
def afficher_comparaison_modeles(y_reel_v1, y_pred_v1, r2_v1,y_reel_v2, y_pred_v2, r2_v2):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # conversion en millions
    reel_v1_m=y_reel_v1/1000000
    pred_v1_m=y_pred_v1/1000000
    reel_v2_m=y_reel_v2/1000000
    pred_v2_m=y_pred_v2/1000000

    axes[0].scatter(reel_v1_m,pred_v1_m,alpha=0.5, color="coral")
    max_val = max(reel_v1_m.max(), pred_v1_m.max())
    axes[0].plot([0, max_val], [0, max_val], "k--",alpha=0.5,label="Prédiction parfaite")
    axes[0].set_xlabel("Valeur réelle (M€)")
    axes[0].set_ylabel("Valeur prédite (M€)")
    axes[0].set_title(f"Sans market_value_prev\nR² = {r2_v1:.3f}")
    axes[0].legend()
    axes[0].grid(True,alpha=0.3)

    axes[1].scatter(reel_v2_m,pred_v2_m,alpha=0.5, color="navy")
    max_val = max(reel_v2_m.max(), pred_v2_m.max())
    axes[1].plot([0, max_val], [0, max_val], "k--",alpha=0.5,label="Prédiction parfaite")
    axes[1].set_xlabel("Valeur réelle (M€)")
    axes[1].set_ylabel("Valeur prédite (M€)")
    axes[1].set_title(f"Avec market_value_prev\nR² = {r2_v2:.3f}")
    axes[1].legend()
    axes[1].grid(True,alpha=0.3)

    plt.suptitle("Comparaison des deux modèles : valeurs prédites vs réelles",fontsize=14)
    plt.tight_layout()
    plt.show()


### 3. Programme et extension

# Dans un premier temps on met en place l'extension, parce qu'elle fera partie du programme

def afficher_liste_gardiens(df):
    gardiens=sorted(df["player"].unique())
    print(f"\n  Gardiens disponibles ({len(gardiens)}) :")
    print("  "+"-" * 40)
    for g in gardiens:
        print(f"  {g}")
    return gardiens

# affiche la fiche complète d'un gardien (infos, valeur marchande réelle vs prédite) et un graphique d'évolution de valeur
def fiche_gardien(nom,df_all,df_test_v2,y_pred_v2):
    df_joueur =df_all[df_all["player"]==nom].sort_values("season")
    print("\n"+"=" * 60)
    print(f"  FICHE GARDIEN : {nom}")
    print("=" * 60)
    
    date_naissance=df_gardiens[df_gardiens["name"]==nom]["date_of_birth"].values[0]
    nationalite= df_joueur["nationality"].iloc[0]
    pied= df_joueur["foot"].iloc[0]
    selections=int(df_joueur["international_caps"].max())
    clubs=df_joueur["team"].unique()
    divisions=df_joueur["league_name"].unique()
    
    print(f"\n  Nom               : {nom}")
    print(f"  Date de naissance : {date_naissance}")
    print(f"  Nationalité       : {nationalite}")
    print(f"  Club(s)           : {', '.join(clubs)}")
    print(f"  Division(s)       : {', '.join(divisions)}")
    print(f"  Pied fort         : {pied}")
    print(f"  Sélections int.   : {selections}")
    
    # Valeur marchande réelle vs prédite (2022-2023)
    ligne_test=df_test_v2[df_test_v2["player"]==nom]
    idx=df_test_v2.index.get_loc(ligne_test.index[0])
    valeur_reelle=ligne_test["market_value_in_eur_x"].values[0]
    valeur_predite=y_pred_v2[idx]
    ecart=valeur_predite - valeur_reelle
    ecart_pct=(ecart/valeur_reelle)*100
    
    print("\n  Valeur marchande 2022-2023 :")
    print(f"    Réelle  : {valeur_reelle:>15,.0f} €")
    print(f"    Prédite : {valeur_predite:>15,.0f} €")
    print(f"    Écart   : {ecart:>+15,.0f} € ({ecart_pct:+.1f}%)")
    
    print(f"\n Ouvrez la fenêtre Graphes pour visualiser l'évolution de la valeur marchande de {nom}")
    
    # Graphique d'évolution
    saisons=df_joueur["season"].values
    valeurs=df_joueur["market_value_in_eur_x"].values/1000000
    plt.figure(figsize=(10,6))
    plt.plot(saisons, valeurs, marker="o",linewidth=2, color="navy",label="Valeur réelle")
    plt.plot("2022-2023", valeur_predite/1000000,marker="D", markersize=10,color="coral",label="Valeur prédite", zorder=5)
    plt.title(f"Évolution de la valeur marchande de {nom}",fontsize=14)
    plt.xlabel("Saison")
    plt.ylabel("Valeur marchande (M€)")
    plt.legend(fontsize=12)
    plt.grid(True,alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# Maintenant le sous-menu pour l'extension :
def menu_extension():
    gardiens=afficher_liste_gardiens(df_test_v2)
    nom=input("\n  Entrez le nom du gardien : ").strip()
    if nom in gardiens:
        fiche_gardien(nom,df_all,df_test_v2,y_pred_v2)
    else:
        print(f"\n  Aucun gardien trouvé pour '{nom}'. Vérifiez l'orthographe.")




# PROGRAMME PRINCIPAL :
    
def menu_principal():
    while True:
        print("\n"+"="*60)
        print("  ANALYSE DES GARDIENS - TOP 5 LIGUES EUROPÉENNES")
        print("="*60)
        print("\n  1. Evolution de la valeur marchande par ligue")
        print("  2. Corrélations entre stats et valeur marchande")
        print("  3. Comparaison Top 20% vs Bottom 20%")
        print("  4. Prédiction SANS valeur marchande précédente")
        print("  5. Prédiction AVEC valeur marchande précédente")
        print("  6. Comparaison visuelle des deux modèles")
        print("  7. Fiche d'un gardien")
        print("  8. Quitter")

        choix=input("\n  Votre choix (1-8) : ").strip()

        if choix=="1":
            print("\n"+"="*60)
            print("ANALYSE 1 : Valeur marchande moyenne par ligue")
            print("="*60)
            tableau_ligues=analyse_valeur_par_ligue(df_all)
            print(tableau_ligues.round(2).to_string())
            afficher_valeur_par_ligue(tableau_ligues)
            print("""
  La Premier League domine nettement avec une valeur moyenne autour de 14 M euros. 
  Cela traduit la puissance financière du championnat anglais qui attire et surpaye 
  les meilleurs gardiens.
  La Liga, autrefois au même niveau que la Premier League en 2018-2019, a connu 
  une forte baisse pour se stabiliser autour de 9-10 M euros.
  La Bundesliga est la ligue qui valorise le moins ses gardiens (environ 4 M euros), 
  probablement en raison d'une politique salariale plus modérée.
  La Ligue 1 et la Serie A restent dans une fourchette intermédiaire (5 à 8 M euros).
""")
            print(" Ouvrez la fenêtre Graphes pour une visualitation graphique.\n")

        elif choix=="2":
            print("\n"+"="*60)
            print("ANALYSE 2 : Corrélations avec la valeur marchande")
            print("="*60)
            matrice_corr=analyse_correlations(df_all)
            print("\nCorrélations avec la valeur marchande :")
            print(matrice_corr["market_value_in_eur_x"].sort_values(ascending=False).round(3))
            afficher_correlations(matrice_corr)
            print("""
  Les variables les plus corrélées à la valeur marchande sont les sélections
  internationales (0.56), le pourcentage de victoires (0.37), le pourcentage
  de clean sheets (0.33) et les mois de contrat restants (0.32).
  Les buts encaissés par 90 minutes sont négativement corrélés (-0.20), ce qui 
  est logique. L'age est faiblement corrélé négativement (-0.12) : les gardiens
  vieillissent mieux que les joueurs de champ en termes de valeur marchande.
  Les stats purement techniques comme le pourcentage de centres arrêtés ou les 
  actions hors surface ont peu d'impact direct sur la valorisation.
""")
            print(" Ouvrez la fenêtre Graphes pour une visualitation graphique.\n")

        elif choix=="3":
            print("\n"+"="*60)
            print("ANALYSE 3 : Top 20% vs Bottom 20%")
            print("="*60)
            comparaison_tb=analyse_top_vs_bottom(df_all)
            print(comparaison_tb.round(2))
            afficher_top_vs_bottom(comparaison_tb)
            print("""
  Les gardiens les plus valorisés sont en moyenne plus jeunes (25.9 vs 27.6 ans), 
  ce qui montre que les recruteurs valorisent le potentiel.
  L'écart le plus marquant concerne les sélections internationales (37.8 vs 2.3) : 
  le statut international est un indicateur fort de la valeur marchande.
  Le pourcentage de victoires est 2.5 fois plus élevé chez les mieux valorisés
  (50% contre 20%), ce qui reflète leur appartenance à des clubs plus performants.
  Les performances individuelles diffèrent aussi nettement : 72.5% d'arrêts 
  contre 59.8%, 33.4% de clean sheets contre 13.2%, et près de deux fois moins 
  de buts encaissés par 90 minutes.
  Enfin, les gardiens les mieux valorisés ont des contrats plus longs (80 mois 
  contre 51 mois), signe de la confiance des clubs envers eux.
""")
            print(" Ouvrez la fenêtre Graphes pour une visualitation graphique.\n")

        elif choix=="4":
            print("\n"+"="*65)
            print("Prédiction SANS valeur marchande précédente")
            print("="*65)
            afficher_selection(selected_v1, scores_v1,"coral", titre="sans market_value_prev")
            print(f"\nVariables retenues ({len(selected_v1)}) : {selected_v1}")
            print(f"\nR² sur le jeu de test : {r2_score(y_test, y_pred_v1):.3f}")
            print(f"Erreur absolue moyenne : {mean_absolute_error(y_test, y_pred_v1):,.0f} €\n")
            print(comparaison_v1.head(15).to_string())
            print("\nImportance des variables retenues :")
            print(importances_v1.sort_values(ascending=False).round(4))
            print("""
  Sans la valeur marchande de la saison précédente, la sélection forward retient
  7 variables. Le R² en validation croisée monte assez haut mais chute 
  nettement sur le jeu de test, avec une erreur moyenne de plus de 4 M euros.
  Le modèle a du mal à généraliser car les stats de performance seules ne 
  suffisent pas à expliquer la valorisation d'un gardien.
""")
            print(" Ouvrez la fenêtre Graphes pour visualiser l'évolution du R² avec l'ajout de variables.\n")

        elif choix=="5":
            print("\n"+"="*65)
            print("Prédiction AVEC valeur marchande précédente")
            print("="*65)
            afficher_selection(selected_v2,scores_v2,"navy",titre="avec market_value_prev")
            print(f"\nVariables retenues ({len(selected_v2)}) : {selected_v2}")
            print(f"\nR² sur le jeu de test : {r2_score(y_test_v2, y_pred_v2):.3f}")
            print(f"Erreur absolue moyenne : {mean_absolute_error(y_test_v2, y_pred_v2):,.0f} €\n")
            print(comparaison_v2.head(15).to_string())
            print("\nImportance des variables retenues :")
            print(importances_v2.sort_values(ascending=False).round(4))
            print("""
  Avec la valeur marchande précédente, la sélection forward ne retient que 
  4 variables. Le R² sur le test passe à 0.81 et l'erreur moyenne descend 
  à environ 2.7 M euros. Le modèle est à la fois plus simple et plus 
  performant. La valeur marchande précédente concentre plus de 86% de 
  l'importance, ce qui confirme que la valeur marchande est très inertielle.
  Les trois autres variables apportent des ajustements : le pourcentage de 
  clean sheets (performance pure), l'âge (dépréciation naturelle) et le 
  nombre de matchs débutés (statut de titulaire).
""")
            print(" Ouvrez la fenêtre Graphes pour visualiser l'évolution du R² avec l'ajout de variables.\n")

        elif choix=="6":
            gardiens_v2=set(df_test_v2["player"].values)
            mask_commun=df_test["player"].isin(gardiens_v2).values
            afficher_comparaison_modeles(
                y_test[mask_commun], y_pred_v1[mask_commun],
                r2_score(y_test[mask_commun], y_pred_v1[mask_commun]),
                y_test_v2, y_pred_v2,
                r2_score(y_test_v2, y_pred_v2))
            print("\n Ouvrez la fenêtre Graphes pour une visualitation graphique.")
            print("""
  Le graphique de gauche (sans market_value_prev) montre que le modèle peine
  à prédire les valeurs marchandes élevées : les points s'éloignent fortement
  de la diagonale pour les gardiens valant plus de 15 M€, et le modèle a
  tendance à sous-estimer leur valeur. Le R² de 0.327 confirme que les stats
  de performance seules expliquent moins d'un tiers de la variance.

  Le graphique de droite (avec market_value_prev) montre une nette amélioration :
  les points se rapprochent de la diagonale sur toute la plage de valeurs,
  y compris pour les gardiens les plus chers. Le R² de 0.810 indique que le
  modèle explique plus de 80% de la variance. On observe tout de même que le
  modèle tend à légèrement sous-estimer les valeurs les plus élevées (au-delà
  de 35 M€), ce qui peut s'expliquer par le faible nombre de gardiens dans
  cette tranche de prix dans les données d'entraînement.
""")
            

        elif choix=="7":
            menu_extension()

        elif choix=="8":
            print("\n Au revoir.")
            break

        else:
            print("\n  Choix invalide, veuillez entrer un nombre entre 1 et 8.")




### Lancement du programme :

if __name__ == "__main__":
    menu_principal()


