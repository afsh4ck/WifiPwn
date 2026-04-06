#!/bin/bash
# Wrapper Docker -> delega en deploy.sh
exec bash "$(dirname "${BASH_SOURCE[0]}")/deploy.sh" docker "$@"