"""Файл с определением констант приложения recipes"""


# Пользовательские имена, которые нельзя использовать как username
FORBIDDEN_USERNAME = ('me',)

# Максимальная длина для email
MAX_LENGTH_EMAIL = 254

# Максимальная длина названия ингредиента
MAX_LENGTH_INGREDIENT_NAME = 128

# Максимальная длина для единицы измерения
MAX_LENGTH_MEASUREMENT_UNIT = 64

# Максимальная длина названия рецепта
MAX_LENGTH_RECIPE_NAME = 256

# Максимальная длина названия тега
MAX_LENGTH_TAG_NAME = 32

# Максимальная длина slug
MAX_LENGTH_TAG_SLUG = 32

# Минимальное значение времени приготовления (мин.)
MIN_COOKING_TIME = 1

# Минимальное значение количества ингредиента
MIN_INGREDIENT_AMOUNT = 1
