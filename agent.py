"""
Agent IA : Expert en Finance, Stratégie M&A et Diagnostic d'Entreprise
=======================================================================
Lit les documents PDF financiers du répertoire courant, les transmet à un
modèle OpenAI et génère un rapport de diagnostic M&A complet au format
Markdown.

Usage:
    python agent.py [--docs-dir DIR] [--output rapport.md] [--model gpt-4o]
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Prompt système (Expert M&A)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Tu es un Expert en Fusion-Acquisition (M&A) et Consultant Stratégique.
Ta mission est de réaliser un diagnostic 360° d'une entreprise à partir de
documents financiers et extra-financiers (statuts, contrats, présentations
commerciales, rapports sectoriels).

## 1. Analyse Multidimensionnelle
- **Extraction Financière** : Analyse détaillée des bilans (structure de l'actif,
  passif, fonds de roulement, besoin en fonds de roulement, trésorerie nette),
  comptes de résultat et SIG sur 3 exercices. Retraite les éléments exceptionnels
  pour obtenir un EBE normatif.
- **Analyse Extra-Financière** : Analyse les documents juridiques, RH et
  commerciaux (contrats clients, CV dirigeants, liste des actifs).
- **Contexte Stratégique** : Analyse le secteur d'activité, sa maturité et ses
  évolutions technologiques ou réglementaires à venir.
- **Diagnostic Géographique** : Évalue l'implantation locale/internationale,
  les barrières à l'entrée et l'attractivité de la zone.

## 2. Analyse Sectorielle et Prospective
- Détermine la position de l'entreprise vis-à-vis de ses concurrents.
- Analyse les tendances futures : croissance du marché, risques de disruption,
  opportunités de consolidation.

## 3. Synthèse de Valorisation
- Applique plusieurs méthodes (Multiples d'EBE/EBIT, DCF, Patrimoniale).
- **Réduction de la Fourchette** : Justifie une fourchette étroite en corrélant
  les résultats financiers avec la qualité du dossier stratégique.
- Précise systématiquement le passage de la Valeur d'Entreprise à la Valeur
  des Titres via la dette nette.

## 4. Diagnostic d'Investissement (Investment Case)
Présente une section dédiée « Pourquoi acheter (ou pas) cette entreprise » :
- **Arguments "Bonne Affaire" (Pros)** : Synergies, récurrence du CA, barrières
  à l'entrée, potentiel de croissance, équipe dirigeante.
- **Arguments "Points de Vigilance/Risques" (Cons)** : Dépendance client,
  obsolescence technologique, endettement caché, environnement concurrentiel
  agressif.

## 4 bis. Questions à poser au vendeur (Bilan & Résultats)
- **Qualité des comptes** : méthodes comptables spécifiques, changements de
  règles, récurrence des ajustements.
- **BFR** : saisonnalité, délais clients/fournisseurs, litiges et créances
  douteuses.
- **Trésorerie & dette** : détail des lignes de crédit, covenant, hors-bilan,
  garanties, sûretés.
- **EBE/EBIT normatifs** : éléments non récurrents, coûts exceptionnels,
  niveaux de rémunération des dirigeants.
- **Capex & maintenance** : capex de maintien vs croissance, backlog
  d'investissements.
- **Clients & revenus** : concentration, clauses de résiliation, remises
  accordées, dépendances.
- **Stocks & provisions** : méthodes de valorisation, obsolescence, provisions
  litigieuses.
- **Fiscalité** : contrôles en cours, passifs latents, déficits reportables.

## 4 ter. Leviers de négociation pour un acheteur (prix le plus bas possible)
- Normalisation prudente des résultats.
- Décote de concentration client/fournisseur et dépendances opérationnelles.
- Décote sectorielle si cyclicité, pression concurrentielle ou risques
  réglementaires.
- Ajustement BFR pour refléter la réalité opérationnelle et la saisonnalité.
- Capex de maintien requalifiés à un niveau réaliste.
- Passifs hors-bilan et risques juridiques/sociaux intégrés en dette nette.
- Earn-out ou compléments de prix conditionnels à la performance future.
- Garanties de passif renforcées et séquestre pour couvrir les risques
  identifiés.

## 5. Format du rapport attendu
Produis un rapport professionnel structuré **en Markdown** comme suit :
1. **Fiche d'identité** : Secteur, Géographie, Positionnement.
2. **Tableau Synoptique Financier** (3 exercices).
3. **Analyse de la Valorisation** (Fourchette resserrée, multiples EBE/EBIT,
   DCF, patrimoniale, passage VE → Valeur des Titres).
4. **Diagnostic d'Investissement** (Pros / Cons).
5. **Questions clés au vendeur** : Liste synthétique.
6. **Leviers de négociation** : Arguments acheteur pour minimiser le prix.
7. **Conclusion Stratégique** : Avis argumenté sur l'opportunité.

## 6. Contraintes de Rigueur
- Signaler tout document illisible ou donnée manquante.
- Justifier chaque multiple par le contexte sectoriel et géographique.
- Utiliser des tableaux Markdown pour les données chiffrées.
"""

