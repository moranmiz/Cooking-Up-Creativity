import traceback
import json
from cooking_up_creativity.src.call_model import call_model
from tqdm import tqdm


PARSE_INGR_BATCH_SIZE = 5
PARSE_INST_BATCH_SIZE = 8

MODEL_NAME = "gpt-4o"
PARSING_SYSTEM_MESSAGE = "You are a cooking recipe parser."

# Parsing ingredients prompt:
parse_ingr_prompt = "Given a recipe title, id, and ingredients, for each ingredient, determine:\n" \
                    "(1) Abbreviation: The shortest clear description.\n" \
                    "(2) Reference Type: Identify if the ingredient is for structure ('structure') or taste ('taste') " \
                    "of the dish. Ingredients impacting both are labeled as 'taste'.\n" \
                    "(3) Core Ingredient: Boolean indicating if the ingredient is essential to the identity of the " \
                    "dish (e.g., True for chocolate in chocolate cake).\n" \
                    "(4) Abstraction: Simplify the ingredient to its base form (e.g., 'basil' to 'herb', ‘walnuts’ " \
                    "to ‘nut’, 'eggs' to 'egg').\n\n" \
                    "Please return the results in the following JSON format only:\n" \
                    "{\"recipe_id\": [[abbreviation, ref, core, abstraction], ...], ...}\n\n"


# Parsing instructions prompt:
parse_instr_prompt = "Given the following cooking instructions, please simplify and shorten them as much as possible. " \
                     "Remove quantities, sizes, and descriptions. Ensure each verb initiates a new sentence, and that " \
                     "a sentence does not contain two verbs. Convert permissive or ambiguous instructions into active " \
                     "forms (e.g., \"let cool\" -> \"cool\", \"alternate layers\" -> \"layer\"). Return output in JSON " \
                     "format with the key as 'recipe_id' and the value as the full simplified text.\n\n"


def parse_ingredients(sampled_recipes: dict, tries: int = 3) -> dict:
    """
    Parsing ingredients for all recipes in sampled_recipes, using GPT-4o model.

    :param sampled_recipes: dictionary of sampled recipes
    :param tries: number of tries (calls for LLM) for parsing ingredients
    :return: sampled_recipes with parsed ingredients added
    """

    to_parse = []

    for dish_name in sampled_recipes:
        for recipe_id in sampled_recipes[dish_name]:
                to_parse += [(dish_name, recipe_id)]

    for i in tqdm(range(0, len(to_parse), PARSE_INGR_BATCH_SIZE)):

        to_parse_batch = to_parse[i:i + PARSE_INGR_BATCH_SIZE]

        parsed_ingr_dict = parse_ingredients_batch(sampled_recipes, to_parse_batch, tries)

        for item in to_parse_batch:
            dish_name, recipe_id = item
            if recipe_id in parsed_ingr_dict:
                sampled_recipes[dish_name][recipe_id]["parsed_ingredients"] = parsed_ingr_dict[recipe_id]

    return sampled_recipes


def parse_ingredients_batch(sampled_recipes: dict, to_parse_batch: list, tries: int) -> dict:
    """
    Parsing ingredients for a batch of recipes.

    :param sampled_recipes: dictionary of sampled recipes
    :param to_parse_batch: list of tuples (dish_name, recipe_id)
    :param tries: number of tries (calls for LLM) for parsing ingredients
    :return: parsed ingredients dictionary
    """

    parsed_ingr_dict = {}

    request = parse_ingr_prompt + "INPUT:\n"

    for dish_name, recipe_id in to_parse_batch:
        request += dish_name + ", " + recipe_id + ", " + str(sampled_recipes[dish_name][recipe_id]["ingredient_list"]) + "\n"

    request += "\nOUTPUT:"

    success = False

    while not success and tries > 0:

        try:
            response = call_model(request=request,
                                  model_name=MODEL_NAME,
                                  system_message=PARSING_SYSTEM_MESSAGE,
                                  temperature=0,
                                  max_tokens=2000)
            response = "{" + response.split("{")[1].split("}")[0].strip() + "}"
            parsed_ingr = json.loads(response)
            success = True

        except:
            print("Error in parsing ingredients. Trying again.")
            tries -= 1
            traceback.print_exc()

    if success:
        for recipe_id in parsed_ingr:
            cur_recipe_parsed_ingrs = {}
            for item in parsed_ingr[recipe_id]:
                abbr = item[0].lower()
                cur_recipe_parsed_ingrs[abbr] = {}
                cur_recipe_parsed_ingrs[abbr]["ref"] = item[1].lower()
                cur_recipe_parsed_ingrs[abbr]["core"] = item[2]
                cur_recipe_parsed_ingrs[abbr]["abstr"] = item[3].lower()
            parsed_ingr_dict[recipe_id] = cur_recipe_parsed_ingrs

    return parsed_ingr_dict



def parse_instructions(sampled_recipes: dict, tries: int = 3) -> dict:
    """
    Parsing instructions for all recipes in sampled_recipes, using GPT-4o model.

    :param sampled_recipes: dictionary of sampled recipes
    :param tries: number of tries (calls for LLM) for parsing instructions
    :return: sampled_recipes with parsed instructions added
    """

    to_parse = []

    for dish_name in sampled_recipes:
        for recipe_id in sampled_recipes[dish_name]:
            to_parse += [(dish_name, recipe_id)]

    for i in tqdm(range(0, len(to_parse), PARSE_INGR_BATCH_SIZE)):

        to_parse_batch = to_parse[i:i + PARSE_INGR_BATCH_SIZE]

        batch_dict = {}
        for dish_name, recipe_id in to_parse_batch:
            batch_dict[recipe_id] = sampled_recipes[dish_name][recipe_id]["instruction_list"]

        parsed_instr_dict = parse_instructions_batch(batch_dict, tries)

        for item in to_parse_batch:
            dish_name, recipe_id = item
            if recipe_id in parsed_instr_dict:
                sampled_recipes[dish_name][recipe_id]["parsed_instructions"] = parsed_instr_dict[recipe_id]

    return sampled_recipes


def parse_instructions_batch(batch_dict: dict, tries: int) -> dict:  # to_parse is a list of tuples (dish_name, recipe_id)
    """
    Parsing instructions for a batch of recipes.

    :param batch_dict: dictionary of recipe_id to instruction_list
    :param tries: number of tries (calls for LLM) for parsing instructions
    :return: parsed instructions dictionary
    """

    parsed_instr_dict = {}

    request = parse_instr_prompt + "INPUT:\n"
    request += str(batch_dict) + "\n"
    request += "\nOUTPUT:"

    success = False

    while not success and tries > 0:

        try:
            response = call_model(request=request,
                                  model_name=MODEL_NAME,
                                  system_message=PARSING_SYSTEM_MESSAGE,
                                  temperature=0,
                                  max_tokens=2500)
            response = "{" + response.split("{")[-1].split("}")[0].strip() + "}"
            parsed_instr_dict = json.loads(response)
            success = True

        except Exception as e:
            print("Error in parsing instructions. Trying again.")
            tries -= 1
            traceback.print_exc()

    return parsed_instr_dict

