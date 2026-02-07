import traceback
import re
import json
import Levenshtein
from tqdm import tqdm

from recipe_parsing import parse_ingredients, parse_instructions, MODEL_NAME, PARSING_SYSTEM_MESSAGE

from cooking_up_creativity.src.call_model import call_model
from cooking_up_creativity.src.constants import INGR_TYPE, ACTION_TYPE, INGR_ABSTR_COLOR, INGR_STRUCTURE_COLOR, \
    INGR_CORE_COLOR, ACTION_ABSTR_COLOR


# A collection of 250 most common action verbs grouped into categories:
with open("../resources/cooking_verbs_to_categories.json", 'r') as f:
    all_cooking_verbs = json.load(f)


# Prompt templates:

# One-shot example for translating recipe to tree in DOT code (a graph description language):
translate_to_tree_one_shot_example = "Title: apple cake\n\n" \
                                     "Ingredients: cinnamon, white sugar, apples, all-purpose flour, salt, baking " \
                                     "powder, eggs, oil, orange juice, vanilla extract, whipped cream.\n\n" \
                                     "Directions:\n" \
                                     "[i1] Preheat oven to 350°F (175°C).\n" \
                                     "[i2] Grease and flour a 10-inch tube pan.\n" \
                                     "[i3] Mix cinnamon, sugar, and apples.\n" \
                                     "[i4] Set aside.\n" \
                                     "[i5] Combine flour, salt, and baking powder.\n" \
                                     "[i6] Beat eggs and sugar until fluffy.\n" \
                                     "[i7] Add flour mixture alternately with oil.\n" \
                                     "[i8] Beat in orange juice and vanilla until smooth.\n" \
                                     "[i9] Pour some batter into the prepared pan.\n" \
                                     "[i10] Layer with apples.\n" \
                                     "[i11] Repeat with remaining batter and apples.\n" \
                                     "[i12] Bake for 1 hour and 30-45 minutes.\n" \
                                     "[i13] Cool for 10 minutes.\n" \
                                     "[i14] Remove and cool completely.\n" \
                                     "[i15] Serve with whipped cream.\n\n" \
                                     "Code:\n" \
                                     "# Define the edges for the tree representation of the recipe in Dot:\n" \
                                     "#  - define an edge from each ingredient to the specific action node that " \
                                     "uses this ingredient.\n" \
                                     "#  - create directed edges between action nodes where one action directly relies " \
                                     "on the outcome of another. Ensure every action node, except for the last one, " \
                                     "has a preceding parent node.\n" \
                                     "oil1 -> i2 # pan is prepared\n" \
                                     "cinnamon -> i3\n" \
                                     "white_sugar1 -> i3\n" \
                                     "apples -> i3\n" \
                                     "i3 -> i4 # apple mixture is ready\n" \
                                     "all_purpose_flour -> i5\n" \
                                     "salt -> i5\n" \
                                     "baking_powder -> i5 # flour mixture is ready\n" \
                                     "eggs -> i6\n" \
                                     "white_sugar2 -> i6\n" \
                                     "i6 -> i7\n" \
                                     "i5 -> i7 # add flour mixture\n" \
                                     "oil2 -> i7\n" \
                                     "i7 -> i8\n" \
                                     "orange_juice -> i8\n" \
                                     "vanilla_extract -> i8 # batter is ready\n" \
                                     "i8 -> i9  # pour batter\n" \
                                     "i2 -> i9  # use prepared pan\n" \
                                     "i9 -> i10 # layer batter\n" \
                                     "i4 -> i10 # use apple mixture\n" \
                                     "i10 -> i11\n" \
                                     "i11 -> i12 # bake\n" \
                                     "i1 -> i12 # use preheated oven\n" \
                                     "i12 -> i13\n" \
                                     "i13 -> i14\n" \
                                     "i14 -> i15\n" \
                                     "whipped_cream -> i15 # serve with whipped cream\n\n" \
                                     "# end of code\n\n"

# Tree correction prompt templates:
tree_correction_prompt = "You are provided with the title, ingredients, and directions of a recipe, along with " \
                         "a partial Dot code that represents the recipe's tree structure. The Dot code is missing " \
                         "some edges. Additionally, you will receive names of nodes for which these connections are " \
                         "missing. For each provided node name, add exactly one edge from this node to the action " \
                         "node that uses it (if it is an ingredient) or processes its outcome (if it is an action). " \
                         "Please return only the Dot code for these specific edges, including necessary comments, " \
                         "and exclude any additional text.\n\n"

