import logging
import random

from pulp import LpMaximize, LpProblem, LpVariable, lpSum, value
from pulp.apis import PULP_CBC_CMD

VALID_OPERATORS = (">=", "<=", "==")


class RecipePicker:

    def __init__(self, recipes, numrecipes, logger=None):
        self.logger = logger
        self.recipes = recipes
        self.numrecipes = numrecipes
        self.numcriteria = 0

        self.model = LpProblem("RecipePicker", LpMaximize)
        self.recipe_vars = LpVariable.dicts("Recipe", [r.id for r in self.recipes], cat='Binary')
        self.model += lpSum(self.recipe_vars.values()) == self.numrecipes

        # introduce randomness to recipe selection
        self.model += lpSum((10 * random.random()) * self.recipe_vars[r.id] for r in self.recipes)

    def _add_constraint(self, found_recipes, numrecipes, operator, exclude=False, description=''):
        found_recipes = list(set(self.recipes) & set(found_recipes))
        if exclude:
            found_recipes = list(set(self.recipes) - set(found_recipes))

        if operator not in VALID_OPERATORS:
            raise ValueError(f'Invalid constraint operator: {operator}. Valid operators are: {VALID_OPERATORS}')

        if operator == ">=" and len(found_recipes) < numrecipes:
            self.logger.warning(
                f'Constraint "{description} {operator} {numrecipes}" may be infeasible: '
                f'only {len(found_recipes)} matching recipes in pool.'
            )
        if operator == "==" and len(found_recipes) < numrecipes:
            self.logger.warning(
                f'Constraint "{description} {operator} {numrecipes}" may be infeasible: '
                f'only {len(found_recipes)} matching recipes in pool.'
            )

        recipe_sum = lpSum(self.recipe_vars[r.id] for r in found_recipes)
        if operator == ">=":
            self.model += recipe_sum >= numrecipes
        elif operator == "<=":
            self.model += recipe_sum <= numrecipes
        elif operator == "==":
            self.model += recipe_sum == numrecipes

        self.logger.debug(f'Added {description} constraint {operator} {numrecipes}. Found {len(found_recipes)} matching recipes.')
        self.numcriteria += 1

    def add_food_constraint(self, found_recipes, numrecipes, operator, exclude=False):
        self._add_constraint(found_recipes, numrecipes, operator, exclude=exclude, description='food')

    def add_book_constraint(self, found_recipes, numrecipes, operator, exclude=False):
        self._add_constraint(found_recipes, numrecipes, operator, exclude=exclude, description='book')

    def add_keyword_constraint(self, found_recipes, numrecipes, operator, exclude=False):
        self._add_constraint(found_recipes, numrecipes, operator, exclude=exclude, description='keyword')

    def add_rating_constraints(self, found_recipes, numrecipes, operator, exclude=False):
        self._add_constraint(found_recipes, numrecipes, operator, exclude=exclude, description='rating')

    def add_createdon_constraints(self, found_recipes, numrecipes, operator, exclude=False):
        self._add_constraint(found_recipes, numrecipes, operator, exclude=exclude, description='createdon')

    def add_cookedon_constraints(self, found_recipes, numrecipes, operator, exclude=False):
        self._add_constraint(found_recipes, numrecipes, operator, exclude=exclude, description='cookedon')

    def solve(self):
        self.logger.debug(f'Solving to choose {self.numrecipes} with {self.numcriteria} unique criteria.')
        debug = self.logger.loglevel == logging.DEBUG
        self.model.solve(PULP_CBC_CMD(msg=debug))
        if self.model.status != 1:
            self.logger.info('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            self.logger.info('No solution found, adjustment of criteria required.')
            self.logger.info('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            raise RuntimeError('No solution found.')
        return [r for r in self.recipes if value(self.recipe_vars[r.id]) >= 0.5]
