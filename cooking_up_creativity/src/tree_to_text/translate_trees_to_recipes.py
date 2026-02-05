import json
import traceback
import re
from tqdm import tqdm

from src.call_model import call_model

MODEL_NAME = "gpt-4o-2024-08-06"
MODEL_EXPERTISE_COOKING_EXPERT = "You are a cooking recipes expert."
MODEL_EXPERTISE_CULINARY_EXPERT = "You are a culinary expert specializing in flavor pairing and ingredient compatibility."


# PROMPT TEMPLATES:

# Translate tree into raw recipe:
tree_to_recipe_prompt = "Given the following DOT code, which represents a recipe graphically by defining " \
                        "ingredient nodes, action nodes, and their interconnections, translate the structure " \
                        "into a natural language recipe. The DOT code maps each ingredient to specific actions, " \
                        "and it outlines the order of these actions to demonstrate the cooking process.\n\n" \
                        "DOT CODE:\n" \
                        "''' {dot_code} '''\n\n" \
                        "Convert this structured representation into a detailed cooking recipe in natural " \
                        "language. Requirements:\n" \
                        "(1) Output should only include the title, ingredients with quantities, and sequential " \
                        "instructions.\n" \
                        "(2) Avoid any explanatory comments or embellishments.\n\n" \
                        "OUTPUT:\n"

# Find issues and correct recipe:
recipe_review_prompt = "Review the recipe provided below, which is written in natural language. Identify and list any" \
                       " potential issues with it, excluding any concerns related to unconventional ingredient" \
                       " combinations. Do not revise the recipe." \
                       "\n\nRECIPE:\n" \
                       "''' {full_recipe} '''"

correct_recipe_prompt = "Please edit the recipe to address the identified issues. Output only the corrected version " \
                        "of the recipe.\n\nOUTPUT:\n"

# Summarize recipe:
summarize_recipe_prompt = "Please summarize the following recipe in a few sentences. Please include all the " \
                          "ingredients in your summary (without their quantities).\n\n" \
                          "RECIPE:\n" \
                          "''' {full_recipe} '''"

# Review ingredients:
review_ingredients_prompt = "You are given a description of a creative recipe.\n\n" \
                            "CREATIVE RECIPE DESCRIPTION:\n" \
                            "''' {creative_recipe_description} '''\n\n" \
                            "Your task is to preserve the creative ingredients in the recipe while suggesting the " \
                            "removal or substitution of ingredients that might negatively impact the dish's flavor. " \
                            "You should:\n" \
                            "- Recognize the unique and unusual ingredients that contribute to the creativity of " \
                            "the dish.\n" \
                            "- Systematically compare all pairs of ingredients in the dish and identify ingredients " \
                            "that have a clear, strong clash with each other due to conflicting flavors. Be thorough " \
                            "and ensure that you include all possible pairs of ingredients that have a strong clash.\n" \
                            "- Based on the identified strong clashes, suggest removals and substitutions of " \
                            "ingredients to avoid clashes, while preserving the creative aspects of the dish.\n\n" \
                            "Return only the following JSON output format:\n" \
                            "{{\"dish_ingredients\": <list of strings: the full list of ingredients in the dish>, " \
                            "\"creative_ingrs\": <list of strings: the list of ingredients that contribute " \
                            "creatively to the dish>, \"flavor_clashes\": <list of string pairs: the clashing " \
                            "ingredients>, \"removals\": <list of strings: the list of ingredients to remove>, " \
                            "\"substitutions\": <list of string pairs: ingredients to substitute - (ingr1, ingr2) " \
                            "means 'replace ingr1 in ingr2'>}}"

# Increase readability
increase_recipe_readability_prompt = "Given the following recipe:\n" \
                                     "(1) Remove the following ingredients: {bad_ingredients}\n" \
                                     "(2) Make the following ingredient substitutions: {required_substitutions}\n" \
                                     "(3) Split its ingredients and instructions into distinct sections to improve " \
                                     "readability (e.g., \"mix dry ingredients\", \"assemble\", etc.). You can " \
                                     "change the order of lines but keep the content unchanged.\n\n" \
                                     "''' {full_recipe} '''"


