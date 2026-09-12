# =============================================================================
# Application R Shiny - Scoring bancaire
# Master 1 ESA - Projet individuel
# Auteur : Quentin Ruel
# Date   : Avril 2026
# =============================================================================


# ---- 1. Packages ------------------------------------------------------------
library(shiny)
library(bslib)
library(DT)
library(plotly)
library(ggplot2)
library(dplyr)
library(tidyr)
library(pROC)
library(stargazer)


# ---- 2. Chargement et préparation des données -------------------------------
credit <- read.csv("credit_defaut.csv")

# Labels pour les variables catégorielles (utilisés dans l'UI et les graphiques)
credit <- credit %>%
  mutate(
    sexe_label      = factor(sexe,
                             levels = c(1, 2),
                             labels = c("Homme", "Femme")),
    education_label = factor(niveau_education,
                             levels = 0:6,
                             labels = c("Autre", "Doctorat", "Master",
                                        "Licence", "Lycée", "Autre 2",
                                        "Autre 3")),
    famille_label   = factor(situation_familiale,
                             levels = 0:3,
                             labels = c("Autre", "Marié(e)",
                                        "Célibataire", "Autre 2")),
    defaut_label    = factor(defaut_paiement_mois_suivant,
                             levels = c(0, 1),
                             labels = c("Non-défaut", "Défaut"))
  )

# Les 23 variables explicatives disponibles (on exclut id_client, la cible et
# les colonnes "_label" qui ne sont utilisées que pour l'affichage).
vars_explicatives <- setdiff(
  names(credit),
  c("id_client", "defaut_paiement_mois_suivant",
    "sexe_label", "education_label", "famille_label", "defaut_label")
)

# Les 18 variables retenues par la procédure stepwise (rapport préalable) :
# ce sont les variables cochées par défaut dans l'onglet "Modélisation".
vars_stepwise <- c(
  "plafond_credit_eur", "sexe", "niveau_education", "situation_familiale",
  "age",
  "retard_paiement_sep_2023", "retard_paiement_aou_2023",
  "retard_paiement_juil_2023", "retard_paiement_mai_2023",
  "encours_carte_sep_2023_eur", "encours_carte_aou_2023_eur",
  "encours_carte_mai_2023_eur",
  "montant_rembourse_sep_2023_eur", "montant_rembourse_aou_2023_eur",
  "montant_rembourse_juil_2023_eur", "montant_rembourse_juin_2023_eur",
  "montant_rembourse_mai_2023_eur", "montant_rembourse_avr_2023_eur"
)

# Libellés lisibles pour chaque variable explicative (utilisés dans les
# sélecteurs de l'UI et les titres des graphiques).
vars_labels <- c(
  "Plafond de crédit (EUR)"                   = "plafond_credit_eur",
  "Sexe"                                      = "sexe",
  "Niveau d'éducation"                        = "niveau_education",
  "Situation familiale"                       = "situation_familiale",
  "Âge"                                       = "age",
  "Retard de paiement - septembre 2023"       = "retard_paiement_sep_2023",
  "Retard de paiement - août 2023"            = "retard_paiement_aou_2023",
  "Retard de paiement - juillet 2023"         = "retard_paiement_juil_2023",
  "Retard de paiement - juin 2023"            = "retard_paiement_juin_2023",
  "Retard de paiement - mai 2023"             = "retard_paiement_mai_2023",
  "Retard de paiement - avril 2023"           = "retard_paiement_avr_2023",
  "Encours de la carte - septembre 2023 (EUR)"= "encours_carte_sep_2023_eur",
  "Encours de la carte - août 2023 (EUR)"     = "encours_carte_aou_2023_eur",
  "Encours de la carte - juillet 2023 (EUR)"  = "encours_carte_juil_2023_eur",
  "Encours de la carte - juin 2023 (EUR)"     = "encours_carte_juin_2023_eur",
  "Encours de la carte - mai 2023 (EUR)"      = "encours_carte_mai_2023_eur",
  "Encours de la carte - avril 2023 (EUR)"    = "encours_carte_avr_2023_eur",
  "Montant remboursé - septembre 2023 (EUR)"  = "montant_rembourse_sep_2023_eur",
  "Montant remboursé - août 2023 (EUR)"       = "montant_rembourse_aou_2023_eur",
  "Montant remboursé - juillet 2023 (EUR)"    = "montant_rembourse_juil_2023_eur",
  "Montant remboursé - juin 2023 (EUR)"       = "montant_rembourse_juin_2023_eur",
  "Montant remboursé - mai 2023 (EUR)"        = "montant_rembourse_mai_2023_eur",
  "Montant remboursé - avril 2023 (EUR)"      = "montant_rembourse_avr_2023_eur"
)

# Variables catégorielles / discrètes : un barplot sera utilisé à leur place
# (plutôt qu'un boxplot) dans l'onglet de statistiques descriptives.
vars_categorielles <- c(
  "sexe", "niveau_education", "situation_familiale",
  "retard_paiement_sep_2023", "retard_paiement_aou_2023",
  "retard_paiement_juil_2023", "retard_paiement_juin_2023",
  "retard_paiement_mai_2023", "retard_paiement_avr_2023"
)

