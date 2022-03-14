import json
import os
import re
import subprocess
from util import clone_folder_path
from util import count_tree_nodes
from util import node_uid


def pull_node_commit_history(node):
    # pulls commit history for a single repo

    # navigate to cloned directory and extract a formatted git log
    if os.path.exists(clone_folder_path(node)):
        cwd = os.getcwd()
        os.chdir(os.path.join(cwd, clone_folder_path(node)))
        completed_process = subprocess.run(['git', 'log', '--pretty=format:"%at %H"'], capture_output=True)
        os.chdir(cwd)

        # parse log
        git_log = completed_process.stdout
        git_log = git_log.decode('ascii')
        git_log = re.sub('"', '', git_log)

        history = []
        for line in git_log.strip().split('\n'):
            timestamp, commit_hash = line.strip().split()
            timestamp = int(timestamp)

            entry = (timestamp, commit_hash)
            history.append(entry)

        return history


def recursively_pull_commit_histories(tree):
    # pulls commit history for all repos, storing as new key in tree

    # add root node
    commit_history = pull_node_commit_history(tree)
    if commit_history is not None:
        tree['commit_history'] = commit_history

    # add all forks
    for fork in tree['forks']:
        fork = recursively_pull_commit_histories(fork)

    return tree


def latest_common_commit(parent, child):
    # establishes latest commit hash common to both repos
    # checks first for identical commits, and picks the latest such commit if found
    # if no common commits, falls back to commit timestamps
    #   chooses the latest commit from the parent which is still prior to the first commit of the child
    # if there is no such commit, either the relationship is invalid, or the commit history was fabricated, so raise an error
    #
    # returns 2 commit hashes, one for the parent and one for the child, indicating branch points
    #   these are usually the same hash, except when commit histories have been altered

    # allow leaves to have no history
    if 'commit_history' not in child:
        return None

    # dissallow parents to have no history
    if 'commit_history' not in parent:
        raise ValueError(f'Parent node has no commit history {node_uid(parent)} -> {node_uid(child)}')

    parent_commit_history = parent['commit_history']
    child_commit_history = child['commit_history']
    child_hashes = [commit_hash for timestamp, commit_hash in child_commit_history]

    # check for identical commits
    for timestamp, commit_hash in sorted(parent_commit_history, reverse=True):
        if commit_hash in child_hashes:
            return (commit_hash, commit_hash)

    # fallback to timestamps
    earliest_child_timestamp, earliest_child_commit_hash = sorted(child_commit_history)[0]
    for timestamp, commit_hash in sorted(parent_commit_history, reverse=True):
        if timestamp <= earliest_child_timestamp:
            return (commit_hash, earliest_child_commit_hash)

    raise ValueError(f'No common hash found bewtween parent and child {node_uid(parent)} -> {node_uid(child)}\n{parent_commit_history}\n{child_commit_history}')


def establish_latest_common_commits(tree):
    # establishes latest commit hashes common to each parent-child pair
    # stores as property of the fork
    # property does not exist on the root node (no parent)

    for fork in tree['forks']:
        fork_points = latest_common_commit(tree, fork)
        if fork_points is not None:
            fork['fork_points'] = fork_points

    return tree


def main():
    f = open('fork_tree_data.json', 'r')
    tree = json.loads(f.read())
    f.close()

    tree = recursively_pull_commit_histories(tree)
    tree = establish_latest_common_commits(tree)

    # save modified data strcuture
    f = open('fork_tree_data_3.json', 'w')
    f.write(json.dumps(tree))
    f.close()


if __name__ == '__main__':
    main()
