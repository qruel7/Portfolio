
***** ***** ATELIER SAS SEMESTRE 1 ***** *****
***** ** Quentin RUEL - Njiva RAKOTO *** *****
***** ***** ***** **** ***** ***** ***** *****


* Nous allons organiser notre script de la même façon que notre présentation. ;

***** SOMMAIRE :
** Partie 0 : Importation et préparation des bases de données 		| lignes 20 à 350
** Partie 1 : Vue d'ensemble de la base de données 					| lignes 355 à 490
** Partie 2 : Evolution des Formations au cours du temps			| lignes 495 à 1875
** Partie 3 : Analyse des tendances des lieux d'alternance 			| lignes 1880 à 3035
** Partie 4 : Analyse des tendances des Masters 					| lignes 3040 à 4405
** Partie 5 : Master ESA en alternance envisageable ? 				| lignes 4410 à 4930




*** PARTIE 0 : Importation et préparation des bases de données ;

* Dans un premier temps, nous définissons une bibliothèque dans laquelle se trouvera l'ensemble de nos tables
* que l'on utilisera au cours de cet atelier, afin d'avoir un environnement organisé ;
libname projets1 "C:\Users\quent\OneDrive\Documents\m1\sas\PROJET";



* Nous pouvons maintenant importer les bases de données brutes sur lesquelles nous allons travailler ;

* Importation de la base de données 2017-2018 ;
proc import datafile="C:\Users\quent\OneDrive\Documents\m1\sas\PROJET\Informations apprentis.xlsx"
	out = projets1.data2017
	dbms = xlsx;
	getnames = YES;
	
* Importation de la base de données 2018-2019 ;
proc import datafile="C:\Users\quent\OneDrive\Documents\m1\sas\PROJET\Informations apprentis.xlsx"
	out = projets1.data2018
	dbms = xlsx;
	sheet = "2018 2019";
	getnames = YES;
	
* Importation de la base de données 2019-2020 ;
proc import datafile="C:\Users\quent\OneDrive\Documents\m1\sas\PROJET\Informations apprentis.xlsx"
	out = projets1.data2019
	dbms = xlsx;
	sheet = "2019 2020";
	getnames = YES;
	
* Importation de la base de données 2020-2021 ;
proc import datafile="C:\Users\quent\OneDrive\Documents\m1\sas\PROJET\Informations apprentis.xlsx"
	out = projets1.data2020
	dbms = xlsx;
	sheet = "2020 2021";
	getnames = YES;
	
* Importation de la base de données 2021-2022 ;	
proc import datafile="C:\Users\quent\OneDrive\Documents\m1\sas\PROJET\Informations apprentis.xlsx"
	out = projets1.data2021
	dbms = xlsx;
	sheet = "2021 2022";
	getnames = YES;
	
* Importation de la base de données 2022-2023 ;	
proc import datafile="C:\Users\quent\OneDrive\Documents\m1\sas\PROJET\Informations apprentis.xlsx"
	out = projets1.data2022
	dbms = xlsx;
	sheet = "2022 2023";
	getnames = YES;
	
* Importation de la base de données 2023-2024 ;	
proc import datafile="C:\Users\quent\OneDrive\Documents\m1\sas\PROJET\Informations apprentis.xlsx"
	out = projets1.data2023
	dbms = xlsx;
	sheet = "2023 2024";
	getnames = YES;



* Nous constatons que certains noms de variables sont longs et peu pratiques à manipuler : nous allons 
* donc les renommer. 
* Pour ce faire, nous avons créé une fonction macro afin de pouvoir appliquer la modification sur toutes
* les bases de données en même temps afin de gagner du temps et de l'espace. ;

* Fonction macro pour renommer les variables 1, 2 et 3 ;
%macro macrename(lib=, jeux=);
	proc datasets lib=&lib;
		%do i = 1 %to %sysfunc(countw(&jeux));
			modify %scan(&jeux, &i);
			rename ETENDU_SITE_APPRENANT= etab
				   ETENDU_FORMATION_APPRENANT= formation_long
				   NOM_FORMATION_APPRENANT= formation_court ;
		%end;
	quit;
%mend;

* On l'applique sur nos 7 bases de données ;
%macrename(lib=projets1, jeux=data2017 data2018 data2019 data2020 data2021 data2022 data2023);



* Nous allons maintenant créer une nouvelle variable prenant comme modalité le numéro de département dans 
* lequel l'étudiant poursuit sa formation. Pour ce faire, nous allons créer une deuxième fonction macro
* qui va extraire le dernier terme de la variable formation_court, qui correspond au numéro de département 
* de l'établissement de l'alternant (la plupart du temps, nous allons voir ça ensuite), et créé une nouvelle
* colonne qui prendra comme modalité le terme extrait ;

* Fonction macro qui extrait le dernier terme de la variable depart_formation ;
%macro nvl_col(lib=, jeux=, var=);
   %do i = 1 %to %sysfunc(countw(&jeux));
      %let jeu = %scan(&jeux, &i);
      
      data &lib..&jeu;
         set &lib..&jeu;
         &var = scan(formation_court, -1); 			/*-1 spécifie qu'on veut extraire le dernier terme*/
      run;
   %end;
%mend;

* On l'applique sur nos 7 bases de données ;
%nvl_col(lib=projets1, jeux=data2017 data2018 data2019 data2020 data2021 data2022 data2023, var=depart_formation);


data test;
	set projets1.data2017 projets1.data2018 projets1.data2019 
	projets1.data2020 projets1.data2021 projets1.data2022 projets1.data2023;
	if depart_formation = "DAAJ";
* On observe que pour toutes les modalités "DAAJ" dans la variable depart_formation le département 
* où l'étudiant suit sa formation est le 45. 
* Nous allons donc remplacer les valeur DAAJ par 45 dans nos bases de données.




*   Au cours de notre étude, nous aimerions voir s'il existe des tendances concernant l'emplacement de 
*   l'entreprise dans laquelle les étudiants font leur alternance. 
*   Pour cela, nous allons créer une nouvelle variable prenant comme modalité le département dans lequel se 
*   situe leur entreprise.
*   Pour ce faire, nous allons extraire les deux premiers termes de la variable CP_ENTREPRISE et les placer dans
*   une nouvelle variable depart_alternance. Cependant, en nous baladant dans la base de données, nous avons 
*   remarqué qu'il y a quelques observations pour lesquelles CP_ENTREPRISE est de longueur 4 et n'est donc pas
*   adapté au format code postal. Nous allons donc ajouter un 0 devant la modalité de CP_ENTREPRISE pour
*   les observations en question, afin de pouvoir travailler avec ;

*   A partir de cette dernière variable créée, nous allons définir une nouvelle variable region_alternance,
*   permettant de regrouper les modalités de depart_alternance dans des classes, et ainsi faciliter l'analyse
*   et l'interprétation que l'on pourrait en faire.  ;



* Nous allons donc créer de nouvelles tables, vérifiant tous les critères cités ci-dessus ;

* Nouvelle Table 2017-2018 ;
data projets1.data2017_bon;
	Annee=2017;
	length etab $33. formation_long $157. formation_court $24. VILLE_ENTREPRISE $30. depart_formation $24.;
	set projets1.data2017;
	if depart_formation = "DAAJ" then depart_formation = "45";
	depart_formation_num = input(depart_formation,8.);
	drop depart_formation;
	if length(put(CP_ENTREPRISE, 8.)) = 4 then
        CP_ENTREPRISE = put(CP_ENTREPRISE, z5.); 
    depart_alternance = substr(put(CP_ENTREPRISE, z5.), 1, 2); 
    length region_alternance $26.;
    region_alternance="Autre";
    if depart_alternance in (01,03,07,15,26,38,45,43,63,69,73,74) then region_alternance="Auvergne-Rhône-Alpes";
    if depart_alternance in (21,25,39,58,70,71,89,90) then region_alternance="Bourgogne-Franche-Comté";
    if depart_alternance in (22,29,35,56) then region_alternance="Bretagne";
    if depart_alternance in (18,28,36,37,41,45) then region_alternance="Centre-Val de Loire";
    if depart_alternance in (08,10,51,52,54,55,57,67,68,88) then region_alternance="Grand Est";
    if depart_alternance in (02,59,60,62,80) then region_alternance="Hauts-de-France";
    if depart_alternance in (75,77,78,91,92,93,94,95) then region_alternance="Île de France";
    if depart_alternance in (14,27,50,61,76) then region_alternance="Normandie";
    if depart_alternance in (16,17,19,23,24,33,40,47,64,79,86,87) then region_alternance="Nouvelle-Aquitaine";
    if depart_alternance in (09,11,12,30,31,32,34,46,48,65,66,81,82) then region_alternance="Occitanie";
    if depart_alternance in (44,49,53,72,85) then region_alternance="Pays de la Loire";
    if depart_alternance in (04,05,06,13,83,84) then region_alternance="Provence-Alpes-Côte d'Azur";

* Nouvelle Table 2018-2019 ;
data projets1.data2018_bon;
	Annee=2018;
	length etab $33. formation_long $157. formation_court $24. VILLE_ENTREPRISE $30. depart_formation $24.;
	set projets1.data2018;
	if depart_formation = "DAAJ" then depart_formation = "45";
	depart_formation_num = input(depart_formation,8.);
	drop depart_formation;
	if length(put(CP_ENTREPRISE, 8.)) = 4 then
        CP_ENTREPRISE = put(CP_ENTREPRISE, z5.); 
    depart_alternance = substr(put(CP_ENTREPRISE, z5.), 1, 2); 
    length region_alternance $26.;
    region_alternance="Autre";
    if depart_alternance in (01,03,07,15,26,38,45,43,63,69,73,74) then region_alternance="Auvergne-Rhône-Alpes";
    if depart_alternance in (21,25,39,58,70,71,89,90) then region_alternance="Bourgogne-Franche-Comté";
    if depart_alternance in (22,29,35,56) then region_alternance="Bretagne";
    if depart_alternance in (18,28,36,37,41,45) then region_alternance="Centre-Val de Loire";
    if depart_alternance in (08,10,51,52,54,55,57,67,68,88) then region_alternance="Grand Est";
    if depart_alternance in (02,59,60,62,80) then region_alternance="Hauts-de-France";
    if depart_alternance in (75,77,78,91,92,93,94,95) then region_alternance="Île de France";
    if depart_alternance in (14,27,50,61,76) then region_alternance="Normandie";
    if depart_alternance in (16,17,19,23,24,33,40,47,64,79,86,87) then region_alternance="Nouvelle-Aquitaine";
    if depart_alternance in (09,11,12,30,31,32,34,46,48,65,66,81,82) then region_alternance="Occitanie";
    if depart_alternance in (44,49,53,72,85) then region_alternance="Pays de la Loire";
    if depart_alternance in (04,05,06,13,83,84) then region_alternance="Provence-Alpes-Côte d'Azur";
    
* Nouvelle Table 2019-2020 ;
data projets1.data2019_bon;
	Annee=2019;
	length etab $33. formation_long $157. formation_court $24. VILLE_ENTREPRISE $30. depart_formation $24.;
	set projets1.data2019;
	if depart_formation = "DAAJ" then depart_formation = "45";
	depart_formation_num = input(depart_formation,8.);
	drop depart_formation;
	if length(put(CP_ENTREPRISE, 8.)) = 4 then
        CP_ENTREPRISE = put(CP_ENTREPRISE, z5.); 
    depart_alternance = substr(put(CP_ENTREPRISE, z5.), 1, 2); 
    length region_alternance $26.;
    region_alternance="Autre";
    if depart_alternance in (01,03,07,15,26,38,45,43,63,69,73,74) then region_alternance="Auvergne-Rhône-Alpes";
    if depart_alternance in (21,25,39,58,70,71,89,90) then region_alternance="Bourgogne-Franche-Comté";
    if depart_alternance in (22,29,35,56) then region_alternance="Bretagne";
    if depart_alternance in (18,28,36,37,41,45) then region_alternance="Centre-Val de Loire";
    if depart_alternance in (08,10,51,52,54,55,57,67,68,88) then region_alternance="Grand Est";
    if depart_alternance in (02,59,60,62,80) then region_alternance="Hauts-de-France";
    if depart_alternance in (75,77,78,91,92,93,94,95) then region_alternance="Île de France";
    if depart_alternance in (14,27,50,61,76) then region_alternance="Normandie";
    if depart_alternance in (16,17,19,23,24,33,40,47,64,79,86,87) then region_alternance="Nouvelle-Aquitaine";
    if depart_alternance in (09,11,12,30,31,32,34,46,48,65,66,81,82) then region_alternance="Occitanie";
    if depart_alternance in (44,49,53,72,85) then region_alternance="Pays de la Loire";
    if depart_alternance in (04,05,06,13,83,84) then region_alternance="Provence-Alpes-Côte d'Azur";

