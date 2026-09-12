** PROJET SAS **


****************************************************************************************;
******* SOMMAIRE ******* ;
****************************************************************************************;

** Partie 0 : Set up et importation des données ;
** Partie 1 : Analyse de la répartition des BUT en France et dans l'académie Orléans-Tours ;
** Partie 2 : Score d'attractivité -> représentation graphique et classement des IUT ;
** Partie 3 : Score de qualité des étudiants ;
** Partie 4 : Respect de la proportion de bac techno et segmentation en classes selon la spécialisation ; 


****************************************************************************************;
****************************************************************************************;




****************************************************************************************;
******* Partie 0 ;
******* Set up et importation des données ;
****************************************************************************************;


* Importation des données *;

****************************************************************************************;

libname prj "C:/Users/quent/OneDrive/Documents/Portfolio/M1/SAS_AttractiviteIUT";

libname tableur xlsx "C:/Users/quent/OneDrive/Documents/Portfolio/M1/SAS_AttractiviteIUT/donnees_good.xlsx";

****************************************************************************************;


****************************************************************************************;
* Création de macros-variables pour les noms des variables afin de faciliter la création de tables selon le besoin ;
* Création de macro-fonctions pour automatiser certaines procédures ;
****************************************************************************************;
%let var_filiere = Filière Formation Formation_detail;
%let var_infoetab = capacité_etablissement type_: rang_: taux_acces part_:;
%let var_coord = nom_etab depart_num depart_char region academie ville coord_gps;
%let var_phaseprincipale = eff_tot_candidats_phase1 eff_tot_candidats_bacgen_p1 eff_tot_candidats_bactech_p1 eff_tot_candidats_bacpro_p1 eff_tot_candidats_autre_p1 eff_tot_candidatsclassés_p1 eff_tot_candidats_admis_p1;
%let var_phasecomplementaire = eff_tot_candidats_phase2 eff_tot_candidats_bacgen_p2 eff_tot_candidats_bactech_p2 eff_tot_candidats_bacpro_p2 eff_tot_candidats_autre_p2 eff_tot_candidatsclassés_p2 eff_tot_candidats_admis_p2;
%let var_infobac = eff_sansmention eff_mention: eff_b:;
%let var_dataglobal = capacité_etablissement eff_tot_candidats eff_candidates eff_tot_candidatsclassés_b: eff_tot_candidatsclassés_autres eff_tot_candidats_propos eff_tot_candidats_admis: eff_admis_meme_academie ;
* bien se rappeler de drop eff_tot_candidats_admis_p1 eff_tot_candidats_admis_p2 pour la dataglobal ;

%macro sorted(table,variable);
	proc sort data=&table;
		by &variable;
	run;
%mend;

%macro sorted_desc(table,variable);
	proc sort data=&table;
		by descending &variable;
	run;
%mend;

****************************************************************************************;
****************************************************************************************;




****************************************************************************************;
******* Partie 1 ;
******* Analyse de la répartition des BUT en France et dans l'académie Orléans-Tours ;
****************************************************************************************;


* Création de la table regroupant les BUT ; 
data prj.but;
	set tableur.feuil1 (keep=&var_filiere &var_infoetab &var_coord);
	where Filière = "BUT";
	if region = "Corse" then depart_num = 20;
	if region = "" then region = "Polynésie française";
	depart_num2 = input(depart_num,8.);
	drop depart_num;
run;

%sorted(prj.but,depart_num2);



*** Une première analyse du nombre de BUT en fonction de la région ;

* Tableau de fréquence pour chaque région ;
proc freq data=prj.but noprint;
	tables region / nocum out=tabfreq;
run;

%sorted_desc(tabfreq,count);

data tabfreq;
	set tabfreq;
	couleur = ifc(region="Centre","a","b");
run;

* Histogramme ;
ods graphics / width=700px height=700px imagename="hist_regions";

proc sgplot data=tabfreq;
	hbar region / response=count datalabel datalabelattrs=(size=9pt weight=bold color=bib) group=couleur barwidth=0.8 categoryorder=respdesc;
	styleattrs datacolors=(lightsteelblue lib);
	xaxis label="Nombre de formation BUT";
	yaxis display=(nolabel);
	title "Répartition des BUT par région";
run;




*** Focus sur la répartition des BUT au sein de l'académie Orléans-Tours ;

