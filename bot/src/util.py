def tuple_to_dict(tup, names: list[str]):
    """ Convert tuple to dict """
    return {k: v for k, v in zip(names, tup)}


def tuples_to_dicts(tups, names: list[str]):
    """ Convert list of tuples to list of dicts """
    return list(map(lambda tup: tuple_to_dict(tup, names), tups))
