def tuple_to_dict(tup, names: list[str]):
    """ Convert tuple to dict """
    return {k: v for k, v in zip(names, tup)}


def tuples_to_dicts(tups, names: list[str]):
    """ Convert list of tuples to list of dicts """
    return list(map(lambda tup: tuple_to_dict(tup, names), tups))


def parse_decimal(value, decimal) -> float:
    """ Parse bigint into human amount. """
    return int(value) / (10**decimal)


def format_decimal(value, decimal):
    """ format human amount into bigint. """
    return int(value * (10**decimal))