* Création de la table pour l'académie Orléans-Tours ;
data prj.orleanstours;
	set prj.but;
	where academie = "Orléans-Tours";
	couleur=ifc(depart_num2=45,"a","b");
run;


* Tableau de fréquence ;
title "Tableau de fréquence du nombre de BUT au sein de la région Centre" ;
proc freq data=prj.orleanstours;
	tables depart_char / nocum ;
run;


* Histogramme ;
ods graphics / width=700px height=700px imagename="hist_orleanstours";

proc sgplot data=prj.orleanstours;
	hbar depart_char / stat=freq datalabel datalabelattrs=(size=12pt weight=bold color=bib) group=couleur barwidth=0.8;
	styleattrs datacolors=(lightsteelblue lib);
	xaxis label="Nombre de formation BUT";
	yaxis display=(nolabel);
	title "Répartition des BUT par département dans l'académie Orléans-Tours";
run;


* Diagramme circulaire ;
goptions ftext="Albany AMT" htitle=14pt htext=12pt;

pattern1 color=lightsteelblue;
pattern2 color=lightsteelblue;
pattern3 color=lightsteelblue;
pattern4 color=lightsteelblue;
pattern5 color=lightsteelblue;
pattern6 color=lib;
proc gchart data=prj.orleanstours;
	pie depart_char / percent=inside;
	title "Répartition des BUT par département dans l'académie Orléans-Tours";
run;
quit;




*** Représentation sur une carte du ratio nombre de candidature par place disponible par IUT au sein de l'académie Orléans-Tours ;

* On regroupe les but de la région Centre dans une table ;
data but_centre (keep=&var_coord &var_dataglobal &var_infoetab);
	set tableur.feuil1 ;
	where Filière="BUT" and region="Centre";
run;

%sorted(but_centre,nom_etab);

data but_centre_ratio (keep=nom_etab ville coord_gps nbr: ratio id);
	set but_centre;
	by nom_etab;
	if first.nom_etab then do;
		nbr_places=0;
		nbr_candidats=0;
	end;
	nbr_places+capacité_etablissement;
	nbr_candidats+eff_tot_candidats;
	if last.nom_etab;
	ratio = nbr_candidats/nbr_places;
	id=input(depart_num,8.);
run;

* On a désormais notre ratio pour chaque IUT de la région Centre. ;
* Grâce à la variable coord_gps, on va extraire les latitudes et longitudes de chaque IUT pour pouvoir les projeter sur une carte ;

data but_centre_ratio_coo;
	set but_centre_ratio;
	latitude=input(scan(coord_gps, 1, ","), 8.4);
	longitude=input(scan(coord_gps, 2, ","), 8.5);
	
	x = longitude * constant('PI') / 180 - 0.0545;
	y = latitude * constant('PI') / 180;
	drop coord_gps;
run;
%sorted(but_centre_ratio_coo,id);


* Maintenant on va faire la carte ;
data centre;
	length id 8. x 8. y 8.;
	set maps.france;
	where id in (18, 28, 36, 37, 41, 45);
	t=1;
	x=LONG;
	y=LAT;
run;


data double;
	set centre but_centre_ratio_coo (in=a);
	villes=a;
run;

proc gproject data=centre out=centreproj project=albers;
	id id;
run;


proc gproject data=but_centre_ratio_coo out=villesproj project=albers;
	id id;
run;


data villesproj1;
 set villesproj;
 format color $10.;
 xsys='2';
 ysys='2';
 hsys='1';
 when = 'A';
 function = 'pie';
 rotate = 360;
 size = 0.3*ratio;
 style='psolid';
 color = 'red'; 
 x=-x;
 if ratio ge 20 then color='cxbe0000';
 else if ratio ge 15 then color = 'cxFF4D00';
 else if ratio ge 10 then color = 'cxFFCC00';
 else color = 'cxDFFF33'; output;
 style = 'pempty'; color = 'gray50'; output;
run;