* Nouvelle Table 2020-2021 ;
data projets1.data2020_bon;
	Annee=2020;
	length etab $33. formation_long $157. formation_court $24. VILLE_ENTREPRISE $30. depart_formation $24.;
	set projets1.data2020;
	if depart_formation = "DAAJ" then depart_formation = "45";
	depart_formation_num = input(depart_formation,8.);
	drop depart_formation;
	if length(put(CP_ENTREPRISE, 8.)) = 4 then
        CP_ENTREPRISE = put(CP_ENTREPRISE, z5.); 
    depart_alternance = substr(put(CP_ENTREPRISE, z5.), 1, 2); 
    length region_alternance $26.;
    region_alternance="Autre";
    if depart_alternance in (01,03,07,15,26,38,45,43,63,69,73,74) then region_alternance="Auvergne-Rhône-Alpes";
    if depart_alternance in (21,25,39,58,70,71,89,90) then region_alternance="Bourgogne-Franche-Comté";
    if depart_alternance in (22,29,35,56) then region_alternance="Bretagne";
    if depart_alternance in (18,28,36,37,41,45) then region_alternance="Centre-Val de Loire";
    if depart_alternance in (08,10,51,52,54,55,57,67,68,88) then region_alternance="Grand Est";
    if depart_alternance in (02,59,60,62,80) then region_alternance="Hauts-de-France";
    if depart_alternance in (75,77,78,91,92,93,94,95) then region_alternance="Île de France";
    if depart_alternance in (14,27,50,61,76) then region_alternance="Normandie";
    if depart_alternance in (16,17,19,23,24,33,40,47,64,79,86,87) then region_alternance="Nouvelle-Aquitaine";
    if depart_alternance in (09,11,12,30,31,32,34,46,48,65,66,81,82) then region_alternance="Occitanie";
    if depart_alternance in (44,49,53,72,85) then region_alternance="Pays de la Loire";
    if depart_alternance in (04,05,06,13,83,84) then region_alternance="Provence-Alpes-Côte d'Azur";

* Nouvelle Table 2021-2022 ;
data projets1.data2021_bon;
	Annee=2021;
	length etab $33. formation_long $157. formation_court $24. VILLE_ENTREPRISE $30. depart_formation $24.;
	set projets1.data2021;
	if depart_formation = "DAAJ" then depart_formation = "45";
	depart_formation_num = input(depart_formation,8.);
	drop depart_formation;
	if length(put(CP_ENTREPRISE, 8.)) = 4 then
        CP_ENTREPRISE = put(CP_ENTREPRISE, z5.); 
    depart_alternance = substr(put(CP_ENTREPRISE, z5.), 1, 2); 
    length region_alternance $26.;
    region_alternance="Autre";
    if depart_alternance in (01,03,07,15,26,38,45,43,63,69,73,74) then region_alternance="Auvergne-Rhône-Alpes";
    if depart_alternance in (21,25,39,58,70,71,89,90) then region_alternance="Bourgogne-Franche-Comté";
    if depart_alternance in (22,29,35,56) then region_alternance="Bretagne";
    if depart_alternance in (18,28,36,37,41,45) then region_alternance="Centre-Val de Loire";
    if depart_alternance in (08,10,51,52,54,55,57,67,68,88) then region_alternance="Grand Est";
    if depart_alternance in (02,59,60,62,80) then region_alternance="Hauts-de-France";
    if depart_alternance in (75,77,78,91,92,93,94,95) then region_alternance="Île de France";
    if depart_alternance in (14,27,50,61,76) then region_alternance="Normandie";
    if depart_alternance in (16,17,19,23,24,33,40,47,64,79,86,87) then region_alternance="Nouvelle-Aquitaine";
    if depart_alternance in (09,11,12,30,31,32,34,46,48,65,66,81,82) then region_alternance="Occitanie";
    if depart_alternance in (44,49,53,72,85) then region_alternance="Pays de la Loire";
    if depart_alternance in (04,05,06,13,83,84) then region_alternance="Provence-Alpes-Côte d'Azur";

* Nouvelle Table 2022-2023 ;
data projets1.data2022_bon;
	Annee=2022;
	length etab $33. formation_long $157. formation_court $24. VILLE_ENTREPRISE $30. depart_formation $24.;
	set projets1.data2022;
	if depart_formation = "DAAJ" then depart_formation = "45";
	depart_formation_num = input(depart_formation,8.);
	drop depart_formation;
	if length(put(CP_ENTREPRISE, 8.)) = 4 then
        CP_ENTREPRISE = put(CP_ENTREPRISE, z5.); 
    depart_alternance = substr(put(CP_ENTREPRISE, z5.), 1, 2); 
    length region_alternance $26.;
    region_alternance="Autre";
    if depart_alternance in (01,03,07,15,26,38,45,42,43,63,69,73,74) then region_alternance="Auvergne-Rhône-Alpes";
    if depart_alternance in (21,25,39,58,70,71,89,90) then region_alternance="Bourgogne-Franche-Comté";
    if depart_alternance in (22,29,35,56) then region_alternance="Bretagne";
    if depart_alternance in (18,28,36,37,41,45) then region_alternance="Centre-Val de Loire";
    if depart_alternance in (08,10,51,52,54,55,57,67,68,88) then region_alternance="Grand Est";
    if depart_alternance in (02,59,60,62,80) then region_alternance="Hauts-de-France";
    if depart_alternance in (75,77,78,91,92,93,94,95) then region_alternance="Île de France";
    if depart_alternance in (14,27,50,61,76) then region_alternance="Normandie";
    if depart_alternance in (16,17,19,23,24,33,40,47,64,79,86,87) then region_alternance="Nouvelle-Aquitaine";
    if depart_alternance in (09,11,12,30,31,32,34,46,48,65,66,81,82) then region_alternance="Occitanie";
    if depart_alternance in (44,49,53,72,85) then region_alternance="Pays de la Loire";
    if depart_alternance in (04,05,06,13,83,84) then region_alternance="Provence-Alpes-Côte d'Azur";

* Nouvelle Table 2023-2024 ;
data projets1.data2023_bon;
	Annee=2023; 
	length etab $33. formation_long $157. formation_court $24. VILLE_ENTREPRISE $30. depart_formation $24.;
	set projets1.data2023;
	if depart_formation = "DAAJ" then depart_formation = "45";
	depart_formation_num = input(depart_formation,8.);
	drop depart_formation;
	if length(put(CP_ENTREPRISE, 8.)) = 4 then
        CP_ENTREPRISE = put(CP_ENTREPRISE, z5.); 
    depart_alternance = substr(put(CP_ENTREPRISE, z5.), 1, 2); 
    length region_alternance $26.;
    region_alternance="Autre";
    if depart_alternance in (01,03,07,15,26,38,45,43,63,69,73,74) then region_alternance="Auvergne-Rhône-Alpes";
    if depart_alternance in (21,25,39,58,70,71,89,90) then region_alternance="Bourgogne-Franche-Comté";
    if depart_alternance in (22,29,35,56) then region_alternance="Bretagne";
    if depart_alternance in (18,28,36,37,41,45) then region_alternance="Centre-Val de Loire";
    if depart_alternance in (08,10,51,52,54,55,57,67,68,88) then region_alternance="Grand Est";
    if depart_alternance in (02,59,60,62,80) then region_alternance="Hauts-de-France";
    if depart_alternance in (75,77,78,91,92,93,94,95) then region_alternance="Île de France";
    if depart_alternance in (14,27,50,61,76) then region_alternance="Normandie";
    if depart_alternance in (16,17,19,23,24,33,40,47,64,79,86,87) then region_alternance="Nouvelle-Aquitaine";
    if depart_alternance in (09,11,12,30,31,32,34,46,48,65,66,81,82) then region_alternance="Occitanie";
    if depart_alternance in (44,49,53,72,85) then region_alternance="Pays de la Loire";
    if depart_alternance in (04,05,06,13,83,84) then region_alternance="Provence-Alpes-Côte d'Azur";



* Nous pouvons nous débarasser des premières bases de données importées, afin de ne pas saturer notre bibliothèque
* et de nous mélanger par la suite ;
proc datasets library=projets1 nolist; 
    delete data2017 data2018 data2019 data2020 data2021 data2022 data2023; 
quit;




* Nous allons créer une nouvelle table regroupant tous les alternants de 2017 à 2024. Pour cela, nous allons
* simplement regrouper nos 7 tables ensemble ;
data projets1.data_all;
	set projets1.data2017_bon projets1.data2018_bon projets1.data2019_bon 
	projets1.data2020_bon projets1.data2021_bon projets1.data2022_bon projets1.data2023_bon;
	


********************************************************************************
********************************************************************************


*** PARTIE 1 : Vue d'ensemble des données ;


********************************************************************************
********************************************************************************


* Dans cette partie, nous allons présenter nos bases de données de manière générale, sans rentrer dans les 
* détails que nous aborderons plus tard ;
* Pour ce faire, nous allons dans un premier temps générer un tableau d'effectif global, affichant pour chaque 
* le nombre d'étudiants en fonction des années. ;

data tabeffectif (keep=Annee Effectif);
	set projets1.data_all;
	by Annee; 
	if first.Annee then count = 0;
	count+1;
	if last.Annee then Effectif = count;
	retain Effectif;
	if last.Annee then count = 0;
	if last.Annee;
	output;

proc transpose data=tabeffectif out=tableau1;
	ID Annee;
	VAR Effectif;
	
data projets1.tab_effectif_global;
	set tableau1;
	rename _NAME_ = Année;
	Total = sum(of _numeric_);

* Tableau d'effectif global ;
proc print data=projets1.tab_effectif_global noobs;




* Nous allons maintenant générer un second tableau d'effectif, mais cette fois en fonction du type de 
* diplôme suivi (BUT, DUT, Master...).
* De plus, nous allons ajouter une variable prenant en modalité la part d'étudiants suivant telle ou telle
* formation par rapport à l'effectif total.

* Pour ce faire, nous devons dans un premier temps trier notre base de données selon le type de formation.
* Nous allons réutiliser ces tables par la suite dans la Partie 3 ;


* Table des BUT ;
data projets1.but_all;
	set projets1.data_all;
	if find(formation_court, "BUT") > 0;
	length Diplome $8.;
	Diplome = "BUT";
	
* Table des DCG ;
data projets1.dcg_all;
	set projets1.data_all;
	if find(formation_court, "DCG") > 0;
	
* Table des DSCG ;
data projets1.dscg_all;
	set projets1.data_all;
	if find(formation_court, "DSCG") > 0;
	
* On observe que les DCG et DSCG ne sont pas très nombreux. Comme les formations sont similaires,
* nous allons les regrouper dans une même table.

* Table qui regroupe les DCG et les DSCG ;
data projets1.dcgdscg_all;
	set projets1.dcg_all projets1.dscg_all;
	length Diplome $8.;
	Diplome = "DCG-DSCG";

* Nous supprimons les tables dcg_all et dscg_all ;
proc datasets library=projets1 nolist; 
    delete dcg_all dscg_all; 
quit;

* Table des DUT ;
data projets1.dut_all;
	set projets1.data_all;
	if find(formation_court, "DUT") > 0;
	length Diplome $8.;
	Diplome = "DUT";
	
