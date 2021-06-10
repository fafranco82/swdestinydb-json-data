#!/usr/bin/env python

import argparse
import json
import jsonschema
import os
import sys
import re

SET_PATH_STRING = os.path.sep + 'set' + os.path.sep

def pluralize(word):
    if word[-1] == 'y':
        return word[:-1]+'ies'
    elif word[-1] == 's' or word[-2:]=='sh':
        return word+'es'
    else:
        return word+'s'

class Logger:
    def __init__(self, verbose, indent=0, prefix=None):
        self.verbose = verbose
        self.indent = indent
        self.prefix = prefix or ""
        self.togglePrefix = True

    def verbose_print(self, text, minimum_verbosity=0):
        if self.verbose >= minimum_verbosity:
            if self.togglePrefix:
                sys.stdout.write((" "*self.indent))
                sys.stdout.write(self.prefix)
            self.togglePrefix = False
            sys.stdout.write(text)
            if "\n" in text:
                self.togglePrefix = True

class ValidatorBase:
    def __init__(self, base_path, logger, fix_formatting):
        self.formatting_errors = 0
        self.nonfixed_formatting_errors = 0
        self.validation_errors = 0
        self.logger = logger
        self.fix_formatting = fix_formatting
        self.collections = {}
        self.base_path = base_path
        self.data_path = base_path
        self.schema_path = os.path.join(base_path, "schema")
        self.re_side_a = re.compile(r'[0-9A]$')


    def validate(self):
        check_dir_access(self.data_path)
        check_dir_access(self.schema_path)
        self.logger.verbose_print("Validating data...\n", 0)

        for thing in ['affiliation', 'faction', 'rarity', 'type', 'subtype', 'sideType', 'cycle', 'set']:
            collection = self.load_collection(thing)
            if collection:
                self.load_collections(thing, collection)
            else:
                self.load_collections(thing, [])

        self.load_sets_collection()

        for thing in ['format']:
            collection = self.load_collection(thing)
            if collection:
                self.load_collections(thing, collection)
            else:
                self.load_collections(thing, [])

    def show_results(self):
        self.logger.verbose_print("Found %s formatting and %s validation errors\n" % (self.formatting_errors, self.validation_errors), 0)
        if self.nonfixed_formatting_errors == 0 and self.validation_errors == 0:
            sys.exit(0)
        else:
            sys.exit(1)

    def load_collection(self, thing):
        plural_thing = pluralize(thing)
        self.logger.verbose_print("Loading collection of %s\n" % plural_thing, 1)

        json_path = os.path.join(self.data_path, "%s.json" % plural_thing)
        check_file_access(json_path)

        things_data = self.load_json_file(json_path)

        if not self.validate_collection(thing, things_data):
            return None

        return things_data

    def load_sets_collection(self):
        self.logger.verbose_print("Loading collection of cards\n", 1)

        json_dir = os.path.join(self.data_path, "%s" % 'set')
        check_dir_access(json_dir)

        for setcode in [s.get('code') for s in sorted(self.collections['set'].values(), key=lambda s: s.get('position'))]:
            self.logger.verbose_print("Loading cards from set '%s'...\n" % setcode, 1)
            json_path = os.path.join(json_dir, "%s.json" % setcode)
            exists = not test_file_access(json_path)
            if exists:
                cards = self.load_json_file(json_path)

                if self.validate_collection('card', cards):
                    self.load_collections('card', cards)


    def load_collections(self, thing, collection):
        if not thing in self.collections:
            self.collections[thing] = {}

        for item in collection:
            #if not item.get("code") in self.collections[thing]:
            #    self.collections[thing][item.get("code")] = []

            #self.collections[thing][item.get("code")].append(item)
            self.collections[thing][item.get("code")] = item

    def validate_collection(self, thing, things_data):
        plural_thing = pluralize(thing)
        self.logger.verbose_print("Validating collection of %s\n" % plural_thing, 1)

        schema_path = os.path.join(self.schema_path, "%s_schema.json" % thing)
        check_file_access(schema_path)
        schema_data = self.load_json_file(schema_path)

        if not isinstance(things_data, list):
            self.logger.verbose_print("Insides of %s collection file are not a list!\n", 0)
            return False
        if not schema_data:
            return False
        if not self.check_json_schema(schema_data, schema_path):
            return False

        retval = True
        for thing_data in things_data:
            retval = self.validate_schema(thing, thing_data, schema_data) and retval

        return retval

    def validate_schema(self, thing, thing_data, schema_data):
        self.logger.verbose_print("Validating %s %s..." % (thing, thing_data.get("code")), 2)
        try:
            jsonschema.validate(thing_data, schema_data)
            self.custom_check(thing, thing_data)
            self.logger.verbose_print(" OK\n", 2)
        except jsonschema.ValidationError as e:
            self.logger.verbose_print("ERROR\n", 2)
            self.logger.verbose_print("Validation error in %s: (code: '%s')\n" % (thing, thing_data.get("code")), 0)
            self.validation_errors += 1
            for line in str(e).split('\n'):
                self.logger.verbose_print(" |    "+line+"\n", 0)
            return False
        return True

    def custom_check(self, thing, thing_data):
        custom_check_method = "custom_check_%s" % thing
        if hasattr(self, custom_check_method) and callable(getattr(self, custom_check_method)):
            getattr(self, custom_check_method)(thing_data)

    def custom_check_set(self, set):
        validations = []

        if not set.get('cycle_code') in self.collections['cycle']:
            validations.append("Cycle code '%s' does not exist in set '%s'" % (set.get('cycle_code'), set.get('code')))

        if validations:
            raise jsonschema.ValidationError("\n".join(["- %s" % v for v in validations]))

    def is_side_a(self, card):
        return self.re_side_a.match(card.get('code'))

    def custom_check_card(self, card):
        validations = []
        #check foreing codes
        for collection in ["affiliation", "faction", "rarity", "type"]:
            field = collection + "_code"
            if field in card and not card.get(field) in self.collections[collection]:
                validations.append("%s code '%s' does not exist in card '%s'" % (collection, card.get(field), card.get('code')))

        #check subtypes
        if 'subtypes' in card:
            for subtype in [s for s in card.get('subtypes') if not s in self.collections['subtype']]:
                validations.append("Subtype code '%s' does not exist in card '%s'" % (subtype, card.get('code')))

        #check reprint of
        if 'reprint_of' in card and not card.get('reprint_of') in self.collections['card']:
            validations.append("Reprinted card %s does not exist" % (card.get('reprint_of')))

        #checks by type
        check_by_type_method = "custom_check_%s_card" % card.get('type_code')
        if hasattr(self, check_by_type_method) and callable(getattr(self, check_by_type_method)):
            validations.extend(getattr(self, check_by_type_method)(card))

        if validations:
            raise jsonschema.ValidationError("\n".join(["- %s" % v for v in validations]))

    def custom_check_character_card(self, card):
        validations = []
        for attr in ['points', 'health']:
            if not card.has_key(attr) and self.is_side_a(card):
                validations.append("Character card %s must have attribute '%s'" % (card.get('code'), attr))

        return validations

    def custom_check_event_card(self, card):
        validations = []
        if not card.has_key('cost'):
            validations.append("Character card %s must have attribute 'cost'" % card.get('code'))

        return validations

    def custom_check_upgrade_card(self, card):
        return self.custom_check_event_card(card)

    def custom_check_support_card(self, card):
        return self.custom_check_event_card(card)

    def custom_check_plot_card(self, card):
        validations = []
        for attr in ['points']:
            if not card.has_key(attr) and self.is_side_a(card):
                validations.append("Plot card %s must have attribute '%s'" % (card.get('code'), attr))

        return validations

    def custom_check_format(self, format):
        validations = []

        for set in format.get('data').get('sets'):
            if not set in self.collections['set']:
                validations.append("Set code '%s' does not exist in format '%s'" % (set, format.get('code')))

        if format.get('data').get('balance') is not None:
            for card, points in format.get('data').get('balance').items():
                if not card in self.collections['card']:
                    validations.append("Card code '%s' does not exist in format '%s' balance of the force" % (card, format.get('code')))

        if format.get('data').get('banned') is not None:
            for card in format.get('data').get('banned'):
                if not card in self.collections['card']:
                    validations.append("Card code '%s' does not exist in format '%s' ban list" % (card, format.get('code')))

        if format.get('data').get('errata') is not None:
            for card in format.get('data').get('errata'):
                if not card in self.collections['card']:
                    validations.append("Card code '%s' does not exist in format '%s' errata" % (card, format.get('code')))

        if validations:
            raise jsonschema.ValidationError("\n".join(["- %s" % v for v in validations]))

    def load_json_file(self, path):
        try:
            with open(path, "rb") as data_file:
                bin_data = data_file.read()
            raw_data = bin_data.decode("utf-8")
            json_data = json.loads(raw_data)
        except ValueError as e:
            self.logger.verbose_print("%s: File is not valid JSON.\n" % path, 0)
            self.validation_errors += 1
            print(e)
            return None

        self.logger.verbose_print("%s: Checking JSON formatting...\n" % path, 4)
        formatted_raw_data = self.format_json(json_data, SET_PATH_STRING in path)

        if formatted_raw_data != raw_data:
            self.logger.verbose_print("%s: File is not correctly formatted JSON.\n" % path, 0)
            self.formatting_errors += 1
            if self.fix_formatting and len(formatted_raw_data) > 0:
                self.logger.verbose_print("%s: Fixing JSON formatting...\n" % path, 0)
                try:
                    with open(path, "wb") as json_file:
                        bin_formatted_data = formatted_raw_data.encode("utf-8")
                        json_file.write(bin_formatted_data)
                except IOError as e:
                    self.nonfixed_formatting_errors += 1
                    self.logger.verbose_print("%s: Cannot open file to write.\n" % path, 0)
                    print(e)
            else:
                self.nonfixed_formatting_errors += 1
        return json_data

    def format_json(self, json_data, sorting=False):
        if sorting:
            json_data = sorted(json_data, key=lambda k: k['code'])
        formatted_data = json.dumps(json_data, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))
        formatted_data += "\n"
        return formatted_data

    def check_json_schema(self, data, path):
        try:
            jsonschema.Draft4Validator.check_schema(data)
            return True
        except jsonschema.exceptions.SchemaError as e:
            self.logger.verbose_print("%s: Schema file is not valid Draft 4 JSON schema.\n" % path, 0)
            self.validation_errors += 1
            print(e)
            return False    