data legend;
 format color function $10. text $50.; 
 
 function='label'; position='5'; size=1.4; when="a"; color = "black"; style='calibri/bold';
 x=35;y=18; text="TOURS";output;
 x=35;y=17; text="37";output;
 
 x=49;y=29; text="BLOIS";output;
 x=49;y=28; text="41";output;
 
 x=55;y=8.5; text="CHÂTEAUROUX";output;
 x=55;y=7.5; text="36";output;
 
 x=61.5;y=16; text="ISSOUDUN";output;
 x=61.5;y=15; text="36";output;
 
 x=80;y=14.5; text="BOURGES";output;
 x=80;y=13.5; text="18";output;
 
 x=72;y=33; text="ORLÉANS";output;
 x=72;y=32; text="45";output;
 
 x=54.5;y=40; text="CHARTRES";output;
 x=54.5;y=39; text="28";output;
run;


data villes_legend;
	set legend villesproj1;
run;


pattern1 color=bwh;
title "Carte représentant le ratio candidature par place disponible en région Centre";
proc gmap data=centreproj map=centreproj anno=villes_legend;
	id id;
	choro t / statistic = first nolegend ;
run;
quit;






****************************************************************************************;
******* Partie 2 ;
******* Score d'attractivité -> représentation graphique et classement des IUT ;
****************************************************************************************;


*** Analyse de l'attractivité en fonction de la région ;

* Ajout de variables pour l'analyse | on va se concentrer sur les régions de France métropolitaine;
data prj.but_attractivite;
	set tableur.feuil1 (keep=&var_filiere &var_infoetab &var_coord &var_dataglobal);
	where Filière="BUT";
	if region = "" then region = "Polynésie française";
	depart_num2 = input(depart_num,8.);
	if region in ("Corse","Guadeloupe","Guyane","Martinique","Polynésie française","Réunion") then delete;
	drop depart_num eff_tot_candidats_admis_p1 eff_tot_candidats_admis_p2;
run;

%sorted(prj.but_attractivite,depart_num2);


* Tableau descriptif en fonction de la région qu'on utilisera ensuite dans l'ACP;
proc means data=prj.but_attractivite n mean nway noprint;
    class region;
    var capacité_etablissement eff_tot_candidats taux_acces;
    output out=stats_means(drop=_type_ _freq_) n=nbr_formations mean=mean_capacité mean_candidats mean_taux;
run;

%sorted_desc(stats_means,nbr_formations);


* Création d'une statistique visant à évaluer l'attractivité d'une région pour les BUT ;
* On standardise nos variables dans un premier temps ;
proc standard data=stats_means mean=0 std=1 out=stats_region_std;
    var nbr_formations mean_capacité mean_candidats mean_taux;
run;

* On fait une Analyse en Composantes Principales (ACP) pour capturer l'information contenue dans nos variables ;
title "Résultats de l'ACP pour les régions";
proc princomp data=stats_region_std out=stats_acp;
    var nbr_formations mean_capacité mean_candidats mean_taux ;
run;

* A partir des résultats de l'ACP, on peut calculer la z_stat du score d'attractivité ;
* On voit que grâce à Prin1 et Prin2, on explique plus de 84% de la variance totale. Inutile d'utiliser Prin3 et 4 car ces composantes apportent peu d'information et pourraient capturer du bruit ;
data z_stat;
	set stats_acp;
	z = 0.6202*Prin1 + 0.2282*Prin2;
run;

* On ramène le score de 0 à 100 pour une meilleure lecture (0=worst, 100=best parmi nos 12 régions) ;
proc sql;
    create table stats_score_0_100 as
    select region, z, 100*(z - min(z)) / (max(z)-min(z)) as score_0_100
    from z_stat;
quit;

data stats_score_0_100;
	set stats_score_0_100;
	couleur = ifc(region="Centre","a","b");
run;


* Représentation en histogramme du score d'attractivité ;
proc sgplot data=stats_score_0_100;
	hbar region / response=score_0_100 datalabel datalabelattrs=(size=9pt weight=bold color=bib) group=couleur categoryorder=respdesc;
	styleattrs datacolors=(lightsteelblue lib);
	xaxis label="Score d'attractivité";
	yaxis display=(nolabel);
	title "Score d'attractivité des BUT en fonction de la région";
run;



*** On va illustrer ce score en créant une carte afin de voir plus facilement si on peut analyser ça géographiquement;

data france;
	length id 8;
	set maps.france;
	x=LONG;
	y=LAT;
	t=1;
	if id<96;
run;

proc gproject data=france out=france2 project=albers;
	id;
run;


