#!/usr/bin/env bash

set -o errexit

# shellcheck source=/dev/null
source dev-container-features-test-lib

check "verify session manager plugin installation" session-manager-plugin --version | grep --extended-regexp '[0-9\.]+'

reportResults