class Validator(ValidatorBase):
    def __init__(self, base_path, logger, fix_formatting):
        ValidatorBase.__init__(self, base_path, logger, fix_formatting)
        self.i18n_path = os.path.join(base_path, "translations")

    def validate(self):
        ValidatorBase.validate(self)

        if self.validation_errors == 0:
            self.validate_locales()
        else:
            self.logger.verbose_print("There were errors in main files. Validation of translated files skipped.\n", 0)

    def validate_locales(self):
        if os.path.exists(self.i18n_path):
            self.logger.verbose_print("Validating I18N files...\n", 0)
            check_dir_access(self.i18n_path)
            locales_path = self.i18n_path
            if os.path.exists(locales_path):
                check_dir_access(locales_path)
                for locale in [l for l in os.listdir(locales_path) if os.path.isdir(os.path.join(locales_path, l))]:
                    self.logger.verbose_print("Validating I18N files for locale '%s'...\n" % locale, 1)
                    i18nValidator = I18NValidator(self, locale, self.i18n_path, self.logger)
                    i18nValidator.validate()
                    self.formatting_errors += i18nValidator.formatting_errors
                    self.nonfixed_formatting_errors += i18nValidator.nonfixed_formatting_errors
                    self.validation_errors += i18nValidator.validation_errors

