import argparse
from math import exp
from random import choices
from functools import lru_cache
from faker import Faker
from faker.config import AVAILABLE_LOCALES


age_labels = {
    "male": [
        "boy",
        "teenage-boy",
        "young-man",
        "man",
        "middle-aged-man",
        "mature-man",
        "senior-man",
        "elderly-man",
        "octogenarian-man",
        "nonagenarian-man",
    ],
    "female": [
        "girl",
        "teenage-girl",
        "young-woman",
        "woman",
        "middle-aged-woman",
        "mature-woman",
        "senior-woman",
        "elderly-woman",
        "octogenarian-woman",
        "nonagenarian-woman",
    ],
}

english_locales = [l for l in AVAILABLE_LOCALES if l.startswith("en_")]
if not english_locales:
    english_locales = ["en_US"]


def build_population():
    values = [2, 3]
    weights = [0.8, 0.2]
    size = choices(values, weights=weights, k=1)[0]
    group_ids = assign_age_groups(size)
    if not isinstance(group_ids, list):
        group_ids = [group_ids]
    genders = choices(["male", "female"], k=len(group_ids))
    names = [generate_name(sex) for sex in genders]
    lines = [f"{name} ({age_labels[sex][gid]})" for gid, sex, name in zip(group_ids, genders, names)]
    return "\n".join(lines)


def assign_age_groups(count: int):
    n = 10
    world_weights = [
        0.125,
        0.205,
        0.217,
        0.137,
        0.137,
        0.113,
        0.070,
        0.035,
        0.016,
        0.005,
    ]

    first_idx = choices(range(n), weights=world_weights, k=1)[0]
    if count == 1:
        return first_idx

    sigma = 1.0
    neighbor_weights = [exp(-((i - first_idx) ** 2) / (2 * (sigma ** 2))) for i in range(n)]
    rest_idx = choices(range(n), weights=neighbor_weights, k=count - 1)
    return [first_idx, *rest_idx]


@lru_cache(maxsize=None)
def get_faker(locale: str) -> Faker:
    return Faker(locale)


def generate_name(gender: str) -> str:
    locale = choices(english_locales, k=1)[0]
    fake = get_faker(locale)
    fmt = choices(["first", "last", "full"], k=1)[0]
    if fmt == "first":
        if gender == "male" and hasattr(fake, "first_name_male"):
            return fake.first_name_male()
        if gender == "female" and hasattr(fake, "first_name_female"):
            return fake.first_name_female()
        return fake.first_name()
    if fmt == "last":
        return fake.last_name()
    if gender == "male" and hasattr(fake, "name_male"):
        return fake.name_male()
    if gender == "female" and hasattr(fake, "name_female"):
        return fake.name_female()
    return f"{fake.first_name()} {fake.last_name()}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    print(build_population())
