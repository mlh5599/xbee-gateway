import logging


def setup_logging(level_name: str) -> None:
    """Configure root logging. Replaces the old LogHelper.SetLogLevel."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