* Table des LP ;
data projets1.lp_all;
	set projets1.data_all;
	if find(formation_court, "LP") > 0;
	length Diplome $8.;
	Diplome = "LP";
	
* Table des Masters ;
data projets1.master_all;
	set projets1.data_all;
	if find(formation_court, "MASTER") > 0;
	length Diplome $8.;
	Diplome = "MASTER";



* Maintenant on regroupe ces tables ensembles, on compte les effectifs et on supprime les variables 
* qui ne nous intéressent pas ;

data work (keep = Diplome Effectif);
	set projets1.but_all projets1.dcgdscg_all projets1.dut_all projets1.lp_all projets1.master_all ;
	by Diplome;
	if first.diplome then count = 0;
	count+1;
	if last.diplome then Effectif = count;
	retain Effectif;
	if last.diplome then count = 0;
	if last.diplome;
	output;	

data work2;
	set work;
	Fréquence = Effectif / 8172 ;
	
proc transpose data=work2 out=tableau2;
	ID Diplome;
	VAR Effectif Fréquence;

data projets1.tab_effectif_par_diplome;
	set tableau2;
	rename _NAME_ = Diplôme;
	

* Tableau d'effectif en fonction du type de diplôme ;
proc print data=projets1.tab_effectif_par_diplome noobs;



********************************************************************************
********************************************************************************


*** Partie 2 : Evolution des Formations au cours du temps


********************************************************************************
********************************************************************************


* Dans cette partie, nous allons nous pencher sur l'évolution du nombre d'étudiants en alternances au cours
* des 8 années qui composent notre base de donnée.
* Pour ce faire, nous allons tout d'abord créer un tableau d'effectif comportant le nombre d'étudiants
* de chaque formation, en fonction des années. ;

data but (keep = Annee BUT);
	set projets1.but_all;
	by Annee;
	if first.Annee then count = 0;
	count+1;
	if last.Annee then BUT = count;
	retain BUT;
	if last.Annee then count = 0;
	if last.Annee;
	output;

proc sort data=projets1.dcgdscg_all;
	by Annee;
data dcgdscg (keep = Annee "DCG-DSCG"n);
	set projets1.dcgdscg_all;
	by Annee;
	if first.Annee then count = 0;
	count+1;
	if last.Annee then "DCG-DSCG"n = count;
	retain "DCG-DSCG"n;
	if last.Annee then count = 0;
	if last.Annee;
	output;
	
data dut (keep = Annee DUT);
	set projets1.dut_all;
	by Annee;
	if first.Annee then count = 0;
	count+1;
	if last.Annee then DUT = count;
	retain DUT;
	if last.Annee then count = 0;
	if last.Annee;
	output;
	
data lp (keep = Annee LP);
	set projets1.lp_all;
	by Annee;
	if first.Annee then count = 0;
	count+1;
	if last.Annee then LP = count;
	retain LP;
	if last.Annee then count = 0;
	if last.Annee;
	output;
	
data master (keep = Annee Master);
	set projets1.master_all;
	by Annee;
	if first.Annee then count = 0;
	count+1;
	if last.Annee then Master = count;
	retain Master;
	if last.Annee then count = 0;
	if last.Annee;
	output;

data all;
	merge dcgdscg dut but lp master; by Annee;
	if dut = . then dut = 0;
	if but = . then but = 0;

proc transpose data=all out=all2;
	ID Annee;
	VAR "DCG-DSCG"n DUT BUT LP Master;

data projets1.tab_effectif_diplome_par_annee;
	set all2;
	rename _NAME_ = Année;


* Tableau d'effectif des différents types de formation en fonction des années ;
proc print data=projets1.tab_effectif_diplome_par_annee noobs;



* Afin de mieux visualiser cette évolution au fil du temps et de pouvoir comparer les tendances entre filières,
* nous avons réalisé le graphique suivant ;

data but2 (keep = Annee Diplome);
	set projets1.but_all;
	length Diplome $8.;
	Diplome = "BUT";
	
data dut2 (keep = Annee Diplome);
	set projets1.dut_all;
	length Diplome $8.;
	Diplome = "DUT";
	
data dcgdscg2 (keep = Annee Diplome);
	set projets1.dcgdscg_all;
	length Diplome $8.;
	Diplome = "DCG-DSCG";
	
data lp2 (keep = Annee Diplome);
	set projets1.lp_all;
	length Diplome $8.;
	Diplome = "LP";

data master2 (keep = Annee Diplome);
	set projets1.master_all;
	length Diplome $8.;
	Diplome = "Master";

proc freq data=but2 noprint;
	tables Annee*Diplome / out=out1;

proc freq data=dut2 noprint;
	tables Annee*Diplome / out=out2;
	
proc freq data=dcgdscg2 noprint;
	tables Annee*Diplome / out=out3;
	
proc freq data=lp2 noprint;
	tables Annee*Diplome / out=out4;

proc freq data=master2 noprint;
	tables Annee*Diplome / out=out5;

data freq_all;
	set out1 out2 out3 out4 out5;
	
proc sort data=freq_all;
	by Diplome Annee;


* Graphique ;
proc sgplot data=freq_all;
	styleattrs datacontrastcolors=(green "#8A2BE2" "#FF8C00" "#4682B4"  red);
    series x=Annee y=COUNT / group=Diplome markers 
           lineattrs=(thickness=2) markerattrs=(symbol=circlefilled);
    keylegend / title="Type de diplôme" location=outside position=right; 
    xaxis label="Année" type=linear; /* Affichage continu si années numériques */
    yaxis label="Effectif";
    title "Evolution des effectifs par diplôme au cours du temps";
run;






* Au cours de cette partie, nous allons nous intéresser particulièrement aux endroits dans lesquels
* les étudiants font leur alternances : voir si l'on peut discerner des tendences en terme de région 
* et/ou de département selon le type de diplome ou le temps, de même en ce qui concerne les distances 
* entre le lieu de formation et le lieu d'alternance...

* Tout d'abord, nous avons réalisé un ensemble de cartes regroupant tous nos étudiants, les triant 
* uniquement par rapport à l'année d'étude. 
* Pour ce faire, nous sommes allés récupérer sur internet les coordonnées gps des communes de France via un tableur 
* excel réalisé en 2023 par l'INSEE, que nous avons manipulé afin de garder uniquement les lignes qui nous
* intéressent ;

* Importation de la base de donnée de l'INSEE ;
proc import datafile="C:\Users\quent\OneDrive\Documents\m1\sas\PROJET\Communes-de-France-2023.xlsx"
	out = projets1.coord_villes
	dbms = xlsx;
	getnames = YES;

* Premier traitement pour garder uniquement les "capitales" de chaque département, ainsi que les variables 
* qui nous intéressent ;
data projets1.coord_villes_2;
	set projets1.coord_villes;
	if "Nom (majuscules)"n in ("BOURG EN BRESSE","SAINT QUENTIN","MONTLUCON","MANOSQUE","BRIANCON","NICE","ANNONAY","CHARLEVILLE MEZIERES","PAMIERS","TROYES","CARCASSONNE","RODEZ","MARSEILLE","CAEN","AURILLAC","ANGOULEME","ROCHELLE","BOURGES","BRIVE LA GAILLARDE","SAINT BRIEUC","DIJON","GUERET","PERIGUEUX","BESANCON","VALENCE","EVREUX","CHARTRES","BREST","NIMES","TOULOUSE","AUCH","BORDEAUX","MONTPELLIER","RENNES","CHATEAUROUX","TOURS","GRENOBLE","DOLE","MONT DE MARSAN","BLOIS","SAINT ETIENNE","PUY EN VELAY","NANTES","ORLEANS","CAHORS","AGEN","MENDE","ANGERS","CHERBOURG EN COTENTIN","REIMS","SAINT DIZIER","LAVAL","NANCY","LORIENT","METZ","NEVERS","LILLE","BEAUVAIS","ALENCON","CALAIS","CLERMONT FERRAND","PAU","TARBES","PERPIGNAN","STRASBOURG","COLMAR","LYON","CHAMPLITTE","CHALON SUR SAONE","MANS","CHAMBERY","ANNECY","PARIS","HAVRE","NIORT","AMIENS","ALBI","MONTAUBAN","TOULON","AVIGNON","ROCHE SUR YON","POITIERS","LIMOGES","EPINAL","AUXERRE","BELFORT","MELUN","VERSAILLES","EVRY COURCOURONNES","BOULOGNE BILLANCOURT","SAINT DENIS","VITRY SUR SEINE","ARGENTEUIL")
	or "Code Commune"n = 55545;
    ID = input("Code département"n,7.);
    LONG = input("Longitude"n,6.);
    LAT = input("Latitude"n,6.);
	zip=input("Code postal"n,8.);
	if "Nom (majuscules)"n = "MANOSQUE" then do;
        "LONG"n = 5.783333;
        "LAT"n = 43.833333;
    end;  
    if "Nom (majuscules)"n = "ANNONAY" then do;
        "LONG"n = 4.66667;
        "LAT"n = 45.23333;
    end;
    if "Nom (majuscules)"n = "NIMES" then do;
        "LONG"n = 4.35;
        "LAT"n = 43.833328;
    end;
    if "Nom (majuscules)"n = "MONT DE MARSAN" then do;
        "LONG"n = -0.5;
        "LAT"n = 43.883331;
    end;
    if "Nom (majuscules)"n = "SAINT DIZIER" then do;
        "LONG"n = 4.95;
        "LAT"n = 48.633331;
    end;
    if "Nom (majuscules)"n = "LORIENT" then do;
        "LONG"n = -3.36667;
        "LAT"n = 47.75;
    end;
    if "Nom (majuscules)"n = "PARIS" then do;
        "LONG"n = 2.333333;
        "LAT"n = 48.866667;
    end;
    test=1;
    	      
* Définition des latitudes et longitudes des villes pour lesquelles elles n'étaient pas renseignées ;
data projets1.coord_villes_2bis (keep="Nom (majuscules)"n "Nom avec article"n "Région"n "ID"n "LAT"n "LONG"n "test"n "zip"n "x"n "y"n);
    set projets1.coord_villes_2;
    if "Nom (majuscules)"n = "MANOSQUE" then do;
        "LONG"n = 5.783333;
        "LAT"n = 43.833333;
    end;  
    if "Nom (majuscules)"n = "ANNONAY" then do;
        "LONG"n = 4.66667;
        "LAT"n = 45.23333;
    end;
    if "Nom (majuscules)"n = "NIMES" then do;
        "LONG"n = 4.35;
        "LAT"n = 43.833328;
    end;
    if "Nom (majuscules)"n = "MONT DE MARSAN" then do;
        "LONG"n = -0.5;
        "LAT"n = 43.883331;
    end;
    if "Nom (majuscules)"n = "SAINT DIZIER" then do;
        "LONG"n = 4.95;
        "LAT"n = 48.633331;
    end;
    if "Nom (majuscules)"n = "LORIENT" then do;
        "LONG"n = -3.36667;
        "LAT"n = 47.75;
    end;
    if "Nom (majuscules)"n = "PARIS" then do;
        "LONG"n = 2.333333;
        "LAT"n = 48.866667;
    end;
    test=1;

* Définition des variables x et y qui nous seront utiles à la composition des cartes ;
data projets1.coord_villes_3;
	set projets1.coord_villes_2bis;
	x="LONG"n;
	y="LAT"n;


* Dans le diaporama, nous allons voir en premier l'évolution de la répartition des lieux d'alternances
* entre 2017 et 2024. Nous allons donc créer 7 cartes de la France recensant la proportion et le lieu de 
* l'alternance ;

* Pour cela, il faut d'abord faire un travail sur les données. Nous avons procédé de la manière suivante ;

* Travail sur la base de données pour l'année 2017-2018 ;
data temp;
	set projets1.data2017_bon;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data merged2017;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
* Voici la table finale que nous allons utiliser afin de placer nos points sur la carte ;
data villes (keep=x y  total ID Nom);
	set merged2017;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;


* Une fois ceci fait, nous pouvons réaliser la carte 2017-2018 ;

