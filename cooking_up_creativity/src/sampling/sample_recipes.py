import re
import json
import random
from sentence_transformers import SentenceTransformer, util
import numpy as np


def organize_1M_recipes_dataset(data_path: str) -> dict:
    """
    Organize the Recipe1M dataset into a dictionary format.

    :param data_path: Path to the JSON file containing the Recipe1M dataset.
    :return: A dictionary with organized recipe data.
    """
    with open(data_path, 'r', encoding='utf8') as f:
        data = json.load(f)

    organized_data = {}

    item_id = 0

    for item in data:
        title = item['title']
        ingredient_list = [ingr['text'] for ingr in item['ingredients']]
        instruction_list = [instr['text'] for instr in item['instructions']]
        organized_data[str(item_id)] = {}
        organized_data[str(item_id)]['title'] = title
        organized_data[str(item_id)]['ingredient_list'] = ingredient_list
        organized_data[str(item_id)]['instruction_list'] = instruction_list
        item_id += 1

    return organized_data


# The following JSON file contains all the words that appear in dish names on Allrecipes.com
with open("words_in_dish_names_all_recipes_site.json", 'r') as f:
    relevant_words = set(json.load(f))


def shorten_title(title: str) -> str:
    """
    Shorten the recipe title to contain only the most relevant words.

    :param title: The original recipe title.
    :return: The shortened recipe title. 
    """

    title = title.strip().lower()
    title = title.replace("&", " and ")
    title = title.replace(" mac ", " macaroni ")
    title = title.replace(" mayo ", " mayonnaise ")
    title = title.replace("-", " ")
    title = re.sub(r'\s*\([^)]*\)', '', title).strip()
    spltd = title.split()
    spltd = [item.strip() for item in spltd if item.strip()]

    shorten_title = ""
    if len(spltd) == 0:
        shorten_title = "no_title"
    elif len(spltd) == 1:
        shorten_title = spltd[0]
    else:
        if spltd[-1] == "recipe":
            spltd = spltd[:-1]
        prev_item_and = False
        prev_item_ends_ed = False
        for item in spltd:
            if item in relevant_words:
                shorten_title += item + " "
            elif item + "s" in relevant_words:
                shorten_title += item + " "
            elif item.endswith("s") and item[:-1] in relevant_words:
                shorten_title += item + " "
            else:
                if prev_item_and:
                    shorten_title = shorten_title[:-4]
                if prev_item_ends_ed:
                    shorten_title += item + " "

            if item == "and":
                prev_item_and = True
            else:
                prev_item_and = False
            if item.endswith("ed"):
                prev_item_ends_ed = True
            else:
                prev_item_ends_ed = False

    shorten_title = shorten_title.strip()

    if len(spltd) < 4:
        if not spltd:
            shorten_title = "no_title"
        elif not shorten_title.endswith(spltd[-1]):
            shorten_title += " " + spltd[-1]

    if shorten_title.endswith(" a"):
        shorten_title = shorten_title[:-2]
    if shorten_title.startswith("a "):
        shorten_title = shorten_title[2:]
    if shorten_title.startswith("and "):
        shorten_title = shorten_title[4:]
    shorten_title = shorten_title.replace("with and", "with")

    return shorten_title.strip()


def get_typical_recipe_ids(dish_names: list, recipe_data: dict) -> dict:
    """
    Identify and return the typical recipe IDs associated with each dish.
    A recipe is considered typical for a dish if its shortened title matches the dish name.

    :param dish_names: A list of dish names.
    :param recipe_data: Dictionary containing recipe IDs and titles.
    :return: A dictionary mapping each dish name to a list of its typical recipe IDs.
    """

    dish_to_typical_recipe_ids = {}

    for dish_name in dish_names:
        dish_to_typical_recipe_ids[dish_name] = []

    for recipe_id in recipe_data:
        title = recipe_data[recipe_id]['title']
        shortened_dish_title = shorten_title(title)
        if shortened_dish_title in dish_to_typical_recipe_ids:
            dish_to_typical_recipe_ids[shortened_dish_title].append(int(recipe_id))

    return dish_to_typical_recipe_ids


def sample_typical_recipes(dish_names: list, recipe_data: dict, sampled_recipes: dict, recipes_per_dish: int = 15):
    """
    Sample typical recipes for each of the given dishes.

    :param dish_names: A list of dish names.
    :param recipe_data: A dictionary containing recipe data.
    :param sampled_recipes: A dictionary to store the sampled recipes.
    :param recipes_per_dish: Number of recipes to sample per dish.
    """

    dish_to_typical_recipe_ids = get_typical_recipe_ids(dish_names, recipe_data)

    for dish_name in dish_names:
        if dish_name not in sampled_recipes:
            sampled_recipes[dish_name] = {}
        typical_recipe_ids = dish_to_typical_recipe_ids[dish_name]
        sampled_ids = random.sample(typical_recipe_ids, min(recipes_per_dish, len(typical_recipe_ids)))
        for recipe_id in sampled_ids:
            sampled_recipes[dish_name][recipe_id] = recipe_data[str(recipe_id)]