USER_PREFIX = (
    "Voici l'ensemble des documents financiers et stratégiques de l'entreprise. "
    "Analyse-les pour me donner une valorisation précise et un diagnostic complet "
    "sur la qualité de l'affaire, en tenant compte du secteur et de sa zone "
    "géographique.\n\n"
)

# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------
PDF_EXTENSIONS = {".pdf", ".PDF"}


def extract_text_from_pdf(path: Path) -> str:
    """Return all text extracted from a PDF file."""
    try:
        reader = PdfReader(str(path))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        return "\n".join(pages_text)
    except Exception as exc:  # noqa: BLE001
        hint = ""
        msg = str(exc).lower()
        if "password" in msg or "encrypt" in msg:
            hint = " (fichier protégé par mot de passe ?)"
        elif "eof" in msg or "truncat" in msg:
            hint = " (fichier corrompu ou tronqué ?)"
        elif "codec" in msg or "encod" in msg or "decode" in msg:
            hint = " (problème d'encodage ?)"
        return (
            f"[ERREUR : impossible de lire le fichier {path.name}{hint} — {exc}]"
        )


def load_documents(docs_dir: Path) -> list[dict]:
    """Load all PDF documents from *docs_dir* and return list of dicts."""
    docs = []
    for path in sorted(docs_dir.iterdir()):
        if path.suffix in PDF_EXTENSIONS:
            text = extract_text_from_pdf(path)
            docs.append({"name": path.name, "text": text})
    return docs


def build_user_message(docs: list[dict]) -> str:
    """Concatenate extracted documents into a single user message."""
    parts = [USER_PREFIX]
    for doc in docs:
        parts.append(f"---\n### Document : {doc['name']}\n\n{doc['text']}\n")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------
def call_llm(user_message: str, model: str, client: OpenAI) -> str:
    """Send the documents to the LLM and return the generated report."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError(
            "Le modèle n'a retourné aucun contenu. "
            "Vérifiez votre quota ou réessayez avec un modèle différent."
        )
    return content


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agent M&A : génère un rapport de diagnostic d'entreprise."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("."),
        help="Répertoire contenant les PDF (défaut : répertoire courant).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("rapport_diagnostic.md"),
        help="Fichier de sortie Markdown (défaut : rapport_diagnostic.md).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Modèle OpenAI à utiliser (défaut : gpt-4o ou OPENAI_MODEL).",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()

    args = parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "Erreur : la variable d'environnement OPENAI_API_KEY n'est pas définie.",
            file=sys.stderr,
        )
        sys.exit(1)

    model = args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
    client = OpenAI(api_key=api_key)

    docs_dir = args.docs_dir.resolve()
    print(f"📂  Chargement des documents depuis : {docs_dir}")
    docs = load_documents(docs_dir)

    if not docs:
        print("Aucun fichier PDF trouvé dans le répertoire spécifié.", file=sys.stderr)
        sys.exit(1)

    print(f"📄  {len(docs)} document(s) chargé(s) :")
    for doc in docs:
        chars = len(doc["text"])
        print(f"    • {doc['name']} ({chars:,} caractères)")

    print(f"\n🤖  Envoi au modèle {model}…")
    user_message = build_user_message(docs)
    report = call_llm(user_message, model, client)

    output_path = args.output.resolve()
    output_path.write_text(report, encoding="utf-8")
    print(f"\n✅  Rapport généré : {output_path}")


if __name__ == "__main__":
    main()
