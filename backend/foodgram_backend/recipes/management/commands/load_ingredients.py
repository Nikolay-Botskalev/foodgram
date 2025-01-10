import json
from django.core.management.base import BaseCommand
from recipes.models import Ingredients


class Command(BaseCommand):
    help = 'Загружает ингредиенты из JSON-файла в базу данных'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help="Путь к json файлу")

    def handle(self, *args, **options):
        file_path = options['file_path']

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл {file_path} не найден.'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Ошибка декодирования JSON в файле {file_path}.'))
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
                self.stdout.write(self.style.SUCCESS(
                    f'Ингредиент {name} создан/обновлен'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'Пропущен ингредиент {ingredient_data}'))
            self.stdout.write(self.style.SUCCESS(
                f'Загрузка завершена. Создано {created_count} новых, обновлено {updated_count}'))
