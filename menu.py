import json
import logging
import os
import re
from datetime import datetime
from shutil import copy2

from reportlab.graphics import renderPDF, renderPM
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from svglib.svglib import svg2rlg

from utils import printable_date


class MenuGenerator:
    def __init__(self, api, options, logger):
        self.options = options
        self.api = api
        self.logger = logger
        self.template_dir = os.path.join(os.getcwd(), 'templates')
        self.output_dir = options.output_dir or self.template_dir
        self.input_file = options.file_template
        self.temp_file = os.path.join(self.output_dir, 'temp.svg')
        self.output_file = self.input_file.split('.')[0]
        self.ext = options.file_format
        self.fonts = [json.loads(f.replace("'", '"')) for f in options.fonts]
        self.replace_text = options.replace_text
        self.separator = options.separator

    def write_menu(self, recipes):
        template = self.open_template()
        if any('ingredients' in r for r in self.options.replace_text['recipe_text']):
            for r in recipes:
                r.addDetails(self.api)
        template = self.find_and_replace(recipes, template)
        self.write_temp_template(template)
        self.convert_svg()
        self.cleanup()

    def convert_svg(self):
        # Register font files
        for f in self.fonts:
            self.logger.debug(f'Loading font {f["name"]} from {os.path.join(self.template_dir, f["file"])}.')
            font = TTFont(f['name'], os.path.join(self.template_dir, f['file']))
            pdfmetrics.registerFont(font)
            self.logger.debug(f'Font {font.fontName} loaded succesfully.')

        # Load the SVG file as a ReportLab graphics object
        drawing = svg2rlg(self.temp_file)

        temp_output = os.path.join(os.getcwd(), f'temp.{self.ext}')
        if self.ext.lower() == 'pdf':
            output_file = os.path.join(self.output_dir, f'{self.output_file}.{self.ext}')
            self.logger.debug(f'Writing PDF to {output_file}.')
            renderPDF.drawToFile(drawing, temp_output)
        else:
            output_file = os.path.join(self.output_dir, f'{self.output_file}.{self.ext}')
            self.logger.debug(f'Writing {self.ext} to {output_file}.')
            renderPM.drawToFile(drawing, temp_output, fmt=self.ext)
        self.logger.debug(f'Moving file {temp_output} to {output_file}.')
        os.rename(temp_output, output_file)
        os.chmod(output_file, 0o755)
        self.archive(output_file)

    def find_and_replace(self, recipes, template):
        def _escape_svg_text(text):
            escapes = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&apos;'
            }
            return re.sub(r'[\&\<\>\"\']', lambda match: escapes[match.group(0)], text)
        if date_text := self.replace_text.get('date_text', None):
            date, ordinal = printable_date(self.options.mp_date, format=date_text.get('format', None))

            # update dates if they exist
            if d := date_text.get('date', None):
                template = re.sub(re.escape(d), date, template)
            if d := date_text.get('ordinal', None):
                template = re.sub(re.escape(d), ordinal, template)
        # create replacement dict
        replacement_dict = self.prepare_replacement(recipes)

        for k, v in replacement_dict.items():
            self.api.update_progress()
            template = re.sub(re.escape(k), _escape_svg_text(v), template)

        return template

    def prepare_replacement(self, recipes):
        def _length_replace_ing(x):
            return len(' '.join(x['ingredients']))

        def _length_recipe_ing(x):
            return len(self.options.separator.join(x))

        def _chunk_ingredients(before, after):
            pairs = []
            separator = self.options.separator.replace(" ", "~|~")
            after = f' {separator} '.join(after).split()
            for x in before:
                chunk = ''
                while after and len(x) >= len(chunk + after[0]):
                    next_chunk = after.pop(0)
                    if chunk == '':
                        if next_chunk == separator:
                            next_chunk = after.pop(0)
                        chunk += next_chunk
                    else:
                        chunk += (" " + next_chunk.replace('~|~', ' ')).replace("  ", " ")

                if chunk:
                    pairs.append((x, chunk))
                else:
                    pairs.append((x, ''))
            return pairs

        # create temporary array to assign before/after values
        temp_text = []
        for idx in range(len(self.options.replace_text['recipe_text'])):
            before = dict(self.options.replace_text['recipe_text'][idx])
            before['after_name'] = recipes[idx].name
            before['after_ing'] = [ing.name for ing in recipes[idx].ingredients]
            temp_text.append(before)

        # confirm that all after strings are shorter than before strings.
        for y in range(len(temp_text)):
            text_fits = len(temp_text[y]['name']) >= len(temp_text[y]['after_name']) and _length_replace_ing(temp_text[y]) >= _length_recipe_ing(temp_text[y]['after_ing'])
            if not text_fits:
                truncate_text = True
                # if there are no other slots that the name and ingredients fit - just truncate the text
                if (
                    any(len(t['name']) >= len(temp_text[y]['after_name']) for t in temp_text) and
                    any(_length_replace_ing(t) >= _length_recipe_ing(temp_text[y]['after_ing']) for t in temp_text)
                ):
                    for z in range(len(temp_text)):
                        # if swapping the recipes between two positions fits the text then do that
                        if (
                            len(temp_text[z]['name']) > len(temp_text[y]['after_name']) and _length_replace_ing(temp_text[z]) >= _length_recipe_ing(temp_text[y]['after_ing']) and
                            len(temp_text[y]['name']) > len(temp_text[z]['after_name']) and _length_replace_ing(temp_text[y]) >= _length_recipe_ing(temp_text[z]['after_ing'])
                        ):
                            tmp_name = temp_text[y]['after_name']
                            tmp_ing = temp_text[y]['after_ing']
                            temp_text[y]['after_name'] = temp_text[z]['after_name']
                            temp_text[y]['after_ing'] = temp_text[z]['after_ing']
                            temp_text[z]['after_name'] = tmp_name
                            temp_text[z]['after_ing'] = tmp_ing
                            truncate_text = False
                if truncate_text:
                    temp_text[y]['after_name'] = temp_text[y]['after_name'][:len(temp_text[y]['name'])]
                    new_ing = []
                    while temp_text[y]['after_ing'] and _length_replace_ing(temp_text[y]) > _length_recipe_ing(new_ing):
                        new_ing.append(temp_text[y]['after_ing'].pop(0))
                    temp_text[y]['after_ing'] = new_ing

        # create replacement dict in the form of key:value = before:after
        replacements = {}
        for y in temp_text:
            replacements[y['name']] = y['after_name']
            after_chunks = _chunk_ingredients(y['ingredients'], y['after_ing'])
            for pair in after_chunks:
                replacements[pair[0]] = pair[1]
        return replacements

    def open_template(self):
        # Open file and read contents
        self.logger.debug(f'Opening template from {os.path.join(self.template_dir, self.input_file)}.')
        with open(os.path.join(self.template_dir, self.input_file)) as f:
            return f.read()

    def write_temp_template(self, template):
        self.logger.debug(f'Writing temporary template to {self.temp_file}.')
        with open(self.temp_file, 'w') as f:
            f.write(template)

    def cleanup(self):
        self.archive(self.temp_file, target_name=self.input_file)
        self.logger.debug(f'Removing temporary file {self.temp_file}.')
        os.remove(self.temp_file)

    def archive(self, file, target_name=None):
        if not target_name:
            target_name = file
        if self.logger.loglevel == logging.DEBUG:
            archive_dir = os.path.join(self.template_dir, 'archive')
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            filename, ext = os.path.splitext(os.path.basename(target_name))
            archive_file = (a_file := f"{filename}-{(datetime.now().strftime('%y%m%d'))}")
            count = 1
            while os.path.exists(os.path.join(archive_dir, f"{archive_file}{ext}")):
                archive_file = a_file + '_' + str(count)
                count += 1
            # os.rename(self.temp_file, os.path.join(archive_dir, "{archive_file}.{ext}"))
            af = os.path.join(archive_dir, f"{archive_file}{ext}")
            self.logger.debug(f'Archiving file {file} to {af}.')
            copy2(file, af)
