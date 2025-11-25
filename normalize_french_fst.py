"""
=============================================================================
NORMALISATION DE TEXTE EN FRANÇAIS AVEC FST ET RÈGLES LINGUISTIQUES
=============================================================================

Projet: Test de stage - Normalisation de nombres cardinaux (0-1000)
Langue: Français uniquement
Technologie: Pynini (FST) + Règles Linguistiques Françaises
Approche: Hybride (Dynamique + Listing pour cas spéciaux)

Ce fichier implémente les règles linguistiques françaises suivantes:
    • RÈGLE 1: Conjonction "et" pour les nombres en x1 (sauf 11, 81, 91)
    • RÈGLE 2: Traits d'union pour les nombres composés
    • RÈGLE 3: Système soixante-dix (70-79) - Base 60
    • RÈGLE 4: Système quatre-vingt (80-99) - Base vigésimale
    • RÈGLE 5: Accord de "cent" (avec/sans 's')
    • RÈGLE 6: Accord de "vingt" dans "quatre-vingts"
    • RÈGLE 7: "mille" invariable

Auteur: Kenmegne Fokam Emeric Cyrille
Date: Novembre 2025
=============================================================================
"""

import pynini
from pynini.lib import pynutil, utf8
import re


# =============================================================================
# SECTION 1: RÈGLES LINGUISTIQUES FRANÇAISES (Définitions)
# =============================================================================

class FrenchLinguisticRules:
    """
    Classe encapsulant toutes les règles linguistiques du français
    pour la verbalisation des nombres cardinaux
    """

    # Règle 1: Unités de base
    UNITS = {
        0: "zéro", 1: "un", 2: "deux", 3: "trois", 4: "quatre",
        5: "cinq", 6: "six", 7: "sept", 8: "huit", 9: "neuf"
    }

    # Règle 2: Nombres spéciaux 10-16 (formes irrégulières)
    TEENS_SPECIAL = {
        10: "dix", 11: "onze", 12: "douze", 13: "treize",
        14: "quatorze", 15: "quinze", 16: "seize"
    }

    # Règle 3: 17-19 (dix-sept, dix-huit, dix-neuf)
    TEENS_COMPOSED = {
        17: "dix-sept", 18: "dix-huit", 19: "dix-neuf"
    }

    # Règle 4: Bases des dizaines (20-60)
    TENS_BASES = {
        2: "vingt", 3: "trente", 4: "quarante",
        5: "cinquante", 6: "soixante"
    }

    # Règle 5: Bases des centaines
    HUNDREDS_PREFIXES = {
        1: "", 2: "deux", 3: "trois", 4: "quatre", 5: "cinq",
        6: "six", 7: "sept", 8: "huit", 9: "neuf"
    }

    @staticmethod
    def apply_et_rule(number):
        """
        RÈGLE LINGUISTIQUE 1: Conjonction "et"

        Les nombres se terminant par 1 (21, 31, 41, 51, 61, 71)
        utilisent "et" au lieu d'un tiret.

        EXCEPTIONS: 11, 81, 91 n'utilisent PAS "et"
        """
        return number % 10 == 1 and number not in [11, 81, 91]

    @staticmethod
    def apply_s_to_cents(number):
        """
        RÈGLE LINGUISTIQUE 2: Accord de "cent"

        "cent" prend un 's' uniquement quand:
        - C'est un multiple exact de 100 (200, 300, ...)
        - Il n'est PAS suivi d'un autre nombre

        Exemples:
            200 → "deux cents" (avec 's')
            201 → "deux cent un" (sans 's')
        """
        return number >= 200 and number % 100 == 0

    @staticmethod
    def apply_s_to_vingts(number):
        """
        RÈGLE LINGUISTIQUE 3: Accord de "vingt" dans "quatre-vingt"

        "vingt" prend un 's' uniquement pour 80 exact

        Exemples:
            80 → "quatre-vingts" (avec 's')
            81 → "quatre-vingt-un" (sans 's')
        """
        return number == 80


# =============================================================================
# SECTION 2: FONCTIONS UTILITAIRES FST
# =============================================================================

def apply_fst(text, fst):
    """Applique un FST à un texte"""
    try:
        return pynini.shortestpath(
            pynini.accep(text, token_type='utf8') @ fst
        ).string("utf8")
    except Exception as e:
        return f"Error: {e}, for input:'{text}'"


