from itertools import chain


def repeat_options(option: str, values: list[str]) -> list[str]:
    """Repeat an option for each value."""
    return list(chain.from_iterable((option, value) for value in values))
