# Spécifications de Nettoyage et Enrichissement des PDFs

## Objectif

Améliorer la qualité du RAG en enrichissant les chunks avec un maximum de contexte avant l'embedding. Cela permet au modèle de mieux comprendre d'où vient l'information et de fournir des réponses plus précises avec des références correctes.

## Problème Actuel

Les chunks actuels ressemblent à :
```
Article 311-1
Le vol est la soustraction frauduleuse de la chose d'autrui.
```

Il manque le contexte : quel code de loi, quelle section, où trouver la source officielle.

## Pipeline de Nettoyage

```
00_clean/
├── input/                    # PDFs bruts de Legifrance
├── 01_output/               # Markdown nettoyé (lisible par humain)
├── 02_structured/           # JSON avec métadonnées complètes
└── legifrance_mapping.json  # Mapping des URLs Legifrance
```

## Métadonnées à Extraire

| Champ | Exemple | Méthode d'extraction |
|-------|---------|----------------------|
| `source_book` | "Code pénal" | Nom du fichier ou métadonnées PDF |
| `source_url` | "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070719" | Mapping depuis le nom du code |
| `hierarchy` | ["Partie législative", "Livre III", "Titre Ier", "Chapitre Ier"] | Parsing des en-têtes |
| `article_id` | "311-1" | Extraction par regex |
| `article_title` | "Du vol" | Depuis les en-têtes de chapitre/section |
| `page` | 42 | Depuis le PDF |

## URLs Legifrance par Code

```json
{
  "Code pénal": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070719",
  "Code civil": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070721",
  "Code du travail": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006072050",
  "Code de commerce": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000005634379",
  "Code de la consommation": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006069565",
  "Code de procédure civile": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070716",
  "Code de procédure pénale": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006071154",
  "Code général des impôts": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006069577",
  "Code de la sécurité sociale": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006073189"
}
```

## Patterns de Détection

### Articles

```python
ARTICLE_PATTERNS = [
    r"Article\s+(L\.?\s*\d+[-–]\d+[-–]?\d*)",      # Article L.311-1, Article L311-1
    r"Article\s+(R\.?\s*\d+[-–]\d+[-–]?\d*)",      # Article R.311-1
    r"Article\s+(D\.?\s*\d+[-–]\d+[-–]?\d*)",      # Article D.311-1
    r"Article\s+(\d+[-–]\d+[-–]?\d*)",              # Article 311-1
    r"Art\.\s*(\d+[-–]\d+)",                        # Art. 311-1
]
```

### Hiérarchie

```python
HIERARCHY_PATTERNS = [
    (r"PARTIE\s+(LÉGISLATIVE|RÉGLEMENTAIRE)", "Partie"),
    (r"LIVRE\s+([IVX]+|PRÉLIMINAIRE)", "Livre"),
    (r"TITRE\s+([IVX]+|PRÉLIMINAIRE)", "Titre"),
    (r"CHAPITRE\s+([IVX]+|\d+)", "Chapitre"),
    (r"SECTION\s+(\d+)", "Section"),
    (r"SOUS-SECTION\s+(\d+)", "Sous-section"),
]
```

## Format de Sortie Enrichi

### JSON Structuré (02_structured/)

```json
{
  "page_content": "Le vol est la soustraction frauduleuse de la chose d'autrui.",
  "metadata": {
    "source": "Code_penal.pdf",
    "source_book": "Code pénal",
    "source_url": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070719",
    "article_id": "311-1",
    "article_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006418131",
    "hierarchy": [
      "Partie législative",
      "Livre III - Des crimes et délits contre les biens",
      "Titre Ier - Des appropriations frauduleuses",
      "Chapitre Ier - Du vol"
    ],
    "page": 42
  }
}
```

### Contenu Enrichi pour Embedding

Le contenu final envoyé à l'embedding doit inclure le contexte en préfixe :

```
Source: Code pénal
Partie législative > Livre III - Des crimes et délits contre les biens > Titre Ier > Chapitre Ier
Article 311-1
URL: https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006418131

Le vol est la soustraction frauduleuse de la chose d'autrui.
```

## Algorithme de Traitement

1. **Lecture du PDF** avec PyMuPDF
2. **Extraction du nom du code** depuis le nom de fichier ou les premières pages
3. **Tracking de la hiérarchie** en parcourant les pages (état persistant)
4. **Détection des articles** par regex
5. **Association article → hiérarchie** courante
6. **Génération des URLs** depuis le mapping
7. **Création du contenu enrichi** avec préfixe contextuel
8. **Chunking** avec RecursiveCharacterTextSplitter
9. **Export** en JSONL avec métadonnées complètes

## Gestion de la Hiérarchie

La hiérarchie doit être trackée comme un état qui persiste entre les pages :

```python
class HierarchyTracker:
    def __init__(self):
        self.current = {
            "partie": None,
            "livre": None,
            "titre": None,
            "chapitre": None,
            "section": None,
        }

    def update(self, level, value):
        """Met à jour un niveau et réinitialise les niveaux inférieurs."""
        levels = ["partie", "livre", "titre", "chapitre", "section"]
        idx = levels.index(level)
        self.current[level] = value
        # Réinitialiser les niveaux inférieurs
        for lower in levels[idx + 1:]:
            self.current[lower] = None

    def get_hierarchy(self):
        """Retourne la hiérarchie actuelle comme liste."""
        return [v for v in self.current.values() if v]
```

## Validation

Après le traitement, vérifier :

- [ ] Chaque chunk a un `source_book`
- [ ] Les articles sont correctement extraits (regex matching)
- [ ] La hiérarchie est cohérente (pas de chapitre sans livre)
- [ ] Les URLs sont valides
- [ ] Le contenu enrichi est bien formaté

## Impact sur le RAG

Avec ce nettoyage, une requête comme "Qu'est-ce que le vol ?" retournera :

**Avant :**
```
Le vol est la soustraction frauduleuse de la chose d'autrui.
```

**Après :**
```
Source: Code pénal
Partie législative > Livre III > Titre Ier > Chapitre Ier
Article 311-1
URL: https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006418131

Le vol est la soustraction frauduleuse de la chose d'autrui.
```

Le LLM peut maintenant citer précisément la source et fournir un lien vers le texte officiel.