tree_correction_code_comment = "# Define the edges for the tree representation of the recipe in Dot:\n" \
                               "#  - define an edge from each ingredient to the specific action node that uses this " \
                               "ingredient.\n" \
                               "#  - create directed edges between action nodes where one action directly relies on " \
                               "the outcome of another. Ensure every action node, except for the last one, has a " \
                               "preceding parent node.\n"


def get_single_recipe_sample(recipe_info: dict, dish_name: str) -> str:
    """
    Create a single recipe sample string for translation to tree.

    :param recipe_info: dictionary with recipe information
    :param dish_name: name of the dish
    :return: sample string
    """

    parsed_ingr = recipe_info["parsed_ingredients"]
    parsed_instr = recipe_info["parsed_instructions"]

    parsed_ingr_str = "Ingredients: " + ", ".join(list(parsed_ingr.keys())) + "."

    parsed_instr.replace(";", ".")
    parsed_instr_str = "Directions:\n"

    i = 1
    for instr in parsed_instr.split("."):
        if instr:
            parsed_instr_str += "[i" + str(i) + "] " + instr.strip() + ".\n"
            i += 1

    sample = "Title: " + dish_name + "\n\n" + parsed_ingr_str + "\n\n" + parsed_instr_str + "\nCode:\n"

    return sample


def get_tree_dot_code(recipe_info: dict, dish_name: str, recipe_id: str, model_code: str,
                      pretty_dot_code: bool = True) -> str:

    """
    Create DOT code for the recipe tree given the recipe info and the generated model code.

    :param recipe_info: dictionary with recipe information
    :param dish_name: name of the dish
    :param recipe_id: ID of the recipe
    :param model_code: generated model code
    :param pretty_dot_code: whether to create pretty DOT code with HTML labels or simple labels
    :return: DOT code string
    """

    tree_dot_start = "digraph " + dish_name.replace(" ", "_") + "_" + recipe_id + " {\n\trankdir=BT ratio=auto\n\n"

    tree_dot_ingr = ""

    parsed_ingr = recipe_info["parsed_ingredients"]

    for abbr in parsed_ingr:

        # remove non-characters from abbr:
        abbr_str = re.sub(r'[^\w\s]', '', abbr.replace("-", " ")).replace(" ", "_".replace("'", "").replace("&", "and"))

        if pretty_dot_code:
            tree_dot_ingr += "\t" + abbr_str + "[label=<" + abbr.replace("&", "and")
            tree_dot_ingr += "<br /> <font color=\"" + INGR_ABSTR_COLOR + "\" point-size=\"10\">" + parsed_ingr[abbr]["abstr"] + "</font>"
            if parsed_ingr[abbr]["ref"] == "structure":
                tree_dot_ingr += "<br /> <font color=\"" + INGR_STRUCTURE_COLOR + "\" point-size=\"10\">(structure)</font>"
            if parsed_ingr[abbr]["core"]:
                tree_dot_ingr += "<br /> <font color=\"" + INGR_CORE_COLOR + "\" point-size=\"10\">(core)</font>"
            tree_dot_ingr += "> shape=box]\n"
        else:
            tree_dot_ingr += "\t" + abbr_str + "[label=\"" + abbr.replace("&", "and") + "\" shape=box]\n"


    parsed_instr = recipe_info["parsed_instructions"]
    parsed_instr.replace(";", ".")

    tree_dot_instr = "\n"

    i = 1
    for instr in parsed_instr.split("."):
        instr = instr.strip().lower()
        if instr:
            instr_verb = instr.split()[0]
            if instr_verb not in all_cooking_verbs:
                for word in instr.split():
                    word = word.replace(",", "")
                    if word in all_cooking_verbs:
                        instr_verb = word
                        break

            if pretty_dot_code:
                if instr_verb in all_cooking_verbs:
                    verb_category = all_cooking_verbs[instr_verb]["category_str"]
                else:
                    verb_category = instr_verb
                tree_dot_instr += "\t" + "i" + str(i) + "[label=<" + instr_verb + "<br /> <font color=\"" + ACTION_ABSTR_COLOR + "\" point-size=\"10\">" + verb_category + "</font>>]\n"
            else:
                tree_dot_instr += "\t" + "i" + str(i) + "[label=\"" + instr_verb + "\"]\n"
            i += 1

    tree_dot_edges = model_code
    tree_dot_edges = tree_dot_edges.replace("\n", "\n\t")
    tree_dot_edges = tree_dot_edges.replace("```dot\n", "")
    tree_dot_edges = "\n\t" + tree_dot_edges[:-4]
    tree_dot_end = "\n}"

    tree_dot = tree_dot_start + tree_dot_ingr + tree_dot_instr + tree_dot_edges + tree_dot_end

    return tree_dot