*************************************************************************
*************************** CARTE 2017-2018 *****************************
************************************************************************* ;

data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.21*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="1-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
* Affichage de la carte 2017-2018 ;
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance par Département en 2017" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;


*********************************************************************************************
*********************************************************************************************

* Travail sur la base de données pour l'année 2018-2019 ;
data temp;
	set projets1.data2018_bon;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;

data merged2018;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set merged2018;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;


*************************************************************************
*************************** CARTE 2018-2019 *****************************
************************************************************************* ;

data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.21*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="1-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance par Département en 2018" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;



******************************************************************************************
******************************************************************************************

* Travail sur la base de données pour l'année 2019-2020 ;
data temp;
	set projets1.data2019_bon;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data merged2019;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set merged2019;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;


*************************************************************************
*************************** CARTE 2019-2020 *****************************
************************************************************************* ;

data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.21*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="1-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 

data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance par Département en 2019" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;



************************************************************************************************
************************************************************************************************

* Travail sur la base de données pour l'année 2020-2021 ;
data temp;
	set projets1.data2020_bon;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data merged2020;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set merged2020;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;
	
	

*************************************************************************
*************************** CARTE 2020-2021 *****************************
************************************************************************* ;

data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.21*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="1-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance par Département en 2020" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 
******************************************************************************************
******************************************************************************************

* Travail sur la base de données pour l'année 2021-2022 ;
data temp;
	set projets1.data2021_bon;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data merged2021;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set merged2021;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;
	
	
*************************************************************************
*************************** CARTE 2021-2022 *****************************
************************************************************************* ;

data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.21*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="1-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance par Département en 2021" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 
 
****************************************************************************************
****************************************************************************************

* Travail sur la base de données pour l'année 2022-2023 ;
data temp;
	set projets1.data2022_bon;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data merged2022;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set merged2022;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;
	
	
*************************************************************************
*************************** CARTE 2022-2023 *****************************
************************************************************************* ;
	
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.21*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="1-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance par Département en 2022" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;

 
****************************************************************************************
****************************************************************************************

* Travail sur la base de données pour l'année 2023-2024 ;
data temp;
	set projets1.data2023_bon;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data merged2023;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set merged2023;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;
	
	
	
*************************************************************************
*************************** CARTE 2023-2024 *****************************
************************************************************************* ;

data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.21*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 
if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="1-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 

data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance par Département en 2023" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;


******************************************************************************************
******************************************************************************************


*** Partie 3 : Analyse des tendances des lieux d'alternance


******************************************************************************************
******************************************************************************************

* Nous allons maintenant générer la carte qui regroupe tous nos étudiants, de 2017 à 2024 ;

* Travail sur la base de données globale ;
data temp;
	set projets1.data_all;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data merged;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set merged;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************************************************************************************
*************************** CARTE ENSEMBLE DES DONNEES *****************************
************************************************************************************ ;

data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.09*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 30 then color='cxDFFF33';
 else if total le 200 then color = 'cxFFCC00';
 else if total le 500 then color = 'cxFF4D00';
 else color = 'cxbe0000' ; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="500+"; output;
 x=16; text="201-500"; output;
 x=25; text="31-200"; output;
 x=34; text="1-30"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 function='label'; position='5'; size=1.6; color = "cxD3D3D3"; style='times/bold';
 x=46; y=75-2.2; text="775";output;
 x=46; y=75-2.2; text="775";output;
 x=46; y=75-2.2; text="775";output;
 x=46; y=75-2.2; text="775";output;
 x=46; y=75-2.2; text="775";output;
 
 x=43.2; y=65.8-2.2; text="2870";output;
 x=43.2; y=65.8-2.2; text="2870";output;
 x=43.2; y=65.8-2.2; text="2870";output;
 x=43.2; y=65.8-2.2; text="2870";output;
 x=43.2; y=65.8-2.2; text="2870";output;
 
 x=40.6; y=70.69-2; text="685";output;
 x=40.6; y=70.69-2; text="685";output;
 x=40.6; y=70.69-2; text="685";output;
 x=40.6; y=70.69-2; text="685";output;
 x=40.6; y=70.69-2; text="685";output;
 
 x=46.6; y=57.7-2.2; text="1276";output;
 x=46.6; y=57.7-2.2; text="1276";output;
 x=46.6; y=57.7-2.2; text="1276";output;
 x=46.6; y=57.7-2.2; text="1276";output;
 x=46.6; y=57.7-2.2; text="1276";output;
 
 function='label'; position='5'; size=1.4; color = "cxD3D3D3"; style='times/bold';
 x=46; y=76.5-2.2; text="75:";output;
 x=46; y=76.5-2.2; text="75:";output;
 x=46; y=76.5-2.2; text="75:";output;
 x=46; y=76.5-2.2; text="75:";output;
 x=46; y=76.5-2.2; text="75:";output;
 
 x=43.2; y=67.3-2.2; text="45:";output;
 x=43.2; y=67.3-2.2; text="45:";output;
 x=43.2; y=67.3-2.2; text="45:";output;
 x=43.2; y=67.3-2.2; text="45:";output;
 x=43.2; y=67.3-2.2; text="45:";output;
 
 x=40.6; y=72.19-2; text="28:";output;
 x=40.6; y=72.19-2; text="28:";output;
 x=40.6; y=72.19-2; text="28:";output;
 x=40.6; y=72.19-2; text="28:";output;
 x=40.6; y=72.19-2; text="28:";output;
 
 x=46.6; y=59.2-2.2; text="18:";output;
 x=46.6; y=59.2-2.2; text="18:";output;
 x=46.6; y=59.2-2.2; text="18:";output;
 x=46.6; y=59.2-2.2; text="18:";output;
 x=46.6; y=59.2-2.2; text="18:";output;

 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternances par Département de 2017 à 2023" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ; 



******************************************************************************************
******************************************************************************************



* Pour finir, nous allons nous analyser la carte de répartition des lieux d'alternances de la Région 
* Centre-Val de Loire, et celle de la Région Île de France.


*********** *********** *********** *********** *********** *********** 
*********** Tri des données Région Centre *********** *********** 
*********** *********** *********** *********** *********** *********** ;

data work;
	set projets1.data_all;
	if region_alternance ="Centre-Val de Loire";
	drop Annee formation_long formation_court etab depart_formation_num region_alterance;
 
proc sort data=work;
	by VILLE_ENTREPRISE;
 
data work2;
	set work;
	by VILLE_ENTREPRISE;
	if first.VILLE_ENTREPRISE then count = 0;
	count+1;
	if last.VILLE_ENTREPRISE then total = count;
	retain total;
	if last.VILLE_ENTREPRISE then count = 0;
	if last.VILLE_ENTREPRISE;
 
data work3;
	set work2;
	ID = input(depart_alternance,8.);
	drop depart_alternance count;
 
data work4;
	set work3;
	if total ge 5;

proc sort data=work4;
	by descending VILLE_ENTREPRISE;

data work5;
	set work4;
	retain aun blo bou cha cha2 cha3 dre epe fle iso jou luc nog oli orl rue bra tou ven vie sul rom fer mes chn loi boig aub urs cyr corps doul aman;
	if VILLE_ENTREPRISE="AUNEAU CEDEX" then aun=total;
	if VILLE_ENTREPRISE="AUNEAU" then total=total+aun;
	if VILLE_ENTREPRISE="BLOIS CEDEX" then blo=total;
	if VILLE_ENTREPRISE="BLOIS" then total=total+blo;
	if VILLE_ENTREPRISE in("BOURGES CEDEX","BOURGES CEDEX 9") then bou+total;
	if VILLE_ENTREPRISE="BOURGES" then total=total+bou;
	if VILLE_ENTREPRISE="CHARTRES CEDEX" then cha=total;
	if VILLE_ENTREPRISE="CHARTRES" then total=total+cha;
	if VILLE_ENTREPRISE="CHATEAUDUN CEDEX" then cha2=total;
	if VILLE_ENTREPRISE="CHATEAUDUN" then total=total+cha2;
	if VILLE_ENTREPRISE="CHATEAUROUX CEDEX" then cha3=total;
	if VILLE_ENTREPRISE="CHATEAUROUX" then total=total+cha3;
	if VILLE_ENTREPRISE="DREUX CEDEX" then dre=total;
	if VILLE_ENTREPRISE="DREUX" then total=total+dre;
	if VILLE_ENTREPRISE="EPERNON CEDEX" then epe=total;
	if VILLE_ENTREPRISE="EPERNON" then total=total+epe;
	if VILLE_ENTREPRISE in ("FLEURY-LES-AUBRAIS CEDEX","FLEURY-LES-AUBRAIS","FLEURY LES AUBRAIS CEDEX") then fle+total;
	if VILLE_ENTREPRISE="FLEURY LES AUBRAIS" then total=total+fle;
	if VILLE_ENTREPRISE="ISSOUDUN CEDEX" then iso=total;
	if VILLE_ENTREPRISE="ISSOUDUN" then total=total+iso;
	if VILLE_ENTREPRISE="JOUE LES TOURS CEDEX" then jou=total;
	if VILLE_ENTREPRISE="JOUE LES TOURS" then total=total+jou;
	if VILLE_ENTREPRISE in("LUCÉ","LUCE CEDEX") then luc=total;
	if VILLE_ENTREPRISE="LUCE" then total=total+luc;
	if VILLE_ENTREPRISE="NOGENT LE ROTROU CEDEX" then nog=total;
	if VILLE_ENTREPRISE="NOGENT LE ROTROU" then total=total+nog;
	if VILLE_ENTREPRISE="OLIVET CEDEX" then oli=total;
	if VILLE_ENTREPRISE="OLIVET" then total=total+oli;
	if VILLE_ENTREPRISE in ("ORLEANS CEDEX 9","ORLEANS CEDEX 2","ORLEANS CEDEX 1","ORLEANS CEDEX") then orl+total;
	if VILLE_ENTREPRISE="ORLEANS" then total=total+orl;
	if VILLE_ENTREPRISE in ("SAINT-JEAN-DE-LA-RUELLE","SAINT-JEAN-DE-LA-RUELLE CEDEX","SAINT JEAN DE LA RUELLE CEDEX") then rue=total;
	if VILLE_ENTREPRISE="SAINT JEAN DE LA RUELLE" then total=total+rue;
	if VILLE_ENTREPRISE in ("SAINT-JEAN-DE-BRAYE","ST JEAN DE BRAYE","SAINT-JEAN-DE-BRAYE CEDEX") then bra+total;
	if VILLE_ENTREPRISE="SAINT JEAN DE BRAYE" then total=total+bra;
	if VILLE_ENTREPRISE in ("TOURS CEDEX 3","TOURS CEDEX 2","TOURS CEDEX 1") then tou+total;
	if VILLE_ENTREPRISE="TOURS" then total=total+tou;
	if VILLE_ENTREPRISE="VENDOME CEDEX" then ven=total;
	if VILLE_ENTREPRISE="VENDOME" then total=total+ven;
	if VILLE_ENTREPRISE="VIERZON CEDEX" then vie=total;
	if VILLE_ENTREPRISE="VIERZON" then total=total+vie;
	if VILLE_ENTREPRISE="SULLY-SUR-LOIRE" then sul=total;
	if VILLE_ENTREPRISE="SULLY-SUR-LOIRE" then total=total+sul;
	if VILLE_ENTREPRISE="ROMORANTIN-LANTHENAY" then rom=total;
	if VILLE_ENTREPRISE="ROMORANTIN LANTHENAY" then total=total+rom;
	if VILLE_ENTREPRISE="LA FERTE-SAINT-AUBIN" then fer=total;
	if VILLE_ENTREPRISE="LA FERTE SAINT AUBIN" then total=total+fer;
	if VILLE_ENTREPRISE="LA CHAPELLE-SAINT-URSIN" then urs=total;
	if VILLE_ENTREPRISE="LA CHAPELLE SAINT URSIN" then total=total+urs;
	if VILLE_ENTREPRISE="LA CHAPELLE-SAINT-MESMIN" then mes=total;
	if VILLE_ENTREPRISE="LA CHAPELLE SAINT MESMIN" then total=total+mes;
	if VILLE_ENTREPRISE="CHATEAUNEUF-SUR-LOIRE" then chn=total;
	if VILLE_ENTREPRISE="CHATEAUNEUF SUR LOIRE" then total=total+chn;
	if VILLE_ENTREPRISE="CHALETTE-SUR-LOING" then loi=total;
	if VILLE_ENTREPRISE="CHALETTE SUR LOING" then total=total+loi;
	if VILLE_ENTREPRISE="BOIGNY-SUR-BIONNE" then boig=total;
	if VILLE_ENTREPRISE="BOIGNY SUR BIONNE" then total=total+boig;
	if VILLE_ENTREPRISE="AUBIGNY-SUR-NERE" then aub=total;
	if VILLE_ENTREPRISE="AUBIGNY SUR NERE" then total=total+aub;
	if VILLE_ENTREPRISE="ST CYR EN VAL" then cyr=total;
	if VILLE_ENTREPRISE="SAINT CYR EN VAL" then total=total+cyr;
	if VILLE_ENTREPRISE="SAINT-PIERRE-DES-CORPS" then corps=total;
	if VILLE_ENTREPRISE="SAINT PIERRE DES CORPS" then total=total+corps;
	if VILLE_ENTREPRISE="SAINT-DOULCHARD" then doul=total;
	if VILLE_ENTREPRISE="SAINT DOULCHARD" then total=total+doul;
	if VILLE_ENTREPRISE="SAINT-AMAND-MONTROND" then aman=total;
	if VILLE_ENTREPRISE="SAINT AMAND MONTROND" then total=total+aman;
	
	

