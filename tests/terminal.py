"""Isolated native-Zsh PTY fixture shared by E2E and performance tests."""
import errno
import fcntl
import os
from pathlib import Path
import pty
import re
import select
import shlex
import signal
import struct
import subprocess
import tempfile
import termios
import time

ROOT = Path(__file__).resolve().parents[1]
PROMPT = b"__ZAKO_READY__> "
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")


def plain(value):
    return ANSI.sub("", value).replace("\r", "")


def plugin_setup(root):
    omz = Path.home() / ".oh-my-zsh"
    required = [omz / "oh-my-zsh.sh", omz / "custom/plugins/zsh-autosuggestions/zsh-autosuggestions.plugin.zsh",
                omz / "custom/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.plugin.zsh"]
    for item in required:
        if not item.is_file():
            raise RuntimeError(f"Required local plugin missing: {item}")
    return f'''
export ZSH={shlex.quote(str(omz))}
export ZSH_CUSTOM={shlex.quote(str(omz / "custom"))}
ZSH_THEME=robbyrussell
ZSH_CACHE_DIR={shlex.quote(str(root / "cache"))}
ZSH_COMPDUMP={shlex.quote(str(root / "zcompdump"))}
HISTFILE={shlex.quote(str(root / "history"))}
_Z_DATA={shlex.quote(str(root / "z-data"))}
DISABLE_AUTO_UPDATE=true
ZSH_DISABLE_COMPFIX=true
zstyle ':omz:update' mode disabled
plugins=(git z zsh-autosuggestions fzf zsh-syntax-highlighting)
source "$ZSH/oh-my-zsh.sh"
(( $+functions[fzf-file-widget] && $+functions[_zsh_autosuggest_start] && $+functions[_zsh_highlight] )) || return 91
'''


def versions():
    result = {"zsh": subprocess.check_output(["zsh", "--version"], text=True).strip()}
    omz = Path.home() / ".oh-my-zsh"
    for name, path in [("oh-my-zsh", omz), ("autosuggestions", omz / "custom/plugins/zsh-autosuggestions"),
                       ("syntax-highlighting", omz / "custom/plugins/zsh-syntax-highlighting")]:
        query = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], text=True, capture_output=True)
        result[name] = {"path": str(path), "commit": query.stdout.strip() if query.returncode == 0 else "not a git checkout"}
    query = subprocess.run(["fzf", "--version"], text=True, capture_output=True)
    if query.returncode:
        raise RuntimeError("fzf unavailable")
    result["fzf"] = query.stdout.strip()
    return result


