from .core.config import Settings
from .runtime_setup import prepare_runtime_database


def main() -> None:
    prepare_runtime_database(Settings.from_env())


if __name__ == "__main__":
    main()
