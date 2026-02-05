import copy
import random
import re
from zss import distance, Node
import json

from cooking_up_creativity.src.constants import INGR_ABSTR_COLOR, INGR_STRUCTURE_COLOR, INGR_CORE_COLOR, \
    ACTION_ABSTR_COLOR, INFTY, UPDATE, MATCH, REMOVE, INSERT


with open("../resources/cooking_verbs_to_categories.json", "r") as f:
    cooking_verbs_to_categories = json.load(f)


def get_tree_dict_root(tree_dict: dict) -> dict:
    """
    Returns the root node name of the given tree.

    :param tree_dict: a dictionary that represents a tree
    :return: the root node name
    """

    root = None
    for item in tree_dict:
        if tree_dict[item]["root"]:
            root = item
            return root

    return root


def get_tree_dict_nodes_with_no_parents(tree_dict: dict) -> list:
    """
    Returns a list of node names that have no parent in the given tree.

    :param tree_dict: a dictionary that represents a tree
    :return: a list of node names with no parent
    """

    no_parent = []
    for item in tree_dict:
        if not tree_dict[item]["parent"]:
            no_parent += [item]

    return no_parent


def add_zss_subtrees_to_tree_dict(tree_dict: dict, verbs_to_categories: dict, node_name: str):
    """
    Recursively adds subtrees to the tree_dict in zss Node format.

    :param tree_dict: the tree dictionary
    :param verbs_to_categories: a dictionary mapping verbs to their categories
    :param node_name: the current node name
    :return: None. The tree_dict is modified in place to include the subtree.
    """

    node_type = tree_dict[node_name]["type"]
    original_label = tree_dict[node_name]["label"]
    label = original_label + "_" + node_type

    if node_type == "action":

        # remove digits from the original_label:
        verb = ''.join([i for i in original_label if not i.isdigit()])
        if verb in verbs_to_categories:
            label += "_" + '/'.join(verbs_to_categories[verb]["direct_category"]) + "_" + '/'.join(verbs_to_categories[verb]["general_category"])
        else:
            label += "_None_None"
    else:
        label += "_" + tree_dict[node_name]["abstr"]

    children = tree_dict[node_name]["children"]
    children_subtrees = []
    if not children:
        tree_dict[node_name]["subtree"] = Node(label, [])
    else:
        for child in children:
            add_zss_subtrees_to_tree_dict(tree_dict, verbs_to_categories, child)
            children_subtrees += [tree_dict[child]["subtree"]]
        tree_dict[node_name]["subtree"] = Node(label, children_subtrees)


def create_zss_tree_from_tree_dict(tree_dict: dict, verbs_to_categories: dict) -> Node:
    """
    Creates a zss tree from a given tree dictionary.

    :param tree_dict: the tree dictionary
    :param verbs_to_categories: a dictionary mapping verbs to their categories
    :return: a zss Node representing the tree
    """

    root = get_tree_dict_root(tree_dict)
    add_zss_subtrees_to_tree_dict(tree_dict, verbs_to_categories, root)

    tree_zss = tree_dict[root]["subtree"]

    # organize tree_dict: remove "subtree"
    for node in tree_dict:
        if "subtree" in tree_dict[node]:
            tree_dict[node].pop("subtree")

    return tree_zss


def print_zss_tree(tree: Node, num_of_tabs: int = 0, out_file: "TextIO" = None):
    """
    A recursive method that given a tree in a zss Node format prints the tree.

    :param tree: the zss tree root node
    :param num_of_tabs: number of tabs for indentation
    :param out_file: file object to write the output to (if None, prints to console)
    """

    if tree:
        label = Node.get_label(tree)
        children = Node.get_children(tree)
        if out_file:
            out_file.write(num_of_tabs * "\t" + label + "\n")
        else:
            print(num_of_tabs*"\t" + label)
        for c in children:
            print_zss_tree(c, num_of_tabs=num_of_tabs+1, out_file=out_file)
    else:
        if out_file:
            out_file.write("empty tree\n")
        else:
            print("empty tree")


def print_tree_dict(tree_dict: dict, root_node: str = None, num_of_tabs: int = 0, out_file: "TextIO" = None,
                    print_labels: bool = True):
    """
    A recursive method that given a tree in a tree_dict format and a node name and prints the subtree
    rooted at that node.

    :param tree_dict: the tree dictionary
    :param root_node: the current root node name
    :param num_of_tabs: the number of tabs for indentation
    :param out_file: the file object to write the output to (if None, prints to console)
    :param print_labels: a boolean indicating whether to print node labels or node names
    """

    if not tree_dict:
        if out_file:
            out_file.write("empty\n")
        else:
            print("empty")
        return
    if not root_node:
        root_nodes = get_tree_dict_nodes_with_no_parents(tree_dict)
        for r in root_nodes:
            print_tree_dict(tree_dict, root_node=r, out_file=out_file, print_labels=print_labels)
    else:
        label = tree_dict[root_node]["label"]
        if not print_labels:
            label = root_node
        children = tree_dict[root_node]["children"]
        if out_file:
            out_file.write(num_of_tabs * "\t" + label + "\n")
        else:
            print(num_of_tabs*"\t" + label)
        for c in children:
            print_tree_dict(tree_dict, root_node=c, num_of_tabs=num_of_tabs+1, out_file=out_file, print_labels=print_labels)


def get_zss_tree_size(tree: Node) -> int:
    """
    A recursive method that given a tree in a zss Node format returns the size of the tree.

    :param tree: the zss tree root node
    :return: the size of the tree
    """
    if not tree:
        return 0
    else:
        size = 1
        children = Node.get_children(tree)
        for c in children:
            size += get_zss_tree_size(c)
        return size


def get_tree_dict_size(tree_dict: dict, node_name: str) -> int:
    """
    A recursive method that given a tree in a tree_dict format and a node name returns the size of the
    subtree rooted at that node.

    :param tree_dict: the tree dictionary
    :param node_name: the given node name
    :return: the size of the subtree rooted at the given node
    """

    if not tree_dict[node_name]["children"]:
        return 1
    else:
        size = 1
        for c in tree_dict[node_name]["children"]:
            size += get_tree_dict_size(tree_dict, c)
        return size


def get_formatted_node_label(tree_dict: dict, node_name: str) -> str:
    """
    Returns the label of the given node in the tree_dict, formatted with type (ingredient or action)
    as well as abstraction (for ingredients) or verb categories (for actions).

    Example label for ingredient: "pecans_ingredient_nut"
    Example label for action: "press_action_Modifying shape_Modification"

    :param tree_dict: the tree dictionary
    :param node_name: the given node name
    :return: the formatted label of the node
    """

    type = tree_dict[node_name]["type"]
    original_label = tree_dict[node_name]["label"]
    label = original_label + "_" + type
    # remove digits from label:
    if type == "action":
        verb = ''.join([i for i in original_label if not i.isdigit()])
        if verb in cooking_verbs_to_categories:
            label += "_" + '/'.join(cooking_verbs_to_categories[verb]["direct_category"]) + "_" + '/'.join(cooking_verbs_to_categories[verb]["general_category"])
        else:
            label += "_None_None"
    else:
        label += "_" + tree_dict[node_name]["abstr"]

    return label