# Grille de notation du sujet : à partir de la probabilité de défaut
# prédite, on attribue une note (AAA à B), une qualification, une décision
# et une couleur d'affichage utilisée dans l'onglet "Prédiction".
attribuer_note <- function(prob) {
  if (is.na(prob)) {
    return(list(note = "?", quali = "Indéterminé",
                decision = "-", color = "#888888"))
  }
  if (prob < 0.10) {
    list(note = "AAA", quali = "Client excellent",
         decision = "Crédit accordé sans réserve", color = "#1a7a3e")
  } else if (prob < 0.25) {
    list(note = "AA", quali = "Très bon client",
         decision = "Crédit accordé", color = "#5fa676")
  } else if (prob < 0.40) {
    list(note = "A", quali = "Bon client",
         decision = "Crédit accordé avec suivi", color = "#a8b830")
  } else if (prob < 0.55) {
    list(note = "BBB", quali = "Profil modéré",
         decision = "Crédit en examen", color = "#f0ad4e")
  } else if (prob < 0.70) {
    list(note = "BB", quali = "Profil risqué",
         decision = "Crédit refusé", color = "#d9534f")
  } else {
    list(note = "B", quali = "Client très risqué",
         decision = "Crédit refusé", color = "#8b1a1a")
  }
}


# ---- 3. Thème ---------------------------------------------------------------
mon_theme <- bs_theme(
  version      = 5,
  bootswatch   = "flatly",
  primary      = "#1f3b5c",   # bleu marine
  secondary    = "#8ab79f",   # vert sauge
  base_font    = font_google("Inter"),
  heading_font = font_google("Inter")
)


