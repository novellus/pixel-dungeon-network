import os


github_rate_limit = 61 # default seconds betweeen requests. Actual is in some cases judged by feedback from server
repos_folder = 'repos'


def node_uid(node):
    user_name = node['api_package']['owner']['login']
    repo_name = node['api_package']['name']
    return (user_name, repo_name)


def clone_folder_path(node):
    name = ','.join(node_uid(node))
    return os.path.join(repos_folder, name)


def acquire_node(tree, node_path):
    # returns the specified node

    # node_path should always begin with tree root, which we do not need to search for
    root_uid = node_uid(tree)
    assert node_path[0] == root_uid, (node_path[0], root_uid)
    del node_path[0]

    node = tree
    for target_uid in node_path:
        for fork in node['forks']:
            fork_uid = node_uid(fork)
            if fork_uid == target_uid:
                node = fork
                break

        else:
            raise ValueError(f"target_uid is invalid, {target_uid} from {node_path}")

    return node


def count_tree_nodes(tree):
    # constructs tree data for base repo, recursively traversing all forks
    # requires API package as input, see below function for entry point with only a repo description

    count = 1
    for fork in tree['forks']:
        count += count_tree_nodes(fork)

    return count
