class MealPlanManager:
    def __init__(self, api, logger):
        self.api = api
        self.logger = logger

    def create_from_recipes(self, recipes, mp_type, date, note=None, share=None):
        if share is None:
            share = []
        for r in recipes:
            self.create(r, mp_type, date, note, share)

    def cleanup_uncooked(self, date, mp_type):
        # get all plans of meal type
        plans = [mp for mp in self.api.get_meal_plans(date, ttl=False) if mp['meal_type']['id'] == mp_type]
        # get all recipes cooked since cleanup date
        cooked_recipes = self.api.get_recipes(params={'cookedon': date.strftime('%Y-%m-%d')}, cache=False)
        # for each plan containing a recipe not cooked since cleanup date - delete the plan
        plans_to_delete = [p for p in plans if p['recipe']['id'] not in [y['id'] for y in cooked_recipes]]
        self.logger.info(f'Deleting {len(plans_to_delete)} meal plans that were not cooked.')
        for plan in plans_to_delete:
            self.api.delete_meal_plan(plan['id'])

    def create(self, recipe, meal_type, date, note, share):
        self.logger.debug(f'Attempting to create mealplan of type {meal_type} for recipe {recipe.name} on {date.strftime("%Y-%m-%d")}')
        self.api.create_meal_plan(
            title=recipe.name,
            recipe=recipe,
            servings=recipe.servings,
            meal_type=meal_type,
            note=note,
            date=date,
            shared=[{'id': x} for x in share]
        )