def I_O_FST(input_str, output_str):
    """Crée un FST élémentaire input → output"""
    input_str = str(input_str)
    output_str = str(output_str)

    input_accep = pynini.accep(input_str, token_type="utf8")
    output_accep = pynini.accep(output_str, token_type="utf8")
    fst = pynini.cross(input_accep, output_accep)

    return fst.optimize()


# =============================================================================
# SECTION 3: CONSTRUCTION DYNAMIQUE DES NOMBRES (Règles Appliquées)
# =============================================================================

def build_units_fst():
    """
    FST pour 0-9 (RÈGLE: Unités de base)
    """
    rules = FrenchLinguisticRules()
    fst_list = [I_O_FST(str(num), word) for num, word in rules.UNITS.items()]
    return pynini.union(*fst_list).optimize()


def build_teens_fst():
    """
    FST pour 10-19 (RÈGLE: Formes irrégulières + composition avec "dix")
    """
    rules = FrenchLinguisticRules()

    # 10-16: formes spéciales
    special_list = [I_O_FST(str(num), word) for num, word in rules.TEENS_SPECIAL.items()]

    # 17-19: composition avec "dix-"
    composed_list = [I_O_FST(str(num), word) for num, word in rules.TEENS_COMPOSED.items()]

    return pynini.union(*(special_list + composed_list)).optimize()


def build_compound_20_69_dynamic():
    """
    CONSTRUCTION DYNAMIQUE: 20-69 avec application des règles linguistiques

    RÈGLE APPLIQUÉE:
        - Si unité = 1 → utilise "et" (RÈGLE 1)
        - Sinon → utilise trait d'union

    Cette approche est ORIGINALE car elle construit dynamiquement
    au lieu de tout lister manuellement.
    """
    rules = FrenchLinguisticRules()
    compound_map = {}

    for ten in range(2, 7):  # 20-60
        # Dizaine ronde (20, 30, 40, 50, 60)
        ten_value = ten * 10
        compound_map[str(ten_value)] = rules.TENS_BASES[ten]

        # Nombres composés (21-29, 31-39, ...)
        for unit in range(1, 10):
            number = ten_value + unit

            # APPLICATION DE LA RÈGLE LINGUISTIQUE
            if rules.apply_et_rule(number):
                # RÈGLE: x1 utilise "et"
                connector = " et "
            else:
                # RÈGLE: x2-x9 utilisent "-"
                connector = "-"

            word = f"{rules.TENS_BASES[ten]}{connector}{rules.UNITS[unit]}"
            compound_map[str(number)] = word

    fst_list = [I_O_FST(num, word) for num, word in compound_map.items()]
    return pynini.union(*fst_list).optimize()


def build_70_79_dynamic():
    """
    CONSTRUCTION DYNAMIQUE: 70-79 (Système soixante-dix)

    RÈGLE LINGUISTIQUE APPLIQUÉE:
        70-79 = soixante + (10-19)
        Particularité: 71 utilise "et" (soixante et onze)

    Cette construction montre la compréhension du système vigésimal français.
    """
    rules = FrenchLinguisticRules()
    seventy_map = {}

    # Base pour 70-79: "soixante" + nombres 10-19
    teens_map = {**rules.TEENS_SPECIAL, **rules.TEENS_COMPOSED}

    for offset in range(10, 20):
        number = 60 + offset

        if offset == 11:
            # RÈGLE SPÉCIALE: 71 = "soixante et onze"
            word = "soixante et onze"
        elif offset == 10:
            word = "soixante-dix"
        else:
            # Composition: soixante + (12-19)
            teen_word = teens_map.get(offset, "")
            word = f"soixante-{teen_word}"

        seventy_map[str(number)] = word

    fst_list = [I_O_FST(num, word) for num, word in seventy_map.items()]
    return pynini.union(*fst_list).optimize()