def get_single_recipe_initial_translation(recipe_info: dict, dish_name: str, recipe_id: str, tries: int) -> str:

    """
    Get the initial tree translation in DOT code for a single recipe.

    :param recipe_info: dictionary with recipe information
    :param dish_name: name of the dish
    :param recipe_id: ID of the recipe
    :param tries: number of tries for calling the model
    :return: DOT code string
    """
    sample = get_single_recipe_sample(recipe_info, dish_name)

    request = translate_to_tree_one_shot_example + sample

    dot_code = ""

    success = False

    while not success and tries > 0:
        try:
            model_code = call_model(request,
                                    model_name=MODEL_NAME,
                                    system_message=PARSING_SYSTEM_MESSAGE,
                                    temperature=0.0,
                                    max_tokens=2500,
                                    stop="# end of code")
            success = True
        except:
            print("Error in translating recipe to tree. Trying again.")
            tries -= 1
            traceback.print_exc()

    if success:
        dot_code = get_tree_dot_code(recipe_info, dish_name, recipe_id, model_code, pretty_dot_code=True)

    return dot_code


def add_recipe_initial_translations(sampled_recipes: dict, tries: int = 3) -> dict:
    """
    Add initial tree translations to DOT code for all recipes in sampled_recipes.

    :param sampled_recipes: dictionary of sampled recipes
    :param tries: number of tries for calling the model (for each recipe)
    :return: sampled_recipes with tree DOT codes added
    """
    for dish_name in sampled_recipes:

        print("dish name:", dish_name)

        for recipe_id in tqdm(sampled_recipes[dish_name].keys()):

            recipe_info = sampled_recipes[dish_name][recipe_id]
            recipe_initial_translation = get_single_recipe_initial_translation(recipe_info, dish_name, recipe_id, tries)
            sampled_recipes[dish_name][recipe_id]["tree_dot_code"] = recipe_initial_translation

    return sampled_recipes


def is_action_node(node_name: str) -> bool:
    """
    Check whether a node is an action node based on its name.

    :param node_name: name of the node
    :return: True if action node, False otherwise
    """

    if node_name.startswith("i"):
        num = node_name.replace("i", "")
        if num.isdigit():
            return True
    return False