* Création d'une table réunissant tous les départements (ID) ainsi que le score d'attractivité pour faire des groupes;
data departements;
	set prj.but (keep=region depart_num2 rename=(depart_num2=id));
	by id;
	if first.id;
	if id<96 and id ne 20;
	if region="Auvergne-Rhône-Alpes" then score=62.064;
	else if region="Hauts-de-France" then score=32.581;
	else if region="Provence-Alpes-Côte d'Azur" then score=55.436;
	else if region="Grand-Est" then score=8.5205;
	else if region="Occitanie" then score=63.34;
	else if region="Normandie" then score=0.6073;
	else if region="Nouvelle Aquitaine" then score=24.269;
	else if region="Centre" then score=8.4654;
	else if region="Bourgogne-Franche-Comté" then score=0;
	else if region="Bretagne" then score=49.812;
	else if region="Ile-de-France" then score=100;
	else score=57.38;
	if score = 100 then groupe=1;
	else if score ge 49 then groupe=2;
	else if score ge 24 then groupe=3;
	else if score = 0 then groupe=4;
	else groupe=5;
run;


data carte;
	merge france2 (in=a) departements (in=b);
	by id;
	if a;
	if id in (9,48,82) then groupe=2;
	else if id in (55,52) then groupe=5;
run;


pattern1 color='cxbe0000';
pattern2 color='cxFF4D00';
pattern3 color='cxFFCC00';
pattern4 color='cx90ee90';
pattern5 color='cxDFFF33';
title "Carte illustrant le score d'attractivité en fonction de la région";
proc gmap data=carte map=carte;
	id id;
	choro groupe / statistic=first nolegend;
run;
quit;


****************************************************************************************;


*** Faire un classement d'attractivité de tous les iut pour voir à quelle place est l'iut d'orléans;
* On va utiliser la même méthode que précédemment avec les régions;

proc means data=prj.but_attractivite n mean nway noprint;
    class nom_etab;
    var capacité_etablissement eff_tot_candidats taux_acces;
    output out=stats_means(drop=_type_ _freq_) n=nbr_formations mean=mean_capacité mean_candidats mean_taux;
run;

%sorted(stats_means,nom_etab);

* On standardise nos variables dans un premier temps ;
proc standard data=stats_means mean=0 std=1 out=stats_iut_std;
    var nbr_formations mean_capacité mean_candidats mean_taux;
run;

* On fait une Analyse en Composantes Principales (ACP) pour capturer l'information contenue dans nos variables ;
title "Résultat de l'ACP pour tous les IUT";
proc princomp data=stats_iut_std out=stats_acp;
    var nbr_formations mean_capacité mean_candidats mean_taux ;
run;

* A partir des résultats de l'ACP, on peut calculer la z_stat du score d'attractivité ;
* On voit que grâce à Prin1 et Prin2, on explique plus de 75% de la variance totale, ce qui est suffisant. Inutile d'utiliser Prin3 et 4 car ces composantes apportent peu d'information et pourraient capturer du bruit ;
data z_stat;
	set stats_acp;
	z = 0.5146*Prin1 + 0.2355*Prin2;
run;

* On ramène le score de 0 à 100 pour une meilleure lecture (0=worst, 100=best) ;
proc sql;
    create table iut_score_attra_100 as
    select nom_etab, 100*(z - min(z)) / (max(z)-min(z)) as score_attra_0_100
    from z_stat;
quit;

%sorted_desc(iut_score_attra_100,score_attra_0_100);

title "Classement des IUT en fonction du score d'attractivité" ;
proc print data=iut_score_attra_100;
run;

*** On voit que l'IUT d'Orléans se classe à la 57ème place sur 189, avec un score d'attractivité évalué à 34.334. ;
*** Pas si mal ;



****************************************************************************************;



*** On va essayer de voir s'il y a une relation entre le score d'attractivité et la population dans la ville dans laquelle se situe l'IUT;

%sorted(prj.but_attractivite,ville);

data all_villes;
	set prj.but_attractivite (keep=nom_etab ville);
	by ville;
	if first.ville;
run;

* Un total de 181 villes dans lesquelles il y a une formation de BUT. ;
* On export en excel dans lequel on va associer la population à chaque ville ;

/*
ods excel file="C:/Users/quent/OneDrive/Documents/Portfolio/M1/SAS_AttractiviteIUT/all_villes.xlsx" options(sheet_name="villes");
title "Tableau recensant toutes les villes de France métropolitaine dans lesquelles il y a un IUT";
proc print data=all_villes noobs;
run;
ods excel close;
*/