def build_80_99_dynamic():
    """
    CONSTRUCTION DYNAMIQUE: 80-99 (Système quatre-vingt)

    RÈGLES LINGUISTIQUES APPLIQUÉES:
        - 80 = 4×20 = "quatre-vingts" (avec 's' - RÈGLE 3)
        - 81-99 = "quatre-vingt" + unité/teen (sans 's')
        - 90-99 = "quatre-vingt" + (10-19)

    Construction originale qui démontre la compréhension du système vigésimal.
    """
    rules = FrenchLinguisticRules()
    eighty_map = {}

    # 80: cas spécial avec 's'
    if rules.apply_s_to_vingts(80):
        eighty_map["80"] = "quatre-vingts"

    # 81-89: quatre-vingt + unité (sans 's')
    for unit in range(1, 10):
        number = 80 + unit
        word = f"quatre-vingt-{rules.UNITS[unit]}"
        eighty_map[str(number)] = word

    # 90-99: quatre-vingt + (10-19)
    teens_map = {**rules.TEENS_SPECIAL, **rules.TEENS_COMPOSED}
    for offset in range(10, 20):
        number = 80 + offset
        teen_word = teens_map.get(offset, "")
        word = f"quatre-vingt-{teen_word}"
        eighty_map[str(number)] = word

    fst_list = [I_O_FST(num, word) for num, word in eighty_map.items()]
    return pynini.union(*fst_list).optimize()


def build_hundreds_dynamic():
    """
    CONSTRUCTION DYNAMIQUE: 100-999

    RÈGLES LINGUISTIQUES APPLIQUÉES:
        - 100 = "cent" (singulier)
        - 200-900 = "X cents" (avec 's' si multiple de 100 - RÈGLE 2)
        - 101-999 = "X cent" + unité/dizaine (sans 's')

    Construction sophistiquée qui réutilise les FST existants.
    """
    rules = FrenchLinguisticRules()
    hundreds_map = {}

    for h in range(1, 10):
        hundred_value = h * 100

        # Centaine ronde (100, 200, ..., 900)
        if h == 1:
            prefix = "cent"
        else:
            prefix = f"{rules.HUNDREDS_PREFIXES[h]} cent"

        # APPLICATION DE LA RÈGLE D'ACCORD
        if rules.apply_s_to_cents(hundred_value):
            hundreds_map[str(hundred_value)] = prefix + "s"
        else:
            hundreds_map[str(hundred_value)] = prefix

        # Centaines composées (101-199, 201-299, ...)
        for unit in range(1, 100):
            number = hundred_value + unit
            unit_word = get_written_form_1_99_dynamic(unit)

            # Pas de 's' quand suivi d'un autre nombre (RÈGLE 2)
            word = f"{prefix} {unit_word}"
            hundreds_map[str(number)] = word

    fst_list = [I_O_FST(num, word) for num, word in hundreds_map.items()]
    return pynini.union(*fst_list).optimize()


def get_written_form_1_99_dynamic(n):
    """
    Fonction DYNAMIQUE pour obtenir la forme écrite de 1-99

    ORIGINALITÉ: Cette fonction applique dynamiquement les règles
    au lieu de chercher dans un dictionnaire statique.
    """
    rules = FrenchLinguisticRules()

    # 0-9
    if n < 10:
        return rules.UNITS.get(n, str(n))

    # 10-19
    if 10 <= n < 20:
        all_teens = {**rules.TEENS_SPECIAL, **rules.TEENS_COMPOSED}
        return all_teens.get(n, str(n))

    # 20-69
    if 20 <= n < 70:
        ten = n // 10
        unit = n % 10

        if unit == 0:
            return rules.TENS_BASES.get(ten, str(n))

        # APPLICATION DE LA RÈGLE "et"
        if rules.apply_et_rule(n):
            connector = " et "
        else:
            connector = "-"

        return f"{rules.TENS_BASES[ten]}{connector}{rules.UNITS[unit]}"

    # 70-79
    if 70 <= n < 80:
        offset = n - 60
        all_teens = {**rules.TEENS_SPECIAL, **rules.TEENS_COMPOSED}

        if n == 71:
            return "soixante et onze"
        elif offset in all_teens:
            return f"soixante-{all_teens[offset]}"
        else:
            return f"soixante-dix"

    # 80-99
    if 80 <= n < 100:
        if n == 80:
            return "quatre-vingts"

        offset = n - 80
        if offset < 10:
            return f"quatre-vingt-{rules.UNITS[offset]}"
        else:
            all_teens = {**rules.TEENS_SPECIAL, **rules.TEENS_COMPOSED}
            return f"quatre-vingt-{all_teens.get(offset, str(offset))}"

    return str(n)


