import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import os
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import io
import pandas as pd
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from config import BOT_TOKEN, logger
from utils import get_weather, get_food_info
import matplotlib
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

matplotlib.use('Agg')  # Используем не-интерактивный бэкенд
matplotlib.rcParams['font.family'] = 'DejaVu Sans'  # Устанавливаем шрифт по умолчанию

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем входящие сообщения
        user_id = event.from_user.id
        username = event.from_user.username
        text = event.text
        
        logger.info(
            f"Сообщение: Пользователь {user_id} ({username}) отправил: {text}"
        )
        
        # Если это callback query, логируем данные callback
        if hasattr(event, 'data'):
            logger.info(
                f"Кнопка: Пользователь {user_id} ({username}) выбрал: {event.data}"
            )
            
        return await handler(event, data)

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регистрируем middleware
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())

# Состояния FSM
class ProfileStates(StatesGroup):
    waiting_weight = State()
    waiting_height = State()
    waiting_age = State()
    waiting_activity = State()
    waiting_city = State()

class FoodStates(StatesGroup):
    waiting_food_name = State()
    waiting_food_weight = State()

# Состояния для логирования еды
FOOD_NAME, FOOD_WEIGHT = range(5, 7)

# Хранилище данных пользователей (в реальном приложении должна быть база данных)
users = {}

def calculate_water_norm(weight: float, activity_minutes: int, temperature: float) -> float:
    """Рассчитывает норму воды в мл"""
    base = weight * 30  # Базовая норма
    activity_addition = (activity_minutes // 30) * 500  # Дополнительно за активность
    temp_addition = 500 if temperature > 25 else 0  # Дополнительно за жару
    return base + activity_addition + temp_addition

def calculate_calories_norm(weight: float, height: float, age: int, activity_minutes: int) -> float:
    """Рассчитывает норму калорий"""
    base = 10 * weight + 6.25 * height - 5 * age  # Базовая формула
    activity_calories = (activity_minutes / 30) * 100  # Дополнительные калории за активность
    return base + activity_calories

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я помогу тебе отслеживать воду и калории.\n\n"
        "⚙️ Основные команды:\n"
        "/set_profile - Настройка профиля\n"
        "/log_food <название продукта (eng)> - Записать потребление пищи\n"
        "/log_water <кол-во мл> - Записать потребление воды (в мл)\n"
        "/log_workout - Записать тренировку\n"
        "/check_progress - Проверить прогресс\n"
        "/plot_progress - Показать графики прогресса\n"
        "/recommend - Рекомендации продуктов и тренировок\n"
        "/delete_data - Удалить все данные\n\n"
        "Выберите действие с помощью меню ниже или отправьте команду вручную.\n\n"
        "Ваш профиль не настроен. Пожалуйста, настройте его с помощью команды /set_profile."
    )

@dp.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await state.set_state(ProfileStates.waiting_weight)
    await message.answer("Введите ваш вес (в кг):")