data work6;
	set work5;
	if VILLE_ENTREPRISE not in ("SAINT-AMAND-MONTROND","SAINT-DOULCHARD","SAINT-PIERRE-DES-CORPS","ST CYR EN VAL","AUNEAU CEDEX","BLOIS CEDEX","BOURGES CEDEX","BOURGES CEDEX 9","CHARTRES CEDEX","CHATEAUDUN CEDEX","CHATEAUROUX CEDEX","DREUX CEDEX","EPERNON CEDEX","FLEURY-LES-AUBRAIS CEDEX","FLEURY-LES-AUBRAIS","FLEURY LES AUBRAIS CEDEX","ISSOUDUN CEDEX","JOUE LES TOURS CEDEX","LUCÉ","LUCE CEDEX","NOGENT LE ROTROU CEDEX","OLIVET CEDEX","ORLEANS CEDEX 9","ORLEANS CEDEX 2","ORLEANS CEDEX 1","ORLEANS CEDEX","SAINT-JEAN-DE-LA-RUELLE","SAINT-JEAN-DE-LA-RUELLE CEDEX","SAINT JEAN DE LA RUELLE CEDEX","SAINT-JEAN-DE-BRAYE","ST JEAN DE BRAYE","SAINT-JEAN-DE-BRAYE CEDEX","TOURS CEDEX 3","TOURS CEDEX 2","TOURS CEDEX 1","VENDOME CEDEX","VIERZON CEDEX","SULLY-SUR-LOIRE","ROMORANTIN-LANTHENAY","LA FERTE-SAINT-AUBIN","LA CHAPELLE-SAINT-MESMIN","CHATEAUNEUF-SUR-LOIRE","CHALETTE-SUR-LOING","BOIGNY-SUR-BIONNE","AUBIGNY-SUR-NERE","LA CHAPELLE-SAINT-URSIN");
	drop urs aman doul region_alternance CP_ENTREPRISE cyr corps aun blo bou cha cha2 cha3 dre epe fle iso jou luc nog oli orl rue bra tou ven vie sul rom fer mes chn loi boig aub;
	
proc sort data=work6;
	by VILLE_ENTREPRISE;	

data work7;
	set work6;
	if VILLE_ENTREPRISE="AUNEAU BLEURY ST SYMPHORIEN" then VILLE_ENTREPRISE="AUNEAU BLEURY SAINT SYMPHORIEN";
	if VILLE_ENTREPRISE="LA CHAPELLE-D ANGILLON" then VILLE_ENTREPRISE="CHAPELLE D ANGILLON";
	if VILLE_ENTREPRISE="LA CHAPELLE SAINT MESMIN" then VILLE_ENTREPRISE="CHAPELLE SAINT MESMIN";
	if VILLE_ENTREPRISE="LA CHAPELLE SAINT URSIN" then VILLE_ENTREPRISE="CHAPELLE SAINT URSIN";
	if VILLE_ENTREPRISE="LA CHATRE" then VILLE_ENTREPRISE="CHATRE";
	if VILLE_ENTREPRISE="LA CHAUSSEE SAINT VICTOR" then VILLE_ENTREPRISE="CHAUSSEE SAINT VICTOR";
	if VILLE_ENTREPRISE="LA FERTE SAINT AUBIN" then VILLE_ENTREPRISE="FERTE SAINT AUBIN";
	if VILLE_ENTREPRISE="LA RICHE" then VILLE_ENTREPRISE="RICHE";
	if VILLE_ENTREPRISE="LE COUDRAY" then VILLE_ENTREPRISE="COUDRAY";
	if VILLE_ENTREPRISE="LE POINCONNET" then VILLE_ENTREPRISE="POINCONNET";
	if VILLE_ENTREPRISE="LE SUBDRAY" then VILLE_ENTREPRISE="SUBDRAY";
	
data work8;
	set work7;
    VILLE = tranwrd(VILLE_ENTREPRISE, "-", " ");
    
proc sort data=work8;
	by VILLE;
	
data work9;
	set work8;
	drop VILLE_ENTREPRISE VILLE ID;
	
	



data test;
    set projets1.coord_villes;
    if "Nom (majuscules)"n in (
        'AMBOISE', 'AMILLY', 'ARDON', 'ARGENTON SUR CREUSE', 'ARTENAY', 'AUBIGNY SUR NERE', 'AUNEAU', 
        'AUNEAU BLEURY SAINT SYMPHORIEN', 'AVOINE', 'AVORD', 'BELLEVILLE SUR LOIRE', 'BLOIS', 'BOIGNY SUR BIONNE', 
        'BOURGES', 'BRIARE', 'BROU', 'BUZANCAIS', 'CERCOTTES', 'CHAINGY', 'CHALETTE SUR LOING', 
        'CHAMBRAY LES TOURS', 'CHAMPHOL', 'CHARTRES', 'CHATEAUDUN', 'CHATEAUMEILLANT', 'CHATEAUNEUF SUR LOIRE', 
        'CHATEAUROUX','CHATRE', 'CHECY', 'CHEVILLY', 'CONTRES', 'COURVILLE SUR EURE', 'DAMPIERRE EN BURLY', 'DEOLS', 
        'DIORS', 'DREUX', 'EPERNON', 'ESCRENNES', 'FAY AUX LOGES', 'FERRIERES EN GATINAIS', 
        'FLEURY LES AUBRAIS', 'FONTENAY SUR LOING', 'FUSSY', 'GALLARDON', 'GARANCIERES EN BEAUCE', 
        'GELLAINVILLE', 'GIDY', 'GIEN', 'HENRICHEMONT', 'INGRE', 'ISSOUDUN', 'JANVILLE', 'JOUE LES TOURS', 
        'CHAPELLE SAINT MESMIN', 'CHAPELLE SAINT URSIN', 'CHATRE', 'CHAPELLE D ANGILLON', 
        'CHAUSSEE SAINT VICTOR', 'FERTE SAINT AUBIN', 'RICHE', 'LAILLY EN VAL', 'LAMOTTE BEUVRON', 
        'COUDRAY', 'POINCONNET', 'SUBDRAY', 'LUCE', 'MAINVILLIERS', 'MALESHERBES', 'MEHUN SUR YEVRE', 
        'MENETOU SALON', 'MER', 'MEREAU', 'MEUNG SUR LOIRE', 'MIGNIERES', 'MONTARGIS', 'MONTIERCHAUME', 
        'MONTRICHARD', 'MONTS', 'NEUVILLE AUX BOIS', 'NEUVY PAILLOUX', 'NOGENT LE PHAYE', 'NOGENT LE ROTROU', 
        'NOGENT SUR VERNISSON', 'NOTRE DAME D OE', 'OLIVET', 'ORLEANS', 'ORMES', 'OUARVILLE', 'PARCAY MESLAY', 
        'PIERRES', 'PITHIVIERS', 'PLAIMPIED GIVAUDINS', 'POUPRY', 'PRUNIERS EN SOLOGNE', 'RIANS', 
        'ROMORANTIN LANTHENAY', 'SAINT AMAND MONTROND', 'SAINT AVERTIN', 'SAINT CYR EN VAL', 'SAINT DOULCHARD', 
        'SAINT FLORENT SUR CHER','SAINT DENIS EN VAL', 'SAINT GERMAIN DU PUY', 'SAINT JEAN DE BRAYE', 'SAINT JEAN DE LA RUELLE', 
        'SAINT JEAN LE BLANC', 'SAINT MAUR', 'SAINT PIERRE DES CORPS', 'SAINT ROCH', 'SAINT SATUR', 
        'SAINT AMAND MONTROND', 'SAINT CYR SUR LOIRE', 'SAINT DENIS DE L HOTEL', 'SAINT DOULCHARD', 
        'SAINT GEORGES SUR ARNON', 'SAINT LAURENT NOUAN', 'SAINT LUBIN DES JONCHERETS', 
        'SAINT MARTIN D ABBAT', 'SALBRIS', 'SANCERRE', 'SARAN', 'SELLES SAINT DENIS', 'SEMOY', 
        'SENONCHES', 'SERMAISES', 'SULLY SUR LOIRE', 'THEILLAY', 'THIRON GARDAIS', 
        'TOURS', 'TROUY', 'VARENNES SUR FOUZON', 'VASSELAY', 'VENDOME', 'VERDIGNY', 'VERNOUILLET', 
        'VIERZON', 'VIGNOUX SUR BARANGEON', 'VILLEMANDEUR', 'VINEUIL'
    );
 
proc sort data=test;
	by "Nom (majuscules)"n;
 
 
data mergedcentre (keep=Nom ID x y zip total);
	merge test work9;
	ID = input("Code département"n,7.);
    x = input("Longitude"n,6.);
    y = input("Latitude"n,6.);
	zip=input("Code postal"n,8.);
	rename "Nom (majuscules)"n = Nom;
 
data villescentre;
	set mergedcentre;
	x = x * constant('PI') / 180 - 0.0545;
	y = y * constant('PI') / 180;




****************************************************************
******** CARTE REGION CENTRE ************************
****************************************************************;

data centre;
	set maps.france;
	where id in (18, 28, 36, 37, 41, 45);
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = centre out = centre2 project = albers ;
 id;

	