def parse_dot_tree_into_tree_dict(tree_dot_code: str) -> tuple:
    """
    Parse DOT code of a tree into a tree dictionary.

    :param tree_dot_code: DOT code string
    :return: tuple of tree dictionary and possibly modified DOT code string
    """

    tree_dict = {}
    to_change_and_delete = {}
    dot_lines = tree_dot_code.split("\n")
    dot_lines = [line.strip() for line in dot_lines if line.strip() and line.startswith("\t")]
    dot_lines = [line for line in dot_lines if not line.startswith("#")][1:]
    last_node = None

    for dline in dot_lines:
        if "->" in dline:  # an edge dot code line
            edge = dline.split("#")[0]
            edge_spltd = edge.split("->")
            edge_spltd = [d.strip() for d in edge_spltd]
            cur_node_name = edge_spltd[0]
            parent_node_name = edge_spltd[1]
            if cur_node_name in tree_dict:
                tree_dict[cur_node_name]["parents"].append(parent_node_name)
            else:  # node without declaration
                # check whether the mistake is in our sample declaration or the model's:
                all_node_names = list(tree_dict.keys())
                closest_node_name = min(all_node_names, key=lambda x: Levenshtein.distance(x, cur_node_name))
                closest_dist = Levenshtein.distance(cur_node_name, closest_node_name)
                if not is_action_node(cur_node_name) and closest_node_name == cur_node_name[:-1]:
                    tree_dot_code = tree_dot_code.replace(cur_node_name, closest_node_name)
                    tree_dict[closest_node_name]["parents"].append(parent_node_name)
                    print("Changed: <" + cur_node_name + "> to: <" + closest_node_name + ">")
                elif not is_action_node(cur_node_name) and closest_dist < 3 and not tree_dict[closest_node_name]["parents"]:
                    if closest_node_name not in to_change_and_delete:
                        to_change_and_delete[closest_node_name] = []
                    to_change_and_delete[closest_node_name] += [cur_node_name]

                    # add new node:
                    tree_dict[cur_node_name] = {}
                    tree_dict[cur_node_name]["dot_line"] = tree_dict[closest_node_name]["dot_line"].replace(closest_node_name, cur_node_name)
                    tree_dict[cur_node_name]["parents"] = [parent_node_name]
                    tree_dict[cur_node_name]["label"] = tree_dict[closest_node_name]["label"]
                    tree_dict[cur_node_name]["root"] = False
                    print("Added: <" + cur_node_name + "> instead of: <" + closest_node_name + ">")

                else:  # ignore the new node and the edge that points from it
                    tree_dot_code = tree_dot_code.replace(dline, "")
                    print("Removed node without declaration: ", cur_node_name)

        elif '[' in dline:  # node
            node_name = dline.split("[")[0]
            node_label = dline.split("[")[1].replace("label=", "")
            if node_label.startswith("<"):
                node_label = node_label[1:].split("<")[0]
            else:
                node_label = node_label[1:].split("\"")[0]
            last_node = node_name
            tree_dict[node_name] = {}
            tree_dict[node_name]["dot_line"] = dline
            tree_dict[node_name]["label"] = node_label
            tree_dict[node_name]["parents"] = []
            tree_dict[node_name]["root"] = False

        elif "#" in dline:  # a comment line that do not refer to a node or an edge
            tree_dot_code = tree_dot_code.replace(dline, "")

    tree_dict[last_node]["root"] = True

    # remove edges to undefined nodes:
    for nn in tree_dict:
        parents = tree_dict[nn]["parents"]
        for p in parents:
            if p not in tree_dict:
                tree_dot_code = tree_dot_code.replace(nn + " -> " + p, "")
                tree_dict[nn]["parents"].remove(p)
                print("Removed edge to undefined node: " + nn + " -> " + p)

    for node_name in to_change_and_delete:
        dlines = ""
        for nn in to_change_and_delete[node_name]:
            dlines += "\t" + tree_dict[nn]["dot_line"] + "\n"
        tree_dot_code = tree_dot_code.replace(tree_dict[node_name]["dot_line"], dlines.strip() + "\n")
        del tree_dict[node_name]

    return tree_dict, tree_dot_code