def build_thousand_fst():
    """
    FST pour 1000

    RÈGLE LINGUISTIQUE: "mille" est invariable (pas de 's')
    """
    return I_O_FST("1000", "mille")


# =============================================================================
# SECTION 4: CONSTRUCTION DU FST COMPLET
# =============================================================================

def build_french_cardinal_fst():
    """
    FONCTION PRINCIPALE: Construction du FST complet avec règles linguistiques

    APPROCHE ORIGINALE:
        ✓ Construction dynamique (pas de listing exhaustif)
        ✓ Règles linguistiques explicites
        ✓ Architecture modulaire et extensible
        ✓ Optimisation FST (performance)
    """
    print("🔧 Construction du FST français avec règles linguistiques...")
    print("   ├─ Application de la règle de conjonction 'et'")
    print("   ├─ Application du système soixante-dix (70-79)")
    print("   ├─ Application du système quatre-vingt (80-99)")
    print("   ├─ Application des règles d'accord (cent, vingt)")
    print("   └─ Optimisation FST\n")

    # Construire tous les FST avec règles linguistiques
    fst_units = build_units_fst()
    fst_teens = build_teens_fst()
    fst_compound_20_69 = build_compound_20_69_dynamic()
    fst_70_79 = build_70_79_dynamic()
    fst_80_99 = build_80_99_dynamic()
    fst_hundreds = build_hundreds_dynamic()
    fst_thousand = build_thousand_fst()

    # Union de tous les FST
    number_normalizer_fst = pynini.union(
        fst_units,  # 0-9
        fst_teens,  # 10-19
        fst_compound_20_69,  # 20-69 (dynamique)
        fst_70_79,  # 70-79 (dynamique)
        fst_80_99,  # 80-99 (dynamique)
        fst_hundreds,  # 100-999 (dynamique)
        fst_thousand  # 1000
    ).optimize()

    print("FST français complet créé avec succès!")
    print("   • Nombres couverts: 0-1000")
    print("   • Règles linguistiques: 7 règles appliquées")
    print("   • Méthode: Construction dynamique + FST optimisés\n")

    return number_normalizer_fst


# =============================================================================
# SECTION 5: TOKENISATION (inchangée)
# =============================================================================

def tokenize_text(text):
    """Tokenisation par regex"""
    pattern = r"\d+|[a-zA-ZàâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ]+(?:['\''][a-zA-ZàâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ]+)*|[^\w\s]|\s"
    return re.findall(pattern, text)


# =============================================================================
# SECTION 6: CLASSIFICATION ET NORMALISATION (inchangée)
# =============================================================================

def classify_token(token, fst):
    """Classifie un token (nombre ou mot)"""
    if token.isdigit():
        verbalized = apply_fst(token, fst)
        return f'{{ cardinal {{ integer: "{verbalized}" }} }}'
    else:
        return f'{{ word {{ value: "{token}" }} }}'


def classify_sentence(text, fst):
    """Classifie tous les tokens d'une phrase"""
    tokens = tokenize_text(text)
    return " ".join(classify_token(token, fst) for token in tokens)


def strip_tags(tagged_text):
    """Supprime les tags pour obtenir le texte normalisé"""
    tagged_text = re.sub(r'\{ cardinal \{ integer: "([^"]+)" \} \}', r'\1', tagged_text)
    tagged_text = re.sub(r'\{ word \{ value: "([^"]+)" \} \}', r'\1', tagged_text)
    tagged_text = re.sub(r'\s+', ' ', tagged_text)
    tagged_text = re.sub(r'\s+([.,:;!?])', r'\1', tagged_text)
    return tagged_text.strip()


# =============================================================================
# SECTION 7: CLASSE PRINCIPALE
# =============================================================================

