import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredients

ROUTE = 'recipes/management/commands/ingredients.json'


class Command(BaseCommand):
    """Команда на добавление ингредиентов в БД."""

    def handle(self, *args, **options):
        file_path = ROUTE

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(
                f'Ошибка декодирования JSON в файле {file_path!r}.'))
            return

        created_count = 0
        updated_count = 0
        for ingredient_data in data:
            name = ingredient_data.get('name')
            measurement_unit = ingredient_data.get('measurement_unit')
            if name and measurement_unit:
                ingredient, created = Ingredients.objects.get_or_create(
                    name=name, defaults={'measurement_unit': measurement_unit})
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Ингредиент {name} создан/обновлен'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'Пропущен ингредиент {ingredient_data}'))
            self.stdout.write(self.style.SUCCESS(
                f'Загрузка завершена. Создано {created_count} записей, '
                f'обновлено {updated_count} записей.'))