def correct_problematic_edges(tree_dict: dict, tree_dot_code: str) -> tuple:
    """
    Correct problematic edges in the tree dictionary and modify DOT code accordingly.

    :param tree_dict: tree dictionary
    :param tree_dot_code: DOT code string
    :return: tuple of modified tree dictionary, modified DOT code string, and problematic edges dictionary
    """
    problematic_edges = {}
    problematic_edges["wrong_direction (ingr->act)"] = []
    problematic_edges["wrong_direction (act->act)"] = []
    problematic_edges["multiple_parents (ingr)"] = []
    problematic_edges["multiple_parents (act)"] = []
    problematic_edges["no_parents (ingr)"] = []
    problematic_edges["no_parents (act)"] = []

    # wrong direction:
    for node_name in tree_dict:
        if is_action_node(node_name):
            for parent_node_name in tree_dict[node_name]["parents"]:
                if not is_action_node(parent_node_name):  # action -> ingredient
                    if parent_node_name in tree_dict:
                        problematic_edges["wrong_direction (ingr->act)"] += [(node_name, tree_dict[node_name]["label"], parent_node_name, tree_dict[parent_node_name]["label"])]
                        tree_dict[parent_node_name]["parents"].append(node_name)
                    # change direction:
                    tree_dict[node_name]["parents"].remove(parent_node_name)
                    tree_dot_code = tree_dot_code.replace(node_name + " -> " + parent_node_name, parent_node_name + " -> " + node_name)
                    print("Changed edge direction: " + node_name + " -> " + parent_node_name + " to " + parent_node_name + " -> " + node_name)
                else:  # action -> action
                    if int(node_name.replace("i", "")) >= int(parent_node_name.replace("i", "")):
                        if parent_node_name in tree_dict:
                            problematic_edges["wrong_direction (act->act)"] += [(node_name, tree_dict[node_name]["label"], parent_node_name, tree_dict[parent_node_name]["label"])]
                        # remove edge:
                        tree_dict[node_name]["parents"].remove(parent_node_name)
                        tree_dot_code = tree_dot_code.replace(node_name + " -> " + parent_node_name, "")
                        print("Removed wrong direction edge: " + node_name + "(" + tree_dict[node_name]["label"] + ") -> " + parent_node_name + "(" + tree_dict[parent_node_name]["label"] + ")")

    # multiple parents:
    nodes_to_delete = []
    nodes_to_add = {}
    for node_name in tree_dict:
        if len(tree_dict[node_name]["parents"]) > 1:
            if not is_action_node(node_name):  # ingredient node that has multiple parents
                problematic_edges["multiple_parents (ingr)"] += [(node_name, tree_dict[node_name]["label"], tree_dict[node_name]["parents"])]
                # split the node into multiple nodes:
                dlines = []
                new_nodes = []

                if node_name[-1].isdigit():
                    new_node_name = node_name[:-1]
                else:
                    new_node_name = node_name

                i = 1
                parents = tree_dict[node_name]["parents"]
                for parent_node_name in parents:
                    if new_node_name + str(i) not in tree_dict:
                        new_nodes += [new_node_name + str(i)]
                        nodes_to_add[new_node_name + str(i)] = {}
                        dot_line = tree_dict[node_name]["dot_line"].replace(node_name, new_node_name + str(i))
                        nodes_to_add[new_node_name + str(i)]["dot_line"] = dot_line
                        nodes_to_add[new_node_name + str(i)]["label"] = tree_dict[node_name]["label"]
                        nodes_to_add[new_node_name + str(i)]["parents"] = [parent_node_name]
                        nodes_to_add[new_node_name + str(i)]["root"] = False
                        dlines += ["\t" + dot_line]
                        tree_dot_code = tree_dot_code.replace(node_name + " -> " + parent_node_name + " ", new_node_name + str(i) + " -> " + parent_node_name + " ")
                        tree_dot_code = tree_dot_code.replace(node_name + " -> " + parent_node_name + "\n", new_node_name + str(i) + " -> " + parent_node_name + "\n")
                    else:
                        tree_dict[new_node_name + str(i)]["parents"] = [parent_node_name]
                        tree_dot_code = tree_dot_code.replace(node_name + " -> " + parent_node_name + " ", new_node_name + str(i) + " -> " + parent_node_name + " ")
                        tree_dot_code = tree_dot_code.replace(node_name + " -> " + parent_node_name + "\n", new_node_name + str(i) + " -> " + parent_node_name + "\n")
                    i += 1

                if dlines:
                    tree_dot_code = tree_dot_code.replace(tree_dict[node_name]["dot_line"], "\n".join(dlines).strip() + "\n")
                    nodes_to_delete += [node_name]
                print("Splitted node: <" + node_name + "> into: " + ", ".join(new_nodes))
            else:  # action node that has multiple parents
                problematic_edges["multiple_parents (act)"] += [(node_name, tree_dict[node_name]["label"], tree_dict[node_name]["parents"])]
                # remove all edges:
                for parent_node_name in tree_dict[node_name]["parents"]:
                    tree_dot_code = tree_dot_code.replace(node_name + " -> " + parent_node_name, "")
                tree_dict[node_name]["parents"] = []
                print("Removed multiple edges from action node: " + node_name + " (" + tree_dict[node_name]["label"] + ")")

    for nn in nodes_to_add:
        tree_dict[nn] = nodes_to_add[nn]

    for nn in nodes_to_delete:
        del tree_dict[nn]

    # remove all lines that are comments or empty lines (excluding an empty line between nodes and edges declarations):
    tree_dot_code = "\n".join([line for line in tree_dot_code.split("\n") if not line.strip().startswith("#") and line.strip()])
    for line in tree_dot_code.split("\n"):
        if "->" in line:
            tree_dot_code = tree_dot_code.replace(line, "\n" + line)
            break

    # no parents:
    for node_name in tree_dict:
        if not tree_dict[node_name]["parents"]:
            if not is_action_node(node_name):  # ingredient node that has no parents
                problematic_edges["no_parents (ingr)"] += [(node_name, tree_dict[node_name]["label"])]
            else:  # action node that has no parents
                if not tree_dict[node_name]["root"]:
                    problematic_edges["no_parents (act)"] += [(node_name, tree_dict[node_name]["label"])]

    return tree_dict, tree_dot_code, problematic_edges