def translate_tree_to_raw_recipe(tree_dot_code: str, tries: int = 3) -> str:

    translate_request = tree_to_recipe_prompt.format(dot_code=tree_dot_code.strip())

    success = False
    while not success and tries > 0:
        try:
            response = call_model(request=translate_request,
                                  model_name=MODEL_NAME,
                                  system_message=MODEL_EXPERTISE_COOKING_EXPERT,
                                  temperature=0.0,
                                  max_tokens=2400)
            raw_recipe_text = response.strip()
            success = True
        except:
            print("Error in translating tree to raw recipe. Trying again.")
            tries -= 1
            traceback.print_exc()

    return raw_recipe_text


def review_and_correct_recipe(raw_recipe_text: str, tries: int = 3) -> str:

    review_recipe_request = recipe_review_prompt.format(full_recipe=raw_recipe_text)

    # find issues in recipe:
    success = False
    while not success and tries > 0:
        try:
            response = call_model(request=review_recipe_request,
                                  model_name=MODEL_NAME,
                                  system_message=MODEL_EXPERTISE_COOKING_EXPERT,
                                  temperature=0.0,
                                  max_tokens=2400)
            raw_recipe_issues = response.strip()
            success = True
        except:
            print("Error in reviewing recipe. Trying again.")
            tries -= 1
            traceback.print_exc()

    # correct the found issues:
    messages_array = [{"role": "user", "content": review_recipe_request},
                      {"role": "system", "content": raw_recipe_issues}]
    success = False
    while not success and tries > 0:
        try:
            response = call_model(request=correct_recipe_prompt,
                                  model_name=MODEL_NAME,
                                  system_message=MODEL_EXPERTISE_COOKING_EXPERT,
                                  messages_array=messages_array,
                                  temperature=0.0,
                                  max_tokens=3000)
            corrected_recipe = response.strip()
            success = True
        except:
            print("Error in correcting recipe based on found issues. Trying again.")
            tries -= 1
            traceback.print_exc()

    return raw_recipe_issues, corrected_recipe


def clean_embelishments(recipe_text: str) -> str:

    cleaned_recipe_text = ""
    recipe_text = recipe_text.split("\n")
    for line in recipe_text:
        if not line.strip():
            cleaned_recipe_text += "\n"
        else:
            line = line.replace("#", "").strip()
            line = re.sub(r'^\d{1,2}\.', '', line)
            line = re.sub(r'\*\*.*?\*\*:', '', line)
            line = re.sub(r'\*\*', '', line)
            line = line.replace("  ", " ")
            line = line.strip()
            if line:
                cleaned_recipe_text += line + "\n"
    return cleaned_recipe_text


def summarize_recipe(recipe_text: str, tries: int = 3) -> str:

    summary_request = summarize_recipe_prompt.format(full_recipe=recipe_text.strip())

    success = False
    while not success and tries > 0:
        try:
            response = call_model(request=summary_request,
                                  model_name=MODEL_NAME,
                                  system_message=MODEL_EXPERTISE_COOKING_EXPERT,
                                  temperature=0.0,
                                  max_tokens=1200)
            recipe_summary = response.strip()
            success = True
        except:
            print("Error in summarizing recipe. Trying again.")
            tries -= 1
            traceback.print_exc()

    return recipe_summary


