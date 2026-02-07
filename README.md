# Tandoor Menu Generator

> Automatically pick recipes from your Tandoor instance, create meal plans, and print beautiful weekly menus -- all from a single command.

Tandoor Menu Generator connects to your [Tandoor Recipes](https://tandoor.dev) server, selects recipes based on rules you define (like "at least 2 vegetarian" or "nothing cooked in the last 30 days"), and optionally creates meal plans and generates printable menu files. It uses constraint solving under the hood, but all you need to do is describe what you want in a config file.

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Installation](#installation)
- [Configuration Guide](#configuration-guide)
- [Usage Examples](#usage-examples)
- [Understanding Rules (Constraints)](#understanding-rules-constraints)
- [Meal Plan Integration](#meal-plan-integration)
- [Menu File Generation](#menu-file-generation)
- [Command-Line Reference](#command-line-reference)
- [Troubleshooting and FAQ](#troubleshooting-and-faq)
- [Contributing](#contributing)
- [License](#license)

## Quick Start

**1. Clone and install dependencies:**

```bash
git clone https://github.com/smilerz/tandoor-menu-generator.git
cd tandoor-menu-generator
pip install -r requirements.txt
```

**2. Create your config file:**

```bash
cp config.ini.example config.ini
```

Open `config.ini` in a text editor and fill in your Tandoor URL and API token:

```ini
[create-menu]
url: https://your-tandoor-server.com
token: tda_your_api_token_here
```

> **Where to find your API token:** In Tandoor, go to **Settings** (gear icon) then scroll to **API Tokens**. Click **Create** to generate a new token. Copy the full token string (it starts with `tda_`).

**3. Run it:**

```bash
python create_menu.py
```

You should see output like this:

```
###########################
Your selected recipes are:
Recipe: <42> Chicken Parmesan: https://your-tandoor-server.com/view/recipe/42
Recipe: <17> Beef Tacos: https://your-tandoor-server.com/view/recipe/17
Recipe: <88> Caesar Salad: https://your-tandoor-server.com/view/recipe/88
Recipe: <23> Mushroom Risotto: https://your-tandoor-server.com/view/recipe/23
Recipe: <56> Grilled Salmon: https://your-tandoor-server.com/view/recipe/56
###########################
```

That's it -- you have a randomly selected menu of 5 recipes. Read on to add rules, create meal plans, or generate printable menus.

## Features

- **Recipe selection with rules** -- Define rules like "at least 2 with keyword Vegetarian" or "no more than 1 pasta dish." The tool finds a set of recipes that satisfies all your rules at once.
- **Flexible recipe filtering** -- Narrow the pool of recipes to choose from using search parameters, custom filters, or existing meal plans.
- **Hierarchical keywords and foods** -- When you specify a keyword like "Protein," child keywords (Chicken, Beef, Pork, etc.) are included automatically.
- **Meal plan creation** -- Automatically create meal plan entries in Tandoor for your selected recipes.
- **Stale plan cleanup** -- Remove old, uncooked meal plans before generating new ones.
- **Printable menu files** -- Generate PNG, JPG, GIF, or PDF menu files from SVG templates with recipe names and ingredients.
- **API caching** -- Results from Tandoor are cached locally to speed up repeated runs.
- **Config file and CLI** -- Set your preferences once in a config file, or override any setting from the command line.

## Installation

### Prerequisites

- Python 3.9 or newer
- A running [Tandoor Recipes](https://tandoor.dev) instance
- An API token from your Tandoor instance (see [How to Get Your API Token](#how-to-get-your-api-token))

### Base install

```bash
git clone https://github.com/smilerz/tandoor-menu-generator.git
cd tandoor-menu-generator
pip install -r requirements.txt
```

This installs everything needed for recipe selection and meal plan creation.

### Menu file dependencies (optional)

If you want to generate printable menu files (PNG, PDF, etc.) from SVG templates, you need the `libcairo2` graphics library and some additional Python packages.

**Debian / Ubuntu:**

```bash
sudo apt install libcairo2-dev
pip install -r pdf_requirements.txt
```

**macOS (Homebrew):**

```bash
brew install cairo
pip install -r pdf_requirements.txt
```

### How to Get Your API Token

1. Log in to your Tandoor instance.
2. Click the **gear icon** (Settings) in the top navigation bar.
3. Scroll down to the **API Tokens** section.
4. Click **Create** to generate a new token.
5. Copy the full token (starts with `tda_`) and paste it into your `config.ini`.

> **Security note:** Your API token grants full access to your Tandoor account. Do not share it or commit it to version control. The `config.ini` file is listed in `.gitignore` by default.

## Configuration Guide

Tandoor Menu Generator uses a config file (`config.ini`) as its primary interface. Every setting in the config file can also be overridden from the command line. When both are provided, the command-line value takes priority.

The config file uses INI format with four sections: `[create-menu]`, `[recipes]`, `[conditions]`, and `[mealplan]`. Menu file settings go in the `[menufile]` section.

### Minimal config

The bare minimum to get started -- this picks 5 random recipes from all your recipes:

```ini
[create-menu]
url: https://your-tandoor-server.com
token: tda_your_api_token_here

[conditions]
choices: 5
```

### How to find IDs in Tandoor

Many settings require the numeric ID of a keyword, food, book, meal type, or user. To find an ID:

1. Navigate to the item in Tandoor (e.g., open a keyword, food, or meal type).
2. Look at the **URL bar** in your browser -- the number at the end is the ID.
   - Example: `https://tandoor.example.com/list/keyword/47/` -- the keyword ID is `47`.

### Configuration reference

#### Connection settings

| Config key | Default | Description |
|---|---|---|
| `url` | *(required)* | Full URL of your Tandoor server, including protocol and port. Example: `https://tandoor.example.com:8080` |
| `token` | *(required)* | Your Tandoor API token (starts with `tda_`). |
| `log` | `info` | Logging level. Set to `debug` for verbose output. |
| `cache` | `240` | Minutes to cache API results. Set to `0` to disable caching. |

#### Recipe selection

These settings control which recipes are eligible to be chosen. By default, all recipes are considered. Use one or more of these to narrow the pool.

| Config key | Section | Default | Description |
|---|---|---|---|
| `recipes` | `[recipes]` | *(all recipes)* | JSON object of search parameters to filter recipes. See [Tandoor API docs](https://your-tandoor-server.com/docs/api/) for available parameters. |
| `filter` | `[recipes]` | `[]` | List of CustomFilter IDs. Recipes matching any of these filters are included. |
| `plan_type` | `[recipes]` | `[]` | List of MealType IDs. Recipes from meal plans of these types on `mp_date` are included. |

#### Recipe rules (constraints)

These settings define rules about the recipes that get selected. See [Understanding Rules](#understanding-rules-constraints) for full documentation and examples.

| Config key | Section | Default | Description |
|---|---|---|---|
| `choices` | `[conditions]` | `5` | Number of recipes to select. |
| `keyword` | `[conditions]` | `[]` | Rules based on recipe keywords. |
| `food` | `[conditions]` | `[]` | Rules based on recipe ingredients (foods). |
| `book` | `[conditions]` | `[]` | Rules based on recipe books. |
| `rating` | `[conditions]` | `[]` | Rules based on recipe rating. |
| `cookedon` | `[conditions]` | `[]` | Rules based on when a recipe was last cooked. |
| `createdon` | `[conditions]` | `[]` | Rules based on when a recipe was created. |
| `include_children` | *(CLI only)* | `true` | When enabled, child keywords and foods satisfy parent rules (e.g., a rule for "Protein" also matches "Chicken"). |

#### Meal plan creation

| Config key | Section | Default | Description |
|---|---|---|---|
| `create_mp` | `[mealplan]` | `false` | Enable meal plan creation. |
| `mp_type` | `[mealplan]` | *(required when `create_mp` is true)* | ID of the MealType to use for created plans. |
| `mp_date` | `[create-menu]` | `0days` | Date for new meal plan entries. Accepts `YYYY-MM-DD` or `Xdays` (X days from today). |
| `mp_note` | `[mealplan]` | `Created by: Tandoor Menu Generator.` | Note text added to each meal plan entry. |
| `share_with` | `[mealplan]` | `[]` | List of user IDs to share the meal plan with. |
| `cleanup_mp` | `[mealplan]` | `false` | Delete uncooked meal plans from previous runs before creating new ones. |
| `cleanup_date` | `[mealplan]` | `-7days` | Starting date for cleanup. Plans from this date onward (of the same meal type) that were not cooked are deleted. Accepts `YYYY-MM-DD` or `-Xdays`. |

#### Menu file generation

| Config key | Section | Default | Description |
|---|---|---|---|
| `create_file` | `[menufile]` | `false` | Enable menu file generation from an SVG template. |
| `file_template` | `[menufile]` | *(required when `create_file` is true)* | Name of the SVG template file, located in the `templates/` directory. |
| `file_format` | `[menufile]` | `PNG` | Output format: `GIF`, `JPG`, `PNG`, or `PDF`. |
| `output_dir` | `[menufile]` | `templates/` | Directory for the output file. Defaults to the templates directory. |
| `fonts` | `[menufile]` | `[]` | Custom fonts needed by the SVG template. Format: `[{"name": "FontName", "file": "font.ttf"}]`. Font files must be in the `templates/` directory. |
| `replace_text` | `[menufile]` | *(none)* | Defines how template placeholder text maps to recipe data. See [Menu File Generation](#menu-file-generation). |
| `separator` | `[menufile]` | `' - '` | Text used to join ingredients on a single line (e.g., `Chicken - Rice - Peppers`). |

## Usage Examples

### Pick 5 random recipes

The default behavior with a minimal config:

```ini
[create-menu]
url: https://tandoor.example.com
token: tda_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

[conditions]
choices: 5
```

```bash
python create_menu.py
```

### Pick 7 recipes for the week, at least 2 vegetarian

Assuming your "Vegetarian" keyword has ID `73`:

```ini
[create-menu]
url: https://tandoor.example.com
token: tda_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

[conditions]
choices: 7
keyword: [{"condition": 73, "count": 2, "operator": ">="}]
```

### At least 2 recipes with chicken, no more than 1 pasta

Assuming "Chicken" food ID is `15` and "Pasta" keyword ID is `47`:

```ini
[conditions]
choices: 5
food: [{"condition": 15, "count": 2, "operator": ">="}]
keyword: [{"condition": 47, "count": 1, "operator": "<="}]
```

### No recipes cooked in the last 30 days

```ini
[conditions]
choices: 5
cookedon: [{"condition": "30days", "count": 0, "operator": "=="}]
```

This says: "Of all recipes cooked in the last 30 days, select exactly 0." In other words, none of the selected recipes should have been cooked recently.

### Only highly-rated recipes

Select 5 recipes, all with a rating of 4 or higher:

```ini
[conditions]
choices: 5
rating: [{"condition": 4, "count": 5, "operator": ">="}]
```

This means: "At least 5 of the selected recipes must have a rating of 4 or above." Since you are selecting 5 total, this ensures all of them are highly rated.

### Create a meal plan and share it

```ini
[create-menu]
url: https://tandoor.example.com
token: tda_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
mp_date: 0days

[conditions]
choices: 5

[mealplan]
create_mp: true
mp_type: 3
share_with: [2, 5]
mp_note: This week's menu
```

### Generate a printable PNG menu

```ini
[menufile]
create_file: true
file_template: weekly_menu.svg
file_format: PNG
```

See [Menu File Generation](#menu-file-generation) for details on setting up templates.

### Clean up old plans before creating new ones

```ini
[mealplan]
create_mp: true
mp_type: 3
cleanup_mp: true
cleanup_date: -7days
```

This deletes any uncooked meal plans of type `3` from the last 7 days before creating new ones.

### Override settings from the command line

Any config setting can be overridden on the command line:

```bash
# Pick 7 recipes instead of the 5 in your config
python create_menu.py --choices 7

# Use a different config file
python create_menu.py -c my_other_config.ini

# Enable debug logging for this run
python create_menu.py --log debug
```

## Understanding Rules (Constraints)

Rules (called "constraints" internally) let you control which recipes are selected. You can set rules based on keywords, foods, books, ratings, and dates.

### Rule format

Each rule is a JSON object with three required fields:

```json
{"condition": <value>, "count": <number>, "operator": "<comparison>"}
```

| Field | Description |
|---|---|
| `condition` | What to match: a keyword ID, food ID, book ID, rating number, or date string. Can be a single value or a list of IDs. |
| `count` | How many of the selected recipes should match this condition. |
| `operator` | How to compare: `>=` (at least), `<=` (at most), or `==` (exactly). |

### Operator reference

| Operator | Meaning | Example |
|---|---|---|
| `>=` | At least | "At least 2 vegetarian recipes" |
| `<=` | At most | "At most 1 pasta dish" |
| `==` | Exactly | "Exactly 3 recipes from Book X" |

### Optional modifiers

Rules can include additional fields to refine the match:

| Modifier | Type | Description |
|---|---|---|
| `exclude` | `true`/`false` | When `true`, the rule applies to all recipes that do **not** match the condition. For example, `"exclude": true` with a "Vegetarian" keyword means the rule applies to non-vegetarian recipes. |
| `except` | ID or list of IDs | Excludes specific items from a hierarchical condition. For example, a rule for "Protein" (which includes Chicken, Beef, Pork) with `"except": [45]` would match all proteins except the one with ID 45. |
| `cooked` | date string | Further filters matching recipes to only those cooked on or after/before a date. Accepts `YYYY-MM-DD` or `Xdays`. |
| `created` | date string | Further filters matching recipes to only those created on or after/before a date. Accepts `YYYY-MM-DD` or `Xdays`. |

### Date formats

Dates can be specified in two ways:

| Format | Meaning | Example |
|---|---|---|
| `YYYY-MM-DD` | Absolute date. Matches recipes on or after this date. Prefix with `-` to match on or before. | `2024-01-01` (on or after), `-2024-06-01` (on or before) |
| `Xdays` | Relative date. X days ago from today. Prefix with `-` to mean "on or before X days ago." | `30days` (within the last 30 days), `-30days` (more than 30 days ago) |

### Worked examples

**"At least 2 vegetarian recipes"** (Vegetarian keyword ID: `73`):

```json
{"condition": 73, "count": 2, "operator": ">="}
```

**"At most 1 recipe with pasta"** (Pasta keyword ID: `47`):

```json
{"condition": 47, "count": 1, "operator": "<="}
```

**"Exactly 3 recipes from my Favorites book"** (Book ID: `5`):

```json
{"condition": 5, "count": 3, "operator": "=="}
```

**"At least 1 recipe with any protein except chicken"** (Protein keyword ID: `100`, Chicken keyword ID: `99`):

```json
{"condition": 100, "count": 1, "operator": ">=", "except": [99]}
```

**"At least 2 recipes with either Italian or Mexican keywords"** (Italian ID: `73`, Mexican ID: `273`):

```json
{"condition": [73, 273], "count": 2, "operator": ">="}
```

**"No recipes cooked in the last 14 days"**:

```json
{"condition": "14days", "count": 0, "operator": "=="}
```

### Combining multiple rules

You can specify multiple rules for the same type. They are all applied simultaneously:

```ini
keyword: [
    {"condition": 73, "count": 2, "operator": ">="},
    {"condition": 47, "count": 1, "operator": "<="}
    ]
```

This says: "At least 2 Vegetarian recipes AND at most 1 Pasta recipe."

You can also combine rules of different types:

```ini
keyword: [{"condition": 73, "count": 2, "operator": ">="}]
food: [{"condition": 15, "count": 1, "operator": ">="}]
rating: [{"condition": 4, "count": 3, "operator": ">="}]
```

This says: "At least 2 Vegetarian, at least 1 with Chicken, and at least 3 rated 4 or above."

### What if my rules conflict?

If your rules are impossible to satisfy (e.g., "at least 4 vegetarian out of 5" combined with "at least 3 with beef"), the solver will report "No solution found." When this happens:

- Relax one or more rules (lower the count, change `>=` to `<=`, etc.)
- Increase the number of `choices` to give the solver more room
- Run with `--log debug` to see which constraints were applied and how many recipes matched each one

### Rating values

Ratings use a scale from 0 to 5. A negative `condition` value means "less than or equal to" the absolute value. For example:

- `"condition": 4` -- matches recipes rated 4 or above
- `"condition": -3` -- matches recipes rated between 0 and 3 (inclusive)

## Meal Plan Integration

### Basic setup

To have the tool create meal plan entries in Tandoor, add a `[mealplan]` section to your config:

```ini
[create-menu]
mp_date: 0days

[mealplan]
create_mp: true
mp_type: 3
```

- `mp_type` is the ID of the MealType to use. You can find this in your Tandoor URL bar when viewing meal types.
- `mp_date` sets the date for the new meal plan entries.

> **Tip:** Create a dedicated MealType in Tandoor (like "Generated Menu") for plans created by this tool. This keeps them separate from manually-created plans and makes cleanup reliable.

### Setting the date

The `mp_date` setting accepts two formats:

| Format | Meaning | Example |
|---|---|---|
| `Xdays` | X days from today | `0days` (today), `1days` (tomorrow), `7days` (next week) |
| `YYYY-MM-DD` | A specific date | `2024-12-25` |

### Sharing with household members

To share the generated meal plans with other Tandoor users, add their user IDs:

```ini
[mealplan]
create_mp: true
mp_type: 3
share_with: [2, 5]
```

### Cleaning up old plans

If you run the tool regularly (e.g., weekly), you can have it delete old uncooked plans before creating new ones:

```ini
[mealplan]
create_mp: true
mp_type: 3
cleanup_mp: true
cleanup_date: -7days
```

This looks at all meal plans of the specified type from 7 days ago onward. Any plans whose recipes were not marked as cooked in Tandoor get deleted. Plans for recipes that were cooked are preserved.

## Menu File Generation

Menu file generation creates a printable image or PDF from an SVG template by replacing placeholder text with recipe names and ingredients.

### Prerequisites

Make sure you have installed the [menu file dependencies](#menu-file-dependencies-optional) (`libcairo2` and `pdf_requirements.txt`).

### Basic setup

```ini
[menufile]
create_file: true
file_template: my_menu.svg
file_format: PNG
```

Place your SVG template file in the `templates/` directory within the project folder.

### How the template system works

The tool opens your SVG template, finds specific placeholder text strings, and replaces them with actual recipe data. You define the mapping between placeholder text and recipe data in the `replace_text` config option.

The placeholder text in your SVG must match exactly (including case and spacing). The replacement text is truncated to fit within the length of the placeholder, so use long placeholder strings to allow room for recipe names and ingredients.

### `replace_text` configuration

The `replace_text` option is a YAML/JSON object with two main sections:

```ini
replace_text: {
    date_text: {
        'date': 'WEEK OF PLACEHOLDER',
        'ordinal': 'XY',
        'format': 'short'
    },
    recipe_text: [
        {
            'name': 'Recipe Title One Placeholder Text Here',
            'ingredients': [
                'Ingredient Line 1 placeholder text goes here',
                'Ingredient Line 2 placeholder text goes here',
                'Ingredient Line 3 placeholder text goes here'
            ]
        },
        {
            'name': 'Recipe Title Two Placeholder Text Here',
            'ingredients': [
                'Ingredient Line 1 placeholder text goes here',
                'Ingredient Line 2 placeholder text goes here'
            ]
        }
    ]
    }
```

**`date_text`** (optional) -- Replaces date placeholder text with the meal plan date:

| Key | Description |
|---|---|
| `date` | Placeholder text to replace with the formatted date. |
| `ordinal` | Placeholder text to replace with the day's ordinal suffix (st, nd, rd, th). |
| `format` | Date format: `short` (Jan 15), `medium` (January 15), `long` (January 15, 2024), or `number` (01/15). |

**`recipe_text`** (required) -- A list of objects, one per recipe. Each object defines:

| Key | Description |
|---|---|
| `name` | Placeholder text in the SVG to replace with the recipe name. |
| `ingredients` | (Optional) List of placeholder text strings for ingredient lines. Ingredients are concatenated using the `separator` setting and wrapped across lines automatically. |

The number of entries in `recipe_text` should match your `choices` setting.

### Separator

The `separator` setting controls how ingredients are joined on each line. The default is `' - '`, which produces output like:

```
Chicken - Rice - Bell Peppers - Onions
```

### Date format options

| Format | Output example |
|---|---|
| `short` | Jan 15 |
| `medium` | January 15 |
| `long` | January 15, 2024 |
| `number` | 01/15 |

### Custom fonts

If your SVG template uses non-system fonts, register them in the config:

```ini
[menufile]
fonts: [{"name": "MyCustomFont", "file": "MyCustomFont.ttf"}]
```

Place the `.ttf` font files in the `templates/` directory alongside your SVG template.

### Output format comparison

| Format | Best for |
|---|---|
| `PNG` | Sharing on screens, messaging apps, photo frames |
| `JPG` | Smaller file size, photos |
| `GIF` | Older systems |
| `PDF` | Printing, archiving |

### Tips for designing templates

- Use a vector graphics editor like [Inkscape](https://inkscape.org) (free) to create your SVG template.
- Make placeholder text strings **longer than the longest recipe name** you expect. If a recipe name is longer than its placeholder, the name is truncated to fit.
- The tool automatically tries to swap recipes between slots if one recipe name fits better in another slot's placeholder space.
- Use distinct, recognizable placeholder text that would not appear in actual recipe data (e.g., "Recipe Title One Lorem Ipsum Dolor Sit Amet").
- For ingredients, more lines with more placeholder text per line gives the tool more room to display all ingredients.

## Command-Line Reference

Every option below can also be set in `config.ini`. Command-line values override config file values.

| Flag | Config key | Default | Description |
|---|---|---|---|
| `-c`, `--my-config` | -- | `config.ini` | Path to configuration file. |
| `--url` | `url` | *(required)* | Full URL of the Tandoor server. |
| `--token` | `token` | *(required)* | Tandoor API token. |
| `--log` | `log` | `info` | Logging level (`info` or `debug`). |
| `--cache` | `cache` | `240` | Minutes to cache API results; `0` to disable. |
| `--recipes` | `recipes` | *(none)* | JSON object of recipe search parameters. |
| `--filters` | `filter` | `[]` | CustomFilter IDs to source recipes from. |
| `--plan_type` | `plan_type` | `[]` | MealType IDs to source recipes from meal plans. |
| `--choices` | `choices` | `5` | Number of recipes to select. |
| `--keyword` | `keyword` | `[]` | Keyword-based rules. |
| `--food` | `food` | `[]` | Food-based rules. |
| `--book` | `book` | `[]` | Book-based rules. |
| `--rating` | `rating` | `[]` | Rating-based rules. |
| `--cookedon` | `cookedon` | `[]` | Last-cooked-date rules. |
| `--createdon` | `createdon` | `[]` | Creation-date rules. |
| `--include_children` | -- | `true` | Include child keywords/foods in rule matching. |
| `--create_mp` | `create_mp` | `false` | Create meal plan entries for selected recipes. |
| `--mp_type` | `mp_type` | *(required with `create_mp`)* | MealType ID for created plans. |
| `--mp_date` | `mp_date` | `0days` | Date for meal plan entries. |
| `--mp_note` | `mp_note` | `Created by: Tandoor Menu Generator.` | Note text for meal plan entries. |
| `--share_with` | `share_with` | `[]` | User IDs to share the meal plan with. |
| `--cleanup_mp` | `cleanup_mp` | `false` | Delete uncooked meal plans before creating new ones. |
| `--cleanup_date` | `cleanup_date` | `-7days` | Start date for cleanup. |
| `--create_file` | `create_file` | `false` | Generate a menu file from an SVG template. |
| `--file_template` | `file_template` | *(required with `create_file`)* | SVG template filename (in `templates/` directory). |
| `--file_format` | `file_format` | `PNG` | Output format: `GIF`, `JPG`, `PNG`, or `PDF`. |
| `--output_dir` | `output_dir` | `templates/` | Output directory for the generated file. |
| `--fonts` | `fonts` | `[]` | Custom font definitions for the SVG template. |
| `--replace_text` | `replace_text` | *(none)* | Template placeholder-to-data mapping. |
| `--separator` | `separator` | `' - '` | Separator for concatenating ingredients. |

## Troubleshooting and FAQ

### "No solution found"

This means your rules are contradictory or too restrictive for the available recipes. Try:

- Lowering the `count` in one or more rules.
- Changing `>=` to `<=` or removing a rule entirely.
- Increasing `choices` to give the solver more flexibility.
- Running with `--log debug` to see how many recipes matched each rule.

### "Not enough recipes to generate a menu"

The total number of available recipes (after filtering) is less than `choices`. Either:

- Add more recipes to Tandoor.
- Reduce the `choices` count.
- Broaden your recipe search parameters or remove filters.

### 403 Forbidden errors

Your API token may be invalid or expired. Generate a new token in Tandoor under **Settings** > **API Tokens**.

### 404 Not Found errors

Check that your `url` setting is correct. It should be the base URL of your Tandoor instance (e.g., `https://tandoor.example.com` or `https://tandoor.example.com:8080`). Do not include `/api/` -- the tool appends that automatically.

### Same recipes every time

The solver introduces randomness, but with tight constraints there may be few valid solutions. Try:

- Loosening your rules to allow more combinations.
- Disabling the cache (`cache: 0`) if your recipe data has changed recently.
- Adding more recipes to Tandoor to give the solver a larger pool.

### Menu file text is cut off

The template system truncates recipe names and ingredients to fit within the length of the placeholder text. To fix this:

- Use longer placeholder strings in your SVG template.
- Add more ingredient lines to give the tool more space.
- Use shorter separator text (e.g., `separator: ', '` instead of the default `' - '`).

### How do I run this on a schedule?

Use cron (Linux/macOS) or Task Scheduler (Windows) to run the tool automatically:

```bash
# Run every Sunday at 6 PM
0 18 * * 0 cd /path/to/tandoor-menu-generator && python create_menu.py
```

### How do I find IDs for keywords, foods, books, or meal types?

Navigate to the item in your Tandoor web interface and look at the URL bar. The number at the end of the URL is the ID. For example:

- `https://tandoor.example.com/list/keyword/47/` -- keyword ID is **47**
- `https://tandoor.example.com/list/food/15/` -- food ID is **15**

## Contributing

Contributions are welcome. Please open an issue or pull request on GitHub.

## License

This project is open source. See the repository for license details.
