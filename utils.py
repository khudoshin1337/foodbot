import aiohttp
from config import WEATHER_API_KEY, FOOD_API_KEY, logger

async def get_weather(city: str) -> float:
    """Получение температуры для города через API"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    temp = data['main']['temp']
                    logger.info(f"Получена температура для города {city}: {temp}°C")
                    return temp
                else:
                    logger.error(f"Ошибка при получении погоды: {response.status}")
                    return 20.0 # Возвращаем среднюю температуру по умолчанию
        except Exception as e:
            logger.error(f"Ошибка при получении погоды: {e}")
            return 20.0

async def get_food_info(food_name: str) -> dict:
    """Получение информации о продукте через USDA API"""
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": "iYNcjx3WdiVo8iHPixsQjsTyVNWvBeuyB0EDeYW3",
        "query": food_name,
        "pageSize": 1,
        "dataType": ["Survey (FNDDS)"]  # Используем базу данных FNDDS для обычных продуктов
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['foods']:
                        food = data['foods'][0]
                        nutrients = food.get('foodNutrients', [])
                        
                        # Ищем калории (Energy)
                        calories = next(
                            (n['value'] for n in nutrients 
                             if n.get('nutrientName', '').lower().startswith('energy')),
                            0
                        )
                        
                        return {
                            'name': food.get('description', food_name),
                            'calories': calories,
                            'details': f"Порция: {food.get('servingSize', 100)}г",
                            'success': True
                        }
                    
                logger.warning(f"Продукт {food_name} не найден в USDA API, использую локальную базу")
                # Если не нашли в API, используем локальную базу
                from food_database import search_food
                local_food = search_food(food_name)
                if local_food:
                    return {
                        'name': local_food['name'],
                        'calories': local_food['calories'],
                        'details': f"Белки: {local_food['protein']}г, Жиры: {local_food['fat']}г, Углеводы: {local_food['carbs']}г",
                        'success': True
                    }
                
                return {
                    'name': food_name.capitalize(),
                    'calories': 100,
                    'details': 'Информация не найдена',
                    'success': False
                }
                    
        except Exception as e:
            logger.error(f"Ошибка при получении информации о продукте: {e}")
            return {
                'name': food_name.capitalize(),
                'calories': 100,
                'details': 'Произошла ошибка при получении информации',
                'success': False
            } 