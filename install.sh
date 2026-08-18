#!/usr/bin/env bash
#
# UMLSL-TK installer
#
# Installs the Python dependencies for the UMLSL toolkit: the editor
# (UMLSL-Edit), the simulator (UMLSL-Sim), or both.
#
#   ./install.sh                 # interactive menu
#   ./install.sh all             # UMLSL-Edit + UMLSL-Sim with RL support
#   ./install.sh edit            # UMLSL-Edit only
#   ./install.sh sim             # UMLSL-Sim only, without RL
#   ./install.sh sim-rl          # UMLSL-Sim only, with RL
#
# Options:
#   --venv PATH   Virtual environment to create/use (default: .env)
#   --no-venv     Install into the currently active Python environment
#   --no-dev      Skip the [dev] extra (pytest), installed by default
#   -h, --help    Show this help
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EDIT_DIR="$ROOT/UMLSL-Edit"
SIM_DIR="$ROOT/UMLSL-Sim"

VENV_DIR="$ROOT/.env"
USE_VENV=1
# The [dev] extra is just pytest, and both pyproject.toml files pin the same
# version so one environment can run every suite. Installed by default so that
# `pytest` works straight after an install, as both READMEs tell the user.
INSTALL_DEV=1
TARGET=""

MIN_PY_MAJOR=3
MIN_PY_MINOR=11

# ---------------------------------------------------------------- helpers ---

if [ -t 1 ]; then
    BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'
    YELLOW=$'\033[33m'; RESET=$'\033[0m'
else
    BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; RESET=""
fi

info()  { printf '%s==>%s %s\n' "$BOLD" "$RESET" "$*"; }
ok()    { printf '%s  ok%s %s\n' "$GREEN" "$RESET" "$*"; }
warn()  { printf '%swarn%s %s\n' "$YELLOW" "$RESET" "$*" >&2; }
die()   { printf '%serror%s %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

usage() {
    # Print the comment block at the top of this file, minus the shebang.
    awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "${BASH_SOURCE[0]}"
    exit "${1:-0}"
}

# Find a Python interpreter that is new enough for both tools.
find_python() {
    local candidate
    for candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= ($MIN_PY_MAJOR, $MIN_PY_MINOR) else 1)" 2>/dev/null; then
                printf '%s' "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

# ------------------------------------------------------------ arg parsing ---

while [ $# -gt 0 ]; do
    case "$1" in
        all|edit|sim|sim-rl)
            [ -n "$TARGET" ] && die "More than one target given ('$TARGET' and '$1')."
            TARGET="$1"; shift ;;
        --venv)
            [ $# -ge 2 ] || die "--venv needs a path argument."
            VENV_DIR="$2"; USE_VENV=1; shift 2 ;;
        --venv=*)
            VENV_DIR="${1#*=}"; USE_VENV=1; shift ;;
        --no-venv)
            USE_VENV=0; shift ;;
        --no-dev)
            INSTALL_DEV=0; shift ;;
        -h|--help)
            usage 0 ;;
        *)
            printf '%serror%s Unknown argument: %s\n\n' "$RED" "$RESET" "$1" >&2
            usage 1 ;;
    esac
done

# ----------------------------------------------------------------- menu -----

if [ -z "$TARGET" ]; then
    cat <<EOF
${BOLD}UMLSL-TK installer${RESET}

  1) Everything            UMLSL-Edit + UMLSL-Sim with RL support
  2) UMLSL-Edit only       the scenario editor and model checker
  3) UMLSL-Sim only        the simulator, without reinforcement learning
  4) UMLSL-Sim with RL     the simulator, including the RL training stack

EOF
    printf 'Choose [1-4]: '
    read -r choice
    case "$choice" in
        1) TARGET="all"    ;;
        2) TARGET="edit"   ;;
        3) TARGET="sim"    ;;
        4) TARGET="sim-rl" ;;
        *) die "Invalid choice: '$choice'" ;;
    esac
    echo
fi

# Decompose the target into the two things we may install.
INSTALL_EDIT=0
INSTALL_SIM=0
SIM_EXTRAS=""
EDIT_EXTRAS=""

case "$TARGET" in
    all)    INSTALL_EDIT=1; INSTALL_SIM=1; SIM_EXTRAS="rl" ;;
    edit)   INSTALL_EDIT=1 ;;
    sim)    INSTALL_SIM=1 ;;
    sim-rl) INSTALL_SIM=1; SIM_EXTRAS="rl" ;;
