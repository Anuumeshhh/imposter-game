import random

# Word pairs format: (Common Word, Imposter Word)
WORD_PAIRS = [
    ("Apple", "Pear"),
    ("Dog", "Wolf"),
    ("Pizza", "Burger"),
    ("Coffee", "Tea"),
    ("Airplane", "Helicopter"),
    ("Guitar", "Violin"),
    ("Doctor", "Nurse"),
    ("Football", "Basketball"),
    ("Cat", "Tiger"),
    ("Sun", "Moon"),
    ("Ocean", "Lake"),
    ("Gold", "Silver"),
    ("Phone", "Tablet"),
    ("Pen", "Pencil"),
    ("Bicycle", "Motorcycle"),
    ("Movie", "Play"),
    ("Shirt", "Jacket"),
    ("Train", "Bus")
]

def get_random_word_pair():
    """Returns a tuple containing (common_word, imposter_word)."""
    return random.choice(WORD_PAIRS)