def review_ingredients(recipe_summary: str, tries: int = 3) -> dict:

    review_ingrs_request = review_ingredients_prompt.format(creative_recipe_description=recipe_summary.strip())

    success = False
    while not success and tries > 0:
        try:
            response = call_model(request=review_ingrs_request,
                                  model_name=MODEL_NAME,
                                  system_message=MODEL_EXPERTISE_CULINARY_EXPERT,
                                  temperature=0.0,
                                  max_tokens=1000)
            raw_response = response.strip()
            raw_response = raw_response.replace("(", "[").replace(")", "]")
            response = "{" + raw_response.split("{")[1].split("}")[0] + "}"
            review_ingrs_dict = json.loads(response)
            removals = review_ingrs_dict["removals"]
            removals = [item for item in removals if item not in review_ingrs_dict["creative_ingrs"]]
            review_ingrs_dict["removals"] = removals
            success = True
        except:
            print("Error in review recipe ingredients. Trying again.")
            tries -= 1
            traceback.print_exc()

    return review_ingrs_dict


def increase_readability(recipe_text: str, removals: list, substitutions: list, tries: int = 3) -> str:

    removals = ', '.join(removals)
    substitutions = ', '.join([sub[0] + "-->" + sub[1] for sub in substitutions])
    request = increase_recipe_readability_prompt.format(full_recipe=recipe_text.strip(),
                                                        bad_ingredients=removals,
                                                        required_substitutions=substitutions)

    success = False
    while not success and tries > 0:
        try:
            response = call_model(request=request,
                                  model_name=MODEL_NAME,
                                  system_message=MODEL_EXPERTISE_COOKING_EXPERT,
                                  temperature=1.0,
                                  max_tokens=2400)
            more_readable_text = response.strip()
            success = True
        except:
            print("Error in increase readability. Trying again.")
            tries -= 1
            traceback.print_exc()

    return more_readable_text


def translate_trees_into_recipes(tree_ideas: dict, tries: int = 3) -> dict:
    """
    Translate all trees in tree_ideas into recipes in natural language using an LLM.
    Also generates a summary for each recipe and computes its final novelty score.
    Note that the tree novelty score and the recipe novelty score may differ (as during the translation
    from the recombined tree into natural-language recipe, the LLM fills in missing details and corrects
    inconsistencies, which can introduce or remove elements and thus change the final novelty score)

    :param sampled_recipes: dictionary of tree ideas
    :param tries: number of tries for calling the model (for each tree idea)
    :return: the updated tree_ideas dictionary with the generated recipes, their summaries and novelty scores.
    """

    for idea_id in tqdm(list(tree_ideas.keys())):

        tree_dot_code = tree_ideas[idea_id]['tree_dot_code']
        raw_recipe_text = translate_tree_to_raw_recipe(tree_dot_code, tries=tries)
        recipe_issues, corrected_recipe = review_and_correct_recipe(raw_recipe_text, tries=tries)
        corrected_recipe = clean_embelishments(corrected_recipe)
        recipe_summary = summarize_recipe(corrected_recipe, tries=tries)
        review_ingrs_dict = review_ingredients(recipe_summary, tries=tries)
        more_readable_text = increase_readability(corrected_recipe, review_ingrs_dict["removals"],
                                                  review_ingrs_dict["substitutions"], tries=tries)

        tree_ideas[idea_id]["raw_recipe_text"] = raw_recipe_text
        tree_ideas[idea_id]["recipe_issues"] = recipe_issues
        tree_ideas[idea_id]["corrected_recipe"] = corrected_recipe
        tree_ideas[idea_id]["recipe_summary"] = recipe_summary
        tree_ideas[idea_id]["review_ingrs_dict"] = review_ingrs_dict
        tree_ideas[idea_id]["more_readable_text"] = more_readable_text

    return tree_ideas


if __name__ == '__main__':

    generated_ideas_path = "generated_recipes_tiny_best_ideas.json"

    # Load generated ideas:
    with open(generated_ideas_path, 'r') as f:
        generated_ideas = json.load(f)

    # Translate trees into recipes:
    updated_generated_ideas = translate_trees_into_recipes(generated_ideas, tries=3)

    # Save updated generated ideas into a new JSON file:
    with open("generated_recipes_final.json", 'w', encoding='utf8') as f:
        json.dump(updated_generated_ideas, f, indent=4)