class Terminal:
    def __init__(self, binary, profile="clean", order="after", integration=True, config="", before="", after="", init=None):
        self.temp = tempfile.TemporaryDirectory(prefix="zako-pty-")
        self.root = Path(self.temp.name)
        for name in ["bin", "config", "cache", "work"]:
            (self.root / name).mkdir()
        self.work = self.root / "work"
        self.config = self.root / "config/config.toml"
        self.config.write_text(config)
        (self.root / "bin/zako").symlink_to(Path(binary).resolve())
        self.transcript = ""
        self.buffer = b""
        self.closed = False
        source = f"source {shlex.quote(str(ROOT / 'integrations/zako.zsh'))}\n" if integration else ""
        if init is not None:
            source = init + "\n"
        plugins = plugin_setup(self.root) if profile == "plugins" else f"autoload -Uz compinit; compinit -d {shlex.quote(str(self.root / 'zcompdump'))}\n"
        if profile == "real":
            actual_rc = Path.home() / ".zshrc"
            # Real login startup files participate too; all history/cache
            # locations used by our scenarios remain in this fixture.
            for name in [".zshenv", ".zprofile", ".zlogin"]:
                original = Path.home() / name
                if original.is_file():
                    (self.root / name).write_text(f"source {shlex.quote(str(original))}\n")
            if integration:
                plugins = f"source {shlex.quote(str(actual_rc))}\n"
            else:
                # Compare the same real startup configuration with only our
                # marked initialization removed; never edit the actual file.
                baseline_rc = self.root / "baseline.zshrc"
                baseline_rc.write_text(re.sub(
                    r"(?ms)^# >>> Zako Shell Companion >>>\n.*?^# <<< Zako Shell Companion <<<\n?",
                    "", actual_rc.read_text()))
                plugins = f"source {shlex.quote(str(baseline_rc))}\n"
            source = ""
        preamble = f'''
unsetopt beep
HISTFILE={shlex.quote(str(self.root / "history"))}
HISTSIZE=200
SAVEHIST=0
export XDG_CACHE_HOME={shlex.quote(str(self.root / "cache"))}
export XDG_DATA_HOME={shlex.quote(str(self.root / "cache/data"))}
export _ZO_DATA_DIR={shlex.quote(str(self.root / "cache/zoxide"))}
ZSH_CACHE_DIR={shlex.quote(str(self.root / "cache"))}
ZSH_COMPDUMP={shlex.quote(str(self.root / "zcompdump"))}
_Z_DATA={shlex.quote(str(self.root / "z-data"))}
DISABLE_AUTO_UPDATE=true
ZSH_DISABLE_COMPFIX=true
zstyle ':omz:update' mode disabled
autoload -Uz add-zsh-hook
_test_before() {{ _TEST_BEFORE_STATUS=$?; (( _TEST_BEFORE_COUNT++ )); return 0; }}
_test_after() {{ _TEST_AFTER_STATUS=$?; (( _TEST_AFTER_COUNT++ )); return 0; }}
typeset -g _TEST_BEFORE_COUNT=0 _TEST_AFTER_COUNT=0
add-zsh-hook precmd _test_before
'''
        ending = r'''
add-zsh-hook precmd _test_after
if (( $+functions[zako] )); then
  functions -c zako _test_original_zako
fi
zako() {
  local native=$?
  if [[ $1 == __state ]]; then
    print -r -- "__STATE__native=$nativeenabled=${_ZAKO_ENABLED-0}mood=${_ZAKO_MOOD-none}failures=${_ZAKO_FAILURES-0}owned=${_ZAKO_PROMPT_OWNED-0}prompt=${RPROMPT-}marker=${_ZAKO_PROMPT_MARKER-}count=${#_ZAKO_SUGGESTIONS}before=$_TEST_BEFORE_STATUSafter=$_TEST_AFTER_STATUSbefore_count=$_TEST_BEFORE_COUNTafter_count=$_TEST_AFTER_COUNTzako_hooks=${#${(M)precmd_functions:#_zako_precmd}}buffer=${_TEST_ZLE_BUFFER-}post=${_TEST_ZLE_POST-}highlight=${_TEST_ZLE_HIGHLIGHT-}"
  elif (( $+functions[_test_original_zako] )); then
    _test_original_zako "$@"
  else
    command zako "$@"
  fi
}
_test_capture() {
  _TEST_ZLE_BUFFER=$BUFFER
  _TEST_ZLE_POST=$POSTDISPLAY
  _TEST_ZLE_HIGHLIGHT="${(j:~:)region_highlight}"
}
zle -N _test_capture
bindkey '^[[24~' _test_capture
PROMPT=$'\n__ZAKO_READY__> '
PS2='continue> '
RPS1=${RPROMPT-}
'''
        rc = preamble + before + "\n" + (source + plugins if order == "before" else plugins + source) + ending + after + "\n"
        (self.root / ".zshrc").write_text(rc)
        env = {**os.environ, "PATH": str(self.root / "bin") + ":" + os.environ["PATH"],
               "ZDOTDIR": str(self.root), "ZAKO_CONFIG_DIR": str(self.root / "config"),
               "TERM": "xterm-256color", "LANG": "en_US.UTF-8"}
        self.started = time.monotonic()
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(self.work)
            os.execvpe("zsh", ["zsh", "-d", *(["-l"] if profile == "real" else []), "-i"], env)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 36, 160, 0, 0))
        try:
            self.startup = self.read_prompt(timeout=20)
            self.startup_ms = (time.monotonic() - self.started) * 1000
        except BaseException:
            self.close()
            raise

    def read_prompt(self, timeout=5):
        return self.read_until(PROMPT, timeout)

    def read_until(self, needle, timeout=5):
        deadline = time.monotonic() + timeout
        while needle not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(f"PTY deadline waiting for {needle!r}: {self.transcript[-3000:]!r}")
            ready, _, _ = select.select([self.fd], [], [], min(remaining, 0.1))
            if ready:
                try:
                    value = os.read(self.fd, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    value = b""
                if not value:
                    raise AssertionError(f"PTY closed before {needle!r}: {self.transcript[-3000:]!r}")
                self.buffer += value
                self.transcript += value.decode("utf-8", errors="replace")
        end = self.buffer.index(needle) + len(needle)
        value, self.buffer = self.buffer[:end], self.buffer[end:]
        return plain(value.decode("utf-8", errors="replace"))

    def send(self, text):
        os.write(self.fd, text.encode() if isinstance(text, str) else text)

    def command(self, text, timeout=5):
        self.send(text + "\n")
        return self.read_prompt(timeout)

    def state(self):
        output = self.command("zako __state")
        match = re.search(r"^__STATE__\x1f([^\n]*)", output, re.M)
        if not match:
            raise AssertionError(f"Missing actual probe output: {output!r}")
        return dict(field.split("=", 1) for field in match[1].split("\x1f"))

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            foreground = os.tcgetpgrp(self.fd)
        except OSError:
            foreground = self.pid
        groups = {self.pid}
        try:
            if foreground > 1 and os.getsid(foreground) == self.pid:
                groups.add(foreground)
        except ProcessLookupError:
            pass
        # Close the PTY master before reaping. macOS can otherwise wait for an
        # unread terminal output queue while the parent waits for Shell exit.
        try:
            os.close(self.fd)
            # HUP usually finishes the Shell itself. Reap before signalling so
            # macOS zombie/session teardown races cannot fail test cleanup.
            for sig, budget in [(None, .15), (signal.SIGTERM, 1), (signal.SIGKILL, 1)]:
                child, _ = os.waitpid(self.pid, os.WNOHANG)
                if child:
                    return
                if sig is not None:
                    for group in groups:
                        try:
                            os.killpg(group, sig)
                        except (ProcessLookupError, PermissionError):
                            # A disappearing group may report EPERM on macOS.
                            # The unreaped, test-owned child is also signalled
                            # directly, and successful reaping remains required.
                            pass
                    try:
                        os.kill(self.pid, sig)
                    except ProcessLookupError:
                        pass
                deadline = time.monotonic() + budget
                while time.monotonic() < deadline:
                    child, _ = os.waitpid(self.pid, os.WNOHANG)
                    if child:
                        return
                    time.sleep(0.01)
            raise RuntimeError(f"Could not reap test Shell {self.pid}")
        except ChildProcessError:
            pass
        finally:
            # OMZ's z plugin intentionally disowns its final directory-data
            # writer. It can rename z-data after the Shell has been reaped.
            # Retry only that filesystem race, never a test or other error.
            cleanup_deadline = time.monotonic() + 2
            while True:
                try:
                    self.temp.cleanup()
                    break
                except OSError as error:
                    if error.errno != errno.ENOTEMPTY or time.monotonic() >= cleanup_deadline:
                        raise
                    time.sleep(.02)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
