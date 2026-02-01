import json
import re
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet

from src.evaluate_ideas.compute_novelty import get_element_pair_occurrences_1M_recipes, SEPERATION_STR, \
    ingr_counts_1M_recipes


PAIRS_OCCURRENCES_IN_DATA_THRESHOLD = 50
FLAVOR_PAIRING_SCORE_THRESHOLD = 0.3
MIN_CLOSEST_JI_SCORE = 0.3


LEMMATIZER = WordNetLemmatizer()


"""
This dictionary maps raw ingredient names to their standardized synonym names. 
The raw ingredient synonyms are based on the flavorDB dataset (https://cosylab.iiitd.edu.in/flavordb/).
"""
with open("raw_ingredients_synonyms_mapping.json", "r", encoding='utf8') as f:
    raw_ingredients_synonyms_dict = json.load(f)

"""
This dictionary maps two raw ingredient names (separated by ' | ') to their flavor pairing score.
The flavor pairing scores are calculated based on the number of flavor molecules they share in flavorDB. 
The scores are normalized between 0 and 1. 
"""
with open("raw_ingredients_pairing_scores.json", "r", encoding='utf8') as f:
    raw_ingredients_pairing_scores = json.load(f)

"""
This dictionary includes mappings from ingredient names to possible raw ingredient names.
For each ingredient name found in the Recipe1M Dataset, we searched 
for its possible raw ingredient names using the flavorDB dataset and FoodData dataset (https://fdc.nal.usda.gov/).
"""
with open("general_ingr_to_raw_ingrs.json", "r", encoding='utf8') as f:
    general_ingr_to_raw_ingrs = json.load(f)


def is_word_combination_in_line(word_combination: str, line: str) -> bool:
    """
    Returns True if the word_combination is found in the line as a whole (case insensitive), False otherwise.

    :param word_combination: the word combination to search for
    :param line: the line to search in
    :return: True if found, False otherwise
    """

    pattern = r'\b' + re.escape(word_combination) + r'\b'
    match = re.search(pattern, line, flags=re.IGNORECASE)
    return bool(match)


def lemmatize_sent(sentence: str) -> str:
    """
    Lemmatizes the given input sentence.

    :param sentence: the input sentence
    :return: the lemmatized sentence
    """

    words = word_tokenize(sentence)
    lemmatized_words = [LEMMATIZER.lemmatize(word, wordnet.NOUN) for word in words]

    return " ".join(lemmatized_words)


def remove_verbs_and_adjectives(sentence: str) -> str:
    """
    Removes verbs and adjectives from the sentence.

    :param sentence: the input sentence
    :return: the sentence with verbs and adjectives removed
    """

    words = word_tokenize(sentence)
    lemmatized_words = [LEMMATIZER.lemmatize(word, wordnet.NOUN) for word in words]
    lemmatized_words = [word for word in lemmatized_words if wordnet.synsets(word, wordnet.NOUN)]
    new_sentence = " ".join(lemmatized_words)
    return new_sentence


def clean_ingredient(ingredient_str: str) -> str:
    """
    Cleans the given ingredient string and returns the standardized ingredient name as appears in our datasets.

    :param ingredient_str: the input ingredient string
    :return: the standardized ingredient name, or None if not found
    """

    lemmatized_line = lemmatize_sent(ingredient_str).lower()

    tmp_ingr = None
    spltd = lemmatized_line.split()

    for i in range(len(spltd))[::-1]:
        if ' '.join(spltd[i:]) in ingr_counts_1M_recipes:
            tmp_ingr = ' '.join(spltd[i:])

    if tmp_ingr:
        lemmatized_line = tmp_ingr

    for ingr in ingr_counts_1M_recipes:
        if is_word_combination_in_line(ingr, lemmatized_line):
            return ingr

    return None


def raw_ingredient_name_options(ingredient: str) -> list:
    """
    Returns a list of possible raw ingredient names for the given ingredient. If there is no raw ingredient name
    that matches the ingredient (could be in case of complex ingredient), an empty list is returned.

    :param ingredient: the ingredient name
    :return: a list of possible raw ingredient names, or an empty list if no match is found
    """

    possible_raw_ingr_names = []

    if ingredient in raw_ingredients_synonyms_dict:
        return [raw_ingredients_synonyms_dict[ingredient]]

    for raw_ingr in raw_ingredients_synonyms_dict:
        if is_word_combination_in_line(ingredient, raw_ingr):
            possible_raw_ingr_names += [raw_ingredients_synonyms_dict[raw_ingr]]

    if not possible_raw_ingr_names:
        ingredient = remove_verbs_and_adjectives(ingredient)
        for raw_ingr in raw_ingredients_synonyms_dict:
            if is_word_combination_in_line(ingredient, raw_ingr):
                possible_raw_ingr_names += [raw_ingredients_synonyms_dict[raw_ingr]]

    possible_raw_ingr_names = list(set(possible_raw_ingr_names))

    if len(possible_raw_ingr_names) > 5:  # too many options for possible entity names. Discarding.
        possible_raw_ingr_names = []

    return possible_raw_ingr_names