# ---- 4. Interface utilisateur -----------------------------------------------
ui <- navbarPage(
  title = "Scoring bancaire - Master 1 ESA",
  theme = mon_theme,
  id    = "nav",
  
  # ---- Onglet 1 : Présentation ----------------------------------------------
  tabPanel(
    "Présentation",
    fluidPage(
      withMathJax(),
      
      # ---- Bandeau d'accueil ------------------------------------------------
      div(
        class = "p-5 mb-4 rounded",
        style = paste(
          "background: linear-gradient(135deg, #1f3b5c 0%, #2d5a8a 100%);",
          "color: white;"
        ),
        h1("Application de scoring bancaire", class = "display-5"),
        p(class = "lead",
          "Évaluation automatisée de la probabilité de défaut de paiement",
          " à partir de modèles Logit et Probit estimés sur ",
          format(nrow(credit), big.mark = " "), " clients."),
        tags$hr(class = "my-3",
                style = "border-color: rgba(255,255,255,0.3);"),
        p(class = "mb-0",
          "Projet individuel - Master 1 ESA - Avril 2026 - Quentin Ruel")
      ),
      
      # ---- Objet ------------------------------------------------------------
      card(
        card_header(
          tags$h4(icon("bullseye"), "  Objet de l'application",
                  class = "mb-0")
        ),
        card_body(
          p("Cette application permet d'évaluer le risque de défaut de",
            " paiement d'un client titulaire d'une carte de crédit.",
            " L'utilisateur peut :"),
          tags$ul(
            tags$li("explorer la base de données de manière interactive,"),
            tags$li("spécifier et estimer des modèles Logit et Probit,"),
            tags$li("mesurer leur performance prédictive",
                    " (courbe ROC, matrice de confusion),"),
            tags$li("simuler le score d'un nouveau client et obtenir une",
                    " recommandation d'octroi.")
          ),
          p("Aucune connaissance préalable de R, Shiny ou d'économétrie",
            " n'est nécessaire : tous les paramètres sont ajustables via",
            " des contrôles interactifs.")
        )
      ),
      
      br(),
      
      # ---- Parcours ---------------------------------------------------------
      card(
        card_header(
          tags$h4(icon("compass"), "  Parcourir l'application",
                  class = "mb-0")
        ),
        card_body(
          p("L'application est organisée en quatre onglets, à parcourir",
            " de préférence dans l'ordre :"),
          layout_columns(
            col_widths = c(6, 6, 6, 6),
            div(
              h5(tags$span(class = "badge bg-primary", "1"),
                 " Présentation"),
              p("Page actuelle. Objet de l'application, structure des",
                " données et cadre méthodologique.")
            ),
            div(
              h5(tags$span(class = "badge bg-primary", "2"), " Données"),
              p("Exploration interactive de la base : tableau filtrable,",
                " histogrammes, lien entre variables explicatives et",
                " défaut.")
            ),
            div(
              h5(tags$span(class = "badge bg-primary", "3"),
                 " Modélisation"),
              p("Sélection des variables, estimation des modèles Logit /",
                " Probit, évaluation des performances (ROC, matrice de",
                " confusion).")
            ),
            div(
              h5(tags$span(class = "badge bg-primary", "4"),
                 " Prédiction"),
              p("Saisie des caractéristiques d'un nouveau client et",
                " restitution du score, de la probabilité de défaut,",
                " de la note de crédit et de la décision associée.")
            )
          )
        )
      ),
      
      br(),
      
      # ---- Base de données --------------------------------------------------
      card(
        card_header(
          tags$h4(icon("database"), "  La base de données",
                  class = "mb-0")
        ),
        card_body(
          p("La base ", tags$code("credit_defaut"), " porte sur ",
            tags$strong(format(nrow(credit), big.mark = " ")),
            " clients titulaires d'une carte de crédit, observés entre",
            " avril et septembre 2023. Elle contient ",
            tags$strong(length(vars_explicatives)),
            " variables explicatives, regroupées en trois catégories :"),
          tags$ul(
            tags$li(tags$strong("Profil sociodémographique"),
                    " : sexe, âge, niveau d'éducation, situation",
                    " familiale."),
            tags$li(tags$strong("Caractéristique du crédit"),
                    " : plafond de la carte (en euros)."),
            tags$li(tags$strong("Historique de paiement"),
                    " : statut de retard, encours et montant remboursé",
                    " pour chacun des six derniers mois.")
          ),
          p("La variable cible, ",
            tags$code("defaut_paiement_mois_suivant"),
            ", est binaire : elle vaut ", tags$strong("1"),
            " en cas de défaut au mois suivant, ",
            tags$strong("0"), " sinon."),
          layout_columns(
            col_widths = c(4, 4, 4),
            value_box(
              title    = "Observations",
              value    = format(nrow(credit), big.mark = " "),
              showcase = icon("users"),
              theme    = "primary"
            ),
            value_box(
              title    = "Variables explicatives",
              value    = length(vars_explicatives),
              showcase = icon("list"),
              theme    = "secondary"
            ),
            value_box(
              title    = "Taux de défaut observé",
              value    = paste0(
                format(round(mean(
                  credit$defaut_paiement_mois_suivant) * 100, 2),
                  nsmall = 2), " %"),
              showcase = icon("triangle-exclamation"),
              theme    = "warning"
            )
          )
        )
      ),
      
      br(),
      
      # ---- Modèles ----------------------------------------------------------
      card(
        card_header(
          tags$h4(icon("chart-line"), "  Les modèles de scoring",
                  class = "mb-0")
        ),
        card_body(
          p("Le scoring bancaire consiste à attribuer à chaque demandeur",
            " un score reflétant sa probabilité de défaut. Cette",
            " application mobilise deux modèles de référence, adaptés",
            " aux variables dépendantes binaires."),
          layout_columns(
            col_widths = c(6, 6),
            card(
              class = "h-100",
              card_header("Modèle Logit",
                          class = "bg-primary text-white"),
              card_body(
                p("Suppose un terme d'erreur distribué selon une ",
                  tags$strong("loi logistique"),
                  ". La probabilité de défaut s'écrit :"),
                p("$$P(y_i = 1 \\mid \\mathbf{x}_i) = ",
                  "\\frac{\\exp(\\mathbf{x}_i' \\boldsymbol{\\beta})}",
                  "{1 + \\exp(\\mathbf{x}_i' \\boldsymbol{\\beta})}$$"),
                p("Avantage principal : interprétation directe des",
                  " coefficients en termes d'", tags$em("odds ratio"),
                  " (rapports de cotes). Un coefficient positif",
                  " augmente la probabilité de défaut.")
              )
            ),
            card(
              class = "h-100",
              card_header("Modèle Probit",
                          class = "bg-secondary text-white"),
              card_body(
                p("Suppose un terme d'erreur distribué selon une ",
                  tags$strong("loi normale centrée réduite"),
                  ". La probabilité de défaut s'écrit :"),
                p("$$P(y_i = 1 \\mid \\mathbf{x}_i) = ",
                  "\\Phi(\\mathbf{x}_i' \\boldsymbol{\\beta})$$"),
                p("où \\(\\Phi\\) désigne la fonction de répartition de",
                  " la loi normale standard. Pas d'interprétation en ",
                  tags$em("odds ratio"), ", mais un comportement très",
                  " proche du Logit en pratique.")
              )
            )
          ),
          br(),
          p(class = "text-muted mb-0",
            icon("circle-info"),
            " Les deux modèles sont estimés par ",
            tags$strong("maximum de vraisemblance"),
            ". Leur comparaison (AIC, BIC, AUC) est réalisée",
            " automatiquement dans l'onglet ",
            tags$em("Modélisation"), ".")
        )
      ),
      
      br(), br()
    )
  ),
  
  # ---- Onglet 2 : Données et statistiques descriptives ---------------------
  tabPanel(
    "Données",
    fluidPage(
      
      # ---- Card 1 : Tableau filtrable --------------------------------------
      card(
        card_header(
          tags$h4(icon("table"), "  Tableau filtrable", class = "mb-0")
        ),
        card_body(
          p("Explorez un extrait de la base en ajustant le nombre de",
            " lignes affichées et en filtrant selon le statut de défaut."),
          layout_columns(
            col_widths = c(4, 4, 4),
            numericInput(
              "nb_lignes",
              "Nombre de lignes par page :",
              value = 10, min = 5, max = 100, step = 5
            ),
            selectInput(
              "filtre_defaut",
              "Filtrer par statut de défaut :",
              choices = c("Tous les clients"  = "tous",
                          "Non-défaut (0)"    = "0",
                          "Défaut (1)"        = "1")
            )
          ),
          DTOutput("table_credit")
        )
      ),
      
      br(),
      
      # ---- Card 2 : Analyse univariée --------------------------------------
      card(
        card_header(
          tags$h4(icon("chart-column"), "  Analyse univariée",
                  class = "mb-0")
        ),
        card_body(
          p("Sélectionnez une variable explicative pour visualiser sa",
            " distribution, ses statistiques descriptives et sa relation",
            " avec la variable cible."),
          selectInput(
            "var_desc",
            "Variable à analyser :",
            choices  = vars_labels,
            selected = "retard_paiement_sep_2023",
            width    = "100%"
          ),
          
          # Ligne 1 : histogramme + tableau de stats
          layout_columns(
            col_widths = c(8, 4),
            div(
              h5(icon("chart-area"), "  Distribution"),
              plotlyOutput("histo_var", height = "380px")
            ),
            div(
              h5(icon("calculator"), "  Statistiques descriptives"),
              tableOutput("stats_var")
            )
          ),
          
          tags$hr(),
          
          # Ligne 2 : graphique comparatif selon la cible
          div(
            h5(icon("scale-balanced"),
               "  Lien avec la variable cible (défaut de paiement)"),
            plotlyOutput("comp_var", height = "380px")
          )
        )
      ),
      
      br(), br()
    )
  ),
  
  # ---- Onglet 3 : Modélisation et performances -----------------------------
  tabPanel(
    "Modélisation",
    layout_sidebar(
      
      # ---- Sidebar : contrôles d'estimation -------------------------------
      sidebar = sidebar(
        width = 340,
        title = tags$span(icon("sliders"), "  Paramètres d'estimation"),
        
        tags$label("Variables explicatives :", class = "fw-bold"),
        tags$p(class = "text-muted small mb-2",
               "Les 18 variables retenues par la procédure stepwise sont",
               " cochées par défaut."),
        div(
          style = paste("max-height: 340px; overflow-y: auto;",
                        "border: 1px solid #dee2e6; border-radius: 6px;",
                        "padding: 8px 12px; background: #f8f9fa;"),
          checkboxGroupInput(
            "vars_modele", label = NULL,
            choices  = vars_labels,
            selected = vars_stepwise
          )
        ),
        
        br(),
        
        sliderInput(
          "prop_train",
          "Proportion de l'échantillon d'entraînement :",
          min = 0.60, max = 0.80, value = 0.70, step = 0.05,
          post = "", ticks = TRUE
        ),
        
        br(),
        
        actionButton(
          "btn_estimer",
          label = tagList(icon("play"), "  Estimer les modèles"),
          class = "btn-primary btn-lg w-100"
        )
      ),
      
      # ---- Panneau principal : résultats ----------------------------------
      
      # --- Résumé de l'estimation ---
      card(
        card_header(
          tags$h4(icon("circle-info"), "  Résumé de l'estimation",
                  class = "mb-0")
        ),
        card_body(uiOutput("info_estimation"))
      ),
      
      br(),
      
      # --- Table de régression (stargazer) ---
      card(
        card_header(
          tags$h4(icon("table"), "  Coefficients estimés", class = "mb-0")
        ),
        card_body(
          tags$p(class = "text-muted small",
                 "Erreurs-types entre parenthèses. Seuils de significativité :",
                 " *** p < 0,01  **  p < 0,05  *  p < 0,1."),
          div(style = "overflow-x: auto;",
              uiOutput("reg_table"))
        )
      ),
      
      br(),
      
      # --- Courbes ROC ---
      card(
        card_header(
          tags$h4(icon("chart-line"), "  Courbes ROC", class = "mb-0")
        ),
        card_body(
          tags$p(class = "text-muted small",
                 "Courbes ROC calculées sur l'échantillon de test. L'aire",
                 " sous la courbe (AUC) quantifie la capacité",
                 " discriminante du modèle."),
          plotlyOutput("roc_plot", height = "460px")
        )
      ),
      
      br(),
      
      # --- Matrice de confusion et métriques ---
      card(
        card_header(
          tags$h4(icon("border-all"),
                  "  Matrice de confusion et métriques",
                  class = "mb-0")
        ),
        card_body(
          layout_columns(
            col_widths = c(6, 6),
            selectInput(
              "model_eval",
              "Modèle évalué :",
              choices = c("Logit" = "logit", "Probit" = "probit")
            ),
            sliderInput(
              "seuil",
              "Seuil de classification :",
              min = 0, max = 1, value = 0.5, step = 0.01
            )
          ),
          br(),
          layout_columns(
            col_widths = c(7, 5),
            div(
              h5(icon("table-cells"), "  Matrice de confusion"),
              tags$p(class = "text-muted small",
                     "Lignes : statut observé — Colonnes : statut prédit."),
              uiOutput("conf_matrix")
            ),
            div(
              h5(icon("gauge-high"), "  Performances"),
              uiOutput("perf_boxes")
            )
          )
        )
      ),
      
      br(), br()
    )
  ),
  
  # ---- Onglet 4 : Prédiction d'un nouveau client ---------------------------
  tabPanel(
    "Prédiction",
    fluidPage(
      
      # ---- Formulaire de saisie -------------------------------------------
      card(
        card_header(
          tags$h4(icon("user-plus"),
                  "  Caractéristiques du nouveau client",
                  class = "mb-0")
        ),
        card_body(
          
          # Identité + choix du modèle
          layout_columns(
            col_widths = c(4, 4, 4),
            textInput("prenom", "Prénom :",  value = "Quentin"),
            textInput("nom",    "Nom :",     value = "Ruel"),
            radioButtons(
              "model_pred", "Modèle utilisé :",
              choices  = c("Logit" = "logit", "Probit" = "probit"),
              selected = "logit",
              inline   = TRUE
            )
          ),
          
          tags$hr(),
          
          tags$p(
            class = "text-muted small",
            "Renseignez ci-dessous les caractéristiques du client. Seules",
            " les variables incluses dans le modèle estimé (onglet ",
            tags$em("Modélisation"), ") sont demandées."
          ),
          
          uiOutput("client_inputs"),
          
          br(),
          
          actionButton(
            "btn_predict",
            label = tagList(icon("calculator"),
                            "  Calculer le score de risque"),
            class = "btn-primary btn-lg w-100"
          )
        )
      ),
      
      br(),
      
      # ---- Barème de notation (replié par défaut) -------------------------
      card(
        card_body(
          tags$details(
            tags$summary(
              style = paste("cursor: pointer; font-weight: 600;",
                            "padding: 4px 0; user-select: none;"),
              icon("table-list"),
              "  Consulter le barème de notation"
            ),
            tags$div(
              style = "margin-top: 16px;",
              tags$table(
                class = "table table-bordered text-center mb-0",
                tags$thead(
                  style = "background-color: #1f3b5c; color: white;",
                  tags$tr(
                    tags$th("Note"),
                    tags$th("Qualification"),
                    tags$th("Probabilité de défaut"),
                    tags$th("Décision")
                  )
                ),
                tags$tbody(
                  tags$tr(
                    tags$td(style = "background-color: #1a7a3e; color: white; font-weight: 700;",
                            "AAA"),
                    tags$td("Client excellent"),
                    tags$td("< 10 %"),
                    tags$td("Crédit accordé sans réserve")
                  ),
                  tags$tr(
                    tags$td(style = "background-color: #5fa676; color: white; font-weight: 700;",
                            "AA"),
                    tags$td("Très bon client"),
                    tags$td("[10 %, 25 %)"),
                    tags$td("Crédit accordé")
                  ),
                  tags$tr(
                    tags$td(style = "background-color: #a8b830; color: white; font-weight: 700;",
                            "A"),
                    tags$td("Bon client"),
                    tags$td("[25 %, 40 %)"),
                    tags$td("Crédit accordé avec suivi")
                  ),
                  tags$tr(
                    tags$td(style = "background-color: #f0ad4e; color: white; font-weight: 700;",
                            "BBB"),
                    tags$td("Profil modéré"),
                    tags$td("[40 %, 55 %)"),
                    tags$td("Crédit en examen")
                  ),
                  tags$tr(
                    tags$td(style = "background-color: #d9534f; color: white; font-weight: 700;",
                            "BB"),
                    tags$td("Profil risqué"),
                    tags$td("[55 %, 70 %)"),
                    tags$td("Crédit refusé")
                  ),
                  tags$tr(
                    tags$td(style = "background-color: #8b1a1a; color: white; font-weight: 700;",
                            "B"),
                    tags$td("Client très risqué"),
                    tags$td("≥ 70 %"),
                    tags$td("Crédit refusé")
                  )
                )
              )
            )
          )
        )
      ),
      
      br(),
      
      # ---- Carte de résultat (apparaît après le clic) ---------------------
      uiOutput("result_card"),
      
      br(), br()
    )
  )
)


