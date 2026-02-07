import json
import logging
import os
import sys

import configargparse
import yaml

from mealplan import MealPlanManager
from models import Book, Food, Keyword, Recipe
from solver import RecipePicker
from tandoor_api import TandoorAPI
from utils import format_date, setup_logging, str2bool


class Menu:

    def __init__(self, options):
        self.options = options
        self.include_children = self.options.include_children
        self.logger = setup_logging(log=self.options.log)
        self.tandoor = TandoorAPI(self.options.url, self.options.token, self.logger, cache=int(self.options.cache))
        self.choices = int(self.options.choices)
        self.recipes = []
        self.selected_recipes = []
        self.recipe_picker = None
        self.keyword_constraints = []
        self.food_constraints = []
        self.book_constraints = []
        self.rating_constraints = []
        self.cookedon_constraints = []
        self.createdon_constraints = []

        self._format_constraints()

    def _format_constraints(self):
        constraints = ['book', 'food', 'keyword', 'rating', 'cookedon', 'createdon']
        for c in constraints:
            setattr(self, f'{c}_constraints', [json.loads(x.replace("'", '"')) for x in getattr(self.options, c, [])])
            for x in getattr(self, f'{c}_constraints', []):
                x['count'] = int(x['count'])
                if y := x.get('cooked', None):
                    x['cooked'], x['cooked_after'] = format_date(y)
                if y := x.get('created', None):
                    x['created'], x['created_after'] = format_date(y)

    def prepare_recipes(self):
        if not self.options.recipes and not self.options.filters and not self.options.plan_type:
            for r in self.tandoor.get_recipes(all_recipes=True):
                self.recipes.append(Recipe(r))
        else:
            for r in self.tandoor.get_recipes(params=self.options.recipes, filters=self.options.filters):
                self.recipes.append(Recipe(r))
            for r in self.tandoor.get_mealplan_recipes(mealtype_id=self.options.plan_type, date=self.options.mp_date, params=self.options.recipes):
                self.recipes.append(Recipe(r))
        self.recipes = list(set(self.recipes))

    def prepare_books(self):
        for constraint in self.book_constraints:
            if not isinstance(c := constraint['condition'], list):
                constraint['condition'] = [c]
            if not isinstance(c := constraint.get('except', []), list):
                constraint['except'] = [c]

            book_list = []
            for bk in constraint['condition']:
                book_list.append(Book(self.tandoor.get_book(bk)))
            constraint['condition'] = book_list

            book_list = []
            for bk in constraint.get('except', []):
                book_list.append(Book(self.tandoor.get_book(bk)))
            constraint['except'] = book_list

            found_recipes = []
            for bk in constraint['condition']:
                for r in self.tandoor.get_book_recipes(bk):
                    found_recipes.append(Recipe(r))

            if cooked := constraint.get('cooked', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'cookedon', cooked, constraint.get('cooked_after', False))
            if created := constraint.get('created', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'createdon', created, constraint.get('created_after', False))
            # TODO I don't like overwriting the condition with the results of that condition
            constraint['condition'] = found_recipes

    def prepare_foods(self):
        for constraint in self.food_constraints:
            if not isinstance(c := constraint['condition'], list):
                constraint['condition'] = [c]
            if not isinstance(c := constraint.get('except', []), list):
                constraint['except'] = [c]

            food_list = []
            for fd in constraint['condition']:
                food_list.append(Food(self.tandoor.get_food(fd)))
            constraint['condition'] = food_list

            food_list = []
            for fd in constraint.get('except', []):
                food_list.append(Food(self.tandoor.get_food(fd)))
            constraint['except'] = food_list

            # recipe api doesn't include ingredients, so get a list of ingredients with the food
            params = {
                'foods_or': [f.id for f in constraint['condition']],
                'foods_or_not': [f.id for f in constraint['except']]
            }
            found_recipes = []
            for r in self.tandoor.get_recipes(params=params):
                found_recipes.append(Recipe(r))
            if cooked := constraint.get('cooked', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'cookedon', cooked, constraint.get('cooked_after', False))
            if created := constraint.get('created', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'createdon', created, constraint.get('created_after', False))
            # TODO I don't like overwriting the condition with the results of that condition
            constraint['condition'] = found_recipes

    def prepare_keywords(self):
        # TODO add 'except' condition to list of keywords
        for constraint in self.keyword_constraints:
            if not isinstance(c := constraint['condition'], list):
                constraint['condition'] = [c]
            if not isinstance(c := constraint.get('except', []), list):
                constraint['except'] = [c]
            kw_tree = []
            if self.include_children:
                for kw in constraint['condition']:
                    kw_tree += self.tandoor.get_keyword_tree(kw)
            else:
                for kw in constraint['condition']:
                    kw_tree.append(self.tandoor.get_food(kw))
            constraint['condition'] = list(set([Keyword(k) for k in kw_tree]))

    def prepare_data(self):
        self.prepare_recipes()
        self.prepare_keywords()
        self.prepare_foods()
        self.prepare_books()

    def select_recipes(self):
        self.recipe_picker = RecipePicker(self.recipes, self.choices, logger=self.logger)
        # add keyword constraints
        for c in self.keyword_constraints:
            exclude = str2bool(c.get('exclude', False))
            found_recipes = Recipe.recipesWithKeyword(self.recipes, c['condition'])
            if cooked := c.get('cooked', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'cookedon', cooked, c.get('cooked_after', False))
            if created := c.get('created', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'createdon', created, c.get('created_after', False))
            self.recipe_picker.add_keyword_constraint(found_recipes, c['count'], c['operator'], exclude=exclude)

        # add food constraints
        for c in self.food_constraints:
            exclude = str2bool(c.get('exclude', False))
            self.recipe_picker.add_food_constraint(c['condition'], c['count'], c['operator'], exclude=exclude)

        # add book constraints
        for c in self.book_constraints:
            exclude = str2bool(c.get('exclude', False))
            self.recipe_picker.add_book_constraint(c['condition'], c['count'], c['operator'], exclude=exclude)

        # add rating contraints
        for c in self.rating_constraints:
            exclude = str2bool(c.get('exclude', False))
            found_recipes = self.recipes
            if cooked := c.get('cooked', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'cookedon', cooked, after=c.get('cooked_after', False))
            if created := c.get('created', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'createdon', created, after=c.get('created_after', False))
            self.recipe_picker.add_rating_constraints(Recipe.recipesWithRating(found_recipes, c.get('condition')), c['count'], c['operator'], exclude=exclude)

        # add cookedon constraints
        for c in self.cookedon_constraints:
            exclude = str2bool(c.get('exclude', False))
            d, a = format_date(c['condition'])
            found_recipes = Recipe.recipesWithDate(self.recipes, 'cookedon', d, after=a)
            if created := c.get('created', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'createdon', created, after=c.get('created_after', False))
            self.recipe_picker.add_cookedon_constraints(found_recipes, c['count'], c['operator'], exclude=exclude)

        # add createdon constraints
        for c in self.createdon_constraints:
            exclude = str2bool(c.get('exclude', False))
            d, a = format_date(c['condition'])
            found_recipes = Recipe.recipesWithDate(self.recipes, 'createdon', d, after=a)
            if cookedon := c.get('cookedon', None):
                found_recipes = Recipe.recipesWithDate(found_recipes, 'cookedon', cookedon, after=c.get('cookedon_after', False))
            self.recipe_picker.add_createdon_constraints(found_recipes, c['count'], c['operator'], exclude=exclude)

        self.selected_recipes = self.recipe_picker.solve()
        return self.selected_recipes

    def generate_menu_file(self, recipes):
        from menu import MenuGenerator
        self.logger.info('Generating menu file, this may take awhile.')
        menu_gen = MenuGenerator(self.tandoor, self.options, self.logger)
        menu_gen.write_menu(recipes)