data duo;
	set centre2 villescentre (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj centreproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output centreproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.08*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 50 then color='cxDFFF33';
 else if total le 200 then color = 'cxFFCC00';
 else if total le 500 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="500+"; output;
 x=16; text="201-500"; output;
 x=25; text="51-200"; output;
 x=34; text="5-50"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 x=32.2;y=39-2.2; text="TOURS";output;
 x=32.2;y=37.5-2.2; text="37";output;
 x=32.2;y=37.5-2.2; text="37";output;
 x=32.2;y=37.5-2.2; text="37";output;
 x=32.2;y=37.5-2.2; text="37";output;
 x=32.2;y=37.5-2.2; text="37";output;
 
 x=44;y=45-2.2; text="BLOIS";output;
 x=44;y=43.5-2.2; text="41";output;
 x=44;y=43.5-2.2; text="41";output;
 x=44;y=43.5-2.2; text="41";output;
 x=44;y=43.5-2.2; text="41";output;
 x=44;y=43.5-2.2; text="41";output;
 
 x=53;y=15.8-2.2; text="CHÂTEAUROUX";output;
 x=53;y=14.3-2.2; text="36";output;
 x=53;y=14.3-2.2; text="36";output;
 x=53;y=14.3-2.2; text="36";output;
 x=53;y=14.3-2.2; text="36";output;
 x=53;y=14.3-2.2; text="36";output;
 
 x=77;y=31-2.2; text="BOURGES";output;
 x=77;y=29.5-2.2; text="18";output;
 x=77;y=29.5-2.2; text="18";output;
 x=77;y=29.5-2.2; text="18";output;
 x=77;y=29.5-2.2; text="18";output;
 x=77;y=29.5-2.2; text="18";output;
 
 x=64;y=61.5-2.2; text="ORLÉANS";output;
 x=64;y=63.1-2.2; text="45";output;
 x=64;y=63.1-2.2; text="45";output;
 x=64;y=63.1-2.2; text="45";output;
 x=64;y=63.1-2.2; text="45";output;
 x=64;y=63.1-2.2; text="45";output;
 
 x=47;y=81.2-2.2; text="CHARTRES";output;
 x=47;y=82.7-2.2; text="28";output;
 x=47;y=82.7-2.2; text="28";output;
 x=47;y=82.7-2.2; text="28";output;
 x=47;y=82.7-2.2; text="28";output;
 x=47;y=82.7-2.2; text="28";output;
 

 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance en Centre-Val de Loire" ;
 proc gmap data = centreproj map = centreproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ; 
 
 
 
 
 
*********** *********** *********** *********** *********** *********** 
*********** Tri des données Région Ile de France *********** *********** 
*********** *********** *********** *********** *********** *********** ;



data paris;
	set projets1.data_all;
	if region_alternance = "Île de France";
	drop Annee formation_long formation_court etab depart_formation_num region_alterance;
 
proc sort data=paris;
	by VILLE_ENTREPRISE;
 
data paris2;
	set paris;
	by VILLE_ENTREPRISE;
	if first.VILLE_ENTREPRISE then count = 0;
	count+1;
	if last.VILLE_ENTREPRISE then total = count;
	retain total;
	if last.VILLE_ENTREPRISE then count = 0;
	if last.VILLE_ENTREPRISE;
 
data paris3;
	set paris2;
	ID = input(depart_alternance,8.);
	drop depart_alternance count;
 
data paris4;
	set paris3;
	if total ge 5;
  
proc sort data=paris4;
	by descending VILLE_ENTREPRISE;

data paris5;
	set paris4;
	retain guy par vel;
	if VILLE_ENTREPRISE="GUYANCOURT CEDEX" then guy=total;
	if VILLE_ENTREPRISE="GUYANCOURT" then total=total+guy;
	if VILLE_ENTREPRISE in("PARIS CEDEX 15","PARIS 9E","PARIS 8E","PARIS 7E","PARIS 6E","PARIS 4E","PARIS 2E","PARIS 19E","PARIS 17E","PARIS 15E","PARIS 14E","PARIS 13E","PARIS 12E","PARIS 11E","PARIS 10E") then par+total;
	if VILLE_ENTREPRISE="PARIS" then total=par+total;
	if VILLE_ENTREPRISE="VELIZY-VILLACOUBLAY" then vel=total;
	if VILLE_ENTREPRISE="VELIZY VILLACOUBLAY" then total=total+vel;
	
data paris6;
	set paris5;
	if VILLE_ENTREPRISE not in ("GUYANCOURT CEDEX","PARIS CEDEX 15","PARIS 9E","PARIS 8E","PARIS 7E","PARIS 6E","PARIS 4E","PARIS 2E","PARIS 19E","PARIS 17E","PARIS 15E","PARIS 14E","PARIS 13E","PARIS 12E","PARIS 11E","PARIS 10E","VELIZY-VILLACOUBLAY");
	VILLE = tranwrd(VILLE_ENTREPRISE, "-", " ");
	if VILLE="LE PERRAY EN YVELINES" then VILLE="PERRAY EN YVELINES";
	drop guy par vel region_alternance CP_ENTREPRISE ID VILLE_ENTREPRISE;
	
proc sort data=paris6;
	by VILLE;
 
 
 
 
data onyva;
    set projets1.coord_villes;
    if "Nom (majuscules)"n in ('CLICHY','CORBEIL ESSONNES','COURBEVOIE',
        'CRETEIL','ELANCOURT','FONTAINEBLEAU','FONTENAY SOUS BOIS','GENNEVILLIERS','GUYANCOURT','IVRY SUR SEINE',
        'PERRAY EN YVELINES','LEVALLOIS PERRET','MASSY','MELUN','MOISSY CRAMAYEL','NANTERRE','ORPHIN','PARIS',
        'PUTEAUX','RAMBOUILLET','SAINT DENIS','SAINT GERMAIN EN LAYE','SAINT OUEN SUR SEINE','TRAPPES','VELIZY VILLACOUBLAY',
        'VERSAILLES','VILLEJUIF'
    );
    rename "Nom (majuscules)"n=Nom;
 
proc sort data=onyva;
	by Nom;
 
 
 
data onyva2 (keep=Nom ID x y zip total);
	merge onyva paris6;
	ID = input("Code département"n,7.);
    x = input("Longitude"n,6.);
    y = input("Latitude"n,6.);
	zip=input("Code postal"n,8.);
 
 
data villesidfcentre;
	set onyva2;
	x = x * constant('PI') / 180 - 0.086;
	y = y * constant('PI') / 180 + 0.001;


****************************************************************
******** CARTE REGION IDF ************************
****************************************************************;

data idfcentre;
	set maps.france;
	where id in (75,77,78,91,92,93,94,95);
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = idfcentre out = idfcentre2 project = albers ;
 id;

	

data duo;
	set idfcentre2 villesidfcentre (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj centreproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output centreproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.5*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1500); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(500);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(300); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=2; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="5-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 function='label'; position='5'; size=2.5; color = "black"; style='calibri/bold';
 x=44.2;y=64.2-2.2; text="PARIS";output;
 x=35;y=63.2-2.2; text="92";output;
 x=51;y=68.5-2.2; text="93";output;
 x=52.5;y=59-2.2; text="94";output;
 
 function='label'; position='5'; size=4; color = "black"; style='calibri/bold';
 x=72;y=54-2.2; text="77";output;
 x=38;y=40-2.2; text="91";output;
 x=16.5;y=66-2.2; text="78";output;
 x=38.5;y=79-2.2; text="95";output;
 

 

 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition globale des lieux d'Alternance en Île de France" ;
 proc gmap data = centreproj map = centreproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ; 
 



******************************************************************************************
******************************************************************************************


* Nous en avons fini avec les cartes (pour l'instant). 

* Nous allons maintenant nous intéresser aux tendances concernant le lieu de formation en fonction du type 
* de diplôme. Pour ce faire, nous avons regroupé les départements selon les régions à laquelle ils appartiennent.
* Cela nous permettra de diminuer drastiquement le nombre de classes, et nous pourrons ainsi mieux 
* analyser nos résultats et en discerner des tendances. 
* Nous avons déjà créé cette variable region_alternance précédemment.

* Nous avons choisi d'analyser les résultats sous forme de diagrammes circulaires.
* Nous en avons donc créé un pour chaque type de diplôme : nous en avons donc 5 au total.



* Diagramme circulaire BUT ;
proc freq data=projets1.but_all noprint;
	tables region_alternance / out=freq_but_all;

pattern1 color=red ;
pattern2 color=blue ;
pattern3 color=yellow ;
pattern4 color=green ;
pattern5 color='#87CEEB' ;
pattern6 color=pink ;
pattern7 color=purple ;
pattern8 color=gold ;
pattern9 color=white ;
pattern10 color=gray ;
pattern11 color=blueviolet ;
pattern12 color=skyblue ;
pattern13 color=aquamarine;
proc gchart data=freq_but_all;
    pie region_alternance / sumvar=Count
                 percent=inside
                 slice=outside
                 value=inside
                 noheading;
    title "Répartition des alternants en BUT par Région";
run;
quit;


* Diagramme circulaire DUT ;
proc freq data=projets1.dut_all noprint;
	tables region_alternance / out=freq_dut_all;
	
pattern1 color=red ;
pattern2 color=blue ;
pattern3 color=yellow ;
pattern4 color=green ;
pattern5 color='#87CEEB' ;
pattern6 color=pink ;
pattern7 color=purple ;
pattern8 color=gold ;
pattern9 color=white ;
pattern10 color=gray ;
pattern11 color=blueviolet ;
pattern12 color=skyblue ;
pattern13 color=aquamarine;
proc gchart data=freq_dut_all;
    pie region_alternance / sumvar=Count
                 percent=inside
                 slice=outside
                 value=inside
                 noheading;
    title "Répartition des alternants en DUT par Région";
run;
quit;


* Diagramme circulaire DCG-DSCG ;
proc freq data=projets1.dcgdscg_all noprint;
	tables region_alternance / out=freq_dcgdscg_all;

pattern1 color=red ;
pattern2 color=pink ;
pattern3 color='#87CEEB' ;
pattern4 color=green ;
pattern5 color=orange ;
pattern6 color=aquamarine ;
pattern7 color=purple ;
pattern8 color=gold ;
pattern9 color=white ;
pattern10 color=gray ;
pattern11 color=blueviolet ;
pattern12 color=skyblue ;
pattern13 color=aquamarine;
proc gchart data=freq_dcgdscg_all;
    pie region_alternance / sumvar=Count
                 percent=inside
                 slice=outside
                 value=inside
                 noheading;
    title "Répartition des alternants en DCG et DSCG par Région";
run;
quit;


* Diagramme circulaire LP ;
proc freq data=projets1.lp_all noprint;
	tables region_alternance / out=freq_lp_all;
	
pattern1 color=red ;
pattern2 color=blue ;
pattern3 color=yellow ;
pattern4 color=green ;
pattern5 color='#87CEEB' ;
pattern6 color=pink ;
pattern7 color=purple ;
pattern8 color=gold ;
pattern9 color=white ;
pattern10 color=gray ;
pattern11 color=blueviolet ;
pattern12 color=skyblue ;
pattern13 color=aquamarine;
pattern14 color=aquamarine;
proc gchart data=freq_lp_all;
    pie region_alternance / sumvar=Count
                 percent=inside
                 slice=outside
                 value=inside
                 noheading;
    title "Répartition des alternants en LP par Région";
run;
quit;


* Diagramme circulaire Master;
proc freq data=projets1.master_all noprint;
	tables region_alternance / out=freq_master_all;
	
pattern1 color=red ;
pattern2 color=blue ;
pattern3 color=yellow ;
pattern4 color=green ;
pattern5 color='#87CEEB' ;
pattern6 color=pink ;
pattern7 color=purple ;
pattern8 color=gold ;
pattern9 color=white ;
pattern10 color=gray ;
pattern11 color=blueviolet ;
pattern12 color=skyblue ;
pattern13 color=aquamarine;
pattern14 color=aquamarine;
proc gchart data=freq_master_all;
    pie region_alternance / sumvar=Count
                 percent=inside
                 slice=outside
                 value=inside
                 noheading;
    title "Répartition des alternants en Master par Région";
run;
quit;




* Nous allons maintenant nous intéresser à la distance qui sépare le lieu de formation de nos étudiants
* de leur ville d'alternance. Pour cela, nous avons analysé la répartition de cette distance, pour chaque
* type de diplôme.

* Afin de bien visualiser cela, nous avons réalisé des diagrammes en boîte pour pouvoir comparer 
* facilement nos 5 classes. ;


/* Extraire les coordonnées de Orléans */
PROC SQL NOPRINT;
    SELECT lat, long
    INTO :lat_orleans, :long_orleans
    FROM projets1.coord_villes_3
    WHERE "Nom (majuscules)"n = "ORLEANS" ;
QUIT;

/* Extraire les coordonnées de Bourges */
PROC SQL NOPRINT;
    SELECT lat, long
    INTO :lat_bourges, :long_bourges
    FROM projets1.coord_villes_3
    WHERE "Nom (majuscules)"n = "BOURGES" ;
QUIT;

/* Extraire les coordonnées de Chateauroux */
PROC SQL NOPRINT;
    SELECT lat, long
    INTO :lat_chateau, :long_chateau
    FROM projets1.coord_villes_3
    WHERE "Nom (majuscules)"n = "CHATEAUROUX" ;
QUIT;

/* Extraire les coordonnées de Chartres */
PROC SQL NOPRINT;
    SELECT lat, long
    INTO :lat_chartres, :long_chartres
    FROM projets1.coord_villes_3
    WHERE "Nom (majuscules)"n = "CHARTRES" ;
QUIT;

%PUT lat_orleans = &lat_orleans;
%PUT lat_bourges = &lat_bourges;
%PUT lat_chateau = &lat_chateau;
%PUT lat_chartres = &lat_chartres;

data calcul_dist_ORL_ces_villes ;
    set projets1.coord_villes_3 ;
    dist_from_orl = geodist (&long_orleans, &lat_orleans, x,y, 'K') ;
    run ;
    
data calcul_dist_BOURGES_ces_villes ;
    set projets1.coord_villes_3 ;
    dist_from_bourges = geodist (&long_bourges, &lat_bourges, x,y, 'K') ;
    run ;

data calcul_dist_CHATEAU_ces_villes ;
    set projets1.coord_villes_3 ;
    dist_from_chateau = geodist (&long_chateau, &lat_chateau, x,y, 'K') ;
    run ;
   
data calcul_dist_CHARTRES_ces_villes ;
    set projets1.coord_villes_3 ;
    dist_from_chartres= geodist (&long_chartres, &lat_chartres, x,y, 'K') ;
    run ;



proc sort data = calcul_dist_BOURGES_ces_villes ;
   by ID ;
   run ;
   
proc sort data = calcul_dist_ORL_ces_villes ;
   by ID ;
   run ;
   
proc sort data = calcul_dist_CHATEAU_ces_villes ;
   by ID ;
   run ;
   
proc sort data = calcul_dist_CHARTRES_ces_villes ;
   by ID ;
   run ;



data projets1.merged_dist (keep= depart_alternance dist_from_bourges dist_from_orl dist_from_chartres dist_from_chateau);
    merge calcul_dist_BOURGES_ces_villes (in=a) calcul_dist_ORL_ces_villes (in = b) calcul_dist_CHATEAU_ces_villes (in = c) calcul_dist_CHARTRES_ces_villes (in = d) ;
    by ID ;
    if length(put(ID, 8.)) = 1 then
        ID = put(ID, z2.);
    depart_alternance = substr(put(ID, z2.), 1, 2);
    run ;
 



proc sort data = projets1.but_all ;
    by depart_alternance ;
    run;

data but_all_dist;
merge projets1.but_all projets1.merged_dist; by depart_alternance; run ;  

data but_all_dist (keep = diplome Distance region_alternance etab formation_court) ;
    set but_all_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
    diplome = "BUT";
   run ;
   


proc sort data = projets1.master_all ;
    by depart_alternance ;
    run ;
data master_all_dist;
merge projets1.master_all projets1.merged_dist; by depart_alternance; run ;  

data master_all_dist (keep = diplome Distance region_alternance etab formation_court) ;
    set master_all_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
    diplome = "MASTER" ;
   run ;

proc sort data = projets1.LP_all ;
    by depart_alternance ;
    run ;
   
data LP_all_dist;
merge projets1.LP_all projets1.merged_dist; by depart_alternance; run ;  
 data LP_all_dist (keep = diplome Distance region_alternance etab formation_court) ;
    set LP_all_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
    diplome = "LP" ;
   run ;
   
   
proc sort data = projets1.DCGDSCG_all ;
    by depart_alternance ;
    run ;
data DCGDSCG_all_distance;
merge projets1.DCGDSCG_all projets1.merged_dist; by depart_alternance;
drop dist_from_orl dist_from_chateau dist_from_chartres;
 run ;  

data DCGDSCG_all_dist (keep = diplome Distance region_alternance etab formation_court) ;
    set DCGDSCG_all_distance ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    Distance = dist_from_bourges;
    diplome = "DCG-DSCG" ;
   run ;  
 
proc sort data = projets1.DUT_all ;
    by depart_alternance ;
    run ;
data dut_all_dist;
merge projets1.dut_all projets1.merged_dist; by depart_alternance; run ;  

data dut_all_dist (keep = diplome Distance region_alternance etab formation_court) ;
    set dut_all_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
    diplome = "DUT" ;
   run ;



proc sort data = but_all_dist ;
    by region_alternance ;
    run ;

proc sort data = dut_all_dist ;
    by region_alternance ;
    run ;

proc sort data = master_all_dist ;
    by region_alternance;
    run ;  
   
proc sort data = DCGDSCG_all_dist ;
    by region_alternance ;
    run ;
   
proc sort data = LP_all_dist ;
    by region_alternance ;
    run ;



data projets1.boxplot_diplomes ;
   merge but_all_dist (in = a) dut_all_dist (in = b) master_all_dist (in = c) DCGDSCG_all_dist (in = d) LP_all_dist (in = e) ;
   by region_alternance diplome;
   rename diplome = Diplôme
   		  Distance = "Distance (en km)"n;
   run ;




* Boxplots avec les valeurs aberrantes ;
title "Diagrammes en boîte des distances aux lieux d'alternances par Diplôme";
proc sgplot data=projets1.boxplot_diplomes;
    vbox "Distance (en km)"n / group=Diplôme meanattrs=(symbol=circle size=10 color=black);
run;



* Boxplots sans les valeurs aberrantes ;
title "Diagrammes en boîte des distances aux lieux d'alternances par Diplôme";
title2 "( sans les valeurs aberrantes )";
proc sgplot data=projets1.boxplot_diplomes;
    vbox "Distance (en km)"n / group=Diplôme nooutliers meanattrs=(symbol=circle size=10 color=black);
    yaxis min=0 max=500;
run;



******************************************************************************************
******************************************************************************************


*** PARTIE 4 : Analyse des tendances des Masters ;


******************************************************************************************
******************************************************************************************


* Tout d'abord, regardons l'évolution de la répartition des lieux d'alternances des Masters au cours des 
* 7 dernières années, puis la répartition cumulée ;


*   Création de tables pour les étudiants ayant fait un master, chaque année séparée;
data projets1.master2017;
	set projets1.data2017_bon;
	if find(formation_court, "MASTER") > 0;		
	
data projets1.master2018;
	set projets1.data2018_bon;
	if find(formation_court, "MASTER") > 0;
		
data projets1.master2019;
	set projets1.data2019_bon;
	if find(formation_court, "MASTER") > 0;
		
data projets1.master2020;
	set projets1.data2020_bon;
	if find(formation_court, "MASTER") > 0;
		
data projets1.master2021;
	set projets1.data2021_bon;
	if find(formation_court, "MASTER") > 0;
		
data projets1.master2022;
	set projets1.data2022_bon;
	if find(formation_court, "MASTER") > 0;
		
data projets1.master2023;
	set projets1.data2023_bon;
	if find(formation_court, "MASTER") > 0;



* Nous allons maintenant réaliser les cartes des Masters allant de 2017-2018 à 2023-2024 ;


********************************************************************
***************** MASTERS 2017 **********************************
********************************************************************;
data temp;
	set projets1.master2017;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************* CARTE MASTERS 2017 **************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.28*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 15 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="16-50"; output;
 x=34; text="1-15"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance par Département pour les Masters en 2017" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 
 
 
 
 
********************************************************************
***************** MASTERS 2018 **********************************
********************************************************************;
data temp;
	set projets1.master2018;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************* CARTE MASTERS 2018 **************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.28*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 15 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="16-50"; output;
 x=34; text="1-15"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance par Département pour les Masters en 2018" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 
 
 
 
********************************************************************
***************** MASTERS 2019 **********************************
********************************************************************;
data temp;
	set projets1.master2019;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************* CARTE MASTERS 2019 **************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.28*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 15 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="16-50"; output;
 x=34; text="1-15"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance par Département pour les Masters en 2019" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 
 
 
 
********************************************************************
***************** MASTERS 2020 **********************************
********************************************************************;
data temp;
	set projets1.master2020;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************* CARTE MASTERS 2020 **************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.28*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 15 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="16-50"; output;
 x=34; text="1-15"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance par Département pour les Masters en 2020" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 
 
 
 
 
********************************************************************
***************** MASTERS 2021 **********************************
********************************************************************;
data temp;
	set projets1.master2021;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************* CARTE MASTERS 2021 **************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.28*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 15 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="16-50"; output;
 x=34; text="1-15"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance par Département pour les Masters en 2021" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 
 
 
 
 
********************************************************************
***************** MASTERS 2022 **********************************
********************************************************************;
data temp;
	set projets1.master2022;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************* CARTE MASTERS 2022 **************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.28*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 15 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="16-50"; output;
 x=34; text="1-15"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance par Département pour les Masters en 2022" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 
 
 
 
 
********************************************************************
***************** MASTERS 2023 **********************************
********************************************************************;
data temp;
	set projets1.master2023;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************* CARTE MASTERS 2023 **************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.28*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 15 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="16-50"; output;
 x=34; text="1-15"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance par Département pour les Masters en 2023" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 


******************************************************************************************
******************************************************************************************


* Et maintenant la carte regroupant tous les masters, de 2017 à 2024 ;


********************************************************************
***************** MASTERS DE 2017 à 2024 ***************************
********************************************************************;
data temp;
	set projets1.master_all;
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;



************* CARTE MASTERS **************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;
	
	

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.12*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 20 then color='cxDFFF33';
 else if total le 100 then color = 'cxFFCC00';
 else if total le 250 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="250+"; output;
 x=16; text="101-250"; output;
 x=25; text="21-100"; output;
 x=34; text="1-20"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance par Département pour les Masters de 2017 à 2023" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;
 
 


*********************************************************************************
*********************************************************************************


*** Partie 5 : Master ESA en alternance envisageable ?


*********************************************************************************
*********************************************************************************


* Nous allons maintenant tenter de répondre à l'interrogation suivante : "Est-il envisageable de 
* proposer le Master ESA en alternance ?"
* Pour ce faire, nous avons trié les différents Masters de la base de données selon des classes en 
* fonction des secteurs d'études dont ils font partie (Droit, Chimie, Gestion/Commerce...)

* Parmi ces classes, nous avons pris le soin d'en créer une dont les spécificités de la formation sont 
* plus ou moins similaires à celles du Master ESA : ce sera notre groupe test/témoin.


* Création des classes ;
**** Créer des classes au sein des masters pour discriminer en fonction du secteur d'études ;

data projets1.master_classe (keep=Annee VILLE_ENTREPRISE region_alternance classe depart_formation_num depart_alternance);
	set projets1.master_all;
	length classe $22.;
	if find(formation_court,"FMB")=0;   	/*On supprime les lignes des masters FMB car ne correpond à aucune de nos classes */
	if prxmatch("/APA-S|STAPS/", formation_court) then classe = "Act. Physique";
	else if prxmatch("/BC|C2AQ|COT|SQCA|EMD|ICMS/", formation_court) then classe = "Physique/Chimie";
	else if prxmatch("/CAU|DIPAT|DMPL|DSGRH|GLPC|MAP|MAPCAR/", formation_court) then classe = "Droit";
	else if prxmatch("/CCA|CGAO|MESC2A|CED|LACI|MPSI/", formation_court) then classe = "Gestion/Commerce";
	else classe = "Data Sciences - Témoin" ;

proc sort data=projets1.master_classe;
	by classe;



* Nous avons créé un tableau d'effectif afin de voir rapidement la composition de chaque classe ;
data tab_effectif_classes (keep=classe Effectif);
	set projets1.master_classe;
	by classe; 
	if first.classe then count = 0;
	count+1;
	if last.classe then Effectif = count;
	retain Effectif;
	if last.classe then count = 0;
	if last.classe;
	output;

proc transpose data=tab_effectif_classes out=tableau3;
	ID classe;
	VAR Effectif;
	
data projets1.tab_effectif_secteur;
	set tableau3;
	rename _NAME_ = Secteur;
	Total = sum(of _numeric_);


* Tableau d'effectif par classes ;
title "Tableau d'effectif de nos classes de Matsers";
proc print data=projets1.tab_effectif_secteur noobs;




* Ce qui nous intéresse, c'est de voir la proportion des alternances en Ile de France par secteur de 
* spécialité des masters ;


******************************************************************************************
******************************************************************************************;


* Dans cette section, nous allons créer des graphiques montrant l'évolution de la part d'alternance en Ile de
* France au cours du temps, pour chaque classe de Master ;


data droit;
	set projets1.master_classe;
	if classe = "Droit";

proc freq data=droit noprint;
    where region_alternance = "Île de France"; /* Filtrer pour l'Île-de-France */
    tables Annee / out=freqdroit; /* Créer une table avec les décomptes */
run;

data freqdroit1;
	set freqdroit;
	Secteur = "Droit";
	
	
data sport;
	set projets1.master_classe;
	if classe = "Act. Physique";
	
proc freq data=sport noprint;
    where region_alternance = "Île de France"; /* Filtrer pour l'Île-de-France */
    tables Annee / out=freqsport; /* Créer une table avec les décomptes */
run;

data freqsport1;
	set freqsport;
	Secteur = "Act. Physique";

	
data chimie;
	set projets1.master_classe;
	if classe = "Physique/Chimie";
	
proc freq data=chimie noprint;
    where region_alternance = "Île de France"; /* Filtrer pour l'Île-de-France */
    tables Annee / out=freqchimie; /* Créer une table avec les décomptes */
run;

data freqchimie1;
	set freqchimie;
	Secteur = "Chimie/Physique";
	
	
data gestion;
	set projets1.master_classe;
	if classe = "Gestion/Commerce";
	
proc freq data=gestion noprint;
    where region_alternance = "Île de France"; /* Filtrer pour l'Île-de-France */
    tables Annee / out=freqgestion; /* Créer une table avec les décomptes */
run;

data freqgestion1;
	set freqgestion;
	Secteur = "Gestion/Commerce";
	

data datasciences;
	set projets1.master_classe;
	if classe = "Data Sciences - Témoin" ;

proc freq data=datasciences noprint;
    where region_alternance = "Île de France"; /* Filtrer pour l'Île-de-France */
    tables Annee / out=freqds; /* Créer une table avec les décomptes */
run;

data freqds1;
	set freqds;
	Secteur = "Data Sciences - Témoin";


data freqidf;
	set freqdroit1 freqsport1 freqgestion1 freqchimie1 freqds1;
	
proc sort data=freqidf;
	by Secteur Annee;


* Graphique montrant l'évolution de la part d'alternances en Ile de France selon le secteur de spécialité du master;
proc sgplot data=freqidf;
	styleattrs datacontrastcolors=(green "#8A2BE2" red "#4682B4" "#FF8C00" );
    series x=Annee y=PERCENT / group=Secteur markers 
    lineattrs=(thickness=2) markerattrs=(symbol=circlefilled);
    keylegend / title="Secteur de la formation" location=outside position=right; 
    xaxis label="Année" type=linear; 
    yaxis label="Part d'alternances en Île-de-France (en %)";
    title "Évolution de la part de l'Île-de-France par année";
run;


* Graphique montrant l'évolution de la part d'alternances en Ile de France pour les Masters Data Sciences;
title "Évolution de la part d'alternants en Île-de-France pour";
title2 "les Masters type ESA";
proc sgplot data=freqds1;
    series x=Annee y=PERCENT / markers 
    lineattrs=(thickness=2 color=red) markerattrs=(symbol=circlefilled color="#B00000");
    xaxis label="Année" type=linear; 
    yaxis label="Part d'alternances en Île-de-France (en %)";
run;



************************************************************************
************************************************************************


* Nous allons maintenant créer un graphique montrant la répartition des distances entre lieu de formation
* et lieu d'alternance pour nos 5 classes de Masters, sous la forme de diagrammes en boîte. ; 


proc sort data = chimie ;
    by depart_alternance ;
    run ;

data chimie_dist;
     merge chimie projets1.merged_dist;
     by depart_alternance;
     run ;

data chimie_dist (keep = classe Distance region_alternance) ;
    set chimie_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
   run ;



proc sort data = droit ;
    by depart_alternance ;
    run ;

data droit_dist;
     merge droit projets1.merged_dist;
     by depart_alternance;
     run ;

data droit_dist (keep = classe Distance region_alternance) ;
    set droit_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
   run ;



proc sort data = sport ;
    by depart_alternance ;
    run ;

data sport_dist;
     merge sport projets1.merged_dist;
     by depart_alternance;
     run ;

data sport_dist (keep = classe Distance region_alternance) ;
    set sport_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
   run ;



proc sort data = gestion ;
    by depart_alternance ;
    run ;

data gestion_dist;
     merge gestion projets1.merged_dist;
     by depart_alternance;
     run ;

data gestion_dist (keep = classe Distance region_alternance) ;
    set gestion_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
   run ;



proc sort data = datasciences ;
    by depart_alternance ;
    run ;

data datasciences_dist;
     merge datasciences projets1.merged_dist;
     by depart_alternance;
     run ;

data datasciences_dist (keep = classe Distance region_alternance depart_alternance) ;
    set datasciences_dist ;
    if not missing (region_alternance) ; /* juste pour supprimer les valeurs manquantes */
    if depart_formation_num=18 then Distance = dist_from_bourges;
    if depart_formation_num = 36 then Distance = dist_from_chateau ;
    if depart_formation_num = 45 then Distance = dist_from_orl ;
    else Distance = dist_from_chartres ;
   run ;



proc sort data = chimie_dist ;
    by region_alternance ;
    run ;

proc sort data = droit_dist ;
    by region_alternance ;
    run ;

proc sort data = sport_dist ;
    by region_alternance;
    run ;  
   
proc sort data = gestion_dist ;
    by region_alternance ;
    run ;
   
proc sort data = datasciences_dist ;
    by region_alternance ;
    run ;



data projets1.boxplot_classe ;
   merge chimie_dist (in = a) droit_dist (in = b) sport_dist (in = c) gestion_dist (in = d) datasciences_dist (in = e) ;
   by region_alternance classe;
   rename Distance = "Distance (en km)"n 
   		  classe = Secteur ;
   run ;


* Boxplots avec les valeurs aberrantes ;
title "Diagrammes en boîte des distances aux lieux d'alternances par Secteur";
proc sgplot data=projets1.boxplot_classe;
    vbox "Distance (en km)"n / group=Secteur meanattrs=(symbol=circle size=10 color=black);
run;



* Boxplots sans les valeurs aberrantes ;
title "Diagrammes en boîte des distances aux lieux d'alternances par Secteur";
title2 "( sans les valeurs aberrantes )";
proc sgplot data=projets1.boxplot_classe;
    vbox "Distance (en km)"n / group=Secteur nooutliers meanattrs=(symbol=circle size=10 color=black);
    yaxis min=0 max=600;
run;

/* Fin du code pour les boxplots par classe */



* Afin de mieux analyser la répartition des distances pour la classe qui nous intéresse particulièrement 
* (Data Sciences), nous allons réaliser son histogramme ;

* Histogramme de la classe Data Sciences ;
title "Histogramme de la Distance entre le lieu de Formation et du lieu D'Alternance";
title2 "pour les Masters type ESA";
proc sgplot data=datasciences_dist;
   histogram Distance / binwidth=50 
   						fillattrs=(color=red transparency=0.4); /* Couleur des barres */
   xaxis label="Distance (en km)" values=(0 to 800 by 100) offsetmin=0.04;
   yaxis label="Fréquence (en %)";
run;




********************************************************************************
********************************************************************************


* Pour finir, nous allons représenter sur une carte la répartition des départements dans lesquel se 
* situent les entreprises dans laquelle les étudiants en Master type Data Sciences font leur alternance.




* Tri des données pour générer la carte des Masters de la classe Témoin ;

data temp;
	set projets1.master_classe;
	if classe="Data Sciences - Témoin";
	
proc sort data=temp;
	by depart_alternance;
	
data temp2;
	set temp;
	by depart_alternance;
	if first.depart_alternance then count = 0;
	count+1;
	if last.depart_alternance then total = count;
	retain total;
	if last.depart_alternance then count = 0;
	if last.depart_alternance;
	drop etab formation_long formation_court CP_ENTREPRISE depart_formation_num count VILLE_ENTREPRISE Annee region_alternance;
	output;
	
data temp3;
	set temp2;
	ID = input(depart_alternance,8.);
	drop depart_alternance;
	output;
	if _n_ = 1 then do;
        ID = 70;
        total = 0;
        output;
    end;
proc sort data=temp3;
	by descending ID;
   
data temp4;
	set temp3;
    retain somme ;
    if ID in (77,78,95,91,92,93,94) then somme+total;
    if ID = 75 then total = total + somme ;
    drop somme;
proc sort data=temp4;
	by ID;
  
data temp5;
	set temp4;
	if ID in (77,78,95,91,92,93,94) then total=0;


data mergedmasters;
	merge projets1.coord_villes_3 temp5;
	by ID;
	rename "Nom avec article"n = Nom;
	
	
data villes (keep=x y  total ID Nom);
	set mergedmasters;
	x = x * constant('PI') / 180 -0.087;
	y = y * constant('PI') / 180+0.0009;
	if ID not in (77,78,91,92,93,94,95);
	if total=. then total=0;
	if total=1 then total=1.01;


*****************************************************************
************* CARTE MASTERS DATA SCIENCES ***********************
*****************************************************************;
data france;
	set maps.france;
	test=1;
	x=LONG;
	y=LAT;

proc gproject data = france out = france2 project = albers ;
 id;

	

data duo;
	set france2 villes (in=A);
	villesdata = A;
	if villesdata=0 then x=LONG;
	if villesdata=0 then y=LAT;
	if villesdata=1 then SEGMENT=1;
	
proc gproject data=duo out=duoproj project=albers parallel1=43.5 parallel2=49;   /* Choisir la projection Lambert */
   id Nom;
   	
data villesproj franceproj;
	set duoproj;
	if villesdata = 1 then output villesproj;
	else output franceproj;


goptions device=png gsfname=outfile gsfmode=replace xpixels=1000 ypixels=1000;	
	
data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.2*sqrt(total);
 style='psolid';
 color = 'red'; 
 x=-x;
 if total le 10 then color='cxDFFF33';
 else if total le 50 then color = 'cxFFCC00';
 else if total le 150 then color = 'cxFF4D00';
 else color = 'cxbe0000'; output;
 if total ne 0;
 style = 'pempty'; color = 'gray50'; output;

 
 data legend;
 format color function $10. text $50.;
 xsys='3'; ysys='3'; hsys='1'; when='a';
 
 function='pie'; rotate=360; ; style='psolid';
 y =12; x=7; color='cxbe0000'; size = 0.115*sqrt(1000); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 11; x=16; color= 'cxFF4D00'; size = 0.115*sqrt(300);style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 10; x=25; color='cxFFCC00'; size = 0.115*sqrt(150); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 y = 09; x=34; color='cxDFFF33'; size = 0.115*sqrt(50); style='psolid';
 output;
 style = 'pempty'; color = 'gray50'; output;
 
 function='label'; position='5'; size=1.7; color = "black"; style='calibri/bold';
 y=6;
 x=7; text="150+"; output;
 x=16; text="51-150"; output;
 x=25; text="11-50"; output;
 x=34; text="1-10"; output;
 y = 4.2;
 x=7; text="Alternances"; output;
 x=16; text="Alternances"; output;
 x=25; text="Alternances"; output;
 x=34; text="Alternances"; output; 
 
 
 
 
 
 
data villes_and_legend;
 set legend villesproj1; 
 
 
pattern1 color=bwh;
title "Répartition des lieux d'Alternance des Masters type Data Sciences" ;
 proc gmap data = franceproj map = franceproj anno = villes_and_legend;
 id ID;
 choro test / statistic = first nolegend ;



********************************************************************************
********************************************************************************
********************************************************************************
********************************************************************************


							FIN DU SCRIPT;



 