def get_tree_dict_node_name(tree_dict: dict, zss_node: Node, match: list = None) -> str:
    """
    Given a zss node with a formatted label, returns the name of the node in tree_dict that matches the zss node.

    :param tree_dict: the tree dictionary
    :param zss_node: the zss node
    :param match: an optional list of node names to consider for matching
    :return: the name of the matching node in tree_dict, or None if no match is found
    """

    node_label = Node.get_label(zss_node)
    node_children = Node.get_children(zss_node)
    children_labels = sorted([Node.get_label(c) for c in node_children])
    for node in tree_dict:
        tree_children_labels = [get_formatted_node_label(tree_dict, c) for c in tree_dict[node]["children"]]
        tree_children_not_in_children_labels = [c for c in tree_children_labels if c not in children_labels]
        if get_formatted_node_label(tree_dict, node).strip() == node_label.strip() and len(tree_children_not_in_children_labels) == 0 and (not match or node in match):
            return node
    return None


def add_node_to_tree_dict(tree_dict: dict, node_name: str, label: str, parent: str, children: list, is_root: bool) -> dict:
    """
    Adds a node to the tree_dict with the given properties.

    :param tree_dict: the tree dictionary
    :param node_name: the name of the node to add
    :param label: the label of the node to add
    :param parent: the parent of the node to add
    :param children: the children of the node to add
    :param is_root: a boolean indicating whether the node is a root
    :return: the updated tree dictionary
    """

    tree_dict[node_name] = {}
    tree_dict[node_name]["label"] = label.split("_")[0]
    tree_dict[node_name]["root"] = is_root
    tree_dict[node_name]["type"] = label.split("_")[1]
    tree_dict[node_name]["abstr"] = label.split("_")[2]
    tree_dict[node_name]["parent"] = parent
    tree_dict[node_name]["children"] = children

    return tree_dict


def insert_node_to_tree_dict_recursively(zss_node: Node, parent_node_name: str, parent_label: str,
                                         tree_dict1: dict, tree_dict2: dict, match_nodes: dict,
                                         operation_list: list, out_file: "TextIO" = None):
    """
    Recursively inserts nodes from the zss subtree rooted at zss_node into tree_dict1 as a child of
    parent_node_name.

    :param zss_node: the zss subtree root node to insert
    :param parent_node_name: the name of the designated parent node in tree_dict1
    :param parent_label: the label of the designated parent node
    :param tree_dict1: the target tree dictionary to insert nodes into
    :param tree_dict2: the source tree dictionary from which nodes are taken
    :param match_nodes: a dictionary to keep track of matched nodes
    :param operation_list: a list to record the operations performed
    :param out_file: file object to write the output for debugging
    :return: None. The tree_dict1 is modified in place to include the inserted nodes.
    """

    node_name = get_tree_dict_node_name(tree_dict2, zss_node)

    if node_name not in tree_dict1:
        match_nodes[node_name] = node_name
        tree_dict1[node_name] = {}
        tree_dict1[node_name]["parent"] = parent_node_name
        node_label = Node.get_label(zss_node)
        tree_dict1[node_name]["label"] = node_label.split("_")[0]
        tree_dict1[node_name]["type"] = node_label.split("_")[1]
        tree_dict1[node_name]["abstr"] = node_label.split("_")[2]
        tree_dict1[node_name]["root"] = False
        tree_dict1[node_name]["children"] = []
        operation_list += ["insert " + node_name + " child of " + parent_node_name]
        if out_file:
            out_file.write("insert " + node_name + " as child of " + parent_node_name + "... \n")
            out_file.write("insert " + node_label + " as child of " + parent_label + "... \n")
            out_file.write("parent: " + parent_node_name + "\n")
            out_file.write("parent children: " + str(tree_dict1[parent_node_name]["children"]) + "\n")
        parent_children = tree_dict1[parent_node_name]["children"] + [node_name]
        parent_children_with_labels = [(child, tree_dict1[child]["label"]) for child in parent_children]
        parent_children_sorted = [child[0] for child in sorted(parent_children_with_labels, key=lambda x: x[1])]
        tree_dict1[parent_node_name]["children"] = parent_children_sorted
        if out_file:
            print_tree_dict(tree_dict1, out_file=out_file)

        for c in Node.get_children(zss_node):
            insert_node_to_tree_dict_recursively(c, node_name, node_label, tree_dict1, tree_dict2, match_nodes, operation_list, out_file=out_file)


def modify_parent_to_orphan_node(parent_node_name: str, orphan_node_name: str, tree_dict: dict):
    """
    Modifies the tree_dict by adding an orphan_node_name as a child of parent_node_name and sorting the children
    lexically by their labels (assumption: orphan_node_name is already in tree_dict).

    :param parent_node_name: the name of the parent node
    :param orphan_node_name: the name of the orphan node to be added as a child to parent node
    :param tree_dict: the tree dictionary
    :return: None. The tree_dict is modified in place to include the orphan node as a child of the parent node.
    """

    parent_children = tree_dict[parent_node_name]["children"]
    parent_children += [orphan_node_name]
    children_with_labels = [(c, tree_dict[c]["label"]) for c in parent_children]
    children_sorted = [c[0] for c in sorted(children_with_labels, key=lambda x: x[1])]
    tree_dict[parent_node_name]["children"] = children_sorted


def get_all_zss_children_recursively(zss_node: Node, all_children: list = None, out_file: "TextIO" = None) -> list:
    """
    A recursive method that given a zss node returns all its children (and their children, etc.) as a list.

    :param zss_node: the zss node
    :param all_children: list of all children collected so far
    :param out_file: file object to write the output for debugging
    :return: a list of all children nodes (tuples of (label, zss node object))
    """

    if not zss_node:
        return None
    if all_children is None:
        all_children = []
    cur_children = [(Node.get_label(c), c) for c in Node.get_children(zss_node)]
    for child in cur_children:
        get_all_zss_children_recursively(child[1], all_children=all_children, out_file=out_file)
    all_children += cur_children
    return all_children