* j'ai rempli le excel avec les populations pour chaque ville, on va maintenant importer cette table ;
libname villes xlsx "C:/Users/quent/OneDrive/Documents/Portfolio/M1/SAS_AttractiviteIUT/all_villes_pop.xlsx";



data pop_ville;
	merge all_villes villes.villes;
	by ville;
	Couleur=ifc(ville="Orléans","Orléans","Autre");
run;
	

%sorted(iut_score_attra_100,nom_etab);
%sorted(pop_ville,nom_etab);

* On merge le score d'attractivité associé à chaque iut ;
* On va calculer le log10 de la population pour ne pas avoir des points aberrants pour les métropoles (genre paris,lyon,marseille...);
data pop_ville2;
	merge pop_ville (in=a) iut_score_attra_100;
	by nom_etab;
	if a;
	pop_log10=log10(population);
run;


* Maintenant on fait le nuage de points ;
proc sgplot data=pop_ville2;
	scatter x=score_attra_0_100 y=pop_log10 / group=Couleur markerattrs=(symbol=circlefilled size=8);
	reg x=score_attra_0_100 y=pop_log10 / lineattrs=(color=orange thickness=2 pattern=dash) ;
	xaxis label="Score d'attractivité";
	yaxis label="Logarithme de la population dans la ville";
	title "Relation entre score d'attractivité et population dans la ville de l'IUT";
run;
quit;

*** On observe clairement une corrélation positive entre score d'attractivité de l'IUT et population dans la ville où se situe l'IUT. ;
*** Cela signifie que les étudiants en BUT privilégient des villes attractives, autrement dit des villes où il y a beaucoup de monde ;
*** et dans laquelle il y a des activités à faire et qui "bouge", ce qui paraît cohérent avec les jeunes ;




****************************************************************************************;
******* Partie 3 ;
******* Score de qualité des étudiants ;
****************************************************************************************;


* Dans un premier temps on regroupe les données par IUT ;

data all_iut ;
	set tableur.feuil1 (keep=&var_filiere &var_infoetab &var_infobac &var_coord eff_tot_candidats_admis);
	where Filière="BUT";
	if region = "" then region = "Polynésie française";
	if region in ("Corse","Guadeloupe","Guyane","Martinique","Polynésie française","Réunion") then delete;
run;

%sorted(all_iut,nom_etab);

* Calcul des sommes ;

data all_iut_sum (keep=nom_etab nbr:);
	set all_iut;
	by nom_etab;
	if first.nom_etab then do;
		nbr_admis=0;
		nbr_felicitations=0;
		nbr_tresbien=0;
		nbr_bien=0;
		nbr_assezbien=0;
	end;
	nbr_admis+eff_tot_candidats_admis;
	nbr_felicitations+eff_mention_felicitation;
	nbr_tresbien+eff_mention_tb;
	nbr_bien+eff_mention_b;
	nbr_assezbien+eff_mention_ab;
	if last.nom_etab;
run;

* On va maintenant calculer notre score de qualité des étudiants selon un modèle confectionné maison ;
data iut_score_etudiants;
	set all_iut_sum;
	score = (5*nbr_felicitations + 3*nbr_tresbien + 2*nbr_bien + nbr_assezbien)/nbr_admis;
run;

* On va ramener le score de 0 à 100 pour faciliter l'analyse ;
proc sql;
    create table iut_score_etudiants_100 as
    select nom_etab, 100*(score - min(score)) / (max(score)-min(score)) as score_etu_0_100 
    from iut_score_etudiants;
quit;

%sorted_desc(iut_score_etudiants_100,score_etu_0_100);

title "Classement des IUT en fonction de la qualité des étudiants";
proc print data=iut_score_etudiants_100;
run;

* On voit que l'IUT d'Orléans est classé 45ème sur 189 en terme de qualité d'étudiants, soit dans le premier quartile (top 24%);
* Pour rappel, le score d'attractivité d'Orléans l'avait classé à la 57ème place parmi tous les IUT de France ;


************************************************************************************************************;

*** Regarder si y'a une relation entre le score d'attractivité et le score de qualité des étudiants ;