class I18NValidator(ValidatorBase):
    def __init__(self, parent, locale, base_path, logger):
        ValidatorBase.__init__(self, base_path, Logger(logger.verbose, logger.indent+4, "[%s] " % locale), parent.fix_formatting)
        self.parent = parent
        self.locale = locale
        self.data_path = os.path.join(base_path, locale)
        self.schema_path = os.path.join(parent.schema_path, 'translations')

    def custom_check(self, thing, thing_data):
        if thing_data.has_key("code") and not self.parent.collections[thing].has_key(thing_data["code"]):
            raise jsonschema.ValidationError("- %s code '%s' does not exist in '%s' %s translations" % (thing, thing_data["code"], self.locale, thing))

    def custom_check_character_card(self, card):
        return []

    def custom_check_event_card(self, card):
        return []

    def custom_check_upgrade_card(self, card):
        return self.custom_check_event_card(card)

    def custom_check_support_card(self, card):
        return self.custom_check_event_card(card)


def parse_commandline():
    argparser = argparse.ArgumentParser(description="Validate JSON in the swdestinydb data repository.")
    argparser.add_argument("-f", "--fix_formatting", default=False, action="store_true", help="write suggested formatting changes to files")
    argparser.add_argument("-v", "--verbose", default=0, action="count", help="verbose mode")
    argparser.add_argument("-b", "--base_path", default=os.getcwd(), help="root directory of JSON repo (default: current directory)")
    args = argparser.parse_args()

    check_dir_access(args.base_path)

    return args

def check_dir_access(path):
    if not os.path.isdir(path):
        sys.exit("%s is not a valid path" % path)
    elif os.access(path, os.R_OK):
        return
    else:
        sys.exit("%s is not a readable directory")

def test_file_access(path):
    if not os.path.isfile(path):
        return "%s does not exist" % path
    elif os.access(path, os.R_OK):
        return
    else:
        return "%s is not a readable file"

def check_file_access(path):
    result = test_file_access(path)
    if result:
        sys.exit(result)

if __name__ == "__main__":
    args = parse_commandline()    
    logger = Logger(args.verbose)
    validator = Validator(args.base_path, logger, args.fix_formatting)
    validator.validate()

    validator.show_results()