def parse_args():
    parser = configargparse.ArgParser(
        config_file_parser_class=configargparse.ConfigparserConfigFileParser,
        description='Create a custom menu from recipes in Tandoor with defined criteria.'
    )
    # application related switches
    parser.add_argument('-c', '--my-config', is_config_file=True, default='config.ini', help='Specify configuration file.')
    parser.add_argument('--log', default='info', help='Sets the logging level')
    parser.add_argument('--cache', default='240', help='Minutes to cache Tandoor API results; 0 to disable.')
    parser.add_argument('--url', type=str, required=True, help='The full url of the Tandoor server, including protocol, name, port and path')
    parser.add_argument('--token', type=str, required=True, help='Tandoor API token.')
    # solver related switches
    parser.add_argument('--recipes', type=yaml.safe_load, help='recipes to choose from; search parameters, see /docs/api/ for full list of parameters')
    parser.add_argument('--filters', nargs='*', default=[], help='Array of CustomFilter IDs')
    parser.add_argument('--plan_type', nargs='*', default=[], help='Array of MealType IDs')
    parser.add_argument('--choices', default=5, help='Number of recipes to choose')
    parser.add_argument('--book', nargs='*', default=[], help="Conditions are all list of dicts of the format {'condition':xx, 'count':yy, 'operator': [>= or <= or ==]}")
    parser.add_argument('--food', nargs='*', default=[], help='Condition = ID or list of IDs')
    parser.add_argument('--keyword', nargs='*', default=[], help="e.g. [{'condition':[73, 273],'count':'1', 'operator':'>='},{'condition':47,'count':'2','operator':'=='}]")
    parser.add_argument('--rating', nargs='*', default=[], help='condition = number between 0 and 5')
    parser.add_argument('--cookedon', nargs='*', default=[], help="condition = date in YYYY-MM-DD format (use 'XXdays' for relative date XX days ago)")
    parser.add_argument('--createdon', nargs='*', default=[], help="condition = date in YYYY-MM-DD format (use 'XXdays' for relative date XX days ago)")
    parser.add_argument('--include_children', action='store_true', default=True, help='For keywords and foods, child objects also satisfy the condition.')
    # mealplan related switches
    parser.add_argument('--create_mp', action='store_true', default=False, help='Add mealplans for chosen recipes.')
    parser.add_argument('--share_with', nargs='*', default=[], help='Share mealplan with ID(s).')
    parser.add_argument('--mp_date', type=str, default='0days', help='Date to create mealplan in YYYY-MM-DD format or XXdays.')
    parser.add_argument('--mp_type', help='ID of meal plan type; separate mealplan types are strongly encouraged.')
    parser.add_argument('--mp_note', type=str, default='Created by: Tandoor Menu Generator.')
    parser.add_argument('--cleanup_mp', action='store_true', default=False, help='Delete uncooked mealplans at next execution.')
    parser.add_argument('--cleanup_date', type=str, default='-7days', help='Starting date to cleanup uncooked mealplans in YYYY-MM-DD format or -XXdays.')
    # menu file creation related switches
    parser.add_argument('--create_file', action='store_true', default=False, help='Create a menu from an SVG template.')
    parser.add_argument('--file_format', type=str, default='PNG', help='File format to save the menu. Options: GIF, JPG, PNG, PDF.')
    parser.add_argument('--output_dir', type=str, help='Defaults to template dir.  Full path required.')
    parser.add_argument('--file_template', type=str, help='Name of SVG file located in templates/ directory.')
    parser.add_argument('--fonts', nargs='*', default=[], help='Non-system fonts required for the SVG template.')
    parser.add_argument('--replace_text', type=yaml.safe_load, help='Text to search for in the template and replace with menu details.')
    parser.add_argument('--separator', type=str, default=' - ', help='Separator to use when concatenating ingredients.')

    args = parser.parse_args()
    args.separator = args.separator.replace("'", "").replace('"', '')
    return args