def remove_node_from_tree_dict(node_name: str, node_label: str, tree_dict: dict, operation_list: list, out_file: "TextIO" = None):
    """
    Removes a given node from tree_dict, updating its parent's children and its children's parent accordingly.

    :param node_name: the given node name
    :param node_label: the given node label
    :param tree_dict: the tree dictionary
    :param operation_list: a list to record the operations performed
    :param out_file: a file object to write the output for debugging
    :return: None. The tree_dict is modified in place to remove the specified node.
    """

    if not node_name:
        return
    operation_list += ["remove " + node_name]
    if out_file:
        out_file.write("remove " + node_name + "...\n")
        out_file.write("remove " + node_label.split("_")[0] + "...\n")
    if node_name in tree_dict:
        parent_name = tree_dict[node_name]["parent"]
        if parent_name:
            parent_children = tree_dict[parent_name]["children"]
            parent_children.remove(node_name)  # remove the node from the parent's children
            for c in tree_dict[node_name]["children"]:  # add the children of the node to the parent's children
                parent_children += [c]
            children_with_labels = [(c, tree_dict[c]["label"]) for c in parent_children]
            children_sorted = [c[0] for c in sorted(children_with_labels, key=lambda x: x[1])]
            tree_dict[parent_name]["children"] = children_sorted
        for c in tree_dict[node_name]["children"]:  # update the parent of the children
            tree_dict[c]["parent"] = parent_name
        del tree_dict[node_name]


def remove_children_from_tree_dict_recursively(zss_node1: Node, zss_node2: Node, tree_dict1: dict, tree_dict2: dict,
                                               new_tree_dict: dict, match: list, operation_list: list,
                                               out_file: "TextIO" = None):
    """
    A recursive method that given two zss nodes (from T1 and T2 respectively) removes from new_tree
    all the children of zss_node1 that are not present in zss_node2.
    
    :param zss_node1: zss node from T1
    :param zss_node2: zss node from T2
    :param tree_dict1: tree dictionary for T1
    :param tree_dict2: tree dictionary for T2
    :param new_tree_dict: the new tree dictionary to modify
    :param match: a list of matched node names between T1 and T2
    :param operation_list: the list of operations performed so far
    :param out_file: file object to write the output for debugging
    :return: None. The new_tree_dict is modified in place to remove the specified nodes.
    """

    children1 = get_all_zss_children_recursively(zss_node1, out_file=out_file)
    if out_file:
        print_zss_tree(zss_node1, out_file=out_file)
    children1_new = [(get_tree_dict_node_name(tree_dict1, c[1]), c[0], c[1]) for c in children1]

    children2 = get_all_zss_children_recursively(zss_node2, out_file=out_file)

    children1_labels = [c[0] for c in children1]
    children2_labels = [] if not children2 else [c[0] for c in children2]
    if out_file:
        out_file.write("children1_labels: " + str(children1_labels) + "\n")
        out_file.write("children2_labels: " + str(children2_labels) + "\n")

    node_names_to_remove = []
    for item in children1_new:
        nn = item[0]
        if nn in match:
            continue
        node_names_to_remove += [(nn, item[1])]
    node_names_to_remove = [nn for nn in node_names_to_remove if nn[0] in new_tree_dict]

    for nn in node_names_to_remove:
        remove_node_from_tree_dict(nn[0], nn[1], new_tree_dict, operation_list, out_file=out_file)
        if out_file:
            print_tree_dict(new_tree_dict, out_file=out_file)


