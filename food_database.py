FOOD_DATABASE = {
    "молоко": {
        "calories": 42,
        "protein": 3.4,
        "fat": 1.0,
        "carbs": 4.7,
        "aliases": ["молочко", "milk", "молоко коровье"],
        "serving_size": 200  # мл
    },
    "яйцо": {
        "calories": 157,
        "protein": 13,
        "fat": 11,
        "carbs": 1.1,
        "aliases": ["яйца", "egg", "яйцо куриное"],
        "serving_size": 1  # штука
    },
    "банан": {
        "calories": 89,
        "protein": 1.1,
        "fat": 0.3,
        "carbs": 22.8,
        "aliases": ["banana", "бананы"],
        "serving_size": 100  # грамм
    },
    "гречка": {
        "calories": 343,
        "protein": 12.6,
        "fat": 3.3,
        "carbs": 68,
        "aliases": ["греча", "гречневая крупа", "buckwheat"],
        "serving_size": 100  # грамм (сухой вес)
    },
    "куриная грудка": {
        "calories": 165,
        "protein": 31,
        "fat": 3.6,
        "carbs": 0,
        "aliases": ["курица", "chicken breast", "грудка"],
        "serving_size": 100  # грамм
    },
    "овсянка": {
        "calories": 68,
        "protein": 2.4,
        "fat": 1.4,
        "carbs": 12,
        "aliases": ["овсяная каша", "oatmeal", "овсяные хлопья"],
        "serving_size": 100  # грамм (готовой каши)
    }
}

def search_food(query: str) -> dict:  # переименовываем из smart_food_search
    """Поиск продукта в базе"""
    query = query.lower()
    best_match = None
    best_score = 0
    
    for food_name, food_data in FOOD_DATABASE.items():
        # Простое сравнение
        if query == food_name.lower():
            return {
                "name": food_name,
                "calories": food_data["calories"],
                "protein": food_data["protein"],
                "fat": food_data["fat"],
                "carbs": food_data["carbs"],
                "serving_size": food_data["serving_size"]
            }
        
        # Проверка альтернативных названий
        for alt_name in food_data["aliases"]:
            if query == alt_name.lower():
                return {
                    "name": food_name,
                    "calories": food_data["calories"],
                    "protein": food_data["protein"],
                    "fat": food_data["fat"],
                    "carbs": food_data["carbs"],
                    "serving_size": food_data["serving_size"]
                }
    return None 