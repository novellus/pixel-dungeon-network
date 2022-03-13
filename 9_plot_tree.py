import graphviz
import json


def init_graph():
    return graphviz.Digraph()


def node_bio(node):
    name = node['api_package']['full_name']
    watchers = node['api_package']['watchers_count']

    return f'{name}\n{watchers} watchers'


def node_uid(node):
    # must be string, used by graph elements behind the scenes
    return node['api_package']['full_name']


def add_node(node, graph, parent=None):
    graph.node(node_uid(node), label=node_bio(node))
    if parent is not None:
        graph.edge(node_uid(parent), node_uid(node))


def recursively_add_nodes(tree, graph, parent=None):
    # add root node
    add_node(tree, graph, parent)

    # add all forks
    for fork in tree['forks']:
        recursively_add_nodes(fork, graph, parent=tree)


# move to graph utility
def prune_uninteresting_repos(tree):
    # prunes non-interesting repos from the tree
    # repos are considered interesting if they meet all the following criteria
    #   repository or one of its forks (recursive) has been modified after forking
    #   repository still exists at time of writing


def prune_uninteresting_commits(tree):
    # prunes non-interesting nodes from the commit histories
    # nodes are considered interesting in any of the following cases
    #   initial commit of the root node
    #       notably, not the initial commits of the non-root nodes
    #       their commits are only interesting beginning at their fork-branch points
    #   latest commit of any node
    #   branch points (both sides)


def main():
    f = open('fork_tree_data.json', 'r')
    tree = json.loads(f.read())
    f.close()

    tree = prune_uninteresting_repos(tree)
    tree = prune_uninteresting_commits(tree)

    graph = init_graph()
    recursively_add_nodes(tree, graph)
    graph.render('graph', format='svg', view=True)


if __name__ == '__main__':
    main()
