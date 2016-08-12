#!/usr/bin/env python

import argparse
import json
import jsonschema
import os
import sys

PACK_DIR="pack"
SCHEMA_DIR="schema"
TRANS_DIR="translations"

formatting_errors = 0
validation_errors = 0

def check_dir_access(path):
    if not os.path.isdir(path):
        sys.exit("%s is not a valid path" % path)
    elif os.access(path, os.R_OK):
        return
    else:
        sys.exit("%s is not a readable directory")

def check_file_access(path):
    if not os.path.isfile(path):
        sys.exit("%s does not exist" % path)
    elif os.access(path, os.R_OK):
        return
    else:
        sys.exit("%s is not a readable file")

def check_json_schema(args, data, path):
    global validation_errors
    try:
        jsonschema.Draft4Validator.check_schema(data)
        return True
    except jsonschema.exceptions.SchemaError as e:
        verbose_print(args, "%s: Schema file is not valid Draft 4 JSON schema.\n" % path, 0)
        validation_errors += 1
        print(e)
        return False

def custom_card_check(args, card, pack_code, locale=None):
    "Performs more in-depth sanity checks than jsonschema validator is capable of. Assumes that the basic schema validation has already completed successfully."
    if locale:
        pass #no checks by the moment
    else:
        if card["pack_code"] != pack_code:
            raise jsonschema.ValidationError("Pack code '%s' of the card '%s' doesn't match the pack code '%s' of the file it appears in." % (card["pack_code"], card["code"], pack_code))

def custom_pack_check(args, pack, cycles_data, locale=None, en_packs=None):
    if locale:
        if pack["code"] not in [p["code"] for p in en_packs]:
            raise jsonschema.ValidationError("Pack code '%s' in translation file for '%s' locale does not exists in original locale." % (pack["code"], locale))
    else: 
        if pack["cycle_code"] not in [c["code"] for c in cycles_data]:
            raise jsonschema.ValidationError("Cycle code '%s' of the pack '%s' doesn't match any valid cycle code." % (pack["cycle_code"], pack["code"]))

def format_json(json_data):
    formatted_data = json.dumps(json_data, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))
    formatted_data += "\n"
    return formatted_data

def load_json_file(args, path):
    global formatting_errors
    global validation_errors
    try:
        with open(path, "rb") as data_file:
            bin_data = data_file.read()
        raw_data = bin_data.decode("utf-8")
        json_data = json.loads(raw_data)
    except ValueError as e:
        verbose_print(args, "%s: File is not valid JSON.\n" % path, 0)
        validation_errors += 1
        print(e)
        return None

    verbose_print(args, "%s: Checking JSON formatting...\n" % path, 1)
    formatted_raw_data = format_json(json_data)

    if formatted_raw_data != raw_data:
        verbose_print(args, "%s: File is not correctly formatted JSON.\n" % path, 0)
        formatting_errors += 1
        if args.fix_formatting and len(formatted_raw_data) > 0:
            verbose_print(args, "%s: Fixing JSON formatting...\n" % path, 0)
            try:
                with open(path, "wb") as json_file:
                    bin_formatted_data = formatted_raw_data.encode("utf-8")
                    json_file.write(bin_formatted_data)
            except IOError as e:
                verbose_print(args, "%s: Cannot open file to write.\n" % path, 0)
                print(e)
    return json_data

def load_cycles(args, locale=None):
    verbose_print(args, "Loading cycle index file...\n", 1)
    cycles_base_path = locale and os.path.join(args.trans_path, locale) or args.base_path
    cycles_path = os.path.join(cycles_base_path, "cycles.json")
    cycles_data = load_json_file(args, cycles_path)

    if not validate_cycles(args, cycles_data, locale):
        return None

    return cycles_data

def load_pack_index(args, cycles_data, locale=None, en_packs=None):
    verbose_print(args, "Loading pack index file...\n", 1)
    packs_base_path = locale and os.path.join(args.trans_path, locale) or args.base_path
    packs_path = os.path.join(packs_base_path, "packs.json")
    packs_data = load_json_file(args, packs_path)

    if not validate_packs(args, packs_data, cycles_data, locale, en_packs):
        return None

    for p in packs_data:
        pack_filename = "{}.json".format(p["code"])
        packs_dir = locale and os.path.join(args.trans_path, locale, PACK_DIR) or args.pack_path
        pack_path = os.path.join(packs_dir, pack_filename)
        check_file_access(pack_path)

    return packs_data

def parse_commandline():
    argparser = argparse.ArgumentParser(description="Validate JSON in the netrunner cards repository.")
    argparser.add_argument("-f", "--fix_formatting", default=False, action="store_true", help="write suggested formatting changes to files")
    argparser.add_argument("-v", "--verbose", default=0, action="count", help="verbose mode")
    argparser.add_argument("-b", "--base_path", default=os.getcwd(), help="root directory of JSON repo (default: current directory)")
    argparser.add_argument("-p", "--pack_path", default=None, help=("pack directory of JSON repo (default: BASE_PATH/%s/)" % PACK_DIR))
    argparser.add_argument("-c", "--schema_path", default=None, help=("schema directory of JSON repo (default: BASE_PATH/%s/" % SCHEMA_DIR))
    argparser.add_argument("-t", "--trans_path", default=None, help=("translations directory of JSON repo (default: BASE_PATH/%s/)" % TRANS_DIR))
    args = argparser.parse_args()

    # Set all the necessary paths and check if they exist
    if getattr(args, "schema_path", None) is None:
        setattr(args, "schema_path", os.path.join(args.base_path,SCHEMA_DIR))
    if getattr(args, "pack_path", None) is None:
        setattr(args, "pack_path", os.path.join(args.base_path,PACK_DIR))
    if getattr(args, "trans_path", None) is None:
        setattr(args, "trans_path", os.path.join(args.base_path,TRANS_DIR))
    check_dir_access(args.base_path)
    check_dir_access(args.schema_path)
    check_dir_access(args.pack_path)

    return args