@dp.message(ProfileStates.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        await state.update_data(weight=weight)
        await message.answer("Введите ваш рост (в см):")
        await state.set_state(ProfileStates.waiting_height)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
        await state.set_state(ProfileStates.waiting_weight)

@dp.message(ProfileStates.waiting_height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
        await state.update_data(height=height)
        await message.answer("Введите ваш возраст:")
        await state.set_state(ProfileStates.waiting_age)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
        await state.set_state(ProfileStates.waiting_height)

@dp.message(ProfileStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await message.answer("Сколько минут активности у вас в день?")
        await state.set_state(ProfileStates.waiting_activity)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
        await state.set_state(ProfileStates.waiting_age)

@dp.message(ProfileStates.waiting_activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        await state.update_data(activity=activity)
        await message.answer("В каком городе вы находитесь?")
        await state.set_state(ProfileStates.waiting_city)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
        await state.set_state(ProfileStates.waiting_activity)

@dp.message(ProfileStates.waiting_city)
async def process_city(message: Message, state: FSMContext):
    city = message.text
    user_id = str(message.from_user.id)
    
    # Получаем данные из состояния
    data = await state.get_data()
    
    # Сохраняем все данные пользователя
    users[user_id] = {
        'weight': data['weight'],
        'height': data['height'],
        'age': data['age'],
        'activity': data['activity'],
        'city': city,
        'logged_water': 0,
        'logged_calories': 0,
        'burned_calories': 0,
        'water_history': defaultdict(float),
        'calories_history': defaultdict(float),
        'food_preferences': [],
        'workout_history': []
    }
    
    # Рассчитываем нормы
    temp = await get_weather(city)
    water_norm = calculate_water_norm(users[user_id]['weight'], 
                                    users[user_id]['activity'], 
                                    temp)
    calories_norm = calculate_calories_norm(users[user_id]['weight'],
                                          users[user_id]['height'],
                                          users[user_id]['age'],
                                          users[user_id]['activity'])
    
    users[user_id]['water_goal'] = water_norm
    users[user_id]['calorie_goal'] = calories_norm
    
    await message.answer(
        f"Профиль настроен!\n"
        f"Ваша норма воды: {water_norm:.0f} мл\n"
        f"Ваша норма калорий: {calories_norm:.0f} ккал"
    )
    
    await state.clear()

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await message.answer('Настройка профиля отменена.')
    await state.clear()

@dp.message(Command("log_water"))
async def cmd_log_water(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile")
        return

    try:
        amount = int(message.text.split()[1])
        users[user_id]['logged_water'] += amount
        
        today = datetime.now().date()
        users[user_id]['water_history'][today] += amount
        
        remaining = max(0, users[user_id]['water_goal'] - users[user_id]['logged_water'])
        
        await message.answer(
            f"Записано: {amount} мл воды\n"
            f"Осталось выпить: {remaining:.0f} мл"
        )
    except (IndexError, ValueError):
        await message.answer("Используйте команду так: /log_water <количество_в_мл>")

@dp.message(Command("log_food"))
async def cmd_log_food(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    if user_id not in users:
        await message.answer(
            "Сначала настройте профиль с помощью /set_profile"
        )
        return

    await state.set_state(FoodStates.waiting_food_name)
    await message.answer(
        "Какой продукт вы съели? Введите название:"
    )

@dp.message(FoodStates.waiting_food_name)
async def process_food_name(message: Message, state: FSMContext):
    food = message.text
    food_info = await get_food_info(food)
    
    await state.update_data(food_info=food_info)
    await message.answer(
        f"🍴 {food_info['name']} — {food_info['calories']} ккал на 100 г\n"
        f"{food_info['details']}\n"
        f"Сколько грамм вы съели?"
    )
    await state.set_state(FoodStates.waiting_food_weight)

@dp.message(FoodStates.waiting_food_weight)
async def process_food_weight(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    try:
        weight = float(message.text)
        data = await state.get_data()  # ✅ Получаем данные
        food_info = data['food_info']  # ✅ Используем полученные данные
        calories = (food_info['calories'] * weight) / 100
        
        users[user_id]['logged_calories'] += calories
        
        # Добавляем в историю
        today = datetime.now().date()
        users[user_id]['calories_history'][today] += calories
        users[user_id]['food_preferences'].append(food_info['name'])
        
        await message.answer(
            f"Записано: {calories:.1f} ккал"
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
        await state.set_state(FoodStates.waiting_food_weight)

@dp.message(Command("log_workout"))
async def cmd_log_workout(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    if user_id not in users:
        await message.answer(
            "Сначала настройте профиль с помощью /set_profile"
        )
        return

    try:
        workout_type = message.text.split()[1]
        duration = int(message.text.split()[2])
        
        # Простой расчет сожженных калорий
        calories_per_minute = {
            'бег': 10,
            'ходьба': 5,
            'велосипед': 7,
            'плавание': 8,
            'йога': 3,
        }.get(workout_type.lower(), 5)
        
        burned = calories_per_minute * duration
        water_needed = (duration // 30) * 200
        
        users[user_id]['burned_calories'] += burned
        
        await message.answer(
            f"🏃‍♂️ {workout_type.capitalize()} {duration} минут\n"
            f"Сожжено калорий: {burned}\n"
            f"Рекомендуется выпить дополнительно {water_needed} мл воды"
        )
    except (IndexError, ValueError):
        await message.answer(
            "Используйте команду так: /log_workout <тип_тренировки> <время_в_минутах>\n"
            "Например: /log_workout бег 30"
        )

@dp.message(Command("check_progress"))
async def cmd_check_progress(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    if user_id not in users:
        await message.answer(
            "Сначала настройте профиль с помощью /set_profile"
        )
        return

    user = users[user_id]
    water_remaining = max(0, user['water_goal'] - user['logged_water'])
    net_calories = user['logged_calories'] - user['burned_calories']
    calories_remaining = max(0, user['calorie_goal'] - net_calories)

    await message.answer(
        "📊 Прогресс:\n\n"
        "Вода:\n"
        f"- Выпито: {user['logged_water']} мл из {user['water_goal']:.0f} мл\n"
        f"- Осталось: {water_remaining:.0f} мл\n\n"
        "Калории:\n"
        f"- Потреблено: {user['logged_calories']:.0f} ккал из {user['calorie_goal']:.0f} ккал\n"
        f"- Сожжено: {user['burned_calories']:.0f} ккал\n"
        f"- Баланс: {net_calories:.0f} ккал\n"
        f"- Осталось до цели: {calories_remaining:.0f} ккал"
    )

@dp.message(Command("plot_progress"))
async def cmd_plot_progress(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile")
        return

    # Проверяем наличие данных
    if not users[user_id]['water_history'] and not users[user_id]['calories_history']:
        await message.answer(
            "Пока нет данных для построения графиков. "
            "Добавьте информацию о потреблении воды и еды!"
        )
        return

    # Создаем график
    plt.style.use('bmh')  # Используем встроенный стиль matplotlib
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # График воды
    dates = list(users[user_id]['water_history'].keys())
    water_amounts = list(users[user_id]['water_history'].values())
    
    if dates and water_amounts:
        ax1.plot(dates, water_amounts, 'b-o', label='Потребление воды', linewidth=2, markersize=8)
        ax1.axhline(y=users[user_id]['water_goal'], color='r', linestyle='--', label='Цель')
        ax1.fill_between(dates, water_amounts, alpha=0.3, color='blue')
    
    ax1.set_title('Прогресс потребления воды', pad=20)
    ax1.set_ylabel('мл')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # График калорий
    calories_dates = list(users[user_id]['calories_history'].keys())
    calories_amounts = list(users[user_id]['calories_history'].values())
    
    if calories_dates and calories_amounts:
        ax2.plot(calories_dates, calories_amounts, 'g-o', label='Потребление калорий', linewidth=2, markersize=8)
        ax2.axhline(y=users[user_id]['calorie_goal'], color='r', linestyle='--', label='Цель')
        ax2.fill_between(calories_dates, calories_amounts, alpha=0.3, color='green')
    
    ax2.set_title('Прогресс потребления калорий', pad=20)
    ax2.set_ylabel('ккал')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Общие настройки
    plt.tight_layout()
    
    # Поворачиваем метки дат для лучшей читаемости
    for ax in [ax1, ax2]:
        ax.tick_params(axis='both', which='major')
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    # Сохраняем график
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    
    # Создаем BufferedInputFile из буфера
    photo = BufferedInputFile(buf.getvalue(), filename="progress.png")
    await message.answer_photo(photo)
    
    # Очищаем память
    plt.close('all')
    buf.close()

@dp.message(Command("get_recommendations"))
async def cmd_get_recommendations(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile")
        return

    user = users[user_id]
    net_calories = user['logged_calories'] - user['burned_calories']
    water_progress = (user['logged_water'] / user['water_goal']) * 100

    recommendations = []

    # Рекомендации по воде
    if water_progress < 50:
        recommendations.append("🚰 Вы выпили меньше половины дневной нормы воды. "
                             "Рекомендуется выпить стакан воды прямо сейчас!")

    # Рекомендации по калориям
    if net_calories > user['calorie_goal']:
        recommendations.extend([
            "🏃‍♂️ Рекомендуемые тренировки для сжигания калорий:",
            "- Бег (30 минут) - сожжет примерно 300 ккал",
            "- Плавание (45 минут) - сожжет примерно 400 ккал",
            "\n🥗 Низкокалорийные продукты:",
            "- Огурцы (15 ккал/100г)",
            "- Листовой салат (12 ккал/100г)",
            "- Томаты (20 ккал/100г)"
        ])
    elif net_calories < user['calorie_goal'] * 0.5:
        recommendations.extend([
            "🍎 Рекомендуемые продукты для набора калорий:",
            "- Бананы (89 ккал/100г)",
            "- Авокадо (160 ккал/100г)",
            "- Орехи (600 ккал/100г)"
        ])

    # Анализ предпочтений пользователя
    if user['food_preferences']:
        favorite_foods = pd.Series(user['food_preferences']).value_counts().head(3)
        recommendations.append("\n👍 Ваши любимые продукты:")
        for food, count in favorite_foods.items():
            recommendations.append(f"- {food} (использовано {count} раз)")

    await message.answer("\n".join(recommendations))

async def main():
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main()) 