def raw_ingr_flavor_pairing_score(ingr1: str, ingr2: str) -> float:
    """
    Returns the flavor pairing score between two raw ingredients. If one of the ingredients is not recognized as
    a raw ingredient, None is returned.

    :param ingr1: the first ingredient name
    :param ingr2: the second ingredient name
    :return: the flavor pairing score, or None if one of the ingredients is not recognized as a raw ingredient
    """

    ingr1 = raw_ingredient_name_options(ingr1)
    ingr2 = raw_ingredient_name_options(ingr2)

    if not ingr1 or not ingr2:
        return None

    max_score = 0
    for e1 in ingr1:
        for e2 in ingr2:
            ingr_pair_str = SEPERATION_STR.join(sorted([e1, e2]))
            if ingr_pair_str in raw_ingredients_pairing_scores:
                score = raw_ingredients_pairing_scores[ingr_pair_str]
                if score > max_score:
                    max_score = score

    return max_score


def complex_ingr_flavor_pairing_score(ingr1: list, ingr2: list) -> float:
    """
    Returns the flavor pairing score between two complex ingredients, each represented as a list of raw ingredients.

    :param ingr1: the first ingredient as a list of raw ingredients
    :param ingr2: the second ingredient as a list of raw ingredients
    :return: the flavor pairing score, or None if no valid pairing score is found
    """

    total_score = []

    for raw_ingr1 in ingr1:
        for raw_ingr2 in ingr2:
            score = raw_ingr_flavor_pairing_score(raw_ingr1, raw_ingr2)
            if not score:
                continue
            if score:
                total_score += [score]

    if not total_score:
        return None

    return min(total_score)


def jaccard_index(phrase1: str, phrase2: str) -> float:
    """
    Calculates the Jaccard index between two phrases.

    :param phrase1: the first phrase
    :param phrase2: the second phrase
    :return: the two phrases Jaccard index score
    """

    set1 = set(phrase1.lower().split())
    set2 = set(phrase2.lower().split())

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    if intersection == 0:
        return 0

    score = intersection / union

    return score


def find_closest_ingr_name_in_dict(target_ingr: str, ingr_dict: dict) -> tuple:
    """
    Finds the closest ingredient name in the given dictionary to the target ingredient name using Jaccard index.

    :param target_ingr: the target ingredient name
    :param ingr_dict: the dictionary of ingredient names to search in
    :return: a tuple containing the closest ingredient name and its Jaccard index score
    """

    max_score = 0
    closest = None

    for candidate in ingr_dict:
        score = jaccard_index(target_ingr, candidate)
        if closest and score == max_score and len(candidate) < len(closest):
            closest = candidate
        if score > max_score:
            max_score = score
            closest = candidate

    return closest, max_score


def get_raw_ingredients(ingr_name: str) -> list:
    """
    Returns a list of possible raw ingredient names for the given ingredient name.

    :param ingr_name: the ingredient name
    :return: a list of possible raw ingredient names, or None if no match is found
    """

    if ingr_name in general_ingr_to_raw_ingrs:
        return general_ingr_to_raw_ingrs[ingr_name]

    # in case ingr_name is not found as is in the dictionary, try to find the closest match:
    closest_ingr_name, score = find_closest_ingr_name_in_dict(ingr_name, general_ingr_to_raw_ingrs)

    if score < MIN_CLOSEST_JI_SCORE:
        return None
    return general_ingr_to_raw_ingrs[closest_ingr_name]


def flavor_pairing_score(ingr_name1: str, ingr_name2: str) -> float:
    """
    Returns the flavor pairing score between two ingredients (which can be either raw or complex).
    If one of the ingredients is not recognized, None is returned.

    :param ingr_name1: the first ingredient name
    :param ingr_name2: the second ingredient name
    :return: the flavor pairing score, or None if one of the ingredients is not recognized
    """

    basic_score = raw_ingr_flavor_pairing_score(ingr_name1, ingr_name2)

    if basic_score:  # the two ingredients are both raw ingredients!
        return basic_score

    # at least one of the ingredients is not a raw ingredient:
    raw_ingr1 = raw_ingredient_name_options(ingr_name1)
    raw_ingr2 = raw_ingredient_name_options(ingr_name2)

    if not raw_ingr1:
        raw_ingr1 = get_raw_ingredients(ingr_name1)
        if not raw_ingr1:
            return None
    if not raw_ingr2:
        raw_ingr2 = get_raw_ingredients(ingr_name2)
        if not raw_ingr2:
            return None

    return complex_ingr_flavor_pairing_score(raw_ingr1, raw_ingr2)