def get_relevant_recipe_ids(dish_names: list, recipe_data: dict) -> dict:
    """
    Identify and return the recipe IDs relevant to each dish.
    A recipe is considered relevant to a dish if its title contains the dish name.

    :param dish_names: A list of dish names.
    :param recipe_data: Dictionary containing recipe IDs and titles.
    :return: A dictionary mapping each dish name to a list of its relevant recipe IDs.
    """

    dish_to_relevant_recipe_ids = {}

    for dish_name in dish_names:
        dish_to_relevant_recipe_ids[dish_name] = []

    for recipe_id in recipe_data:
        title = recipe_data[recipe_id]['title'].lower().split()
        for dish_name in dish_names:
            if all(word in title for word in dish_name.split()):
                dish_to_relevant_recipe_ids[dish_name].append(int(recipe_id))

    return dish_to_relevant_recipe_ids


def get_diverse_recipe_ids(dish_recipes: list, dish_ids: list, model: SentenceTransformer,
                           num_of_recipes_to_sample: int) -> list:
    """
    Use the GMM greedy algorithm to sample diverse recipe IDs based on their embeddings.
    The GMM algorithm identifies the dish's embedding centroid and iteratively selects recipes that are furthest
    from both the centroid and previously chosen samples.

    :param dish_recipes: A list of recipe texts for a specific dish.
    :param dish_ids: A list of recipe IDs corresponding to the dish_recipes.
    :param model: A SentenceTransformer model for embedding generation.
    :param num_of_recipes_to_sample: Number of diverse recipes to sample.
    :return: A list of sampled diverse recipe IDs.
    """

    chosen_dish_ids = []
    chosen_embeddings = []
    distances_to_chosen = []

    embeddings = model.encode(dish_recipes, show_progress_bar=True)
    centroid = np.mean(embeddings, axis=0)

    distances = np.linalg.norm(embeddings - centroid, axis=1)
    distances_to_chosen += [distances]

    closest_index = np.argsort(distances)[1]  # skip the centroid itself
    chosen_dish_ids += [dish_ids[closest_index]]
    chosen_embeddings += [embeddings[closest_index]]

    furthest_index = np.argsort(distances)[-1]
    chosen_dish_ids += [dish_ids[furthest_index]]
    chosen_embeddings += [embeddings[furthest_index]]
    min_dist = distances

    for i in range(num_of_recipes_to_sample - 2):
        last_distances = np.linalg.norm(embeddings - chosen_embeddings[-1], axis=1)
        distances_to_chosen += [last_distances]
        min_dist = np.minimum(min_dist, last_distances)
        chosen_index = np.argmax(min_dist)
        chosen_dish_ids += [dish_ids[chosen_index]]
        chosen_embeddings += [embeddings[chosen_index]]

    return chosen_dish_ids


def sample_diverse_recipes(dish_names: list, recipe_data: dict, sampled_recipes: dict, recipes_per_dish=15):
    """
    Sample diverse recipes for each of the given dishes using the GMM greedy algorithm over recipe embeddings.

    :param dish_names: A list of dish names.
    :param recipe_data: A dictionary containing recipe data.
    :param sampled_recipes: A dictionary to store the sampled recipes.
    :param recipes_per_dish: Number of recipes to sample per dish.
    """

    model = SentenceTransformer('moranmiz/recipe-sbert-model')

    dish_to_relevant_recipe_ids = get_relevant_recipe_ids(dish_names, recipe_data)

    for dish_name in dish_names:

        if dish_name not in sampled_recipes:
            sampled_recipes[dish_name] = {}

        relevant_recipe_ids = dish_to_relevant_recipe_ids[dish_name]
        relevant_recipe_ids = random.sample(relevant_recipe_ids, min(1000, len(relevant_recipe_ids)))

        dish_recipes = []
        for recipe_id in relevant_recipe_ids:
            recipe_text = "Ingredients: " + ', '.join(recipe_data[str(recipe_id)]["ingredient_list"]) \
                              + ". Instructions: " + ' '.join(recipe_data[str(recipe_id)]["instruction_list"])
            dish_recipes += [recipe_text]

        diverse_recipe_ids = get_diverse_recipe_ids(dish_recipes, relevant_recipe_ids, model, recipes_per_dish)

        for recipe_id in diverse_recipe_ids:
            sampled_recipes[dish_name][recipe_id] = recipe_data[str(recipe_id)]


if __name__ == '__main__':

    # Path to the JSON file containing the Recipe1M dataset
    # (download from: https://github.com/torralba-lab/im2recipe?tab=readme-ov-file#recipe1m-dataset):
    recipe_data_path = "layer1.json"

    recipe_data = organize_1M_recipes_dataset(recipe_data_path)

    with open("100_most_popular_dishes.txt", 'r', encoding='utf8') as f:
        dish_names = [line.strip() for line in f.readlines()]

    sampled_recipes = {}

    # for each dish sample 15 recipes at random to capture the typical version of the dish:
    sample_typical_recipes(dish_names, recipe_data, sampled_recipes, recipes_per_dish=15)

    # for each dish sample 15 more recipes to maximize diversity (using the GMM algorithm over recipe embeddings):
    sample_diverse_recipes(dish_names, recipe_data, sampled_recipes, recipes_per_dish=15)

    with open("sampled_recipes.json", 'w', encoding='utf8') as f:
        json.dump(sampled_recipes, f, indent=4, ensure_ascii=False)
