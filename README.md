# Agent IA – Expert M&A & Diagnostic d'Entreprise

Cet agent Python analyse automatiquement les documents financiers et
extra-financiers d'une entreprise (bilans, comptes de résultat, SIG,
plaquettes commerciales, retraitements de charges) et produit un **rapport
de diagnostic M&A complet** au format Markdown.

## Prérequis

- Python 3.10+
- Une clé API OpenAI

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copiez `.env.example` en `.env` et renseignez votre clé OpenAI :

```bash
cp .env.example .env
# Éditez .env et remplacez sk-... par votre clé
```

## Utilisation

```bash
# Analyse les PDF du répertoire courant, génère rapport_diagnostic.md
python agent.py

# Spécifier un répertoire et un fichier de sortie
python agent.py --docs-dir /chemin/vers/docs --output mon_rapport.md

# Utiliser un modèle spécifique
python agent.py --model gpt-4o-mini
```

## Structure du rapport généré

1. **Fiche d'identité** – Secteur, géographie, positionnement
2. **Tableau Synoptique Financier** – 3 exercices comparatifs
3. **Analyse de la Valorisation** – Multiples EBE/EBIT, DCF, patrimoniale,
   passage Valeur d'Entreprise → Valeur des Titres
4. **Diagnostic d'Investissement** – Arguments pour et contre l'acquisition
5. **Questions clés au vendeur** – Points d'éclaircissement nécessaires
6. **Leviers de négociation** – Arguments acheteur pour minimiser le prix
7. **Conclusion Stratégique** – Avis argumenté sur l'opportunité

## Documents analysés (exemple – SARL AGINUM THERMAE)

| Fichier | Contenu |
|---|---|
| `bilan 2023 aginum.PDF` | Comptes annuels FY 2022/2023 |
| `plaquette 2024.pdf` | Comptes annuels FY 2023/2024 |
| `2025.pdf` | Comptes annuels FY 2024/2025 |
| `retraitement Charges Aginum - Feuille 1.pdf` | Retraitement des charges |
| `2023 SCI.pdf` | Comptes SCI FY 2023 |
| `2024 SCI.pdf` | Comptes SCI FY 2024 |
| `2025 SCI.pdf` | Comptes SCI FY 2025 |