def pair_well(ingr1: str, ingr2: str) -> bool:
    """
    Returns True if the two ingredients pair well based on their flavor pairing score, False otherwise.

    :param ingr1: the first ingredient name
    :param ingr2: the second ingredient name
    :return: True if ingr1 and ingr2 pair well, False otherwise
    """

    score = flavor_pairing_score(ingr1, ingr2)

    if not score:
        return False

    if score < FLAVOR_PAIRING_SCORE_THRESHOLD:
        return False

    return True


def get_ingr_collision_count(problematic_pairs: list, preferred_order: list = []) -> dict:
    """
    Returns a dictionary mapping each ingredient to the number of collisions it is involved in.

    :param problematic_pairs: a list of problematic ingredient pairs (collisions)
    :param preferred_order: a list of ingredients in a preferred order (to be prioritized less for removal)
    :return: a dictionary mapping each ingredient to its collision count (sorted by count and essentials)
    """

    ingr_problematic_pair_count = {}

    for pair in problematic_pairs:
        ingr1, ingr2 = pair
        if ingr1 not in ingr_problematic_pair_count:
            ingr_problematic_pair_count[ingr1] = 0
        if ingr2 not in ingr_problematic_pair_count:
            ingr_problematic_pair_count[ingr2] = 0
        ingr_problematic_pair_count[ingr1] += 1
        ingr_problematic_pair_count[ingr2] += 1

    # sort based if the ingredient is in the top items:
    ingr_problematic_pair_count = {k: v for k, v in sorted(ingr_problematic_pair_count.items(), key=lambda item: item[0] in preferred_order)}

    # sort the ingredients by the number of problematic pairs they are in:
    ingr_problematic_pair_count = {k: v for k, v in sorted(ingr_problematic_pair_count.items(), key=lambda item: item[1], reverse=True)}

    return ingr_problematic_pair_count


def cause_taste_collisions(recipe_ingredients: list, preferred_order: list = []) -> list:
    """
    Returns a list of ingredients that cause taste collisions in the given recipe ingredients list.

    :param recipe_ingredients: a recipe ingredients list
    :param preferred_order: a list of ingredients in a preferred order (to be prioritized less for removal)
    :return: a list of ingredients that cause taste collisions that should be removed from the recipe
    """

    recipe_ingredients = list(sorted(recipe_ingredients))

    # we start by checking for every pair of ingredients in the recipe whether they occur frequently together
    # in recipes. If not, we turn to check their flavor pairing score.

    pairs_to_check_further = []

    for i in range(len(recipe_ingredients)):
        for j in range(i+1, len(recipe_ingredients)):

            num_occurences = get_element_pair_occurrences_1M_recipes(recipe_ingredients[i], recipe_ingredients[j])

            if not num_occurences or num_occurences < PAIRS_OCCURRENCES_IN_DATA_THRESHOLD:
                pairs_to_check_further += [(recipe_ingredients[i], recipe_ingredients[j])]

    # we turn to check flavor pairing score for the pairs that do not occur frequently together in recipes:

    problematic_pairs = []

    for pair in pairs_to_check_further:
        ingr1, ingr2 = pair[0], pair[1]
        if not pair_well(ingr1, ingr2):
            problematic_pairs += [(ingr1, ingr2)]

    # given the problematic pairs, we now turn to decide which ingredients should be removed from the recipe
    # to resolve all taste collisions (we prefer to first remove less essential ingredients for the dish):

    problematic_count = get_ingr_collision_count(problematic_pairs, preferred_order)

    ingr_to_remove = []

    # while not_handled_pairs:  # iteratively remove the ingredients with the highest number of flavor collisions:
    while problematic_pairs:  # iteratively remove the ingredients with the highest number of flavor collisions:

        most_problematic_ingr = list(problematic_count.keys())[0]
        problematic_pairs = [pair for pair in problematic_pairs if most_problematic_ingr not in pair]
        ingr_to_remove += [most_problematic_ingr]
        problematic_count = get_ingr_collision_count(problematic_pairs, preferred_order)

    return ingr_to_remove


if __name__ == '__main__':

    ingr1 = "avocado"
    ingr2 = "chocolate"

    print("Flavor pairing score for " + ingr1 + " and " + ingr2 + ": " + str(flavor_pairing_score(ingr1, ingr2)))
    print("Pair well?", "Yes! :-)" if pair_well(ingr1, ingr2) else "No :-(")
    print()

    recipe_ingrs = ["apple", "applesauce", "avocado", "bacon", "cake", "cinnamon", "dressing", "lettuce", "miracle whip", "oatmeal", "pasta", "plum"]
    problematic_ingrs = cause_taste_collisions(recipe_ingrs)

    print("Given the recipe ingredients:", recipe_ingrs)
    print("Problematic ingredients to remove:", problematic_ingrs)


