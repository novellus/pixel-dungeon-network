import graphviz
import json
import os


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


def main():
    f = open('fork_tree_data.json', 'r')
    tree = json.loads(f.read())
    f.close()

    graph = init_graph()
    recursively_add_nodes(tree, graph)
    graph.render('graph', format='svg', view=True)


if __name__ == '__main__':
    main()