def validate_args(args):
    valid = True
    args.mp_date, _ = format_date(args.mp_date, future=True)
    if not args.output_dir:
        args.output_dir = os.path.join(os.getcwd(), 'templates')
    if args.create_mp:
        if not (args.mp_date and args.mp_type):
            valid = False
            raise RuntimeError('When "create_mp" is enabled, both "mp_date" and "mp_type" must be provided.')
        try:
            args.mp_type = int(args.mp_type)
        except (ValueError, TypeError):
            valid = False
            raise RuntimeError('"mp_type" must be a valid Meal Type ID.')
        if args.cleanup_mp:
            args.cleanup_date, _ = format_date(args.cleanup_date)
            print(f'Uncooked meal plans will be cleaned up beginning on {args.cleanup_date.strftime("%Y-%m-%d")} with meal type {args.mp_type}.')
        print(f'Meal plan creation enabled.  Recipes will be added on {args.mp_date.strftime("%Y-%m-%d")} with meal type {args.mp_type}.')
    return valid


if __name__ == "__main__":
    args = parse_args()
    validate_args(args)
    menu = Menu(args)
    for arg in args._get_kwargs():
        menu.logger.debug(f'Argument {arg[0]}: {arg[1]}')
    menu.prepare_data()

    if len(menu.recipes) < menu.choices:
        menu.logger.info(f"Not enough recipes to generate a menu.  Only {len(menu.recipes)} recipes to work with.")
        sys.exit(1)

    recipes = menu.select_recipes()

    menu.logger.info(f'Selected {len(recipes)} recipes for the menu.')
    if menu.logger.loglevel == logging.DEBUG:
        for r in recipes:
            date_cooked = (x := getattr(r, 'cookedon', None)) and x.strftime("%Y-%m-%d") or "Never"
            menu.logger.debug(f'Selected recipe {r} for the menu with rating {r.rating}. Created on: {r.createdon.strftime("%Y-%m-%d")} and last cooked {date_cooked}')
            kw_list = []
            for kw in r.keywords:
                kw_list.append(kw)
            menu.logger.debug(f'Selected recipe {r} contains keywords {kw_list}.')

    print('\n\n###########################\nYour selected recipes are:')
    for r in recipes:
        print(f'Recipe: <{r.id}> {r.name}: {menu.tandoor.url.replace("/api/","/view/recipe/")}{r.id}')

    print('###########################\n')
    if args.create_mp:
        mpm = MealPlanManager(menu.tandoor, menu.logger)
        if args.cleanup_mp:
            mpm.cleanup_uncooked(date=args.cleanup_date, mp_type=args.mp_type)
        mpm.create_from_recipes(recipes, args.mp_type, date=args.mp_date, note=args.mp_note, share=args.share_with)

    if args.create_file:
        menu.generate_menu_file(recipes)

    if menu.tandoor.progress:
        menu.tandoor.progress.last_step()
        menu.tandoor.progress.close()
