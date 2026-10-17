# Zako Shell Companion — Zsh 5.9+. No ZLE widgets or keybindings.
# Load with: eval "$(zako init zsh)"
_zako_init() {
  emulate -L zsh
  [[ -o interactive && -z ${_ZAKO_INITIALIZED-} ]] || return 0
  (( $+commands[zako] )) || return 0
  autoload -Uz add-zsh-hook
  zmodload zsh/datetime && zmodload zsh/system || {
    print -ru2 -- 'Zako 无法加载 Zsh 内置模块，已安全停用。'
    return 0
  }
  typeset -g _ZAKO_INITIALIZED=1 _ZAKO_ENABLED=0 _ZAKO_FAILURES=0
  typeset -g _ZAKO_BINARY=$commands[zako] _ZAKO_CONFIG_JSON='' _ZAKO_REPLY=''
  typeset -g _ZAKO_MOOD=idle _ZAKO_LAST_COMMAND='' _ZAKO_LAST_INTERACTION_MS=0
  typeset -g _ZAKO_PROMPT_MARKER='' _ZAKO_RENDERED_RPROMPT='' _ZAKO_PROMPT_OWNED=0
  typeset -g _ZAKO_PROMPT_MODE=off _ZAKO_PROMPT_REASON='disabled' _ZAKO_ERROR_SHOWN=0
  typeset -ga _ZAKO_SUGGESTIONS=() _ZAKO_REASONS=()

  # One short-lived worker per event. A private pipe, bounded reads and explicit
  # worker PID allow a hung Core to be killed without a daemon, polling process,
  # temporary command file, global coprocess, or external timeout utility.
  _zako_call() {
    emulate -L zsh
    unsetopt bg_nice monitor
    local fd chunk buffer='' header worker='' rc=1
    local -a lines
    local -F deadline=$(( EPOCHREALTIME + 0.25 )) remaining
    _ZAKO_REPLY=''
    exec {fd}< <(
      print -r -- "P:$sysparams[pid]"
      exec "$_ZAKO_BINARY" --shell-transport "$@" 2>/dev/null
    )
    while (( EPOCHREALTIME < deadline )); do
      remaining=$(( deadline - EPOCHREALTIME ))
      sysread -t $remaining -s 16384 -i $fd chunk 2>/dev/null || break
      buffer+=$chunk
      if [[ -z $worker && $buffer == *$'\n'* ]]; then
        header=${buffer%%$'\n'*}
        [[ $header == P:<-> && ${#header} -lt 14 ]] || break
        worker=${header#P:}
      fi
      (( ${#buffer} <= 32768 )) || break
      if [[ $buffer == *$'\nS:'<->$'\n' ]]; then
        buffer=${buffer%$'\n'}
        lines=("${(@f)buffer}")
        if (( ${#lines} == 3 )) && [[ $lines[3] == S:0 ]]; then
          _ZAKO_REPLY=$lines[2]
          rc=0
        fi
        break
      fi
    done
    exec {fd}<&-
    if (( rc != 0 )) && [[ $worker == <-> ]] && (( worker > 1 )); then
      kill -KILL $worker 2>/dev/null
    fi
    return $rc
  }

  _zako_clear_target() {
    _ZAKO_SUGGESTIONS=()
    _ZAKO_REASONS=()
    return 0
  }
  _zako_render_prompt() {
    emulate -L zsh
    (( _ZAKO_PROMPT_OWNED )) || return 0
    if [[ ${RPROMPT-} != $_ZAKO_RENDERED_RPROMPT ]]; then
      _ZAKO_PROMPT_OWNED=0
      _ZAKO_PROMPT_REASON='RPROMPT taken over by theme/user'
      return 0
    fi
    if (( _ZAKO_ENABLED )); then RPROMPT=$_ZAKO_PROMPT_MARKER; else RPROMPT=''; fi
    _ZAKO_RENDERED_RPROMPT=$RPROMPT
    return 0
  }
  _zako_try_prompt() {
    if [[ $_ZAKO_PROMPT_MODE == auto && ${RPROMPT-} == '' ]]; then
      _ZAKO_PROMPT_OWNED=1
      _ZAKO_RENDERED_RPROMPT=''
      _ZAKO_PROMPT_REASON='automatic'
      _zako_render_prompt
    elif [[ $_ZAKO_PROMPT_MODE == off ]]; then
      _ZAKO_PROMPT_REASON='prompt.mode=off'
    else
      _ZAKO_PROMPT_REASON='RPROMPT already in use'
    fi
    return 0
  }
  _zako_disable_error() {
    _ZAKO_ENABLED=0
    _ZAKO_FAILURES=0
    _ZAKO_LAST_COMMAND=''
    _ZAKO_PROMPT_MARKER=''
    _zako_clear_target
    _zako_render_prompt
    if (( ! _ZAKO_ERROR_SHOWN )); then
      print -ru2 -- 'Zako 配置无效或 Core 不可用，已安全停用；运行 `zako doctor` 查看原因。'
      _ZAKO_ERROR_SHOWN=1
    fi
    return 0
  }
  _zako_valid_fields() {
    emulate -L zsh
    local item
    for item in "$@"; do
      [[ $item != *[[:cntrl:]]* && ${#item} -le 8192 ]] || return 1
    done
    return 0
  }
  _zako_valid_marker() {
    [[ $1 == (':3'|':)'|':/'|':|'|':D'|'♡ (¬_¬)'|'♡ (＾▽＾)'|'♡ (ಠ_ಠ)'|'♡ (・_・;)'|'♡ (≧▽≦)') ]]
  }
  _zako_load_session() {
    emulate -L zsh
    local -a fields
    _zako_call session || { _zako_disable_error; return 1; }
    fields=("${(@ps:\x1f:)_ZAKO_REPLY}")
    (( ${#fields} == 6 )) && [[ $fields[1] == 1 && $fields[2] == (0|1) && $fields[3] == (auto|off) ]] \
      && _zako_valid_fields "${fields[@]}" && _zako_valid_marker "$fields[4]" || { _zako_disable_error; return 1; }
    _ZAKO_ENABLED=$fields[2]
    _ZAKO_PROMPT_MODE=$fields[3]
    _ZAKO_PROMPT_MARKER=$fields[4]
    _ZAKO_CONFIG_JSON=$fields[6]
    (( _ZAKO_ENABLED )) && [[ -n $fields[5] ]] && print -r -- "$fields[5]"
    if (( _ZAKO_ENABLED )); then _zako_try_prompt; fi
    return 0
  }
  _zako_is_internal() {
    emulate -L zsh
    local line=$1
    # Compound commands still expire an old correction target.
    [[ $line != *[\;\|\&\(\)\$\`\<\>\$'\n']* ]] || return 1
    local -a words
    words=("${(@z)line}")
    [[ $words[1] == command ]] && words=("${words[@]:1}")
    [[ $words[1] == zako ]] && (( ${#words} <= 2 ))
  }
  _zako_preexec() {
    emulate -L zsh
    if _zako_is_internal "$1"; then
      _ZAKO_LAST_COMMAND=''
      return 0
    fi
    _zako_clear_target
    if (( _ZAKO_ENABLED )); then _ZAKO_LAST_COMMAND=$1; else _ZAKO_LAST_COMMAND=''; fi
    return 0
  }
  _zako_precmd() {
    local final_status=$?
    emulate -L zsh
    local -a fields
    local -i index count
    local -i now=$(( EPOCHREALTIME * 1000 ))
    local command_line=$_ZAKO_LAST_COMMAND
    _ZAKO_LAST_COMMAND=''
    if (( ! _ZAKO_ENABLED )) || [[ -z $command_line ]]; then
      _zako_render_prompt
      return 0
    fi
    _zako_call event --protocol-version 1 --config-json "$_ZAKO_CONFIG_JSON" \
      --command "$command_line" --exit-code "$final_status" --failures "$_ZAKO_FAILURES" \
      --now-ms "$now" --last-interaction-ms "$_ZAKO_LAST_INTERACTION_MS" || {
        _zako_disable_error
        return 0
      }
    fields=("${(@ps:\x1f:)_ZAKO_REPLY}")
    if (( ${#fields} != 13 )) || [[ $fields[1] != 1 || $fields[2] != (idle|happy|annoyed|concerned|proud) \
      || $fields[3] != <0-4294967295> || $fields[4] != (success|interrupted|neutral|correctable|unknown|disabled) \
      || $fields[7] != (0|1|2|3) ]] || ! _zako_valid_fields "${fields[@]}" || ! _zako_valid_marker "$fields[6]"; then
      _zako_disable_error
      return 0
    fi
    count=$fields[7]
    if { (( count > 0 )) && [[ $fields[4] != correctable ]]; } || { (( count == 0 )) && [[ $fields[4] == correctable ]]; }; then
      _zako_disable_error
      return 0
    fi
    for (( index=count; index<3; index++ )); do
      [[ -z $fields[$((8+index*2))] && -z $fields[$((9+index*2))] ]] || { _zako_disable_error; return 0; }
    done
    _zako_clear_target
    for (( index=0; index<count; index++ )); do
      [[ -n $fields[$((8+index*2))] && -n $fields[$((9+index*2))] ]] || { _zako_disable_error; return 0; }
      _ZAKO_SUGGESTIONS+=("$fields[$((8+index*2))]")
      _ZAKO_REASONS+=("$fields[$((9+index*2))]")
    done
    _ZAKO_MOOD=$fields[2]
    _ZAKO_FAILURES=$fields[3]
    _ZAKO_PROMPT_MARKER=$fields[6]
    if [[ -n $fields[5] ]]; then
      print -r -- "$fields[5]"
      _ZAKO_LAST_INTERACTION_MS=$now
    fi
    _zako_render_prompt
    # Zsh itself restores the original command status between hooks and at the
    # next prompt. Returning zero keeps the remaining plugin hooks running.
    return 0
  }
  _zako_chpwd() { _zako_clear_target; return 0; }

  zako() {
    emulate -L zsh
    case ${1-} in
      on)
        [[ -n $_ZAKO_CONFIG_JSON ]] || _zako_load_session || return 1
        _ZAKO_ENABLED=1
        _zako_try_prompt
        print -r -- 'Zako 已开启。'
        ;;
      off)
        _ZAKO_ENABLED=0
        _ZAKO_FAILURES=0
        _ZAKO_LAST_COMMAND=''
        _zako_clear_target
        _zako_render_prompt
        print -r -- 'Zako 已关闭。'
        ;;
      fix)
        local -i i
        if (( ${#_ZAKO_SUGGESTIONS} )); then
          for (( i=1; i<=${#_ZAKO_SUGGESTIONS}; i++ )); do
            print -r -- "建议：$_ZAKO_SUGGESTIONS[$i]"
            print -r -- "原因：$_ZAKO_REASONS[$i]"
          done
          print -r -- '请手动确认并输入；Zako 不会自动执行。'
        else print -r -- '当前没有可用的高置信度纠错建议。'; fi
        ;;
      status) print -r -- "enabled=$_ZAKO_ENABLED mood=$_ZAKO_MOOD failures=$_ZAKO_FAILURES" ;;
      doctor)
        print -r -- "session: enabled=$_ZAKO_ENABLED; hooks: preexec=${preexec_functions[(I)_zako_preexec]} precmd=${precmd_functions[(I)_zako_precmd]} chpwd=${chpwd_functions[(I)_zako_chpwd]}"
        print -r -- "session prompt: $_ZAKO_PROMPT_REASON; marker=\${_ZAKO_PROMPT_MARKER}"
        if [[ -n $_ZAKO_CONFIG_JSON ]]; then command "$_ZAKO_BINARY" doctor --config-json "$_ZAKO_CONFIG_JSON"; else command "$_ZAKO_BINARY" doctor; fi
        ;;
      *) command "$_ZAKO_BINARY" "$@" ;;
    esac
  }
  add-zsh-hook preexec _zako_preexec
  add-zsh-hook precmd _zako_precmd
  add-zsh-hook chpwd _zako_chpwd
  _zako_load_session
  return 0
}
_zako_init
unfunction _zako_init