def get_edges_part_only(dot_tree_code):
    """
    Get only the edges part from the DOT tree code.

    :param dot_tree_code: DOT code string
    :return: edges part string
    """

    lines = dot_tree_code.split("\n")
    lines = [line.strip() for line in lines]
    edges_lines = []
    for line in lines:
        if "->" in line:
            edges_lines += [line]

    return "\n".join(edges_lines)


def finalize_tree_dict(tree_dict):
    """
    Process the tree dictionary to finalize its structure (for a later use in minimum edit distance algorithm).

    :param tree_dict: tree dictionary
    :return: processed tree dictionary
    """
    node_names = list(tree_dict.keys())

    for node_name in node_names:
        dot_line = tree_dict[node_name]["dot_line"]
        if "shape=box" in dot_line:  # this is an ingredient node
            extra_info = []
            if INGR_STRUCTURE_COLOR in dot_line:
                extra_info += ["structure"]
            if INGR_CORE_COLOR in dot_line:
                extra_info += ["core"]
            spltd = dot_line.split("<br />")
            for item in spltd:
                if INGR_ABSTR_COLOR in item:
                    abstr = item.split(">")[1].split("<")[0]
                    tree_dict[node_name]["type"] = INGR_TYPE
                    tree_dict[node_name]["abstr"] = abstr
            if extra_info:
                tree_dict[node_name]["extra_info"] = extra_info
        else:  # this is an action node
            abstr = dot_line.replace("</font>>]", "").split(">")[-1]
            tree_dict[node_name]["type"] = ACTION_TYPE
            tree_dict[node_name]["abstr"] = abstr

        del tree_dict[node_name]["dot_line"]

        if tree_dict[node_name]["parents"]:
            tree_dict[node_name]["parent"] = tree_dict[node_name]["parents"][0]
        else:
            tree_dict[node_name]["parent"] = None

        del tree_dict[node_name]["parents"]

        tree_dict[node_name]["children"] = []

    for node_name in node_names:
        if tree_dict[node_name]["parent"]:
            if tree_dict[node_name]["parent"] in tree_dict:
                tree_dict[tree_dict[node_name]["parent"]]["children"] += [node_name]

    return tree_dict


