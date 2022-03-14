import graphviz
import json
from util import acquire_node
from util import clone_folder_path
from util import node_uid


def delete_node(tree, user_name, repo_name):
    # removes a node from the tree (if it exists), other than the root node

    target_uid = (user_name, repo_name)

    for i_fork, fork in enumerate(tree['forks']):
        if node_uid(fork) == target_uid:
            del tree['forks'][i_fork]
            return tree

        tree = delete_node(fork, user_name, repo_name)

    return tree


def dfs_node_order(tree, root=[]):
    # computes a static search order
    # returns list of node paths

    order = []
    node_path = root + [node_uid(tree)]

    # add leaves
    for fork in tree['forks']:
        order += dfs_node_order(fork, root=node_path)

    # add root node
    order.append(node_path)


def repo_unchanged(tree, node_path):
    # return boolean comparing a forked repo to its parent
    # returns None for the root node

    node = acquire_node(tree, node_path)
    if 'fork_points' not in node:
        return None

    latest_timestamp, latest_commit_hash = sorted(node['commit_history'])[-1]
    parent_branch_hash, child_branch_hash = node['fork_points']
    return parent_branch_hash == latest_commit_hash


def prune_uninteresting_repos(tree):
    # prunes non-interesting repos from the tree
    # repos are considered interesting if they meet all the following criteria
    #   repository or one of its forks (recursive) has been modified after forking
    #   repository still exists at time of writing

    # these repos do not exist at time of cloning, despite apparent existence in the metadata
    for node_path in dfs_node_order(tree):
        node = acquire_node(tree, node_path)
        if not os.path.exists(clone_folder_path(node)):
            if not node['forks']:
                tree = delete_node(tree, *node_path[-1])
            else:
                raise ValueError(f'node with children has no cloned repo {node_uid(node)}')

    # prunes repos which have not changed since forking
    # use a static search order since we're modifying the tree
    for node_path in dfs_node_order(tree):
        if repo_unchanged(tree, node_path):
            tree = delete_node(tree, *node_path[-1])

    return tree


def prune_uninteresting_commits(tree):
    # creates list of interesting commits for each node
    # prunes non-interesting nodes from the commit histories
    # nodes are considered interesting in any of the following cases
    #   initial commit of the root node
    #       notably, not the initial commits of the non-root nodes
    #       their commits are only interesting beginning at their fork-branch points
    #   latest commit of any node
    #   branch points (both sides)

    for node_path in dfs_node_order(tree):
        node = acquire_node(tree, node_path)

        # deduplicate hashes, ignoring downstream timestamps
        interesting_hashes = set()

        if 'fork_points' in node:
            # incoming branch point
            parent_branch_hash, child_branch_hash = node['fork_points']
            interesting_hashes.add(child_branch_hash)
        else:
            # root node initial commit
            timestamp, commit_hash = sorted(node['commit_history'])[0]
            interesting_hashes.add(commit_hash)
        
        # outgoing branch points
        for fork in node['forks']:
            node_branch_hash, fork_branch_hash = fork['fork_points']
            interesting_hashes.add(node_branch_hash)

        # last commit
        timestamp, commit_hash = sorted(node['commit_history'])[-1]
        interesting_hashes.add(commit_hash)

        # compile deduplicated hashes into commit list
        node['interesting_commits'] = []
        for commit in node['commit_history']:
            timestamp, commit_hash = commit
            if commit_hash in interesting_hashes:
                node['interesting_commits'].append(commit)

    return tree


def init_graph():
    return graphviz.Digraph()


def comit_bio(node, commit):
    # composes text used in commit bubble on graph
    # TODO
    #   remove watcher counts from each node which are not correct across all time (only for latest commit at time of writing)
    #   add branch / release name information for each commit
    name = node['api_package']['full_name']
    watchers = node['api_package']['watchers_count']

    return f'{name}\n{watchers} watchers\n{commit}'


def commit_uid(node, commit_hash):
    # must be string, used by graph elements behind the scenes
    return f'{node_uid(node)},{commit_hash}'


def graph_commit(node, commit, graph, parent=None):
    # graphs a single commit from a single repo
    # TODO align horizontally and vertically per constraints

    timestamp, commit_hash = commit
    graph.node(commit_uid(node, commit_hash), label=comit_bio(node, commit))


def graph_repo(node, graph, parent=None):
    # graphs all commits from a repo
    # graphs edges where forks exist

    # graph commits within the repo
    commits = sorted(node['interesting_commits'])
    for commit in commits:
        graph_commit(node, commit, graph, parent)

    # graph edges between commits
    for former_commit, later_commit in zip(commits, commits[1:]):
        former_timestamp, former_commit_hash = former_commit
        later_timestamp, later_commit_hash = later_commit
        graph.edge(commit_uid(node, former_commit), commit_uid(node, later_commit))

    # graph fork edge
    if parent is not None:
        parent_branch_hash, child_branch_hash = node['fork_points']
        graph.edge(commit_uid(parent, parent_branch_hash), commit_uid(node, child_branch_hash))


def recursively_graph_repos(tree, graph, parent=None):
    # graphs all commits from all repos
    # add root node
    graph_repo(tree, graph, parent)

    # add all forks
    for fork in tree['forks']:
        recursively_graph_repos(fork, graph, parent=tree)


def main():
    f = open('fork_tree_data_3.json', 'r')
    tree = json.loads(f.read())
    f.close()

    tree = prune_uninteresting_repos(tree)
    tree = prune_uninteresting_commits(tree)

    graph = init_graph()
    recursively_graph_repos(tree, graph)
    graph.render('graph', format='svg', view=True)


if __name__ == '__main__':
    main()


# constraints
#   every interesting commit from every interesting repo is ploted on the graph
#   each commit is a node where
#       the horizontal position of the node corresponds to the timestamp of the commit
#       all commits from the same repo have the same vertical rank (in a row, left to right)
#       no 2 repos share a vertical rank
#       forks are at a lower vertical rank than their parent
#   edges exist between
#       sequential commits in a repo
#       parent and child commits between repos for forks
