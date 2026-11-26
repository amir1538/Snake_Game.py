"""Snaky Game — Constants, Palettes, Presets & 17 Mode Definitions (1:1 parity with approved HTML prototype)."""

PRODUCT_NAME = "Snaky Game"

BOARD_SIZES = {
    "regular": {"id": "regular", "label": "Regular (17x15)", "cols": 17, "rows": 15},
    "small":   {"id": "small",   "label": "Small (10x9)",    "cols": 10, "rows": 9},
    "big":     {"id": "big",     "label": "Big (24x21)",     "cols": 24, "rows": 21},
}
BOARD_SIZE_ORDER = ["regular", "small", "big"]

SPEEDS = {
    "snake":  {"id": "snake",  "label": "Normal", "interval_ms": 135.0},
    "rabbit": {"id": "rabbit", "label": "Fast",   "interval_ms": 90.0},
    "turtle": {"id": "turtle", "label": "Slow",   "interval_ms": 195.0},
}
SPEED_ORDER = ["snake", "rabbit", "turtle"]

FOOD_COUNTS = {
    "1":    {"id": "1",    "label": "1",    "count": 1, "is_dice": False},
    "3":    {"id": "3",    "label": "3",    "count": 3, "is_dice": False},
    "5":    {"id": "5",    "label": "5",    "count": 5, "is_dice": False},
    "dice": {"id": "dice", "label": "Dice", "count": 1, "is_dice": True},
}
FOOD_COUNT_ORDER = ["1", "3", "5", "dice"]

FOOD_TYPES = {
    "apple":      {"id": "apple",      "label": "Apple",      "color": (231, 71, 29)},
    "banana":     {"id": "banana",     "label": "Banana",     "color": (247, 201, 39)},
    "pineapple":  {"id": "pineapple",  "label": "Pineapple",  "color": (234, 179, 8)},
    "grapes":     {"id": "grapes",     "label": "Grapes",     "color": (139, 66, 217)},
    "cherry":     {"id": "cherry",     "label": "Cherry",     "color": (217, 27, 66)},
    "watermelon": {"id": "watermelon", "label": "Watermelon", "color": (232, 56, 79)},
    "strawberry": {"id": "strawberry", "label": "Strawberry", "color": (242, 43, 63)},
    "orange":     {"id": "orange",     "label": "Orange",     "color": (250, 139, 20)},
    "random":     {"id": "random",     "label": "Random",     "color": (231, 71, 29)},
}
FOOD_TYPE_ORDER = [
    "apple", "banana", "pineapple", "grapes", "cherry",
    "watermelon", "strawberry", "orange", "random",
]
CONCRETE_FOOD_KEYS = [
    "apple", "banana", "pineapple", "grapes", "cherry",
    "watermelon", "strawberry", "orange",
]

SNAKE_COLORS = {
    "blue":   {"id": "blue",   "label": "Blue",   "head": (79, 120, 248),  "tail": (62, 102, 228),  "outline": (54, 92, 210),  "mouth": (24, 54, 142),  "pupil": (17, 63, 167)},
    "cyan":   {"id": "cyan",   "label": "Cyan",   "head": (34, 196, 232),  "tail": (22, 162, 202),  "outline": (16, 132, 168), "mouth": (10, 82, 108),  "pupil": (10, 74, 102)},
    "purple": {"id": "purple", "label": "Purple", "head": (142, 92, 246),  "tail": (114, 64, 216),  "outline": (88, 46, 178),  "mouth": (54, 24, 114),  "pupil": (48, 20, 102)},
    "pink":   {"id": "pink",   "label": "Pink",   "head": (212, 96, 208),  "tail": (182, 66, 178),  "outline": (148, 46, 144), "mouth": (96, 24, 92),   "pupil": (84, 20, 82)},
    "red":    {"id": "red",    "label": "Red",    "head": (232, 66, 66),   "tail": (192, 42, 42),   "outline": (154, 28, 28),  "mouth": (96, 16, 16),   "pupil": (86, 16, 16)},
    "orange": {"id": "orange", "label": "Orange", "head": (245, 132, 36),  "tail": (216, 100, 20),  "outline": (176, 76, 14),  "mouth": (110, 44, 10),  "pupil": (92, 36, 10)},
    "yellow": {"id": "yellow", "label": "Yellow", "head": (242, 192, 34),  "tail": (214, 154, 18),  "outline": (176, 120, 12), "mouth": (112, 72, 8),   "pupil": (94, 58, 8)},
    "green":  {"id": "green",  "label": "Green",  "head": (66, 178, 78),   "tail": (48, 148, 60),   "outline": (36, 118, 46),  "mouth": (20, 74, 28),   "pupil": (18, 66, 26)},
    "black":  {"id": "black",  "label": "Black",  "head": (38, 42, 48),    "tail": (20, 22, 26),    "outline": (12, 14, 17),   "mouth": (10, 11, 14),   "pupil": (15, 17, 21)},
}
SNAKE_COLOR_ORDER = ["blue", "cyan", "purple", "pink", "red", "orange", "yellow", "green", "black"]

