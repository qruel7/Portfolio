# Corpus Sapin 2 — pointeur

Le PDF n'est pas versionné (`*.pdf` et `data/` sont ignorés). On garde ici de quoi le retrouver et vérifier qu'on travaille sur le même fichier.

| Champ | Valeur |
|---|---|
| Texte | Loi n° 2016-1691 du 9 décembre 2016 relative à la transparence, à la lutte contre la corruption et à la modernisation de la vie économique (« Sapin 2 ») |
| Version | Consolidée, Légifrance, en vigueur au 24/10/2026 (données mises à jour le 01/12/2025) |
| Source | legifrance.gouv.fr, fiche LODA JORFTEXT000033558528, export PDF |
| Fichier local | `data/corpus/sapin2-legifrance-2026-10-24.pdf` |
| Taille | 1 437 080 octets, 76 pages |
| SHA-256 du PDF | `47ef8d381a30e9740431ab6248010a69da810838e8c987fd9303d3a946cf3cb9` |
| SHA-256 du texte nettoyé | `ce42aa5e24af94a8d4204ee93176168fa3f7bedc455a7927387147970578b8de` |
| Taille du texte | 141 690 caractères, ≈ 46 600 tokens (estimation) |
| Découpage | 9 sections de 4 000 à 8 000 tokens ; l'article 17 est en S03 (« Article 13 → Titre III ») |

## Ce qu'il faut savoir sur ce texte

- **La version JO de 2016 est écartée.** Elle est périmée : l'article 17 a été modifié depuis, en dernier lieu par la loi n° 2025-532 du 13 juin 2025.
- **98 articles sur 175 sont de simples renvois** (« A modifié les dispositions suivantes : … »). Ils modifient des codes dont le texte n'est pas reproduit ici. L'Agent 1 en tirera peu de lignes, et c'est normal.
- **Mentions éditoriales de Légifrance** : « EN VIGUEUR DEPUIS LE… », « Modifié par LOI n°… ». Ce sont des métadonnées, pas des exigences. À contrôler dans la sortie de l'Agent 1.
- **Subdivisions romaines « I.-Les… », sans espace après le tiret.** Le découpage les reconnaît depuis le 24/10. L'article 17 est ainsi découpé en I à VIII, ce qui permet à la passe de rattrapage de travailler à ce niveau. Ce changement est sans effet sur IFRS 9 : sections et paragraphes omis sont identiques, ce qui a été vérifié.
- **Peu de tournures prescriptives explicites.** On en compte 18 sur tout le texte (613 pour IFRS 9), parce que le droit français prescrit au présent (« mettent en œuvre »). Pour la passe de rattrapage, il faudra probablement `--seuil 0`. Décision à prendre au vu du diagnostic `couverture_paragraphes.py`.
- **Référentiel :** fourni par Deloitte, confidentiel, non publié.