def concretize_tree_edit_operations(tree_dict1: dict, tree_dict2: dict, operations: list, out_file: "TextIO" = None) -> list:
    """
    The input for this method is the high-level tree edit operations to transform T1 into T2 using the Zhang-Shasha
    tree edit distance algorithm (Insert / Remove / Match / Update).

    Problem: ZSS operations omit intermediates / implied structural changes, and are too abstract to be interpreted
    as concrete editing steps.

    Output: A concrete, ordered list of atomic edit actions, each: (1) grounded in specific nodes; (2) explicit about
    parent-child relations; (3) executable / interpretable at the tree level.

    :param tree_dict1: tree dictionary for T1
    :param tree_dict2: tree dictionary for T2
    :param operations: the list of edit operations to apply obtained from the ZSS tree edit distance algorithm
    :param out_file: file object to write the intermediate trees after each edit operation for debugging
    :return: a list of concrete edit operations to perform to transform T1 into T2
    """

    new_tree = copy.deepcopy(tree_dict1)
    out_operations = []
    if out_file:
        print_tree_dict(new_tree, out_file=out_file)
    orphan_nodes = []
    match_nodes = {}

    for i in range(len(operations)):

        op = operations[i]

        if out_file:
            out_file.write("=====================================\n")
            out_file.write(str(op) + "\n")

        if op.type == INSERT:
            noi = op.arg2  # node of interest
            noi_name = get_tree_dict_node_name(tree_dict2, noi)

            if Node.get_children(noi):
                # check whether the children of noi are already in the new_tree:
                existing_children = [get_tree_dict_node_name(new_tree, c, match_nodes) for c in Node.get_children(noi) if get_tree_dict_node_name(new_tree, c, match_nodes) is not None]
                children_with_labels = [(c, new_tree[c]["label"]) for c in existing_children]
                existing_children = [c[0] for c in sorted(children_with_labels, key=lambda x: x[1]) if c[0] in match_nodes]
                if out_file:
                    out_file.write("match nodes: " + str(match_nodes) + "\n")
                    out_file.write(str([c for c in Node.get_children(noi)]) + "\n")

                non_existing_children = [c for c in Node.get_children(noi) if get_tree_dict_node_name(new_tree, c) not in existing_children]  # get_node_name(new_tree, c) is None]

                if existing_children:
                    noi_parent = None
                    noi_is_root = False
                    for c in existing_children:
                        if not noi_parent:
                            noi_parent = new_tree[c]["parent"]
                        if new_tree[c]["root"]:
                            noi_is_root = True
                            new_tree[c]["root"] = False
                        new_tree[c]["parent"] = noi_name
                        orphan_nodes = [o for o in orphan_nodes if o != c]

                    out_operations += ["insert " + noi_name + " father of " + ','.join(existing_children)]

                    if out_file:
                        out_file.write("insert " + noi_name + " as father of " + ','.join(existing_children) + "...\n")
                        out_file.write("insert " + Node.get_label(noi).split("_")[0] + " as father of " + ','.join(sorted([Node.get_label(c).split("_")[0] for c in Node.get_children(noi)])) + "...\n")

                    new_tree = add_node_to_tree_dict(new_tree, noi_name, Node.get_label(noi), noi_parent, existing_children, noi_is_root)
                    match_nodes[noi_name] = noi_name

                    if noi_parent:
                        noi_parent_children = new_tree[noi_parent]["children"]
                        for c in existing_children:
                            if c in noi_parent_children:
                                noi_parent_children.remove(c)
                        noi_parent_children += [noi_name]
                        children_with_labels = [(child, new_tree[child]["label"]) for child in noi_parent_children]
                        children_sorted = [child[0] for child in sorted(children_with_labels, key=lambda x: x[1])]
                        new_tree[noi_parent]["children"] = children_sorted

                    else:
                        new_tree[noi_name]["root"] = True
                        orphan_nodes += [noi_name]

                    if out_file:
                        print_tree_dict(new_tree, out_file=out_file)

                if non_existing_children:  # there are children that are not in the tree - insert all the children of noi

                    if not existing_children:

                        new_tree = add_node_to_tree_dict(new_tree, noi_name, Node.get_label(noi), None, [], False)
                        match_nodes[noi_name] = noi_name
                        orphan_nodes.append(noi_name)
                        out_operations += ["insert " + noi_name]

                        if out_file:
                            out_file.write("insert " + noi_name + " as leaf...\n")
                            out_file.write("insert " + Node.get_label(noi).split("_")[0] + " as leaf...\n")
                            print_tree_dict(new_tree, out_file=out_file)

                    for c in non_existing_children:
                        insert_node_to_tree_dict_recursively(c, noi_name, Node.get_label(noi), new_tree, tree_dict2, match_nodes, out_operations, out_file=out_file)

                    children = new_tree[noi_name]["children"]
                    children_with_labels = [(c, new_tree[c]["label"]) for c in children]  # node name, label
                    children_sorted = [c[0] for c in sorted(children_with_labels, key=lambda x: x[1])]
                    new_tree[noi_name]["children"] = children_sorted

            else:

                # insert as a leaf:
                new_tree = add_node_to_tree_dict(new_tree, noi_name, Node.get_label(noi), None, [], False)
                match_nodes[noi_name] = noi_name
                orphan_nodes.append(noi_name)
                out_operations += ["insert " + noi_name]

                if out_file:
                    out_file.write("insert " + noi_name + " as leaf...\n")
                    out_file.write("insert " + Node.get_label(noi).split("_")[0] + " as leaf...\n")
                    print_tree_dict(new_tree, out_file=out_file)

        elif op.type == REMOVE:

            noi = op.arg1
            noi_name = get_tree_dict_node_name(tree_dict1, noi)
            remove_children_from_tree_dict_recursively(op.arg1, op.arg2, tree_dict1, tree_dict2, new_tree, match_nodes, out_operations, out_file=out_file)
            remove_node_from_tree_dict(noi_name, Node.get_label(noi), new_tree, out_operations, out_file=out_file)

            if out_file:
                print_tree_dict(new_tree, out_file=out_file)

        elif op.type == UPDATE:

            noi_name = get_tree_dict_node_name(tree_dict1, op.arg1)
            out_operations += ["update " + noi_name + " label to " + get_tree_dict_node_name(tree_dict2, op.arg2) + " label"]  # Node.get_label(op.arg2).split("_")[0]]

            if out_file:
                out_file.write("update " + noi_name + "'s label to " + Node.get_label(op.arg2).split("_")[0] + "...\n")
                out_file.write("update " + Node.get_label(op.arg1).split("_")[0] + " to " + Node.get_label(op.arg2).split("_")[0] + "...\n")

            new_label = Node.get_label(op.arg2)

            new_tree[noi_name]["label"] = new_label.split("_")[0]
            new_tree[noi_name]["type"] = new_label.split("_")[1]
            new_tree[noi_name]["abstr"] = new_label.split("_")[2]
            match_nodes[noi_name] = noi_name

            if out_file:
                print_tree_dict(new_tree, out_file=out_file)

        else:  # MATCH

            match_nodes[get_tree_dict_node_name(tree_dict1, op.arg1)] = get_tree_dict_node_name(tree_dict2, op.arg2)
            out_operations += ["match " + get_tree_dict_node_name(tree_dict1, op.arg1) + " to " + get_tree_dict_node_name(tree_dict2, op.arg2)]

            if out_file:
                out_file.write(get_tree_dict_node_name(tree_dict1, op.arg1) + " matches " + get_tree_dict_node_name(tree_dict2, op.arg2) + "\n")

            match_nodes[get_tree_dict_node_name(tree_dict1, op.arg1)] = get_tree_dict_node_name(tree_dict2, op.arg2)

            if out_file:
                out_file.write("match " + Node.get_label(op.arg1).split("_")[0] + " to " + Node.get_label(op.arg2).split("_")[0] + "...\n")
                out_file.write("match_nodes: " + str(match_nodes) + "\n")

        if op.type == UPDATE or op.type == MATCH:

            # check whether there are forgotten children to insert
            match_children = [Node.get_label(c).split("_")[0] for c in Node.get_children(op.arg2)]
            if out_file:
                out_file.write("match_children: " + str(match_children) + "\n")

            parent = get_tree_dict_node_name(new_tree, op.arg2)
            if not parent:
                parent = get_tree_dict_node_name(tree_dict1, op.arg1)

            if out_file:
                out_file.write("orphan_nodes: " + str(orphan_nodes) + "\n")

            delete_from_orphan = []

            for cur_orphan_name in orphan_nodes:

                cur_orphan_label = new_tree[cur_orphan_name]["label"]

                if cur_orphan_label in match_children:

                    out_operations += [cur_orphan_name + " child of " + parent]

                    if out_file:
                        out_file.write(cur_orphan_name + " is a child of " + parent + "...\n")
                        out_file.write(cur_orphan_label + " is a child of " + Node.get_label(op.arg2).split("_")[0] + "...\n")

                    new_tree[cur_orphan_name]["parent"] = parent
                    modify_parent_to_orphan_node(parent, cur_orphan_name, new_tree)
                    delete_from_orphan.append(cur_orphan_name)

                    if out_file:
                        print_tree_dict(new_tree, out_file=out_file)

            orphan_nodes = [o for o in orphan_nodes if o not in delete_from_orphan]

            # check whether there are more children of the op tree to insert
            new_tree_children_labels = [new_tree[n]["label"] for n in new_tree[parent]["children"]]
            for c in Node.get_children(op.arg2):
                if Node.get_label(c).split("_")[0] not in new_tree_children_labels:
                    insert_node_to_tree_dict_recursively(c, parent, Node.get_label(op.arg2), new_tree, tree_dict2, match_nodes, out_operations, out_file=out_file)

            t1_size = get_tree_dict_size(new_tree, get_tree_dict_node_name(tree_dict1, op.arg1))
            t2_size = get_zss_tree_size(op.arg2)

            if out_file:
                out_file.write("size of tree 1: " + str(t1_size) + "\n")
                out_file.write("size of tree 2: " + str(t2_size) + "\n")
            if t1_size > t2_size:
                # check whether there are forgotten children to remove
                if out_file:
                    out_file.write("remove children recursively...\n")
                remove_children_from_tree_dict_recursively(op.arg1, op.arg2, tree_dict1, tree_dict2, new_tree, match_nodes, out_operations, out_file=out_file)

        if out_file:
            out_file.write("=====================================\n")

    return out_operations