* On regroupe les scores d'attractivité et de qualité des étudiants dans la même table ;
%sorted(iut_score_etudiants_100,nom_etab);
%sorted(iut_score_attra_100,nom_etab);

data deux_scores;
	merge iut_score_etudiants_100 iut_score_attra_100;
	by nom_etab;
	couleur=ifc(nom_etab="I.U.T d'Orléans","Orléans","Autre");
run;

* Maintenant on fait le nuage de points ;
proc sgplot data=deux_scores;
	scatter x=score_attra_0_100 y=score_etu_0_100 / group=Couleur markerattrs=(symbol=circlefilled size=8);
	reg x=score_attra_0_100 y=score_etu_0_100 / lineattrs=(color=orange thickness=2 pattern=dash) ;
	xaxis label="Score d'attractivité";
	yaxis label="Score de qualité des étudiants";
	title "Relation entre score d'attractivité et score de qualité des étudiants";
run;
quit;





****************************************************************************************;
******* Partie 4 ;
******* Respect de la proportion de bac techno et segmentation en classes selon la spécialisation ;
****************************************************************************************;


*** Je vais calculer les parts de bacgen et bactech parmi chaque intitulé de formation ;
data temp;
	set tableur.feuil1 (keep=&var_coord &var_filiere &var_infoetab &var_dataglobal);
	if Filière="BUT";
	drop eff_tot_candidats_admis_p1 eff_tot_candidats_admis_p2;
run;
data temp2;
	set temp (keep=Formation_detail eff_tot_candidats_admis eff_tot_candidats_admis_bacgen eff_tot_candidats_admis_bactech eff_tot_candidats_admis_bacpro eff_tot_candidats_admis_autre);
run;
%sorted(temp2,Formation_detail);

data somme (keep=Formation_detail nbr:);
	set temp2;
	by Formation_detail;
	if first.Formation_detail then do;
		nbr_admis=0;
		nbr_bacgen=0;
		nbr_bactech=0;
		nbr_bacpro=0;
		nbr_autre=0;
	end;
	nbr_admis+eff_tot_candidats_admis;
	nbr_bacgen+eff_tot_candidats_admis_bacgen;
	nbr_bactech+eff_tot_candidats_admis_bactech;
	nbr_bacpro+eff_tot_candidats_admis_bacpro;
	nbr_autre+eff_tot_candidats_admis_autre;
	if last.Formation_detail;
run;


data somme2;
	set somme;
	part_bacgen=nbr_bacgen / nbr_admis;
	part_bactech=nbr_bactech / nbr_admis;
	part_bacpro=nbr_bacpro / nbr_admis;
	part_autre=nbr_autre / nbr_admis;
	format part: percent8.2;
	drop nbr_b: nbr_autre;
run;

* En survolant les données, on observe qu'aucune des formations ne respectent les 50% de bac techno. 
* On peut afficher ceux dont la proportion est supérieure ou égale à 40% (qui est déjà pas mal) ;

data bactechge40;
	set somme2;
	where part_bactech ge 0.4;
run;

title "Filières pour lesquels la part de bac techno est >=40%";
proc print data=bactechge40;
	var Formation_detail part_bactech;
run;

* Seulement 11 formations respectent à peu près les 50% de bac techno. ;


*** Voyons ce qu'il en est pour chaque formation pour chaque IUT ;
data all_formations (keep=nom_etab Formation_detail part:);
	set temp (keep=nom_etab Formation_detail eff_tot_candidats_admis eff_tot_candidats_admis_bacgen eff_tot_candidats_admis_bactech eff_tot_candidats_admis_bacpro eff_tot_candidats_admis_autre);
	part_bacgen = eff_tot_candidats_admis_bacgen / eff_tot_candidats_admis;
	part_bactech = eff_tot_candidats_admis_bactech / eff_tot_candidats_admis;
	part_bacpro = eff_tot_candidats_admis_bacpro / eff_tot_candidats_admis;
	part_autre = eff_tot_candidats_admis_autre / eff_tot_candidats_admis;
	format part: percent8.2;
run;
%sorted_desc(all_formations,part_bactech);

data formation_ge50;
	set all_formations;
	where part_bactech ge 0.5;
run;

title "Formations pour lesquels la part de bac techno est >=50%" ;
proc print data=formation_ge50;
	var nom_etab Formation_detail part_bactech;
run;

