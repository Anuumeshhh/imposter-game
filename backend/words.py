import random

WORD_PAIRS = [
    ("Pizza", "Burger"),
    ("Coffee", "Tea"),
    ("Cat", "Dog"),
    ("Sun", "Moon"),
    ("Guitar", "Piano"),
    ("Laptop", "Tablet"),
    ("Ocean", "River"),
    ("Doctor", "Nurse"),
    ("Football", "Basketball"),
    ("Mountain", "Hill"),
]

def get_random_word_pair():
    common, imposter = random.choice(WORD_PAIRS)
    if random.choice([True, False]):
        return common, imposter
    return imposter, common