def update_node_children_in_tree_dict(tree_dict: dict, node_name: str, to_remove: list, to_add: list):
    """
    Updates the children of a given node in tree_dict by removing and adding specified children.

    :param tree_dict: the tree dictionary
    :param node_name: the given node name
    :param to_remove: a list of children to remove
    :param to_add: a list of children to add
    :return: None. The tree_dict is modified in place to update the children of the specified node.
    """

    if node_name:
        node_children = tree_dict[node_name]["children"]
        node_children = [c for c in node_children if c not in to_remove]
        node_children += to_add
        tree_dict[node_name]["children"] = sorted(node_children, key=lambda x: tree_dict[x]["label"])


def build_tracking_tree_dict_for_ops(all_operations: list, tree_dict1: dict, tree_dict2: dict) -> dict:
    """
    Builds a template (tracking) tree for applying a tree-edit operation sequence.

    Starting from T1 as a base, according to the given edit operations, this function inserts all T2 nodes (and links)
    that are needed in order to transform T1 into T2. The resulting template contains all the nodes from both T1 and T2
    and records each node's final parent.

    Knowing each node's final parent in advance allows insertions to be applied in arbitrary order (e.g., before
    the parent itself is inserted) without creating disconnected components. This will help us later to ensure
    every intermediate structure obtained when applying a shuffled operation sequence results in a single rooted tree
    (in contrast to a forest).

    :param all_operations: the list of all tree-edit operations
    :param tree_dict1: the tree dictionary for T1
    :param tree_dict2: the tree dictionary for T2
    :return: the template tree dictionary for the given edit operations
    """

    tracking_tree = copy.deepcopy(tree_dict1)

    for operation in all_operations:
        spltd = operation.split()
        node_name = spltd[1]

        if operation.startswith("insert"):
            node_label = tree_dict2[node_name]["label"]
            if len(spltd) == 2:  # insert node_name
                tracking_tree[node_name] = {"label": node_label, "children": [], "root": False, "parent": None, "marked": False,
                                            "type": tree_dict2[node_name]["type"], "abstr": tree_dict2[node_name]["abstr"]}
            else:  # insert node_name child / parent of children_names / parent_name
                if spltd[2] == "child":
                    parent_name = spltd[4]
                    tracking_tree[node_name] = {"label": node_label, "children": [], "root": False, "parent": parent_name, "marked": False,
                                                "type": tree_dict2[node_name]["type"], "abstr": tree_dict2[node_name]["abstr"]}
                    update_node_children_in_tree_dict(tracking_tree, parent_name, to_remove=[], to_add=[node_name])
                else:  # insert node_name father of children_names
                    children_names = spltd[4].split(',')
                    is_root = False
                    root_children = [cn for cn in children_names if tracking_tree[cn]["root"]]
                    if root_children:
                        tracking_tree[root_children[0]]["root"] = False
                        is_root = True
                    children_names = sorted(children_names, key=lambda x: tracking_tree[x]["label"])
                    parent = None
                    for cn in children_names:
                        if tracking_tree[cn]["parent"]:
                            parent = tracking_tree[cn]["parent"]
                        tracking_tree[cn]["parent"] = node_name

                    tracking_tree[node_name] = {"label": node_label, "children": children_names, "root": is_root, "parent": parent, "marked": False,
                                                "type": tree_dict2[node_name]["type"], "abstr": tree_dict2[node_name]["abstr"]}

                    update_node_children_in_tree_dict(tracking_tree, parent, to_remove=children_names, to_add=[node_name])

        elif operation.startswith("remove"):
            tracking_tree[node_name]["marked"] = True
        elif operation.startswith("update"):
            tracking_tree[node_name]["marked"] = True
            updated_node_name = spltd[4]
            tracking_tree[node_name]["label"] = tree_dict2[updated_node_name]["label"]
            tracking_tree[node_name]["type"] = tree_dict2[updated_node_name]["type"]
            tracking_tree[node_name]["abstr"] = tree_dict2[updated_node_name]["abstr"]
        elif operation.startswith("match"):
            tracking_tree[node_name]["marked"] = True
        else:  # node_name child of parent_name
            node_name = spltd[0]
            parent_name = spltd[3]
            tracking_tree[node_name]["parent"] = parent_name
            update_node_children_in_tree_dict(tracking_tree, parent_name, to_remove=[], to_add=[node_name])

    return tracking_tree


def get_nearest_marked_descendants_rec(tracking_tree: dict, node_name: str, marked_descendants: list) -> list:
    """
    A recursive method that returns the nearest marked descendants of a given node in the tracking tree.

    :param tracking_tree: the tracking tree dictionary
    :param node_name: the given node name
    :param marked_descendants: the list of marked descendants collected so far
    :return: a list of nearest marked descendants
    """

    children = tracking_tree[node_name]["children"]
    if not children:
        return []
    for child in children:
        if tracking_tree[child]["marked"]:
            marked_descendants += [child]
        else:
            marked_descendants += get_nearest_marked_descendants_rec(tracking_tree, child, marked_descendants)
    return list(set(marked_descendants))


def get_nearest_marked_descendants(tracking_tree: dict, node_name: str) -> list:
    """
    Returns the closest marked descendants of a node in the tracking tree.

    Marked nodes correspond to nodes that already exist in the current intermediate tree.
    When inserting a node whose descendants may not yet exist, these marked descendants
    indicate which existing nodes should be reparented under the inserted node.

    :param tracking_tree: the tracking tree dictionary
    :param node_name: the given node name
    :return: the list of nearest marked descendants
    """

    marked_children = get_nearest_marked_descendants_rec(tracking_tree, node_name, [])
    return sorted(marked_children, key=lambda x: tracking_tree[x]["label"])


def get_nearest_marked_ancestor(tracking_tree: dict, node_name: str) -> str:
    """
    Returns the closest marked ancestor of a node in the tracking tree.

    Marked nodes correspond to nodes that already exist in the current intermediate tree.
    When inserting a node whose parent may not yet exist, this marked ancestor
    indicates to which temporary parent the inserted node should be attached.

    :param tracking_tree: the tracking tree dictionary
    :param node_name: the given node name
    :return: the nearest marked ancestor node name, or None if there is no such ancestor
    """

    parent = tracking_tree[node_name]["parent"]
    if not parent:
        return None
    if tracking_tree[parent]["marked"]:
        return parent
    return get_nearest_marked_ancestor(tracking_tree, parent)


def get_concise_operations(all_operations: list) -> list:
    """
    Converts detailed operations into concise format.

    :param all_operations: the list of all detailed operations
    :return: a list of concise operations
    """

    concise_operations = []
    for operation in all_operations:
        spltd = operation.split()
        node_name = spltd[1]
        if operation.startswith("insert"):
            concise_operations += ["ADD " + node_name]
        elif operation.startswith("remove"):
            concise_operations += ["DEL " + node_name]
        elif operation.startswith("update"):
            new_label = spltd[4]
            concise_operations += ["UPDATE " + node_name + " " + new_label]

    return concise_operations