esac

if [ "$INSTALL_DEV" -eq 1 ]; then
    SIM_EXTRAS="${SIM_EXTRAS:+$SIM_EXTRAS,}dev"
    EDIT_EXTRAS="dev"
fi

# pip wants the extras as `path[a,b]`, and an empty `[]` is a syntax error,
# so the brackets only appear when there is something to put inside them.
SIM_EXTRA="${SIM_EXTRAS:+[$SIM_EXTRAS]}"
EDIT_EXTRA="${EDIT_EXTRAS:+[$EDIT_EXTRAS]}"

if [ "$INSTALL_EDIT" -eq 1 ] && [ ! -d "$EDIT_DIR" ]; then
    die "UMLSL-Edit not found at $EDIT_DIR"
fi
if [ "$INSTALL_SIM" -eq 1 ] && [ ! -d "$SIM_DIR" ]; then
    die "UMLSL-Sim not found at $SIM_DIR"
fi

# --------------------------------------------------------------- python -----

if [ "$USE_VENV" -eq 1 ]; then
    if [ -x "$VENV_DIR/bin/python" ]; then
        info "Using existing virtual environment: $VENV_DIR"
    else
        PYTHON="$(find_python)" || die "No Python >= $MIN_PY_MAJOR.$MIN_PY_MINOR found. Install one and re-run."
        info "Creating virtual environment with $($PYTHON -V 2>&1): $VENV_DIR"
        "$PYTHON" -m venv "$VENV_DIR"
    fi
    PY="$VENV_DIR/bin/python"
else
    PY="$(command -v python3 || command -v python)" || die "No Python interpreter found."
    "$PY" -c "import sys; sys.exit(0 if sys.version_info >= ($MIN_PY_MAJOR, $MIN_PY_MINOR) else 1)" \
        || die "$("$PY" -V 2>&1) is too old; UMLSL-TK needs Python >= $MIN_PY_MAJOR.$MIN_PY_MINOR."
    info "Installing into the active environment: $("$PY" -c 'import sys; print(sys.prefix)')"
fi

info "Updating pip"
"$PY" -m pip install --upgrade --quiet pip

# -------------------------------------------------------------- install -----

if [ "$INSTALL_EDIT" -eq 1 ]; then
    info "Installing UMLSL-Edit"
    # Editable, like UMLSL-Sim: both tools use a src/ layout, so the package
    # must be installed to be importable.
    "$PY" -m pip install -e "$EDIT_DIR$EDIT_EXTRA"
    ok "UMLSL-Edit ready"
fi

if [ "$INSTALL_SIM" -eq 1 ]; then
    # Keyed on the rl extra alone: [dev] is one small package, so it is the
    # RL stack that makes this slow and that the warning is about.
    case ",$SIM_EXTRAS," in
        *,rl,*) info "Installing UMLSL-Sim with reinforcement-learning support (this may take a while)" ;;
        *)      info "Installing UMLSL-Sim" ;;
    esac
    # Installed in editable mode on purpose: UMLSL-Sim resolves its scenario
    # directory relative to the package source, so scenarios exported from
    # UMLSL-Edit into UMLSL-Sim/src/umlsl_sim/scenario/scenarios/ are only picked up
    # when the package still points at this working tree.
    "$PY" -m pip install -e "$SIM_DIR$SIM_EXTRA"
    ok "UMLSL-Sim ready"
fi

# ---------------------------------------------------------------- report ----

echo
printf '%sInstallation complete.%s\n\n' "$BOLD" "$RESET"

if [ "$USE_VENV" -eq 1 ]; then
    printf 'Activate the environment with:\n\n    %ssource %s/bin/activate%s\n\n' \
        "$DIM" "$VENV_DIR" "$RESET"
fi

if [ "$INSTALL_EDIT" -eq 1 ]; then
    printf 'Run %sUMLSL-Edit%s:\n\n    python -m umlsl_edit.main\n\n' "$BOLD" "$RESET"
fi

if [ "$INSTALL_SIM" -eq 1 ]; then
    printf 'Run %sUMLSL-Sim%s:\n\n    python -m umlsl_sim.app.run_control_gui\n\n' "$BOLD" "$RESET"
fi

printf 'See README.md for the export/import workflow between the two tools.\n'
