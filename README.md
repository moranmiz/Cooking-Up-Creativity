# Cooking Up Creativity: Enhancing LLM Creativity through Structured Recombination

This repository contains the code and data for [our paper](https://arxiv.org/abs/2504.20643) (accepted to TACL, presented at EMNLP'25).

Authors: **Moran Mizrahi**, **Chen Shani**, **Gabriel Stanovsky**, **Dan Jurafsky** and **Dafna Shahaf**. 
<br>
**The Hebrew University of Jerusalem** & **Stanford University**.

<br>

- [INSTALLATION](#installation)
- [CODE](#code)
  - [Code Structure and Execution](#code-structure-and-execution)
  - [Fine-Tuned SBERT Model on Recipes](#fine-tuned-sbert-model-on-recipes)
  - [Sampling Ideas](#sampling-ideas) (Step I)
  - [Text to Tree](#text-to-tree) (Step II)
  - [Generate Ideas](#generate-ideas) (Step III)
  - [Evaluate Ideas](#evaluate-ideas) (Step IV)
  - [Tree to Text](#tree-to-text) (Step V)
- [DATA](#data)
  - [DishCOVER Dataset](#dishcover-dataset)
  - [Other Data Files](#other-data-files)
- [CITATION](#citation)

<br>

## INSTALLATION
1. Download the repository (or clone it)
2. Install dependencies:
```pip install -r requirements.txt```


## CODE

### Code Structure and Execution

This project utilizes a Sentence-BERT (SBERT) model fine-tuned specifically on culinary recipes.

The project pipeline is composed of several **modular components**:

* Each component can be executed **independently** for experimentation.  
* Each component includes a small `main` section with a simple usage example.  

### Fine-Tuned SBERT Model on Recipes

Our initial experiments with the standard sentence-level Sentence-BERT (SBERT) model revealed that it tends to group recipes based mainly on **textual instructions**, while overlooking **ingredients**. To better capture recipe similarity, we fine-tuned a Sentence-BERT model on recipes. 

**Usage:**

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('moranmiz/recipe-sbert-model')
```

### Sampling Ideas 

We sampled 30 recipes for each of the 100 most popular dishes in the [Recipe1M+ dataset](https://pic2recipe.csail.mit.edu/), yielding a total of 3,000 recipes. 

For each dish, to balance representativeness and diversity, we sampled 15 recipes **at random** (to capture typical variants of the dish) and 15 recipes that **maximize diversity** (using a greedy farthest-point algorithm over recipe embeddings produced by our fine-tuned SBERT model).

The folder `src/sampling` contains the sampling code (`sampled_recipes.py`) and the resulting set of 3K sampled recipes used in the paper (`sampled_recipes.json`).


### Text to Tree 

To translate recipe text into a tree representation, we first use an LLM to parse the ingredients and simplify the instructions, and then leverage the LLM’s coding capabilities to generate a directed tree in DOT, a standard graph description language.

The folder `src/text_to_tree` contains the code for translating recipes into trees (`translate_to_tree.py`). 
This folder also includes a compressed JSON file with the translations for all 3K sampled recipes (`sampled_recipes_parsed.zip`). 
Each entry in this JSON file follows this structure: 

```json
"817274": {
  "title": "Low-Fat Bruschetta",
  "ingredient_list": ["14 cup dry-pack sun-dried tomato", ...],
  "instruction_list": ["Place the sun-dried tomatoes in a...", ...]
  "parsed_ingredients": {
    "sun-dried tomato": {
      "ref": "taste",
      "core": false,
      "abstr": "tomato"
    },
      ...
  }
  "parsed_instructions": "Soften tomatoes in boiling water. Drain. Pat dry...",
  "tree_dot_code": "digraph bruschetta_817274 {...}",
  "tree_dict": {...},
  "is_tree": true
}
```
Where: 
* `title`: the recipe title
* `ingredient_list`: the recipe ingredient list
* `instruction_list`: the recipe instruction list
* `parsed_ingredients`: a dictionary whose keys are ingredient names and whose values specify: (1) whether the ingredient contributes to the dish’s structure (e.g., lasagna sheets in lasagna) or flavor (e.g., lemon in lemon pie) (`ref`), (2) whether the ingredient is a core ingredient of the dish (`core`), and (3) a simplified abstraction of the ingredient (e.g., “basil” → herb, “walnut” → nut) (`abstr`).
* `parsed_instructions`: the parsed instructions
* `tree_dot_code`: the tree in DOT format
* `tree_dict`: the tree as a dictionary (used later for recombination)
* `is_tree`: a boolean flag indicating whether the generated code is a valid tree.

#### Tree representation (`tree_dict`)

Recipes are represented as directed trees encoded in a dictionary called `tree_dict`.
Each entry corresponds to a single node in the tree, identified by a unique key.
Nodes are of two types: **ingredient nodes** (`type: "ingredient`) or **action nodes** (`type: "action`). 
Each node stores both semantic and structural information needed for later recombination.

In this example _italian bread_ is an ingredient node, marked as a _core_ ingredient that contributes to the structure of the dish via `extra_info`, with an abstract category of _bread_ (`abstr`). The node _toast_ is an action node that operates on it (`"children": ["italian_bread"]`).

```json
"tree_dict": {
  "italian_bread": {
    "label": "italian bread",
    "root": false,
    "type": "ingredient",
    "abstr": "bread",
    "extra_info": ["structure", "core"],
    "parent": "i1",
    "children": []
  },
  …
  "i1": {
    "label": "toast",
    "root": false,
    "type": "action",
    "abstr": "heat",
    "parent": "i2",
    "children": ["italian_bread"]
  },
  …
}
```

#### Tree visualization
Below is an example visualization of a single recipe’s tree DOT code (bruschetta):​

<img width="1337" height="907" alt="bruschetta_217157" src="https://github.com/user-attachments/assets/a580710e-7d98-4bc9-a570-e80d7d1cd20d" />

Leaf nodes correspond to ingredients (boxed nodes), and internal nodes represent the actions performed on them (circular nodes). For each ingredient, the label shows its name (black), its abstraction (purple), whether it is a core ingredient (blue), and whether it contributes to the dish structure (pink). For each action node, the label shows the cooking verb and its category (e.g., “heat” for “bake” or “toast”, in green).

To visualize a tree from DOT code, use Graphviz:
```python
import graphviz

graph = graphviz.Source(dot_code)
graph.render(filename=file_name, directory=file_path, format='png', cleanup=True)
```

### Generate Ideas 
To generate new recipe ideas, we **recombine existing recipe trees** using a tree edit-distance framework. Specifically, we apply the **Zhang–Shasha tree edit-distance algorithm** and extract **intermediate representations** that arise during the transformation between two recipe trees. Rather than using only the final transformed tree, we focus on trees that appear **midway through the edit sequence**, which combine structural and semantic elements from both source recipes.

The folder `src/generate_ideas` contains the code for generating novel recipe trees (`tree_edit_distance.py`) for given pairs of dishes. For each pair of dishes (e.g., _chocolate pie_ and _lasagna_), the function `combine_two_dishes` retrieves the trees of the sampled recipes for each dish, computes tree edit-distance transformations between all recipe pairs, and generates multiple intermediate trees by shuffling edit operations and stopping at different points along the transformation process. This results in multiple structurally distinct recombinations for each recipe pair.

The output of this step is a JSON file containing all generated tree ideas, structured as follows:
```json
"chocolate_pie_to_lasagna": {
	"chocolate_pie_580232_to_lasagna_51349_v1": {
		"tree_dict" : {...}
		"tree_dot_code": "digraph G {...}"
  }
}
```
Where:
* The top-level key corresponds to a pair of source dishes
* Each inner key represents a specific recombination instance
* `tree_dict` is the dictionary representation of the generated tree 
* `tree_dot_code` is the DOT code that represents the generated tree

### Evaluate Ideas 
To evaluate the generated idea candidates, we enforce **value** (taste coherence) as a constraint, then rank the remaining candidates by **novelty** (surprise) and **keep the top ideas**.
The folder `src/evaluate_ideas` contains the evaluation code (`pick_best_ideas.py`). Specifically, `evaluate_taste.py` computes ingredient pairing / test-coherence signals, and `compute_novelty.py` computes an IDF-style novelty score over idea elements (ingredients + actions). 

### Tree to Text 
Finally, we translate the top tree ideas into natural-language recipes using an LLM. We note that the LLM plays a key role in _surface realization_. Specifically, it draws on commonsense and somain knowledge to fill in missing details (e.g., ingredient quantities, cooking times), and correct inconsistencies introduced during recombination (e.g., restoring a missing step for cooking raw chicken). 
The file `src/tree_to_text/translate_tree_to_recipes.py` contains the code for translating recipe tree ideas into coherent recipes.


## DATA 

### DishCOVER Dataset
The `data/` folder contains a zipped directory named `DishCOVER_dataset`, which includes the DishCOVER dataset: ~5K recipes generated using our algorithm, formatted as JSON.
This zipped folder contains two files:
* `DishCOVER_dataset_core.json` – includes only the essential information for each generated recipe
* `DishCOVER_dataset_extended.json` - includes additional fields that may be useful for deeper analysis


Each entry in the core dataset follows this structure:

```json
"4": {
  "dish_pair": "apple_cake_to_banana_bread",
  "full_recipe_text": "Title: Caramel Banana Spice Cake\n\n Ingredients: ...\n\n Instructions: ...",
  "recipe_summary": "Caramel Banana Spice Cake is a decadent dessert featuring layers of banana bread, spiced cake, and rich caramel flavors...",
  "recipe_novelty_score": 77.439,
  "picked_1st_exp": false, 
  "picked_2nd_exp": false
}
```
Each key corresponds to the index of a recipe.
* `dish_pair`: the pair of source dishes (e.g., apple cake and banana bread)
* `full_recipe_text`: the complete generated recipe (title, ingredients, instructions)
* `recipe_summary`: a short summary of the recipe generated by the LLM
* `recipe_novelty_score`: the novelty score of the recipe elements (ingredients and actions), computed as described in the paper
* `picked_1st_exp` / `picked_2nd_exp`: booleans indicating whether this recipe was sampled for either of the evaluation experiments


Each entry in the extended dataset includes all core fields, plus additional information:

```json
"4": {
  "dish_pair": "apple_cake_to_banana_bread",
  "recipe_A": "apple_cake_545366",
  "recipe_B": "banana_bread_23078",
  "tree_dot_code": "digraph G {...} ",
  "tree_novelty_score": 63.357,
  "recipe_title": "Caramel Banana Spice Cake",
  "recipe_ingredients": ["1 loaf banana bread, sliced", "1/2 cup brown sugar", ...],
  "recipe_instructions": ["In a small saucepan, heat the brown sugar over low heat until it is warm...", "Arrange the sliced banana bread...", ...],
  "full_recipe_text": "Title: Caramel Banana Spice Cake\n\n Ingredients: ...\n\n Instructions: ...",
  "recipe_summary": "Caramel Banana Spice Cake is a decadent dessert featuring layers of banana bread, spiced cake, and rich caramel flavors...",
  "recipe_element_novelty_score": [["mascarpone", 7.121], ["distribute", 5.764], ...],
  "recipe_novelty_score": 77.439,
  "picked_1st_exp": false, 
  "picked_2nd_exp": false
}
```
In addition to the core fields:
* `recipe_A` / `recipe_B`: IDs of the original recipes that were recombined
* `tree_dot_code`: DOT-format graph representing the recombined recipe tree 
* `tree_novelty_score`: novelty score of the recombined tree
* `recipe_title` / `recipe_ingredients` / `recipe_instructions`: extracted recipe fields for convenience
* `recipe_element_novelty_score`: a sorted list of the elements (ingredients and actions) that contributed most to the recipe’s novelty score

Note that the tree novelty score and the recipe novelty score may differ (as during the translation from the recombined tree into natural-language recipe, the LLM fills in missing details and corrects inconsistencies, which can introduce or remove elements and thus change the final novelty score).



### Other Data Files

The `data/` folder also includes the prompt variations curated for both experiments:
* `prompt_variations_1st_exp.csv`
* `prompt_variations_2nd_exp.csv`

These files list all prompt variants used in our experiments. As described in the paper, culinary experts evaluated the recipes generated by GPT-4o using these variants. Their assessments determined the best-performing prompts, which were then used for the final GPT-4o prompting.

Additionally, the folder includes a zipped directory named `exp_recipes/`, containing all recipes used to evaluate our model against GPT-4o.



## CITATION

To acknowledge this work, please use the following citation:
```
@article{mizrahi2025cooking,
  title={Cooking Up Creativity: Enhancing LLM Creativity through Structured Recombination},
  author={Mizrahi, Moran and Shani, Chen and Stanovsky, Gabriel and Jurafsky, Dan and Shahaf, Dafna},
  journal={arXiv preprint arXiv:2504.20643},
  year={2025}
}
```


<br>

![image](https://github.com/user-attachments/assets/0a635e88-a53d-47e3-a292-18d25909f7fc)

<br>


