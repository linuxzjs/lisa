#!/bin/bash
#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2015, ARM Limited and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Script run by github CI, VM setup check etc.


# Some commands are allowed to fail in init_env, e.g. to probe for installed
# tools. However, the overall script has to succeed.
source init_env || exit 1

# Failing commands will make the script return with an error code
set -e

echo "Starting self tests ..."
# Use timeout to send SIGINT if the test hangs, so we get a proper backtrace
# before github action kills the whole thing without any useful log
timeout -s INT 1h python3 -m pytest -vv

echo "Starting exekall self tests"
exekall run "$LISA_HOME/tools/exekall/exekall/tests"

echo "Available LISA tests:"
lisa-test --list

echo "Starting documentation pedantic build ..."
lisa-doc-build

echo "Checking that the man pages are up to date ..."

if ! git diff --exit-code doc/man1/; then
    echo "Please regenerate man pages in doc/man1 and commit them"
    exit 1
fi

(
    set +e
    # Check for commits touching subtrees
    ignored_commits='496b859d1a64e5195500aa52040abafb241657ab'
    illegal_location="external/"
    illegal_commits=$(find "$illegal_location" -mindepth 1 -maxdepth 1 -type d -print0 | xargs -0 git log --no-merges --format='%H %s' | grep -v "$ignored_commits")

    if [[ -n "$illegal_commits" ]]; then
        echo -e "The following commits are touching $illegal_location, which is not allowed apart from updates:\n$illegal_commits"
        exit 1
    fi;
)