def verify_and_correct_single_recipe_translation(recipe_info: dict, dish_name: str, tries) -> dict:
    """
    Verify and correct the tree translation of a single recipe.

    :param recipe_info: single recipe information dictionary
    :param dish_name: name of the dish
    :param tries: number of tries for calling the model
    :return: corrected recipe information dictionary
    """

    sample = get_single_recipe_sample(recipe_info, dish_name)
    tree_dot_code = recipe_info["tree_dot_code"]

    if not tree_dot_code:
        return recipe_info

    tree_dict, tree_dot_code = parse_dot_tree_into_tree_dict(tree_dot_code)

    tree_dict, tree_dot_code, problematic_edges = correct_problematic_edges(tree_dict, tree_dot_code)

    # in check_for_problematic_edges() every problematic edge is fixed or removed, therefore only nodes
    # with no parents remain to be fixed using the model again
    nodes_with_no_parents = [item[0] for item in problematic_edges["no_parents (ingr)"]] + [item[0] for item in problematic_edges["no_parents (act)"]]

    if len(nodes_with_no_parents) > 0:

        request = tree_correction_prompt + sample.replace("Code:", "Partial Dot Code:") \
                  + tree_correction_code_comment + get_edges_part_only(tree_dot_code) \
                  + "\n\nName of nodes with missing edges:\n" + ", ".join(nodes_with_no_parents) + "\n\n" \
                  + "Output:\n"

        success = False

        while not success and tries > 0:
            try:
                response = call_model(request,
                                      model_name=MODEL_NAME,
                                      system_message=PARSING_SYSTEM_MESSAGE,
                                      temperature=0.0,
                                      max_tokens=100)
                success = True
            except:
                print("Error in correcting tree. Trying again.")
                traceback.print_exc()
                tries -= 1

        response_lines = response.split("\n")
        edges = ["\t" + line for line in response_lines if "->" in line]

        if edges:
            for edge in edges:
                edge_no_comment = edge.split("#")[0].strip()
                edge_start = edge_no_comment.split("->")[0].strip()
                edge_end = edge_no_comment.split("->")[1].strip()
                if edge_start in nodes_with_no_parents:
                    if edge_start in tree_dict and edge_end in tree_dict:
                        if tree_dict[edge_start]["parents"]:
                            print("Node <" + edge_start + "> already has a parent. Overwriting parent to: <" + edge_end + ">")
                            tree_dot_code.replace(edge_start + " -> " + tree_dict[edge_start]["parents"][0], "")
                        tree_dict[edge_start]["parents"] = [edge_end]
                else:
                    print("Received edge for node <" + edge_start + "> that was not listed as problematic. Removing edge.")
                    tree_dot_code.replace(edge, "")  # remove irrelevant edge from code

            edges_str = "\n".join(edges)
            tree_dot_code = tree_dot_code.replace("}", edges_str + "\n}")

    # correct problematic edges again (after additional edges added by the model):
    tree_dict, tree_dot_code, problematic_edges = correct_problematic_edges(tree_dict, tree_dot_code)
    nodes_with_no_parents = [item[0] for item in problematic_edges["no_parents (ingr)"]] + [item[0] for item in problematic_edges["no_parents (act)"]]

    is_tree = True
    if len(nodes_with_no_parents) > 0:
        is_tree = False

    final_tree_dict = finalize_tree_dict(tree_dict)

    # update recipe_info:
    recipe_info["tree_dot_code"] = tree_dot_code
    recipe_info["tree_dict"] = final_tree_dict
    recipe_info["is_tree"] = is_tree

    return recipe_info


def verify_and_correct_recipe_translations(sampled_recipes: dict, tries: int = 3) -> dict:
    """
    Verify and correct the tree translations of all recipes in sampled_recipes.

    :param sampled_recipes: dictionary of sampled recipes with initial tree translations
    :param tries: number of tries for calling the model (for each recipe)
    :return: sampled_recipes with verified and corrected tree translations
    """
    for dish_name in sampled_recipes:

        print("dish name:", dish_name)

        for recipe_id in tqdm(list(sampled_recipes[dish_name].keys())):

            recipe_info = sampled_recipes[dish_name][recipe_id]
            corrected_recipe_info = verify_and_correct_single_recipe_translation(recipe_info, dish_name, tries)

            sampled_recipes[dish_name][recipe_id] = corrected_recipe_info

    return sampled_recipes


def translate_recipes_to_trees(sampled_recipes: dict, tries: int = 3) -> dict:

    """
    Translate all recipes in sampled_recipes to tree representations in DOT code.

    :param sampled_recipes: dictionary of sampled recipes
    :param tries: number of tries for calling the model (for each recipe)
    :return: the dictionary of sampled recipes with tree representations added
    """

    print("Parsing all recipe ingredients...")
    sampled_recipes_ingr_parsed = parse_ingredients(sampled_recipes, tries=tries)

    print("Parsing all recipe instructions...")
    sampled_recipes_parsed = parse_instructions(sampled_recipes_ingr_parsed, tries=tries)

    print("Create initial tree translations into DOT code...")
    sampled_recipes_initial_trees = add_recipe_initial_translations(sampled_recipes_parsed, tries=tries)

    print("Verify and correct all trees...")
    sampled_recipes_final_trees = verify_and_correct_recipe_translations(sampled_recipes_initial_trees, tries=tries)

    return sampled_recipes_final_trees


if __name__ == '__main__':

    sampled_recipes_path = "../toy_example_files/sampled_recipes_tiny.json"

    # Load sampled recipes:
    with open(sampled_recipes_path, 'r', encoding='utf8') as f:
        sampled_recipes = json.load(f)

    # Translate recipes to trees:
    sampled_recipes_trees = translate_recipes_to_trees(sampled_recipes, tries=3)

    # Save parsed outputs into a new JSON file:
    out_path = sampled_recipes_path.replace(".json", "_parsed_new.json")
    with open(out_path, 'w', encoding='utf8') as f:
        json.dump(sampled_recipes_trees, f, indent=4, ensure_ascii=False)

