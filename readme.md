# Бот для подсчета калорий и воды

## Что реализовано

- Настройка профиля пользователя (/set_profile) - можно указать вес, рост, возраст, уровень активности и город
- Расчет нормы воды с учетом веса, активности и погоды в городе
- Расчет нормы калорий по формуле из ТЗ 
- Логирование воды (/log_water)
- Логирование еды (/log_food) через OpenFoodFacts API + своя база продуктов
- Логирование тренировок (/log_workout) с подсчетом сожженных калорий
- Просмотр прогресса (/check_progress)
- Построение графиков потребления воды и калорий (/show_stats)

## Как запустить

1. Создать файл .env и добавить:
BOT_TOKEN=ваш_токен_бота
WEATHER_API_KEY=ваш_ключ_openweathermap
2. Установить зависимости:
pip install -r requirements.txt
3. Запустить бот:
python bot.py

