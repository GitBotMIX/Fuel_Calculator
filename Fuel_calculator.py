import os
import re
import speech_recognition as sr
from pydub import AudioSegment
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fuzzywuzzy import process

# Данные о машинах
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

keywords = {
    "brand": ["маз", "зил"],
    "model": ["5434", "5337", "131", "130"],
    "distance": ["километр", "расстояние", "проехал"],
    "idle_time": ["без насоса", "работа без насоса", "время без насоса", "холостой ход"],
    "initial_fuel": ["топливо до выезда", "начальный уровень топлива", "остаток перед выездом", 'топливо в баке', "топлива до выезда",]
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
            match = re.search(rf"{word}\s*(\d+)(?:\s+(\d+))?", command)
            if match:
                first_number_str = match.group(1)  # Строковое представление первого числа
                
                # Проверяем, является ли первое число float
                if '.' in first_number_str:
                    return float(first_number_str)
                else:
                    # Преобразуем первое число в целое
                    first_number = int(first_number_str)
                    
                    # Если есть второе число после пробела, добавляем его как дробную часть
                    if match.group(2):  # Проверка на наличие второго числа
                        second_number = match.group(2)  # Строка второго числа
                        combined_number = float(f"{first_number}.{second_number}")
                        return combined_number
                    else:
                        # Если второго числа нет, возвращаем первое число как float
                        return float(first_number)
    return None

# Функция для извлечения информации из команды
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

# Функция для вычислений
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

# Обработка голосового сообщения
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Скачиваем голосовое сообщение
    voice = await update.message.voice.get_file()
    await voice.download_to_drive("voice.ogg")
    
    # Конвертируем в формат .wav для распознавания речи
    sound = AudioSegment.from_ogg("voice.ogg")
    sound.export("voice.wav", format="wav")
    
    # Распознаем речь с помощью speech_recognition
    recognizer = sr.Recognizer()
    with sr.AudioFile("voice.wav") as source:
        audio = recognizer.record(source)
        try:
            command = recognizer.recognize_google(audio, language="ru-RU")
            brand, model, distance, idle_time, initial_fuel = parse_command(command)
            await update.message.reply_text(f"Распознанная команда: {command}")
            if brand and model:
                try:
                    remaining_fuel, total_fuel_used = calculate_fuel(brand, model, distance, idle_time, initial_fuel)
                except Exception as e:
                    calculator_error = calculate_fuel(brand, model, distance, idle_time, initial_fuel)
                    await update.message.reply_text(f"{calculator_error}")
                    return
                print(f"Потраченное топливо: {total_fuel_used:.3f} литров")
                print(f"Остаток топлива: {remaining_fuel:.3f} литров")
            else:
                print("Марка или модель не распознаны.")
                print("Запрашиваемая команда: {command}")
            # Отправляем результат
            result_message = (
                
                f"Потраченное топливо: {total_fuel_used:.3f} литров\n"
                f"Остаток топлива: {remaining_fuel:.3f} литров"
            )
            await update.message.reply_text(result_message)
        except sr.UnknownValueError:
            await update.message.reply_text("Не удалось распознать речь.")
        except sr.RequestError:
            await update.message.reply_text("Ошибка при запросе к сервису распознавания.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при обработке команды: {e}")
    
    # Удаляем временные файлы
    os.remove("voice.ogg")
    os.remove("voice.wav")

# Команда старт для приветствия
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Отправьте голосовое сообщение с командой для расчёта топлива.")
    
async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(update.message.text)
        # Скачиваем голосовое сообщение
    try:
        command = update.message.text
        await update.message.reply_text(f"Команда: {command}")
            
            # Парсим команду
        car, distance, idle_time, initial_fuel = parse_command(command)
            
            # Выполняем расчёт
        remaining_fuel, total_fuel_used = calculate_fuel(car, distance, idle_time, initial_fuel)
            
            # Отправляем результат
        result_message = (
            f"Потраченное топливо: {total_fuel_used:.3f} литров\n"
            f"Остаток топлива: {remaining_fuel:.3f} литров"
        )
        await update.message.reply_text(result_message)
    except sr.UnknownValueError:
            await update.message.reply_text("Не удалось распознать речь.")
    except sr.RequestError:
        await update.message.reply_text("Ошибка при запросе к сервису распознавания.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при обработке команды: {e}")


# Основная функция для запуска бота
def main():
    # Ваш токен, полученный от BotFather
    token = "7036265580:AAECGBqOXYCJAkN-TYawvYm0--O1STkZ12Y"
    
    application = Application.builder().token(token).build()
    
    # Обработчики команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
