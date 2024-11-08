import re
from fuzzywuzzy import process

# Данные о машинах
cars_data = { 
    "маз": {
        "5434": {
            'fuel_per_km': 0.447,
            "fuel_per_min": 0.066
            },
        "5337": {
            'fuel_per_km': 0.666,
            "fuel_per_min": 0.105
            },
    },
    "зил": {
        "131": {
            'fuel_per_km': 0.800,
            "fuel_per_min": 0.234
        },
        "130": {
            'fuel_per_km': 0.774,
            "fuel_per_min": 0.203
        },
    },
}


command = "маз 5337 без холостой ход 7 мин"
# Синонимы для разных команд и данных
keywords = {
    "brand": ["маз", "зил"],
    "model": ["5434", "5337", "131", "130"],
    "distance": ["километр", "расстояние", "проехал"],
    "idle_time": ["без насоса", "работа без насоса", "время без насоса", "холостой ход"],
    "initial_fuel": ["топливо до выезда", "начальный уровень топлива", "остаток перед выездом", 'топливо в баке']
}


def find_closest_word(input_word, possible_words):
    """Находит наиболее похожее слово из возможных, используя fuzzy matching."""
    match, score = process.extractOne(input_word, possible_words)
    return match if score > 10 else None  # Порог схожести — 60

def extract_value_after_keyword(command, keyword_list):
    """Находит ближайшее числовое значение после ключевого слова из списка синонимов."""
    for word in keyword_list:
        if word in command:
            # Ищем ближайшее число после ключевого слова
            match = re.search(rf"{word}\s*(\d+\.?\d*)", command)
            if match:
                return float(match.group(1))
    return None

def parse_command(command):
    """
    Извлекает марку, модель, расстояние, время без насоса и начальный уровень топлива из команды.
    """
    # Преобразуем команду в нижний регистр
    command = command.lower()
    
    # Ищем марку и модель
    brand = find_closest_word(command, keywords["brand"])
    model = find_closest_word(command, keywords["model"])
    
    # Ищем значения для каждого параметра
    distance = extract_value_after_keyword(command, keywords["distance"]) or 0
    idle_time = extract_value_after_keyword(command, keywords["idle_time"]) or 0
    initial_fuel = extract_value_after_keyword(command, keywords["initial_fuel"]) or 0.0
    
    return brand, model, distance, idle_time, initial_fuel

def calculate_fuel(brand, model, distance, idle_time, initial_fuel):
    """Вычисляет расход топлива и остаток."""
    if brand not in cars_data or model not in cars_data[brand]:
        return "Не найдены данные для указанной марки и модели."
    
    # Извлекаем данные о расходе топлива
    fuel_per_km = cars_data[brand][model]["fuel_per_km"]
    fuel_per_min = cars_data[brand][model]["fuel_per_min"]
    
    # Считаем затраты топлива
    fuel_used_for_distance = distance * fuel_per_km
    fuel_used_for_idle = idle_time * fuel_per_min
    total_fuel_used = fuel_used_for_distance + fuel_used_for_idle
    remaining_fuel = initial_fuel - total_fuel_used
    
    return remaining_fuel, total_fuel_used

# Пример использования функции

brand, model, distance, idle_time, initial_fuel = parse_command(command)

# Выполнение расчёта, если данные найдены
if brand and model:
    remaining_fuel, total_fuel_used = calculate_fuel(brand, model, distance, idle_time, initial_fuel)
    print(f"Потраченное топливо: {total_fuel_used:.3f} литров")
    print(f"Остаток топлива: {remaining_fuel:.3f} литров")
else:
    print("Марка или модель не распознаны.")
