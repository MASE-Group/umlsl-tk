import logging
import subprocess
from pathlib import Path

# Configuration
# Where your .ui and .qrc files live (and the 'icons' folder)
SEARCH_DIR = Path(".") / "qt_widgets"

# Where compiled .py files are written
OUTPUT_DIR = Path(".") / "compiled_widgets"

UIC_CMD = "pyside6-uic"
RCC_CMD = "pyside6-rcc"

logger = logging.getLogger(__name__)


def compile_project() -> None:
    logger.info("--- Compiling UI Files ---")
    logger.info("Source: %s", SEARCH_DIR)
    logger.info("Target: %s", OUTPUT_DIR)

    # Check if source exists to prevent confusing errors
    if not SEARCH_DIR.exists():
        logger.error("Source directory '%s' not found.", SEARCH_DIR)
        return

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create __init__.py so 'compiled_widgets' is treated as a python package
    (OUTPUT_DIR / "__init__.py").touch()

    # Compile resources (.qrc -> _rc.py)
    # Use .resolve() to get absolute paths so commands work from any folder.
    for qrc_file in SEARCH_DIR.rglob("*.qrc"):
        output_file = OUTPUT_DIR / f"{qrc_file.stem}_rc.py"

        if needs_compile(qrc_file, output_file):
            # We run the command INSIDE the qt_widgets folder (cwd=qrc_file.parent)
            # so that relative paths like "icons/image.svg" inside the .qrc file work.
            cmd = [RCC_CMD, qrc_file.name, "-o", str(output_file.resolve())]

            logger.info("Compiling %s...", qrc_file.name)
            try:
                subprocess.run(cmd, check=True, cwd=qrc_file.parent)
                logger.info(" -> Success")
            except subprocess.CalledProcessError as e:
                logger.error(" -> ERROR: %s", e)
        else:
            logger.info("Skipped: %s (up to date)", qrc_file.name)

    # Compile UI files (.ui -> ui_*.py)
    for ui_file in SEARCH_DIR.rglob("*.ui"):
        output_file = OUTPUT_DIR / f"ui_{ui_file.stem}.py"

        if needs_compile(ui_file, output_file):
            cmd = [UIC_CMD, str(ui_file), "-o", str(output_file)]
            logger.info("Compiling %s...", ui_file.name)
            try:
                subprocess.run(cmd, check=True)

                # Patch imports
                # Changes 'import resources_rc' to 'from . import resources_rc'
                fix_imports(output_file)
                logger.info(" -> Success (imports patched)")

            except subprocess.CalledProcessError as e:
                logger.error(" -> ERROR: %s", e)
        else:
            logger.info("Skipped: %s (up to date)", ui_file.name)


def needs_compile(source: Path, target: Path) -> bool:
    """Returns True if target doesn't exist or source is newer."""
    return not target.exists() or source.stat().st_mtime > target.stat().st_mtime


def fix_imports(py_file: Path) -> None:
    """
    Reads the generated python file and changes absolute imports
    of resource files to relative imports so they work within the package.
    """
    try:
        content = py_file.read_text(encoding='utf-8')

        # uic generates: import resources_rc
        # we need:       from . import resources_rc
        old_import = "import resources_rc"
        new_import = "from . import resources_rc"

        if old_import in content and new_import not in content:
            content = content.replace(old_import, new_import)
            py_file.write_text(content, encoding='utf-8')

    except Exception as e:
        logger.warning("Could not patch imports in %s: %s", py_file.name, e)


if __name__ == "__main__":
    compile_project()
