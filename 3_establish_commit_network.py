import json
import os
import subprocess
from 2_clone_repos import clone_folder_path


def node_uid(node):
    return node['api_package']['full_name']


def pull_node_commit_history(node):
    # pulls commit history for a single repo

    # navigate to cloned directory and extract a formatted git log
    cwd = os.getcwd()
    os.chdir(os.path.join(cwd, clone_folder_path(node)))
    git_log = subprocess.run(['git', 'log', '--pretty=format:"%at %H"'], capture_output=True)
    os.chdir(cwd)

    # parse log
    log = re.sub('"', '', git_log)
    history = []
    for line in log.split('\n'):
        timestamp, commit_hash = line.strip().split()
        timestamp = int(timestamp)

        entry = (timestamp, commit_hash)
        history.append(entry)

    return history


def recursively_pull_commit_histories(tree):
    # pulls commit history for all repos

    commit_histories = {}

    # add root node
    commit_histories[node_uid(tree)] = pull_node_commit_history(tree)

    # add all forks
    for fork in tree['forks']:
        recursively_pull_commit_histories(fork)

    return commit_histories


def latest_common_commit(parent_commit_history, child_commit_history):
    child_hashes = [commit_hash for timestamp, commit_hash in child_commit_history]

    # establishes latest commit hash common to both repos
    for timestamp, commit_hash in sorted(parent_commit_history, reverse=True):
        if commit_hash in child_hashes:
            return commit_hash

    raise ValueError(f'No common hash found bewtween parent and child\n{parent_commit_history}\n{child_commit_history}')


def establish_commit_network(tree, commit_histories):
    # establishes latest commit hashes common to each parent-child pair


def simplify_commit_network
    # prunes non-interesting nodes from the commit histories
    # nodes are considered interesting in any of the following cases
    #   initial commit of the root node
    #   latest commit of any node
    #   branch points (both sides)


def main():
    f = open('fork_tree_data.json', 'r')
    tree = json.loads(f.read())
    f.close()

    commit_histories = recursively_pull_commit_histories(tree)


if __name__ == '__main__':
    main()