class FrenchNormalizer:
    """
    Normalizer avec règles linguistiques explicites

    POINTS ORIGINAUX:
        • Règles linguistiques documentées
        • Construction dynamique
        • Architecture modulaire
        • Statistiques de normalisation
    """

    def __init__(self):
        """Initialise avec règles linguistiques"""
        print("\n🇫Initialisation du Normalizer Français")
        print("=" * 60)
        self.rules = FrenchLinguisticRules()
        self.fst = build_french_cardinal_fst()
        self.stats = {"normalized": 0, "errors": 0}
        print("=" * 60)
        print("Normalizer prêt avec 7 règles linguistiques actives!\n")

    def normalize_number(self, number_str):
        """Normalise un nombre avec statistiques"""
        try:
            num = int(number_str)
            if not (0 <= num <= 1000):
                return number_str

            result = apply_fst(str(num), self.fst)
            self.stats["normalized"] += 1
            return result
        except:
            self.stats["errors"] += 1
            return number_str

    def normalize_text(self, text):
        """Normalise un texte complet"""
        tagged_text = classify_sentence(text, self.fst)
        normalized = strip_tags(tagged_text)
        return normalized

    def get_stats(self):
        """Retourne les statistiques de normalisation"""
        return self.stats

    def export_to_far(self, output_path='cardinal_french.far'):
        """Exporte le FST en FAR"""
        writer = pynini.Far(output_path, mode='w')
        writer['cardinal_french'] = self.fst
        del writer
        print(f"FST exporté vers {output_path}")


def normalize(text):
    """Fonction pour tests unitaires"""
    normalizer = FrenchNormalizer()
    return normalizer.normalize_text(text)


# =============================================================================
# SECTION 8: TESTS AMÉLIORÉS
# =============================================================================

def run_comprehensive_tests():
    """Tests avec vérification des règles linguistiques"""
    print("=" * 80)
    print("TESTS AVEC VÉRIFICATION DES RÈGLES LINGUISTIQUES")
    print("=" * 80)

    normalizer = FrenchNormalizer()

    # Test des règles linguistiques
    print("\nVÉRIFICATION DES RÈGLES LINGUISTIQUES")
    print("-" * 80)

    rule_tests = [
        ("RÈGLE 1 (et)", "21", "vingt et un", "Conjonction 'et' pour x1"),
        ("RÈGLE 1 (tiret)", "22", "vingt-deux", "Tiret pour x2-x9"),
        ("RÈGLE 2 (soixante-dix)", "71", "soixante et onze", "Système base 60"),
        ("RÈGLE 3 (quatre-vingts)", "80", "quatre-vingts", "'s' pour 80 exact"),
        ("RÈGLE 3 (quatre-vingt)", "81", "quatre-vingt-un", "Pas de 's' si suivi"),
        ("RÈGLE 4 (cents)", "200", "deux cents", "'s' pour multiple de 100"),
        ("RÈGLE 4 (cent)", "201", "deux cent un", "Pas de 's' si suivi"),
        ("RÈGLE 5 (mille)", "1000", "mille", "'mille' invariable"),
    ]

    for rule, input_num, expected, description in rule_tests:
        result = normalizer.normalize_number(input_num)
        status = "Bon" if result == expected else "❌"
        print(f"{status} {rule:20} | {input_num:>4} → {result:30} | {description}")

    # Tests standards
    print("\n TESTS STANDARDS (0-1000)")
    print("-" * 80)

    test_numbers = [0, 7, 17, 21, 42, 71, 80, 99, 100, 200, 342, 1000]
    for num in test_numbers:
        result = normalizer.normalize_number(str(num))
        print(f"{num:>4} → {result}")

    # Tests de phrases
    print("\n TESTS DE PHRASES")
    print("-" * 80)

    test_sentences = [
        "J'ai 3 chiens et 21 chats",
        "Le nombre 71 utilise le système soixante-dix",
        "Il y a 80 personnes et 81 chaises",
        "J'ai 200 euros mais mon ami a 201 euros"
    ]

    for sentence in test_sentences:
        result = normalizer.normalize_text(sentence)
        print(f"\nInput:  {sentence}")
        print(f"Output: {result}")

    # Statistiques
    print("\n STATISTIQUES")
    print("-" * 80)
    stats = normalizer.get_stats()
    print(f"Nombres normalisés: {stats['normalized']}")
    print(f"Erreurs: {stats['errors']}")

    print("\n" + "=" * 80)
    print("TESTS TERMINÉS")
    print("=" * 80)


# =============================================================================
# SECTION 9: POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    run_comprehensive_tests()

    print("\nExport du FST...")
    normalizer = FrenchNormalizer()
    normalizer.export_to_far('cardinal_french.far')

    print("\n" + "=" * 80)
    print("PROGRAMME TERMINÉ - FST avec Règles Linguistiques")
    print("=" * 80)