def handle_one_operation(intermediate_tree: dict, short_operation: str, tracking_tree: dict) -> tuple:
    """
    Applies a single edit to the current intermediate tree.
    Insertions are anchored using the tracking tree: the inserted node is attached using its nearest already-present
    ancestor, and it adopts its nearest already-present descendants as children.
    If the operation cannot be applied without ruining the tree structure (i.e., it results in a forest),
    it is postponed.

    :param intermediate_tree: the current intermediate tree dictionary
    :param short_operation: the short operation to apply
    :param tracking_tree: the tracking tree dictionary
    :return: a tuple containing: (postponed operation (if any), added node name (if any), removed node label (if any),
    list of removed edges (if any), updated node name (if any))
    """

    postponed = None
    added = None
    removed = None
    removed_edges = None
    updated = None

    spltd = short_operation.split()
    node_name = spltd[1]

    if spltd[0] == "ADD":
        added = node_name
        first_marked_children = get_nearest_marked_descendants(tracking_tree, node_name)
        first_marked_ancestor = get_nearest_marked_ancestor(tracking_tree, node_name)
        if first_marked_children or first_marked_ancestor:
            intermediate_tree[node_name] = {"label": tracking_tree[node_name]["label"], "children": [], "root": False,
                                        "parent": None, "type": tracking_tree[node_name]["type"], "abstr": tracking_tree[node_name]["abstr"]}
            if first_marked_children:
                intermediate_tree[node_name]["children"] = first_marked_children
                for child in first_marked_children:
                    if intermediate_tree[child]["root"]:
                        intermediate_tree[child]["root"] = False
                        intermediate_tree[node_name]["root"] = True
                    intermediate_tree[child]["parent"] = node_name
            if first_marked_ancestor:
                intermediate_tree[node_name]["parent"] = first_marked_ancestor
                update_node_children_in_tree_dict(intermediate_tree, first_marked_ancestor, to_remove=first_marked_children, to_add=[node_name])
            tracking_tree[node_name]["marked"] = True
        else:
            postponed = short_operation

    elif spltd[0] == "DEL":
        removed_edges = []
        parent = intermediate_tree[node_name]["parent"]
        children = intermediate_tree[node_name]["children"]
        if not parent and len(children) > 1:
            postponed = short_operation
        else:
            removed = intermediate_tree[node_name]["label"]
            if parent:
                update_node_children_in_tree_dict(intermediate_tree, parent, to_remove=[node_name], to_add=children)
            for child in children:
                intermediate_tree[child]["parent"] = parent
                if parent:
                    removed_edges += [(child, parent)]
                else:
                    intermediate_tree[child]["root"] = True
            del intermediate_tree[node_name]

            # remove also from tracking:
            parent_tracking = tracking_tree[node_name]["parent"]
            children_tracking = tracking_tree[node_name]["children"]
            if parent_tracking:
                update_node_children_in_tree_dict(tracking_tree, parent_tracking, to_remove=[node_name], to_add=children_tracking)
            for child in children_tracking:
                tracking_tree[child]["parent"] = parent_tracking
            del tracking_tree[node_name]

    else:  # UPDATE
        updated = node_name
        intermediate_tree[node_name]["label"] = tracking_tree[node_name]["label"]
        intermediate_tree[node_name]["abstr"] = tracking_tree[node_name]["abstr"]

    return postponed, added, removed, removed_edges, updated


def apply_tree_edits(tree_dict: dict, short_operations: list, tracking_tree: dict, stop_index: int) -> dict:
    """
    Applies a sequence of (possibly shuffled) short edit operations to a tree.
    Produces a valid rooted tree after every applied operation.
    Operations that cannot yet be applied are postponed and retried after each successful step.

    :param tree_dict: the initial tree dictionary
    :param short_operations: the list of short operations to apply
    :param tracking_tree: the tracking tree dictionary
    :param stop_index: applies operations up to this index
    :return: the resulting intermediate tree dictionary after applying the operations
    """

    intermediate_tree = copy.deepcopy(tree_dict)
    tracking_tree = copy.deepcopy(tracking_tree)
    postponed_operations = []

    short_operations = short_operations[:stop_index]

    for operation in short_operations:

        postponed = handle_one_operation(intermediate_tree, operation, tracking_tree)[0]

        if postponed:
            postponed_operations += [postponed]
        else:
            for po in postponed_operations:
                # try applying postponed operation:
                postponed = handle_one_operation(intermediate_tree, po, tracking_tree)[0]
                if not postponed:  # success in handling postponed operation
                    postponed_operations.remove(po)

    for node_name in intermediate_tree:
        intermediate_tree[node_name]["children"] = [c for c in intermediate_tree[node_name]["children"] if intermediate_tree[c]["parent"] == node_name]

    return intermediate_tree



def shuffle_operation_order(dish1_ingr_dict: dict, dish2_ingr_dict: dict, short_operations: list) -> list:
    """
    Shuffles the order of operations to generate new intermediate ideas.
    To produce more coherent results, we impose a partial order on the shuffled operations. Specifically,
    we prioritize inserting and updating key flavor ingredients from the target recipe (e.g., “lemon” in a lemon pie)
    so they appear earlier in the transformation, and delay deleting or updating structural ingredients from the
    source recipe (e.g., “lasagna sheets” in lasagna) to preserve its core structure.

    :param dish1_ingr_dict: the ingredient dictionary for dish 1
    :param dish2_ingr_dict: the ingredient dictionary for dish 2
    :param short_operations: the list of short operations
    :return: a reordered list of the short operations
    """

    ingr1_structure = [ingr for ingr in dish1_ingr_dict if dish1_ingr_dict[ingr]["ref"] == "structure"]
    ingr2_core = [ingr for ingr in dish2_ingr_dict if dish2_ingr_dict[ingr]["core"]]

    core_ingr_names = [re.sub(r'[^a-zA-Z\s]', '', item).replace(" ", "_") + "_b" for item in ingr2_core]
    structure_ingr_names = [re.sub(r'[^a-zA-Z\s]', '', item).replace(" ", "_") + "_a" for item in ingr1_structure]

    add_core_operations = [op for op in short_operations if op.split()[0] == "ADD" and op.split()[1].strip() in core_ingr_names]
    update_core_operations = [op for op in short_operations if op.split()[0] == "UPDATE" and op.split()[2].strip() in core_ingr_names]
    del_structure_operations = [op for op in short_operations if op.split()[0] == "DEL" and op.split()[1].strip() in structure_ingr_names]
    update_structure_operations = [op for op in short_operations if op.split()[0] == "UPDATE" and op.split()[1].strip() in structure_ingr_names]

    other_operations = [op for op in short_operations if op not in add_core_operations and op not in update_core_operations and op not in del_structure_operations and op not in update_structure_operations]
    random.shuffle(other_operations)

    short_operations_mixed = add_core_operations + update_core_operations + other_operations + del_structure_operations + update_structure_operations

    return short_operations_mixed


