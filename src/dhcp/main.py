# entry point to DHCP

from src.utils import config, init_config


def main() -> None:
    init_config()

    print("Hello World DHCP")


if __name__ == "__main__":
    main()