* On constate que seulement 80 IUT respectent le quota de 50% de bac techno, soit moins de 10% de toutes les formations disponibles.




****************************************************************************************;



*** Voir ce qu'il en est concernant l'IUT d'Orléans ;

data remplissage_orleans;
	set tableur.feuil1 (keep=&var_infoetab &var_filiere &var_coord &var_dataglobal);
	where nom_etab="I.U.T d'Orléans" and Filière="BUT";
	part_bacgen = eff_tot_candidats_admis_bacgen / eff_tot_candidats_admis;
	part_bactech = eff_tot_candidats_admis_bactech / eff_tot_candidats_admis;
	part_autre = eff_tot_candidats_admis_autre / eff_tot_candidats_admis;
	format part: percent8.2;
	drop eff_tot_candidats_admis_p1 eff_tot_candidats_admis_p2;
run;

data remplissage_orleans2;
	set remplissage_orleans (keep=nom_etab capacité_etablissement eff_tot_candidats_admis part_bacgen part_bactech part_autre Formation_detail);
run;

title "Répartitions des provenances des admis au sein des formations de l'IUT d'Orléans" ;
proc print data=remplissage_orleans2;
	var Formation_detail part:;
run;

* On voit que globalement la proportion de bac techno est plus ou moins respectée, mais des formations comme ;
* BUT Chimie ou Qualité logistique industrielle et organisation semblent tirer la moyenne vers le bas. ;

* C'est pourquoi on va tenter de voir si on peut regrouper les filières en fonction du domaine de spécialisation, ;
* et ainsi déceler des domaines dans lesquels les bac techno ne sont pas très représentés, et inversement ;


****************************************************************************************;


*** On va regarder le nombre d'intitulé de formation différents parmi les BUT ;
data nbr_formation;
	set tableur.feuil1 (keep=&var_coord &var_filiere);
	if Filière="BUT";
run;
%sorted(nbr_formation,Formation_detail);
data nbr_formation2;
	set nbr_formation;
	by Formation_detail;
	if first.Formation_detail;
run;

* On voit qu'on en a seulement 36 formations différentes à travers toute la France ; 
* On va essayer de faire des groupes en fonction des domaines de spécialisation afin de pouvoir ;
* comparer les spécialités et essayer de déceler lesquelles acceptent plus de bac généraux ou ;
* inversement plus de bac techno ;


*** On va maintenant regrouper en classe pour pouvoir généraliser en fonction du domaine de spécialité ;

* En analysant les différentes formations, j'ai pu créer 5 groupes par rapport au domaine de la formation, à savoir ;
* - Sciences : Chimie, Génie biologique (les 5 différents intitulés), Génie chimique, Hygiène sécurité environnement, Mesures physiques, Science des données, Science et génie des matériaux ;
* - Social / Juridique : Carrières juridiques, Carrières sociales (les 5 différents intitulés) ;
* - Communication / Marketing : Information communication (les 5 différents intitulés), Métiers du multimédia et d'internet, Packaging, emballage et conditionnement, Réseaux et télécommunication, Techniques de communication ;
* - Gestion / Management : Gestion administrative et commerciale des organisations, Gestion des entreprises et des administrations, Management de la logistique des transports, Qualité logistique industrielle et organisation ;
* - Ingénieurie / Techniques industrielles : Génie civil, Génie industriel et maintenance, Génie mécanique et productique, Génie électrique et informatique industriel, Informatique, Métiers de la transition et de l'efficacité énergétique ;

* On va former ces 5 groupes dans une table ;