def handle_same_labels(tree_dict: dict) -> dict:
    """
    Handles same labels in the tree by appending a unique suffix to each duplicate label.

    :param tree_dict: the tree dictionary
    :return: the modified tree dictionary with unique labels
    """

    labels_to_node_names = {}
    for node_name in tree_dict:
        label = tree_dict[node_name]['label']
        if label not in labels_to_node_names:
            labels_to_node_names[label] = []
        labels_to_node_names[label] += [node_name]

    for label in labels_to_node_names:
        if len(labels_to_node_names[label]) > 1:
            node_names = labels_to_node_names[label]
            for i in range(len(node_names)):
                tree_dict[node_names[i]]['label'] = tree_dict[node_names[i]]['label'] + str(i+1)

    return tree_dict


def add_suffix_to_all_node_names(tree_dict: dict, suffix: str) -> dict:
    """
    Adds a suffix to all node names in the tree dictionary (this is useful for distinguishing nodes from different
    trees when combining them).

    :param tree_dict: the tree dictionary
    :param suffix: the suffix to add to each node name in the tree dictionary
    :return: the modified tree dictionary with updated node names
    """

    new_tree_dict = {}
    for node_name in tree_dict:
        new_tree_dict[node_name + "_" + suffix] = tree_dict[node_name]
        parent = tree_dict[node_name]['parent']
        if parent:
            new_tree_dict[node_name + "_" + suffix]['parent'] = parent + "_" + suffix
        children = tree_dict[node_name]['children']
        if children:
            new_children = [node_name + "_" + suffix for node_name in children]
            new_tree_dict[node_name + "_" + suffix]['children'] = new_children

    return new_tree_dict


def order_node_children_lexicographically(tree_dict: dict) -> dict:
    """
    Orders the children of each node in the tree dictionary lexicographically based on their labels.
    This is important for the Zhang-Shasha algorithm to work correctly as it assumes an ordered tree (otherwise
    computing tree edit distance is NP-hard). An ordered tree is a tree in which each set of siblings has a defined
    left-to-right order.

    :param tree_dict: the tree dictionary
    :return: the modified tree dictionary with lexicographically ordered children
    """

    for node_name in tree_dict:
        children = tree_dict[node_name]['children']
        children_with_labels = [(child, tree_dict[child]['label']) for child in children]
        if children:
            children_with_labels.sort(key=lambda x: x[1])
            tree_dict[node_name]['children'] = [child[0] for child in children_with_labels]
    return tree_dict


def prepare_tree_dict_for_recombination(tree_dict: dict, suffix: str) -> dict:
    """
    Prepares the tree dictionary for recombination by handling same labels, adding suffixes to node names for
    distinction between trees when combining them, and ordering children lexicographically for the Zhang-Shasha
    algorithm to work properly.

    :param tree_dict: the tree dictionary
    :param suffix: the suffix to add to each node name
    :return: the modified tree dictionary ready for recombination
    """

    tree_dict = handle_same_labels(tree_dict)
    tree_dict = add_suffix_to_all_node_names(tree_dict, suffix)
    tree_dict = order_node_children_lexicographically(tree_dict)
    return tree_dict


def insertion_cost(zss_node: Node) -> int:
    """
    Insertion cost function for zss tree edit distance.
    :param zss_node: zss node to be inserted
    :return: cost of insertion
    """

    return 100  # intentionally high to prefer update (if possible) over insert+remove in the edit script


def remove_cost(zss_node: Node) -> int:
    """
    Removal cost function for zss tree edit distance.
    :param zss_node: zss node to be removed
    :return: cost of removal
    """

    return 100  # intentionally high to prefer update (if possible) over insert+remove in the edit script


def update_cost(zss_node1: Node, zss_node2: Node) -> int:
    """
    Update cost function for zss tree edit distance.
    The update cost is 0 if the nodes are identical (based on label and type), and very small (1-5) for nodes that
    share a type and a similar abstraction. The cost is very high (INFTY) otherwise.

    :param zss_node1: the first zss node
    :param zss_node2: the second zss node
    :return: the cost of updating zss_node1 to zss_node2
    """

    node_text1 = Node.get_label(zss_node1)
    node_text2 = Node.get_label(zss_node2)
    spltd1 = node_text1.split('_')
    spltd2 = node_text2.split('_')
    type1 = spltd1[1]
    type2 = spltd2[1]

    if type1 != type2:
        return INFTY

    label1 = spltd1[0]
    label1 = ''.join([i for i in label1 if not i.isdigit()])  # remove digits
    label2 = spltd2[0]
    label2 = ''.join([i for i in label2 if not i.isdigit()])  # remove digits

    if label1 == label2:
        return 0

    if type1 == "action":  # two action nodes
        direct_category1 = spltd1[2]
        general_category1 = spltd1[3]
        direct_category2 = spltd2[2]
        general_category2 = spltd2[3]
        if direct_category1 == direct_category2 and direct_category1 != "None":
            return 1
        elif general_category1 == general_category2 and general_category1 != "None":
            return 5
        else:
            return INFTY
    else:  # two ingredient nodes
        abstr1 = spltd1[2]
        abstr2 = spltd2[2]
        if abstr1 == abstr2:
            return 5
        else:
            return INFTY


def create_dot_code_for_tree(tree_dict: dict, file_path: str = None) -> str:
    """
    Creates a DOT code for a given tree dictionary.

    :param tree_dict: the tree dictionary
    :param file_path: the file path to save the DOT code (if None, the code is not saved to a file)
    :return: the DOT code as a string
    """

    dot_code_str = "digraph G {\n"
    dot_code_str += "\trankdir=BT ratio=auto;\n"
    for node in tree_dict:
        node_type = tree_dict[node]["type"]
        label = re.sub(r'\d+', '', tree_dict[node]["label"])
        if node_type == "ingredient":
            dot_code_str += "\t" + node + "[label=<" + label
            dot_code_str += "<br /> <font color=\"" + INGR_ABSTR_COLOR + "\" point-size=\"10\">" + tree_dict[node]["abstr"] + "</font>"
            if "extra_info" in tree_dict[node]:
                if "structure" in tree_dict[node]["extra_info"]:
                    dot_code_str += "<br /> <font color=\"" + INGR_STRUCTURE_COLOR + "\" point-size=\"10\">(structure)</font>"
                if "core" in tree_dict[node]["extra_info"]:
                    dot_code_str += "<br /> <font color=\"" + INGR_CORE_COLOR + "\" point-size=\"10\">(core)</font>"
            dot_code_str += "> shape=box"
        else:  # node_type == "action"
            dot_code_str += '\t' + node + ' [label=<' + label
            dot_code_str += "<br /> <font color=\"" + ACTION_ABSTR_COLOR + "\" point-size=\"10\">" + tree_dict[node]["abstr"] + "</font>>"
        dot_code_str += '];\n'
    for node in tree_dict:
        for child in tree_dict[node]["children"]:
            dot_code_str += '\t' + child + " -> " + node
            dot_code_str += ";\n"
    dot_code_str += "}"

    if file_path:
        with open(file_path, "w") as f:
            f.write(dot_code_str)

    return dot_code_str


