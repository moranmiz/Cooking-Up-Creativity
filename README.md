# Cooking Up Creativity: Enhancing LLM Creativity through Structured Recombination

This repository contains the code and data for [our paper](https://arxiv.org/abs/2504.20643) (TACL'25, presented at EMNLP'25).

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
  - [Run Full Pipeline](#run-full-pipeline)
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
* A separate script (`run_all.py`) is provided to run the full pipeline **end-to-end**.

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

#### Example tree
Below is an example visualization of a single recipe’s tree DOT code:​

<img width="1337" height="907" alt="bruschetta_217157" src="https://github.com/user-attachments/assets/a580710e-7d98-4bc9-a570-e80d7d1cd20d" />

Leaf nodes correspond to ingredients (boxed nodes), and internal nodes represent the actions performed on them (circular nodes). For each ingredient, the label shows its name (black), its abstraction (purple), whether it is a core ingredient (blue), and whether it contributes to the dish structure (pink). For each action node, the label shows the cooking verb and its category (e.g., “heat” for “bake” or “toast”, in green).

### Generate Ideas 
[TBD] 

### Evaluate Ideas 
[TBD] 

### Tree to Text 
[TBD] 

### Run Full Pipeline
[TBD]

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


