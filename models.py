import random
from datetime import datetime


class SetEnabledObjects:
    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f'{self.id}: <{self.name}>'

    def __str__(self):
        return self.name


class Food(SetEnabledObjects):
    def __init__(self, food_json):
        self.id = food_json['id']
        self.name = food_json['name']
        self.shopping = food_json['shopping']
        self.recipe = food_json['recipe']
        self.onhand = food_json['food_onhand']
        self.ignore_shopping = food_json['ignore_shopping']
        self.substitute_onhand = food_json['substitute_onhand']


class Recipe(SetEnabledObjects):
    def __init__(self, json_recipe, get_food=False):
        self.id = json_recipe['id']
        self.name = json_recipe['name']
        self.description = json_recipe['description']
        self.new = json_recipe['new']
        self.servings = json_recipe['servings']
        self.keywords = [kw['id'] for kw in json_recipe['keywords']]
        try:
            self.cookedon = datetime.fromisoformat(json_recipe['last_cooked'])
        except (ValueError, TypeError):
            self.cookedon = None
        self.createdon = datetime.fromisoformat(json_recipe['created_at'])
        self.rating = json_recipe['rating']
        self.ingredients = []  # List of Ingredient objects5

    @staticmethod
    def recipesWithKeyword(recipes, keywords):
        '''
        filters a list of recipes that contain any of a list of keywords
        recipes: list of Recipes
        keywords: list of Keywords

        Returns:
            filtered list of Recipes
        '''
        return [r for r in recipes if any(k in r.keywords for k in [x.id for x in keywords])]

    @staticmethod
    def recipesWithDate(recipes, field, date, after=True):
        '''
        filters a list of recipes based on a date condition
        recipes: list of Recipes
        field: field to compare: either createdon or cookedon
        date: (datetime) date to filter field on
        after: (bool) filter recipes after provided date

        Returns:
            filtered list of Recipes
        '''
        if after:
            return [r for r in recipes if (d := getattr(r, field, None)) is not None and d >= date]

        else:
            return [r for r in recipes if (d := getattr(r, field, None)) is not None and d <= date]

    @staticmethod
    def recipesWithRating(recipes, rating):
        '''
        filters a list of recipes based on rating
        recipes: list of Recipes
        rating: number between -5 and 5.  Negative value implies lessthan comparison.

        Returns:
            filtered list of Recipes
        '''
        lessthan = rating < 0
        if lessthan:
            return [r for r in recipes if 0 < (getattr(r, 'rating', None) or 0) <= abs(rating)]
        else:
            return [r for r in recipes if getattr(r, 'rating', 0) >= rating]

    def addDetails(self, api):
        recipe = api.get_recipe_details(self.id)
        for f in [i['food'] for s in recipe['steps'] for i in s['ingredients']]:
            if not f['food_onhand']:
                onhand_substitutes = api.get_food_substitutes(f['id'], substitute='food')
                if onhand_substitutes:
                    f = api.get_food(random.choice(onhand_substitutes)['id'])
            self.ingredients.append(Food(f))


class Keyword(SetEnabledObjects):
    def __init__(self, json_kw):
        self.id = json_kw['id']
        self.name = json_kw['name']


class Book(SetEnabledObjects):
    def __init__(self, json_bk):
        self.id = json_bk['id']
        self.name = json_bk['name']
        if f := json_bk.get('filter', None):
            self.filter = f.get('id', None)
        else:
            self.filter = None