def create_single_combination(sampled_recipes: dict, dish_name1: str, recipe_id1: str, dish_name2: str, recipe_id2: str) -> dict:
    """
    Creates a single combination of two specific recipe trees by computing the tree edit distance between them, and
    then applying a random subset of edit operations for transforming the first tree into the second tree.

    :param sampled_recipes: the sampled recipes dictionary
    :param dish_name1: the name of the first dish
    :param recipe_id1: a recipe tree ID of the first dish
    :param dish_name2: the name of the second dish
    :param recipe_id2: a recipe tree ID of the second dish
    :return: an intermediate tree dictionary representing the combination
    """

    t1_tree_dict = copy.deepcopy(sampled_recipes[dish_name1][recipe_id1]["tree_dict"])
    t1_tree_dict = prepare_tree_dict_for_recombination(t1_tree_dict, "a")

    t2_tree_dict = copy.deepcopy(sampled_recipes[dish_name2][recipe_id2]["tree_dict"])
    t2_tree_dict = prepare_tree_dict_for_recombination(t2_tree_dict, "b")

    dish1_ingr_dict = sampled_recipes[dish_name1][recipe_id1]["parsed_ingredients"]  # ignr_name -> "ref", "core", "abstr".
    dish2_ingr_dict = sampled_recipes[dish_name2][recipe_id2]["parsed_ingredients"]

    T1 = create_zss_tree_from_tree_dict(t1_tree_dict, cooking_verbs_to_categories)
    T2 = create_zss_tree_from_tree_dict(t2_tree_dict, cooking_verbs_to_categories)

    dist, operations = distance(T1, T2, get_children=Node.get_children_ordered,
                                insert_cost=lambda n: insertion_cost(n),
                                remove_cost=lambda n: remove_cost(n),
                                update_cost=lambda n1, n2: update_cost(n1, n2),
                                return_operations=True)

    all_operations = concretize_tree_edit_operations(t1_tree_dict, t2_tree_dict, operations)
    tracking_tree = build_tracking_tree_dict_for_ops(all_operations, t1_tree_dict, t2_tree_dict)

    short_operations = get_concise_operations(all_operations)
    short_operations_mixed_order = shuffle_operation_order(dish1_ingr_dict, dish2_ingr_dict, short_operations)

    # we want to stop somewhere in the middle and apply only part of the operations:
    index_of_interest = random.randint(1*len(short_operations)//6, 5*len(short_operations)//6)

    intermediate_tree = apply_tree_edits(tree_dict=t1_tree_dict,
                                         short_operations=short_operations_mixed_order,
                                         tracking_tree=tracking_tree,
                                         stop_index=index_of_interest)

    return intermediate_tree


def combine_two_dishes(sampled_recipes_parsed: dict, dish1: str, dish2: str, reverse_transformation: bool = True,
                       versions: int = 1) -> dict:
    """
    Produce tree combinations of two dishes by combining all recipe trees from dish1 with all recipe trees from dish2.

    :param sampled_recipes_parsed: the sampled recipes dictionary (with parsed ingredients and tree structures)
    :param dish1: the name of the first dish
    :param dish2: the name of the second dish
    :param reverse_transformation: a boolean indicating whether to also create reverse transformations (from dish2 to dish1)
    :param versions: the number of versions to create for each recipe pair
    :return: a dictionary of the generated combinations
    """

    dish1_recipe_ids = [key for key in sampled_recipes_parsed[dish1]]
    dish2_recipe_ids = [key for key in sampled_recipes_parsed[dish2]]

    combinations_dict = {}

    for recipe_id1 in dish1_recipe_ids:
        for recipe_id2 in dish2_recipe_ids:

            recipe_A = dish1.replace(" ", "_") + "_" + recipe_id1
            recipe_B = dish2.replace(" ", "_") + "_" + recipe_id2

            if sampled_recipes_parsed[dish1][recipe_id1]["is_tree"] and sampled_recipes_parsed[dish2][recipe_id2]["is_tree"]:

                for i in range(versions):

                    cur_version = "v" + str(i+1)

                    combination_key = recipe_A + "_to_" + recipe_B + "_" + cur_version
                    intermediate_tree = create_single_combination(sampled_recipes_parsed, dish1, recipe_id1, dish2, recipe_id2)
                    dot_code = create_dot_code_for_tree(intermediate_tree)

                    combinations_dict[combination_key] = {}
                    combinations_dict[combination_key]["tree_dict"] = intermediate_tree
                    combinations_dict[combination_key]["tree_dot_code"] = dot_code

                    if reverse_transformation:
                        combination_rev_key = recipe_B + "_to_" + recipe_A + "_" + cur_version
                        intermediate_tree_rev = create_single_combination(sampled_recipes_parsed, dish2, recipe_id2, dish1, recipe_id1)
                        dot_code_rec = create_dot_code_for_tree(intermediate_tree_rev)

                        combinations_dict[combination_rev_key] = {}
                        combinations_dict[combination_rev_key]["tree_dict"] = intermediate_tree_rev
                        combinations_dict[combination_rev_key]["tree_dot_code"] = dot_code_rec

    return combinations_dict


if __name__ == '__main__':

    # Load sampled recipes data (with parsed ingredients and tree dicts):
    with open("../toy_example_files/sampled_recipes_tiny_parsed.json", "r", encoding="utf8") as f:
        sampled_recipes_parsed = json.load(f)

    generated_trees = {}

    # Choose dishes to combine:
    dish_pairs = [('chocolate pie', 'lasagna'), ('apple salad', 'dumplings')]

    # Generate new idea trees that are combinations of the chosen dishes:
    for pair in dish_pairs:
        combinations_dict = combine_two_dishes(sampled_recipes_parsed, pair[0], pair[1], reverse_transformation=True, versions=5)
        generated_trees[pair[0].replace(" ", "_") + "_to_" + pair[1].replace(" ", "_")] = combinations_dict

    # Save generated idea trees to a JSON file:
    with open("../toy_example_files/generated_recipes_tiny.json", "w", encoding="utf8") as f:
        json.dump(generated_trees, f, indent=4)