def validate_card(args, card, card_schema, pack_code, locale=None):
    global validation_errors

    try:
        verbose_print(args, "Validating card %s... " % (locale and ("%s-%s" % (card["code"], locale)) or card["name"]), 2)
        jsonschema.validate(card, card_schema)
        custom_card_check(args, card, pack_code, locale)
        verbose_print(args, "OK\n", 2)
    except jsonschema.ValidationError as e:
        verbose_print(args, "ERROR\n",2)
        verbose_print(args, "Validation error in card: (pack code: '%s' card code: '%s' name: '%s')\n" % (pack_code, card.get("code"), card.get("name")), 0)
        validation_errors += 1
        print(e)

def validate_cards(args, packs_data, locale=None):
    global validation_errors

    card_schema_path = os.path.join(args.schema_path, locale and "card_schema_trans.json" or "card_schema.json")

    CARD_SCHEMA = load_json_file(args, card_schema_path)
    if not CARD_SCHEMA:
        return
    if not check_json_schema(args, CARD_SCHEMA, card_schema_path):
        return

    for p in packs_data:
        verbose_print(args, "Validating cards from %s...\n" % (locale and "%s-%s" % (p["code"], locale) or p["name"]), 1)

        pack_base_path = locale and os.path.join(args.trans_path, locale, PACK_DIR) or args.pack_path
        pack_path = os.path.join(pack_base_path, "{}.json".format(p["code"]))
        pack_data = load_json_file(args, pack_path)
        if not pack_data:
            continue

        for card in pack_data:
            validate_card(args, card, CARD_SCHEMA, p["code"], locale)

def validate_cycles(args, cycles_data, locale=None):
    global validation_errors

    verbose_print(args, "Validating cycle index file...\n", 1)
    cycle_schema_path = os.path.join(args.schema_path, locale and "cycle_schema_trans.json" or "cycle_schema.json")
    CYCLE_SCHEMA = load_json_file(args, cycle_schema_path)
    if not isinstance(cycles_data, list):
        verbose_print(args, "Insides of cycle index file are not a list!\n", 0)
        return False
    if not CYCLE_SCHEMA:
        return False
    if not check_json_schema(args, CYCLE_SCHEMA, cycle_schema_path):
        return False

    retval = True
    for c in cycles_data:
        try:
            verbose_print(args, "Validating cycle %s... " % c.get("name"), 2)
            jsonschema.validate(c, CYCLE_SCHEMA)
            verbose_print(args, "OK\n", 2)
        except jsonschema.ValidationError as e:
            verbose_print(args, "ERROR\n",2)
            verbose_print(args, "Validation error in cycle: (code: '%s' name: '%s')\n" % (c.get("code"), c.get("name")), 0)
            validation_errors += 1
            print(e)
            retval = False

    return retval

def validate_packs(args, packs_data, cycles_data, locale=None, en_packs=None):
    global validation_errors

    verbose_print(args, "Validating pack index file...\n", 1)
    pack_schema_path = os.path.join(args.schema_path, locale and "pack_schema_trans.json" or "pack_schema.json")
    PACK_SCHEMA = load_json_file(args, pack_schema_path)
    if not isinstance(packs_data, list):
        verbose_print(args, "Insides of pack index file are not a list!\n", 0)
        return False
    if not PACK_SCHEMA:
        return False
    if not check_json_schema(args, PACK_SCHEMA, pack_schema_path):
        return False

    retval = True
    for p in packs_data:
        try:
            verbose_print(args, "Validating pack %s... " % p.get("name"), 2)
            jsonschema.validate(p, PACK_SCHEMA)
            custom_pack_check(args, p, cycles_data, locale, en_packs)
            verbose_print(args, "OK\n", 2)
        except jsonschema.ValidationError as e:
            verbose_print(args, "ERROR\n",2)
            verbose_print(args, "Validation error in pack: (code: '%s' name: '%s')\n" % (p.get("code"), p.get("name")), 0)
            validation_errors += 1
            print(e)
            retval = False

    return retval

def validate_locales(args, en_cycles, en_packs):
    verbose_print(args, "Validating I18N files...\n", 1)
    if os.path.exists(args.trans_path):
        check_dir_access(args.trans_path)
        for locale in [l for l in os.listdir(args.trans_path) if os.path.isdir(os.path.join(args.trans_path, l))]:
            verbose_print(args, "Validating I18N files for locale '%s'...\n" % locale, 1)

            cycles = load_cycles(args, locale)

            packs = load_pack_index(args, cycles, locale, en_packs)

            if packs:
                validate_cards(args, packs, locale)
            else:
                verbose_print(args, "Couldn't open packs file correctly, skipping card validation...\n", 0)


def verbose_print(args, text, minimum_verbosity=0):
    if args.verbose >= minimum_verbosity:
        sys.stdout.write(text)

def main():
    # Initialize global counters for encountered validation errors
    global formatting_errors
    global validation_errors
    formatting_errors = 0
    validation_errors = 0

    args = parse_commandline()

    cycles = load_cycles(args)

    packs = load_pack_index(args, cycles)

    if packs:
        validate_cards(args, packs)
    else:
        verbose_print(args, "Couldn't open packs file correctly, skipping card validation...\n", 0)

    validate_locales(args, cycles, packs)

    sys.stdout.write("Found %s formatting and %s validation errors\n" % (formatting_errors, validation_errors))
    if formatting_errors == 0 and validation_errors == 0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
