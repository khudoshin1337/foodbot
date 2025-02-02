from dataclasses import dataclass
from typing import Dict, List

@dataclass
class UserProfile:
    user_id: int
    weight: float 
    height: float
    age: int
    activity_minutes: int
    city: str
    water_goal: float = 0
    calorie_goal: float = 0
    logged_water: float = 0
    logged_calories: float = 0
    burned_calories: float = 0
    food_log: List[Dict] = None
    workout_log: List[Dict] = None

    def __post_init__(self):
        if self.food_log is None:
            self.food_log = []
        if self.workout_log is None:
            self.workout_log = [] 