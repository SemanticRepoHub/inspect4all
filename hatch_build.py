import platform
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_LIBS_DIR = Path(__file__).parent / "src" / "inspect4all" / "libs"
_EXPECTED = {
    "Linux": "libenry.so",
    "Darwin": "libenry.dylib",
    "Windows": "libenry.dll",
}


class CustomBuildHook(BuildHookInterface):
    """Set a platform-specific wheel tag and verify libenry is present."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        if version == "editable":
            return  # compiled binary not needed at this stage

        system = platform.system()
        machine = platform.machine()

        expected = _EXPECTED.get(system)
        if expected and not (_LIBS_DIR / expected).exists():
            raise RuntimeError(
                f"{expected} not found in {_LIBS_DIR}. "
                f"Run 'make libenry' before building the wheel."
            )

        if system == "Linux":
            arch = "x86_64" if machine == "x86_64" else "aarch64"
            build_data["tag"] = f"py3-none-linux_{arch}"
        elif system == "Darwin":
            if machine == "arm64":
                build_data["tag"] = "py3-none-macosx_11_0_arm64"
            else:
                build_data["tag"] = "py3-none-macosx_10_9_x86_64"
