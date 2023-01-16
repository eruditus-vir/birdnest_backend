import math


def distance_from_location(xp, yp, xc, yc):
    """
    p indicates position, c indicates center, calculate the distance from center
    :param xp:
    :param yp:
    :param xc:
    :param yc:
    :return:
    """
    return math.sqrt((xp - xc) ** 2 + (yp - yc) ** 2)
