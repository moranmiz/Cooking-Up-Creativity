import json
import math


SEPERATION_STR = " | "

INGR_GENERAL_MIN_OCCURRENCES = 250
ELEMENT_GENERAL_OCCURRENCES = 1000

NOVELTY_K = 10  # number of top idf scores to consider when computing the novelty score


"""
This dictionary maps two elements (sorted alphabetically and separated by ' | ') to the number of recipes
that include both elements in Recipe1M Dataset (https://github.com/torralba-lab/im2recipe).
An element could be either an ingredient or a cooking verb. 
"""
with open("../resources/element_pairs_1M_recipes.json", 'r') as f:
    element_pairs_1M_recipes = json.load(f)

"""
This dictionary maps each ingredient to the number of recipes that include it in Recipe1M Dataset.
"""
with open("../resources/ingredient_counts_1M_recipes.json", "r", encoding='utf8') as f:
    ingr_counts_1M_recipes = json.load(f)



def get_element_occurrences_1M_recipes(element: str) -> int:
    """
    Returns the number of recipes in Recipe1M that include the given element.

    :param element: the given element (ingredient or cooking verb)
    :return: the number of recipes that include the given element
    """

    if not element:
        return None

    element_str = element + SEPERATION_STR + element

    if element_str not in element_pairs_1M_recipes:
        return None

    return element_pairs_1M_recipes[element + SEPERATION_STR + element]


def get_element_pair_occurrences_1M_recipes(element1: str, element2: str) -> int:
    """
    Returns the number of recipes in Recipe1M that include both given elements.

    :param element1: the first given element
    :param element2: the second given element
    :return: the number of recipes that include both given elements
    """

    element_str = SEPERATION_STR.join(sorted([element1, element2]))

    if element_str not in element_pairs_1M_recipes:
        return None

    return element_pairs_1M_recipes[element_str]


def get_element_idf_score(fixed_element: str, element: str) -> float:
    """
    Computes a normalized idf score of an element with respect to a fixed element.

    The idf score of a given element e' with respect to a fixed element e is computed as:
        idf(e, e') = log( N(e) / N(e, e') ) / log( N(e) )

    Where N(e) is the number of recipes that include element e, and N(e, e') is the number of recipes that include both
    elements e and e'.

    In case N(e') is less than INGR_GENERAL_MIN_OCCURRENCES the idf score is set to 0.0.
    In case N(e, e') = 0 and N(e') > ELEMENT_GENERAL_OCCURRENCES, the idf score is set to 1.0.

    :param fixed_element: the fixed element to compute the idf score with respect to
    :param element: the given element to compute the idf score for
    :return: the normalized idf score of the given element with respect to the fixed element
    """

    element_idf_score = 0.0

    element_count = get_element_occurrences_1M_recipes(element)

    # ignore ingredients that can get high novelty scores just because they are rare overall:
    if not element_count or element_count < INGR_GENERAL_MIN_OCCURRENCES:
        return element_idf_score

    fixed_element_count = get_element_occurrences_1M_recipes(fixed_element)
    pair_count = get_element_pair_occurrences_1M_recipes(fixed_element, element)

    if pair_count:

        element_idf_score = math.log(fixed_element_count / pair_count)

        # normalize element idf score (to be between 0.0 to 1.0):
        if element_idf_score < 0:
            element_idf_score = 0
        else:
            element_idf_score = element_idf_score / math.log(fixed_element_count)

    else:  # this is a new element pair that never appeared together in Recipe1M

        # a common element that never appeared with the fixed element in the same recipe
        if element_count > ELEMENT_GENERAL_OCCURRENCES:
            element_idf_score = 1.0

    return element_idf_score


def get_recipe_novelty_score(elements_in_recipe: list, score_only: bool = True) -> float or tuple:
    """
    Computes the novelty score of a recipe based on its elements (ingredients and cooking verbs).
    The novelty score is computed by fixating on each element in the recipe, computing the idf scores
    of all other elements with respect to the fixated element, summing the top K idf scores, and then
    summing the top K element-fixated novelty scores.

    :param elements_in_recipe: list of elements (ingredients and cooking verbs) in the recipe
    :param score_only: if True, only the novelty score is returned; if False, a tuple of the novelty
    score and the relevant elements with their scores is returned
    :return: the novelty score of the recipe, or a tuple of the novelty score and the relevant
    elements with their scores
    """

    element_scores_element_fixate = []

    for fixed_element in elements_in_recipe:

        cur_element_scores = []

        for element in elements_in_recipe:

            fixed_element_count = get_element_occurrences_1M_recipes(fixed_element)
            if not fixed_element_count:
                continue

            element_score = get_element_idf_score(fixed_element, element)
            cur_element_scores += [[element, element_score]]

        cur_element_scores = sorted(cur_element_scores, key=lambda x: x[1], reverse=True)
        element_fixate_novelty_score = sum([item[1] for item in cur_element_scores[:min(NOVELTY_K, len(cur_element_scores))]])
        element_scores_element_fixate += [[fixed_element, element_fixate_novelty_score]]

    element_scores_element_fixate = sorted(element_scores_element_fixate, key=lambda x: x[1], reverse=True)
    novelty_score = sum([item[1] for item in element_scores_element_fixate[:min(NOVELTY_K, len(element_scores_element_fixate))]])

    if score_only:
        return novelty_score

    element_scores = element_scores_element_fixate[:min(NOVELTY_K, len(element_scores_element_fixate))]

    return novelty_score, element_scores


if __name__ == '__main__':

    print()
    print("Idf score examples (the higher the score the more novel the element is in respect to the fixed element):")
    print("-------------------------------------------------------------------------------------------------------")
    print()

    print("idf score of tomato in respect to avocado:", get_element_idf_score("avocado", "tomato"))
    print("idf score of chocolate in respect to avocado:", get_element_idf_score("avocado", "chocolate"))
    print("idf score of strawberry in respect to avocado:", get_element_idf_score("avocado", "strawberry"))
    print("idf score of mango in respect to avocado:", get_element_idf_score("avocado", "mango"))
    print("idf score of strawberry in respect to chocolate:", get_element_idf_score("chocolate", "strawberry"))
    print("idf score of milk in respect to chocolate:", get_element_idf_score("chocolate", "milk"))
    print("idf score of tahini in respect to chocolate:", get_element_idf_score("chocolate", "tahini"))
    print()

    print("Novelty score examples (the higher the score the more novel the recipe elements are):")
    print("-------------------------------------------------------------------------------------")
    print()

    recipe_elements = ['butter', 'cake', 'cook', 'frost', 'juice', 'mix', 'rum', 'serve', 'spread', 'stir', 'sugar']
    total_novelty_score, element_scores = get_recipe_novelty_score(recipe_elements, score_only=False)
    print("Recipe elements:", recipe_elements)
    print("Total novelty score:", total_novelty_score)
    print("Top elements and their scores:", element_scores)
    print()

    recipe_elements = ['add', 'apple', 'cake', 'cayenne', 'chicken', 'cook', 'cream', 'cumin', 'curry', 'cut', 'frost', 'frosting', 'garlic', 'heat', 'measure', 'onion', 'potato', 'slice', 'spread', 'stir']
    total_novelty_score, element_scores = get_recipe_novelty_score(recipe_elements, score_only=False)
    print("Recipe elements:", recipe_elements)
    print("Total novelty score:", total_novelty_score)
    print("Top elements and their scores:", element_scores)
    print()