data groupes (keep=Groupe capacité_etablissement eff_tot_candidats eff_tot_candidats_admis eff_tot_candidats_admis_b: eff_tot_candidats_admis_a:);
	set tableur.feuil1 (keep=&var_filiere &var_dataglobal);
	if Filière="BUT";
	length Groupe $38.;
	if Formation_detail in ("Carrières juridiques","Carrières sociales Parcours animation sociale et socioculturelle","Carrières sociales Parcours assistance sociale","Carrières sociales Parcours éducation spécialisée","Carrières sociales parcours coordination et gestion des établissements et services sanitaires et sociaux","Carrières sociales parcours villes et territoires durables") then Groupe="Social / Juridique";
	else if Formation_detail in ("Chimie","Génie biologique Parcours agronomie","Génie biologique Parcours diététique et nutrition","Génie biologique parcours biologie médicale et biotechnologie","Génie biologique parcours sciences de l'aliment et biotechnologie","Génie biologique parcours sciences de l'environnement et écotechnologies","Génie chimique génie des procédés","Hygiène Sécurité Environnement","Mesures physiques","Science des données","Science et génie des matériaux") then Groupe="Sciences";
	else if Formation_detail in ("Gestion administrative et commerciale des organisations","Gestion des entreprises et des administrations","Management de la Logistique et des Transports","Qualité, logistique industrielle et organisation") then Groupe="Gestion / Management";
	else if Formation_detail in ("Génie civil - Construction durable","Génie industriel et maintenance","Génie mécanique et productique","Génie électrique et informatique industrielle","Informatique","Métiers de la Transition et de l'Efficacité Énergétiques") then Groupe="Ingénieurie / Techniques industrielles";
	else Groupe="Communication / Marketing";
run;
%sorted(groupes,Groupe);

data groupes_sum (keep=Groupe nbr:);
	set groupes;
	by Groupe;
	if first.Groupe then do;
		nbr_admis=0;
		nbr_bacgen=0;
		nbr_bactech=0;
		nbr_bacpro=0;
		nbr_autre=0;
	end;
	nbr_admis+eff_tot_candidats_admis;
	nbr_bacgen+eff_tot_candidats_admis_bacgen;
	nbr_bactech+eff_tot_candidats_admis_bactech;
	nbr_bacpro+eff_tot_candidats_admis_bacpro;
	nbr_autre+eff_tot_candidats_admis_autre;
	if last.Groupe;
run;
	
data groupes_part_bactech (keep=Groupe part_bactech);
	set groupes_sum;
	part_bactech = nbr_bactech/nbr_admis;
	format part_bactech percent8.2;
run;

* On va représenter en histogramme ;
proc sgplot data=groupes_part_bactech;
	vbar Groupe / response=part_bactech datalabel datalabelattrs=(size=9pt weight=bold color=bib);
	refline 0.4 / axis=y lineattrs=(pattern=dash color=orange thickness=2);
	styleattrs datacolors=(lightsteelblue lib);
	xaxis display=(nolabel);
	yaxis label="Part de bac techno (en %)";
	title "Part de bac techno en fonction du domaine de formation";
run;



****************************************************************************************;

* Il serait aussi intéressant d'analyser s'il y a des domaines qui sont plus demandés par les étudiants que ;
* les autres, et pour cela nous allons comparer la distribution du ratio nombre de candidature par place disponible ;
* pour chacune de nos classes ;


*** Diagramme en boîte pour comparer la demande en fonction du domaine de spécialité ;

* Calcul du ratio ;
data groupes_ratio;
	set groupes (keep=capacité_etablissement eff_tot_candidats Groupe);
	ratio = eff_tot_candidats / capacité_etablissement;
	drop eff_tot_candidats capacité_etablissement;
run;

title "Diagrammes en boîte montrant la distribution du nombre de demande par place pour chaque domaine de spécialité";
proc sgplot data=groupes_ratio;
    vbox ratio / group=Groupe meanattrs=(symbol=circle size=10 color=black);
    yaxis label="Ratio Candidature/Place disponible";
run;








************************************************************************************************************;
************************************************************************************************************;


*** BONUS *** ;

* Calculer le ratio pour tous les iut de france, pour avoir une base sur laquelle comparer;

data ratio_france (keep=&var_coord &var_dataglobal &var_infoetab);
	set tableur.feuil1;
	where Filière="BUT";
run;

%sorted(ratio_france,nom_etab);

data ratio_france_2 (keep=nom_etab nbr: ratio_iut);
	set ratio_france;
	by nom_etab;
	if first.nom_etab then do;
		nbr_places=0;
		nbr_candidats=0;
	end;
	nbr_places+capacité_etablissement;
	nbr_candidats+eff_tot_candidats;
	if last.nom_etab;
	ratio_iut = nbr_candidats/nbr_places;
run;
	
title "statistiques descriptives du ratio nombre de candidature par place disponible sur l'ensemble des IUT de France";
proc means data=ratio_france_2;
	var ratio_iut;
run;

*** Du coup avec ça jpense tu peux calculer des z-stats pour chaque iut pour avoir un score et les classer ;



************************************************************************************************************;
************************************************************************************************************;





