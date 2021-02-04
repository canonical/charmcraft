# -*- mode: sh; sh-shell: bash; -*-

# Copyright 2020 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft

_charmcraft()
{
    local cur prev words cword cmd cmds
    cmds=(build version login logout whoami names upload revisions status release)
    _init_completion || return

    # only offer long options, as they should be self-explanatory (and
    # it's not like it's more typing for the user)

    if [ "$cword" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "--help --verbose --quiet --project-dir ${cmds[*]}" -- "$cur") )
        return
    fi

    case "$prev" in
        --help)
            return
            ;;
        --verbose|--quiet)
            COMPREPLY=( $(compgen -W "${cmds[*]}" -- "$cur") )
            return
            ;;
        login|logout|whoami|version|names|register|create-lib|publish-lib|fetch-lib|list-lib|register-bundle|upload|revisions|status|pack)
            COMPREPLY=( $(compgen -W "--help --verbose --quiet --project-dir" -- "$cur") )
            return
            ;;
        build)
            COMPREPLY=( $(compgen -W "--help --verbose --quiet --project-dir --from --entrypoint --requirement" -- "$cur") )
            return
            ;;
        release)
            COMPREPLY=( $(compgen -W "--help --verbose --quiet --project-dir --revision --channel" -- "$cur") )
            return
            ;;
        init)
            COMPREPLY=( $(compgen -W "--help --verbose --quiet --project-dir --name --author --series --force" -- "$cur") )
            return
            ;;
    esac

    # we're inside a command; which one?
    local u w
    for w in "${words[@]}"; do
        for u in "${cmds[@]}"; do
            if [ "$u" = "$w" ]; then
                cmd="$u"
                break
            fi
        done
        if [ "$cmd" ]; then
            break
        fi
    done

    # NOTE cmd can be empty

    case "$cmd" in
        "build")
            case "$prev" in
                -r|--requirement)
                    _filedir txt
                    ;;
                -e|--entrypoint)
                    _filedir py
                    ;;
                -f|--from)
                    _filedir -d
                    ;;
            esac
            ;;
        "init")
            case "$prev" in
                --project-dir)
                    _filedir -d
                    ;;
            esac
            ;;
        "pack")
            case "$prev" in
                -f|--from)
                    _filedir -d
                    ;;
            esac
            ;;
    esac
}
complete -F _charmcraft charmcraft
