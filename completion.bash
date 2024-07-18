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
    cmds=(
        analyse
        clean
        close
        create-lib
        expand-extensions
        fetch-lib
        init
        list-lib
        list-extensions
        login
        logout
        names
        pull
        build
        stage
        prime
        pack
        promote-bundle
        publish-lib
        register
        register-bundle
        unregister
        release
        resource-revisions
        resources
        revisions
        status
        upload
        upload-resource
        version
        whoami
    )
    _init_completion || return

    # only offer long options, as they should be self-explanatory (and
    # it's not like it's more typing for the user)
    globals=(--help --verbose --quiet --project-dir)

    # if user just wrote --project-dir, only offer directories
    if [ "$prev" = "--project-dir" ] || [ "$prev" = "-p" ]; then
        _filedir -d
        return
    fi

    # check if any of the words is a command: if yes, offer the options for that
    # command (and the global ones), else offer the commands and global options
    local w c
    for w in "${words[@]}"; do
        for c in "${cmds[@]}"; do
            if [ "$c" = "$w" ]; then
                cmd="$c"
                break
            fi
        done
        if [ "$cmd" ]; then
            break
        fi
    done

    if [ -z "$cmd" ]; then
        # no command yet! show global options and the commands
        COMPREPLY=( $(compgen -W  "${globals[*]} ${cmds[*]}" -- "$cur") )
        return
    fi

    # offer the options for the given command (and global ones, always available)
    case "$cmd" in
        analyse)
            ;&
        analyze)
            COMPREPLY=( $(compgen -W "${globals[*]} --force --format" -- "$cur") )
            ;;
        login)
            case "$prev" in
                --export)
                    _filedir
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "${globals[*]} --export --charm --bundle --permission --channel --ttl" -- "$cur") )
                    ;;
            esac
            ;;
        pack)
            COMPREPLY=( $(compgen -W "${globals[*]} --force --format" -- "$cur") )
            ;;
        promote-bundle)
            case "$prev" in
                --output-bundle)
                    _filedir
                    ;;
                --exclude)
                    # TODO: This should contain a list of charms in the appropriate bundle.yaml file
                    ;;
                *edge*)
                    COMPREPLY=( $(compgen -W "$(echo $prev | sed s/edge/beta/) $(echo $prev | sed s/edge/candidate/) $(echo $prev | sed s/edge/stable/)" -- "$cur") )
                    ;;
                *beta*)
                    COMPREPLY=( $(compgen -W "$(echo $prev | sed s/beta/candidate/) $(echo $prev | sed s/beta/stable/)" -- "$cur") )
                    ;;
                *candidate*)
                    COMPREPLY=( $(compgen -W "$(echo $prev | sed s/candidate/stable/)" -- "$cur") )
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "${globals[*]} --output-bundle --exclude latest/edge latest/beta latest/candidate latest/stable" -- "$cur") )
                    ;;
            esac
            ;;
        release)
            COMPREPLY=( $(compgen -W "${globals[*]} --revision --channel --resource" -- "$cur") )
            ;;
        init)
            COMPREPLY=( $(compgen -W "${globals[*]} --name --author --force --profile" -- "$cur") )
            ;;
        upload)
            COMPREPLY=( $(compgen -W "${globals[*]} --release --resource --format" -- "$cur") )
            ;;
        upload-resource)
            case "$prev" in
                --filepath)
                    _filedir
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "${globals[*]} --filepath --image" -- "$cur") )
                    ;;
            esac
            ;;
        version)
            COMPREPLY=( $(compgen -W "${globals[*]} --format" -- "$cur") )
            ;;
        whoami)
            COMPREPLY=( $(compgen -W "${globals[*]} --format" -- "$cur") )
            ;;
        names)
            COMPREPLY=( $(compgen -W "${globals[*]} --format --include-collaborations" -- "$cur") )
            ;;
        revisions)
            COMPREPLY=( $(compgen -W "${globals[*]} --format" -- "$cur") )
            ;;
        status)
            COMPREPLY=( $(compgen -W "${globals[*]} --format" -- "$cur") )
            ;;
        create-lib)
            COMPREPLY=( $(compgen -W "${globals[*]} --format" -- "$cur") )
            ;;
        publish-lib)
            COMPREPLY=( $(compgen -W "${globals[*]} --format" -- "$cur") )
            ;;
        fetch-lib)
            COMPREPLY=( $(compgen -W "${globals[*]} --format" -- "$cur") )
            ;;
        list-lib)
            COMPREPLY=( $(compgen -W "${globals[*]} --format" -- "$cur") )
            ;;
        *)
            # by default just the global options
            COMPREPLY=( $(compgen -W "${globals[*]}" -- "$cur") )
            ;;
    esac
}
complete -F _charmcraft charmcraft
