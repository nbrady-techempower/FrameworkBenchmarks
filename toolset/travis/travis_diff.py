#!/usr/bin/env python

# @file:        toolset/travis/travis_diff.py
# @author:      Nate Brady
#
# @description: This script is only for use within Travis-CI. It is meant to
# look through the commit history and determine whether or not the current
# framework test directory needs to be run. It compares the state of the PR
# branch against the target branch.
#
# Any changes found in the toolset/* directory other than continuous/*, travis/*
# and scaffolding/* will cause all tests to be run.
#
# The following commands can be put in commit messages to affect which tests
# will run:
#
# [ci skip] - Provided by Travis. Travis won't trigger any builds.
# [ci run-all] - This will force all tests to run.
# [ci fw-only Java/gemini JavaScript/nodejs] - Ensures that only Java/gemini and
#   JavaScript/nodejs tests are run despite the detected changes.
# [ci fw Java/gemini] - Forces Java/gemini to run in addition to detected changes.
# [ci lang-only Java C++] - Ensures that only Java and C++ run despite detected changes.
# [ci lang Java C++] - Forces Java and C++ tests to run in addition to detected changes.
#
# If only a single test within a language group is forced to run, none of the
# other tests in that language group will run.
#
# The master branch will run the full suite of tests.
#
# IMPORTANT: the [ci *] commands must be added to every commit message. We do
# not look at previous commit messages. Make sure to keep your PR branch
# up-to-date with the target branch to avoid running unwanted tests.


import subprocess
import os
import re


def fw_found_in_changes(test, changes_output):
    return re.search(
        r"frameworks/" + re.escape(test) + "/",
        changes_output, re.M)


# Cleans up diffing and grep output and into an array of strings
def clean_output(output):
    return os.linesep.join([s for s in output.splitlines() if s])


def quit_diffing():
    if len(run_tests):
        print("travis-run-tests {!s}".format(" ".join(set(run_tests))))
    else:
        print("No tests to run.")
    exit(0)


curr_branch = ""
is_PR = (os.getenv("PR_NUMBER") != "")
# BRANCH_NAME is the the name of the branch
is_master = not is_PR and os.getenv("BRANCH_NAME") == "master"

if is_PR:
    curr_branch = "FETCH_HEAD"
elif not is_master:
    curr_branch = os.getenv("GITHUB_SHA")

# Also fetch master to compare against
subprocess.check_output(['bash', '-c', 'git fetch origin master:master'])
# https://stackoverflow.com/questions/25071579/list-all-files-changed-in-a-pull-request-in-git-github
changes = clean_output(
    subprocess.check_output([
        'bash', '-c',
        'git --no-pager diff --name-only {0} $(git merge-base {0} master)'
            .format(curr_branch)
    ]))
print("Determining what to run based on the following file changes: \n{!s}"
    .format('\n'.join(changes.split('\n')[0:10])))
if len(changes.split('\n')) > 10:
    print("Too many files to show.")


# COMMIT MESSAGES:
# Before any complicated diffing, check for forced runs from the commit message
# Use -2 because travis now inserts a merge commit as the last commit
last_commit_msg = os.getenv("COMMIT_MESSAGE")

test_dirs = []
run_tests = []

# Break the test env variable down into test directories
if os.getenv("TESTLANG"):
    dir = "frameworks/" + os.getenv("TESTLANG") + "/"
    test_dirs = map(lambda x: os.getenv("TESTLANG") + "/" + x,
                    filter(lambda x: os.path.isdir(dir + x), os.listdir(dir)))
elif os.getenv("TESTDIR"):
    test_dirs = os.getenv("TESTDIR").split(' ')

# Forced full run
if is_master or re.search(r'\[ci run-all\]', last_commit_msg, re.M):
    print("All tests have been forced to run from the commit message.")
    run_tests = test_dirs
    quit_diffing()

# Forced *fw-only* specific tests
if re.search(r'\[ci fw-only .+\]', last_commit_msg, re.M):
    tests = re.findall(r'\[ci fw-only (.+)\]', last_commit_msg, re.M)[0].strip().split(' ')
    for test in tests:
        if test in test_dirs:
            print("{!s} has been forced to run from the commit message.".format(test))
            run_tests.append(test)

    # quit here because we're using "only"
    quit_diffing()

# Forced *lang-only* specific tests
if re.search(r'\[ci lang-only .+\]', last_commit_msg, re.M):
    langs = re.findall(r'\[ci lang-only (.+)\]', last_commit_msg, re.M)[0].strip().split(' ')
    for test in test_dirs:
        for lang in langs:
            if test.startswith(lang + "/"):
                print("{!s} has been forced to run from the commit message.".format(test))
                run_tests.append(test)

    # quit here because we're using "only"
    quit_diffing()

# Forced framework run in addition to other tests
if re.search(r'\[ci fw .+\]', last_commit_msg, re.M):
    tests = re.findall(r'\[ci fw (.+)\]', last_commit_msg, re.M)[0].strip().split(' ')
    for test in tests:
        if test in test_dirs:
            print("{!s} has been forced to run from the commit message.".format(test))
            run_tests.append(test)

# Forced lang run in addition to other running tests
if re.search(r'\[ci lang .+\]', last_commit_msg, re.M):
    langs = re.findall(r'\[ci lang (.+)\]', last_commit_msg, re.M)[0].strip().split(' ')
    for test in test_dirs:
        for lang in langs:
            if test.startswith(lang + "/"):
                print("{!s} has been forced to run from the commit message.".format(test))
                run_tests.append(test)


# Ignore travis, continuous and scaffolding changes
if re.search(r'^toolset\/(?!(travis\/|continuous\/|scaffolding\/))', changes, re.M) is not None:
    print("Found changes to core toolset. Running all tests.")
    run_tests = test_dirs
    quit_diffing()

for test in test_dirs:
    if fw_found_in_changes(test, changes):
        print("Found changes that affect {!s}".format(test))
        run_tests.append(test)

quit_diffing()