# ---- 5. Server --------------------------------------------------------------
server <- function(input, output, session) {
  
  # --------------------------------------------------------------------------
  # Cœur réactif de l'application : estimation des modèles Logit et Probit.
  #
  # L'objet `modeles()` est un eventReactive déclenché par le bouton
  # input$btn_estimer (qui sera ajouté à l'onglet Modélisation à l'étape 3).
  # Il renvoie une liste contenant :
  #   - logit, probit : les deux modèles glm estimés
  #   - train, test   : les partitions d'entraînement et de test
  #   - vars          : les variables sélectionnées par l'utilisateur
  #   - formule       : la formule utilisée
  #
  # Cette liste est ensuite consommée par les onglets "Modélisation"
  # (affichage des coefficients, ROC, matrice de confusion) et "Prédiction"
  # (calcul du score pour un nouveau client), ce qui garantit que les
  # modèles ne sont estimés qu'une seule fois, conformément à l'exigence
  # technique n°2 du sujet.
  # --------------------------------------------------------------------------
  modeles <- eventReactive(input$btn_estimer, {
    
    # Sécurité : attendre que les inputs de l'onglet Modélisation soient
    # disponibles et qu'au moins une variable soit sélectionnée.
    req(input$vars_modele, input$prop_train)
    req(length(input$vars_modele) >= 1)
    
    # Variables sélectionnées par l'utilisateur (par défaut : celles
    # retenues par la stepwise).
    vars <- input$vars_modele
    
    # Proportion d'entraînement choisie via le curseur (60-80 %).
    prop_train <- input$prop_train
    
    # Partition aléatoire reproductible (exigence technique n°3 du sujet).
    set.seed(123)
    n         <- nrow(credit)
    idx_train <- sample(seq_len(n), size = floor(prop_train * n))
    train     <- credit[idx_train, ]
    test      <- credit[-idx_train, ]
    
    # Formule à estimer.
    formule <- as.formula(
      paste("defaut_paiement_mois_suivant ~", paste(vars, collapse = " + "))
    )
    
    # Estimation des deux modèles.
    logit  <- glm(formule, data = train, family = binomial(link = "logit"))
    probit <- glm(formule, data = train, family = binomial(link = "probit"))
    
    list(
      logit   = logit,
      probit  = probit,
      train   = train,
      test    = test,
      vars    = vars,
      formule = formule,
      prop    = prop_train
    )
  }, ignoreNULL = FALSE)
  # ignoreNULL = FALSE : une estimation "par défaut" est lancée au démarrage
  # avec les variables cochées par défaut (les 18 retenues par stepwise) et
  # la proportion d'entraînement par défaut (70 %). Le reactive est ensuite
  # relancé à chaque clic sur "Estimer".
  
  
  # ==========================================================================
  # Onglet 2 : Données et statistiques descriptives
  # ==========================================================================
  
  # ---- Tableau filtrable ---------------------------------------------------
  output$table_credit <- DT::renderDT({
    data <- credit %>% select(-ends_with("_label"))
    
    if (input$filtre_defaut != "tous") {
      data <- data[
        data$defaut_paiement_mois_suivant == as.numeric(input$filtre_defaut),
      ]
    }
    
    DT::datatable(
      data,
      rownames = FALSE,
      options  = list(
        pageLength   = input$nb_lignes,
        scrollX      = TRUE,
        lengthChange = FALSE,   # on pilote la taille via notre numericInput
        language     = list(
          search        = "Rechercher :",
          info          = "Affichage de _START_ à _END_ sur _TOTAL_ clients",
          paginate      = list(previous = "Précédent", `next` = "Suivant"),
          zeroRecords   = "Aucun client ne correspond au filtre"
        )
      )
    )
  })
  
  # ---- Histogramme interactif de la variable sélectionnée ------------------
  output$histo_var <- renderPlotly({
    var       <- input$var_desc
    label_var <- names(vars_labels)[vars_labels == var]
    is_cat    <- var %in% vars_categorielles
    
    if (is_cat) {
      p <- ggplot(credit, aes(x = factor(.data[[var]]))) +
        geom_bar(fill = "#1f3b5c", color = "white") +
        labs(x = label_var, y = "Effectif") +
        theme_minimal()
    } else {
      p <- ggplot(credit, aes(x = .data[[var]])) +
        geom_histogram(fill = "#1f3b5c", color = "white", bins = 30) +
        labs(x = label_var, y = "Effectif") +
        theme_minimal()
    }
    
    ggplotly(p) %>% config(displayModeBar = FALSE)
  })
  
  # ---- Tableau de statistiques descriptives --------------------------------
  output$stats_var <- renderTable({
    x <- credit[[input$var_desc]]
    data.frame(
      Statistique = c("Moyenne", "Médiane", "Écart-type",
                      "Minimum", "Maximum"),
      Valeur      = c(
        format(round(mean(x),   2), big.mark = " ", nsmall = 2),
        format(round(median(x), 2), big.mark = " ", nsmall = 2),
        format(round(sd(x),     2), big.mark = " ", nsmall = 2),
        format(round(min(x),    2), big.mark = " ", nsmall = 2),
        format(round(max(x),    2), big.mark = " ", nsmall = 2)
      )
    )
  }, striped = TRUE, bordered = TRUE, align = "lr", width = "100%")
  
  # ---- Graphique comparatif selon le statut de défaut ----------------------
  output$comp_var <- renderPlotly({
    var       <- input$var_desc
    label_var <- names(vars_labels)[vars_labels == var]
    is_cat    <- var %in% vars_categorielles
    palette   <- c("Non-défaut" = "#1f3b5c", "Défaut" = "#8ab79f")
    
    if (is_cat) {
      # Barplot groupé : effectifs par modalité, colorés par statut
      df_plot <- credit %>%
        count(.data[[var]], defaut_label) %>%
        rename(modalite = 1)
      
      p <- ggplot(df_plot,
                  aes(x = factor(modalite), y = n, fill = defaut_label)) +
        geom_col(position = "dodge") +
        scale_fill_manual(values = palette) +
        labs(x = label_var, y = "Effectif", fill = "Statut") +
        theme_minimal()
    } else {
      # Boxplot selon le statut de défaut
      p <- ggplot(credit,
                  aes(x = defaut_label, y = .data[[var]],
                      fill = defaut_label)) +
        geom_boxplot(alpha = 0.85, outlier.alpha = 0.3) +
        scale_fill_manual(values = palette) +
        labs(x = "Statut de défaut", y = label_var, fill = "Statut") +
        theme_minimal() +
        theme(legend.position = "none")
    }
    
    ggplotly(p) %>% config(displayModeBar = FALSE)
  })
  
  # ==========================================================================
  # Onglet 3 : Modélisation et performances
  # ==========================================================================
  
  # ---- Résumé de l'estimation ----------------------------------------------
  output$info_estimation <- renderUI({
    mod <- modeles()
    req(mod)
    
    layout_columns(
      col_widths = c(3, 3, 3, 3),
      value_box(
        title    = "Variables sélectionnées",
        value    = length(mod$vars),
        showcase = icon("list-check"),
        theme    = "primary"
      ),
      value_box(
        title    = "Partition train / test",
        value    = paste0(round(mod$prop * 100), " / ",
                          round((1 - mod$prop) * 100), " %"),
        showcase = icon("scale-unbalanced"),
        theme    = "secondary"
      ),
      value_box(
        title    = "Échantillon d'entraînement",
        value    = format(nrow(mod$train), big.mark = " "),
        showcase = icon("graduation-cap"),
        theme    = "primary"
      ),
      value_box(
        title    = "Échantillon de test",
        value    = format(nrow(mod$test), big.mark = " "),
        showcase = icon("flask-vial"),
        theme    = "secondary"
      )
    )
  })
  
  # ---- Table de régression (stargazer) -------------------------------------
  output$reg_table <- renderUI({
    mod <- modeles()
    req(mod)
    
    html_out <- capture.output(
      stargazer(
        mod$logit, mod$probit,
        type             = "html",
        column.labels    = c("Logit", "Probit"),
        dep.var.labels   = "Défaut de paiement",
        star.cutoffs     = c(0.1, 0.05, 0.01),
        omit.stat        = c("f", "ser", "adj.rsq"),
        no.space         = TRUE,
        digits           = 4,
        header           = FALSE
      )
    )
    HTML(paste(html_out, collapse = "\n"))
  })
  
  # ---- Courbes ROC ---------------------------------------------------------
  output$roc_plot <- renderPlotly({
    mod <- modeles()
    req(mod)
    
    y_test <- mod$test$defaut_paiement_mois_suivant
    
    # Probabilités prédites sur l'échantillon de test
    prob_logit  <- predict(mod$logit,  newdata = mod$test, type = "response")
    prob_probit <- predict(mod$probit, newdata = mod$test, type = "response")
    
    # Objets ROC (pROC) - quiet = TRUE pour supprimer les messages
    roc_logit  <- pROC::roc(y_test, prob_logit,  quiet = TRUE)
    roc_probit <- pROC::roc(y_test, prob_probit, quiet = TRUE)
    
    auc_logit  <- as.numeric(pROC::auc(roc_logit))
    auc_probit <- as.numeric(pROC::auc(roc_probit))
    
    plot_ly() %>%
      add_trace(
        x    = 1 - roc_logit$specificities,
        y    = roc_logit$sensitivities,
        type = "scatter", mode = "lines",
        name = paste0("Logit (AUC = ", round(auc_logit, 4), ")"),
        line = list(color = "#1f3b5c", width = 3)
      ) %>%
      add_trace(
        x    = 1 - roc_probit$specificities,
        y    = roc_probit$sensitivities,
        type = "scatter", mode = "lines",
        name = paste0("Probit (AUC = ", round(auc_probit, 4), ")"),
        line = list(color = "#8ab79f", width = 3, dash = "dash")
      ) %>%
      add_trace(
        x = c(0, 1), y = c(0, 1),
        type = "scatter", mode = "lines",
        name = "Classement aléatoire",
        line = list(color = "gray", width = 1, dash = "dot"),
        showlegend = FALSE
      ) %>%
      layout(
        xaxis  = list(title = "1 - Spécificité (taux de faux positifs)",
                      range = c(0, 1)),
        yaxis  = list(title = "Sensibilité (taux de vrais positifs)",
                      range = c(0, 1),
                      scaleanchor = "x"),
        legend = list(x = 0.55, y = 0.1,
                      bgcolor = "rgba(255,255,255,0.7)"),
        margin = list(l = 60, r = 40, t = 20, b = 60)
      ) %>%
      config(displayModeBar = FALSE)
  })
  
  # ---- Données communes pour la matrice de confusion et les métriques -----
  conf_data <- reactive({
    mod <- modeles()
    req(mod)
    
    model_obj <- if (input$model_eval == "logit") mod$logit else mod$probit
    
    prob <- predict(model_obj, newdata = mod$test, type = "response")
    
    # Factorisation avec levels = c(0, 1) pour garantir une matrice 2x2
    # même si le seuil est très bas / très haut.
    obs  <- factor(mod$test$defaut_paiement_mois_suivant, levels = c(0, 1))
    pred <- factor(as.integer(prob > input$seuil),       levels = c(0, 1))
    
    cm <- table(Observé = obs, Prédit = pred)
    
    tn <- cm[1, 1]; fp <- cm[1, 2]
    fn <- cm[2, 1]; tp <- cm[2, 2]
    total <- sum(cm)
    
    list(
      cm          = cm,
      accuracy    = (tp + tn) / total,
      err_rate    = (fp + fn) / total,
      sensitivity = if ((tp + fn) > 0) tp / (tp + fn) else NA,
      specificity = if ((tn + fp) > 0) tn / (tn + fp) else NA
    )
  })
  
  # ---- Matrice de confusion (tableau formaté) ------------------------------
  output$conf_matrix <- renderUI({
    cd <- conf_data()
    cm <- cd$cm
    
    tags$table(
      class = "table table-bordered text-center",
      style = "margin-bottom: 0;",
      tags$thead(
        tags$tr(
          tags$th(""),
          tags$th(colspan = 2,
                  style = "background-color: #1f3b5c; color: white;",
                  "Prédit")
        ),
        tags$tr(
          tags$th(style = "background-color: #1f3b5c; color: white;",
                  "Observé"),
          tags$th("Non-défaut (0)"),
          tags$th("Défaut (1)")
        )
      ),
      tags$tbody(
        tags$tr(
          tags$th("Non-défaut (0)",
                  style = "background-color: #f8f9fa;"),
          tags$td(style = "background-color: #d4edda;",
                  tags$strong(format(cm[1, 1], big.mark = " "))),
          tags$td(style = "background-color: #f8d7da;",
                  format(cm[1, 2], big.mark = " "))
        ),
        tags$tr(
          tags$th("Défaut (1)",
                  style = "background-color: #f8f9fa;"),
          tags$td(style = "background-color: #f8d7da;",
                  format(cm[2, 1], big.mark = " ")),
          tags$td(style = "background-color: #d4edda;",
                  tags$strong(format(cm[2, 2], big.mark = " ")))
        )
      )
    )
  })
  
  # ---- Value boxes des métriques de performance ----------------------------
  output$perf_boxes <- renderUI({
    cd <- conf_data()
    
    fmt_pct <- function(x) {
      if (is.na(x)) return("--")
      paste0(format(round(x * 100, 2), nsmall = 2), " %")
    }
    
    tagList(
      value_box(
        title    = "Taux d'erreur global",
        value    = fmt_pct(cd$err_rate),
        showcase = icon("triangle-exclamation"),
        theme    = "warning"
      ),
      br(),
      value_box(
        title    = "Sensibilité (TVP)",
        value    = fmt_pct(cd$sensitivity),
        showcase = icon("bullseye"),
        theme    = "primary"
      ),
      br(),
      value_box(
        title    = "Spécificité (TVN)",
        value    = fmt_pct(cd$specificity),
        showcase = icon("shield-halved"),
        theme    = "secondary"
      )
    )
  })
  
  # ==========================================================================
  # Onglet 4 : Prédiction d'un nouveau client
  # ==========================================================================
  
  # ---- Génération dynamique des contrôles de saisie ------------------------
  # On ne demande à l'utilisateur que les variables effectivement utilisées
  # par le modèle courant (mod$vars). Le contrôle est adapté au type de
  # variable : selectInput pour les catégorielles, sliderInput pour les
  # retards (échelle ordinale -2 à 8), numericInput pour les continues.
  output$client_inputs <- renderUI({
    mod <- modeles()
    req(mod)
    
    inputs <- lapply(mod$vars, function(v) {
      label_var <- names(vars_labels)[vars_labels == v]
      input_id  <- paste0("pred_", v)
      
      if (v == "sexe") {
        selectInput(input_id, label_var,
                    choices  = c("Homme (1)" = 1, "Femme (2)" = 2),
                    selected = 1)
        
      } else if (v == "niveau_education") {
        selectInput(input_id, label_var,
                    choices  = c("Autre (0)"   = 0, "Doctorat (1)" = 1,
                                 "Master (2)"  = 2, "Licence (3)"  = 3,
                                 "Lycée (4)"   = 4, "Autre 2 (5)"  = 5,
                                 "Autre 3 (6)" = 6),
                    selected = 2)
        
      } else if (v == "situation_familiale") {
        selectInput(input_id, label_var,
                    choices  = c("Autre (0)"       = 0,
                                 "Marié(e) (1)"    = 1,
                                 "Célibataire (2)" = 2,
                                 "Autre 2 (3)"     = 3),
                    selected = 2)
        
      } else if (grepl("^retard_paiement_", v)) {
        sliderInput(input_id, label_var,
                    min = -2, max = 8, value = 0, step = 1)
        
      } else {
        # Variables continues : pré-remplissage avec la médiane,
        # sauf pour l'âge qui est fixé à 24 ans (profil par défaut).
        x       <- credit[[v]]
        med_val <- median(x, na.rm = TRUE)
        step_v  <- if (v == "age") 1 else 100
        default_val <- if (v == "age") 24 else round(med_val)
        numericInput(input_id, label_var,
                     value = default_val,
                     min   = min(x, na.rm = TRUE),
                     max   = max(x, na.rm = TRUE),
                     step  = step_v)
      }
    })
    
    # Mise en page : 2 colonnes, autant de lignes que nécessaire.
    do.call(layout_columns,
            c(list(col_widths = rep(6, length(inputs))),
              inputs))
  })
  
  # ---- Calcul de la prédiction (déclenché par le bouton) -------------------
  prediction <- eventReactive(input$btn_predict, {
    mod <- modeles()
    req(mod)
    
    vars   <- mod$vars
    values <- lapply(vars, function(v) input[[paste0("pred_", v)]])
    
    # Sécurité : tous les inputs doivent être renseignés.
    req(all(!sapply(values, is.null)))
    
    # Construction du data.frame du nouveau client.
    client <- as.data.frame(setNames(
      lapply(values, function(x) as.numeric(x)),
      vars
    ))
    
    # Modèle choisi par l'utilisateur.
    model_obj <- if (input$model_pred == "logit") mod$logit else mod$probit
    
    # Score linéaire (x'beta) et probabilité de défaut prédite.
    score <- as.numeric(predict(model_obj, newdata = client, type = "link"))
    prob  <- as.numeric(predict(model_obj, newdata = client,
                                type = "response"))
    
    note_info <- attribuer_note(prob)
    
    list(
      prenom   = input$prenom,
      nom      = input$nom,
      model    = input$model_pred,
      score    = score,
      prob     = prob,
      note     = note_info$note,
      quali    = note_info$quali,
      decision = note_info$decision,
      color    = note_info$color
    )
  })
  
  # ---- Carte de résultat ---------------------------------------------------
  output$result_card <- renderUI({
    
    # Avant tout calcul : afficher un message d'invitation.
    if (is.null(input$btn_predict) || input$btn_predict == 0) {
      return(div(
        class = "alert alert-light border text-center p-4",
        icon("circle-info"), "  ",
        "Renseignez les caractéristiques du client puis cliquez sur ",
        tags$strong("Calculer le score de risque"),
        " pour obtenir l'analyse."
      ))
    }
    
    pred <- prediction()
    req(pred)
    
    fmt_num <- function(x, dec = 4) {
      format(round(x, dec), decimal.mark = ",", nsmall = dec)
    }
    fmt_pct <- function(x, dec = 2) {
      paste0(format(round(x * 100, dec), nsmall = dec,
                    decimal.mark = ","), " %")
    }
    
    modele_label <- if (pred$model == "logit") "Modèle Logit" else "Modèle Probit"
    nom_complet  <- paste(pred$prenom, pred$nom)
    
    card(
      class = "shadow",
      card_header(
        style = paste0("background-color: ", pred$color,
                       "; color: white;"),
        tags$h4(
          icon("clipboard-check"),
          "  Analyse de ", nom_complet,
          tags$small(class = "ms-2",
                     style = "opacity: 0.85; font-weight: 400;",
                     paste0("(", modele_label, ")")),
          class = "mb-0"
        )
      ),
      
      card_body(
        
        # ---- Grosse note centrale ----
        div(
          class = "text-center mb-4",
          tags$div(
            style = paste0(
              "display: inline-block; padding: 24px 60px;",
              "background-color: ", pred$color, "; color: white;",
              "font-size: 4.5rem; font-weight: 700; line-height: 1;",
              "border-radius: 12px; letter-spacing: 6px;",
              "box-shadow: 0 6px 18px rgba(0,0,0,0.18);"
            ),
            pred$note
          ),
          tags$div(
            class = "h4 mt-3 mb-0 fw-semibold",
            style = paste0("color: ", pred$color, ";"),
            pred$quali
          )
        ),
        
        # ---- Score linéaire et probabilité ----
        layout_columns(
          col_widths = c(6, 6),
          value_box(
            title    = "Score linéaire",
            value    = fmt_num(pred$score, 4),
            showcase = icon("calculator"),
            theme    = "primary"
          ),
          value_box(
            title    = "Probabilité de défaut estimée",
            value    = fmt_pct(pred$prob, 2),
            showcase = icon("percent"),
            theme    = "secondary"
          )
        ),
        
        br(),
        
        # ---- Décision ----
        tags$div(
          class = "p-3 rounded text-center",
          style = paste0(
            "background-color: ", pred$color, "20;",
            "border-left: 5px solid ", pred$color, ";"
          ),
          tags$div(class = "small text-uppercase fw-bold text-muted",
                   "Décision"),
          tags$div(class = "h4 mb-0 mt-1",
                   style = paste0("color: ", pred$color, ";"),
                   pred$decision)
        )
      )
    )
  })
}


# ---- 6. Lancement de l'application ------------------------------------------
shinyApp(ui = ui, server = server)