THEMES = {
    "classic": {
        "id": "classic",
        "label": "Day",
        "top_bar": (74, 117, 44),
        "border": (87, 138, 52),
        "light_cell": (170, 215, 81),
        "dark_cell": (162, 209, 73),
        "shadow": (130, 175, 55),
        "card_sky": (77, 193, 249),
        "grass_light": (166, 217, 72),
        "grass_dark": (142, 204, 58),
    },
    "night": {
        "id": "night",
        "label": "Night",
        "top_bar": (38, 50, 56),
        "border": (46, 61, 68),
        "light_cell": (59, 77, 86),
        "dark_cell": (51, 67, 75),
        "shadow": (34, 46, 52),
        "card_sky": (42, 111, 168),
        "grass_light": (59, 77, 86),
        "grass_dark": (51, 67, 75),
    },
    "winter": {
        "id": "winter",
        "label": "Winter",
        "top_bar": (59, 122, 158),
        "border": (76, 146, 186),
        "light_cell": (216, 240, 250),
        "dark_cell": (199, 230, 245),
        "shadow": (152, 195, 217),
        "card_sky": (77, 193, 249),
        "grass_light": (216, 240, 250),
        "grass_dark": (199, 230, 245),
    },
    "volcano": {
        "id": "volcano",
        "label": "Volcano",
        "top_bar": (82, 37, 33),
        "border": (107, 48, 43),
        "light_cell": (110, 82, 79),
        "dark_cell": (94, 68, 65),
        "shadow": (63, 43, 41),
        "card_sky": (184, 74, 57),
        "grass_light": (110, 82, 79),
        "grass_dark": (94, 68, 65),
    },
}
THEME_ORDER = ["classic", "night", "winter", "volcano"]

GRAPHICS_STYLES = {
    "smooth": {"id": "smooth", "label": "Smooth"},
    "pixel":  {"id": "pixel",  "label": "Pixel"},
}
GRAPHICS_STYLE_ORDER = ["smooth", "pixel"]

MODES = [
    {"id": "classic",     "name": "Classic",     "desc": "Eat food to grow. Avoid walls and your own body.", "blendable": False},
    {"id": "wall",        "name": "Wall",        "desc": "Every fruit eaten spawns a brick wall obstacle.", "blendable": True},
    {"id": "portal",      "name": "Portal",      "desc": "Eating a portal fruit teleports you to a partner portal.", "blendable": True},
    {"id": "cheese",      "name": "Cheese",      "desc": "Alternating body segments are gaps you can pass through.", "blendable": True},
    {"id": "noborders",   "name": "No Borders",  "desc": "Wrap seamlessly around opposite board edges.", "blendable": True},
    {"id": "twin",        "name": "Twin",        "desc": "Eating food swaps your head and tail, reversing direction.", "blendable": True},
    {"id": "winged",      "name": "Winged",      "desc": "Food moves around the board and bounces off obstacles.", "blendable": True},
    {"id": "yinyang",     "name": "Yin Yang",    "desc": "Control two mirrored snakes simultaneously.", "blendable": True},
    {"id": "key",         "name": "Key",         "desc": "Collect keys to unlock deadly locked blocks into food.", "blendable": True},
    {"id": "sokoban",     "name": "Sokoban",     "desc": "Push crates onto target tiles to unlock points.", "blendable": True},
    {"id": "poison",      "name": "Poison",      "desc": "Avoid gray poison fruit that triggers random turns.", "blendable": True},
    {"id": "dimension",   "name": "Dimension",   "desc": "Eating shifts between two alternating dimensions.", "blendable": True},
    {"id": "minesweeper", "name": "Minesweeper", "desc": "Mines spawn with a 3x3 countdown danger zone.", "blendable": True},
    {"id": "statue",      "name": "Statue",      "desc": "Eating turns your trailing body into solid stone walls.", "blendable": True},
    {"id": "light",       "name": "Light",       "desc": "Darkened board lit only around your head and pulses.", "blendable": True},
    {"id": "peace",       "name": "Peace",       "desc": "No wall or self-collision deaths; relax and fill the board.", "blendable": True},
    {"id": "blender",     "name": "Blender",     "desc": "Combine two or more game modes simultaneously.", "blendable": False},
]
MODE_MAP = {m["id"]: m for m in MODES}
BLENDABLE_MODES = [m for m in MODES if m["blendable"]]

# UI Reference Exact Colors
UI_CARD_SKY = (77, 193, 249)
UI_SETTINGS_HEADER = (58, 145, 187)
UI_SETTINGS_DIVIDER = (135, 206, 250)
UI_BTN_BLUE = (17, 85, 204)
UI_BTN_BLUE_HOVER = (27, 101, 224)
UI_WHITE = (255, 255, 255)
UI_GOLD = (252, 193, 1)
UI_GOLD_DARK = (232, 174, 0)
UI_GOLD_LIGHT = (255, 213, 79)
UI_TONGUE_RED = (231, 71, 29)
