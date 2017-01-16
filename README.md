SWDestinyDB cards JSON data [![CircleCI](https://circleci.com/gh/fafranco82/swdestinydb-json-data.svg?style=svg)](https://circleci.com/gh/fafranco82/swdestinydb-json-data)
=========

The goal of this repository is to store [SWDestinyDB](https://swdestinydb.com) card data in a format that can be easily updated by multiple people and their changes reviewed.

## Validating and formatting JSON

Using python >=2.6, type in command line:

```
./validate.py --verbose --fix_formatting
```

The above script requires python package `jsonschema` which can be installed using `pip` via `pip install -U jsonschema`.

You can also just try to follow the style existing files use when editing entries. They are all formatted and checked using the script above.

## Description of properties in schemas

Required properties are in **bold**.

#### Set schema

* **code** - identifier of the set. The acronym of the set name, with matching case. Examples: `"AW"` for Awakenings.
* **name** - properly formatted name of the set. Examples: `"Awakenings"`.
* **position** - number of the set. Examples: `1` for Awakenings.
* **released** - date when the set was officially released by FFG. When in doubt, look at the date of the pack release news on FFG's news page. Format of the date is YYYY-MM-DD. May be `null` - this value is used when the date is unknown. Examples: `"2016-12-01"` for Awakenings, `null` for unreleased previewed packs.
* **size** - number of different cards in the set. May be `null` - this value is used when the pack is just an organizational entity, not a physical set.  Examples: `174` for Awakenings, `null` for assorted draft cards.

#### Card schema

* **affiliation_code**
* **code** - 5 digit card identifier. Consists of two zero-padded numbers: first two digits are the set position, last three are position of the card within the set (printed on the card).
* cost - Play cost of the card. Relevant for all cards except characters and battlefields. May be `null` - this value is used when the card has a special, possibly variable, cost (i.e. `X` values).
* **deck_limit**
* **faction_code**
* flavor
* **has_die** - whether the card has a die (true) or not (false)
* health - Characters only
* illustrator
* **is_unique**
* **name**
* points - Characters only
* **position**
* **rarity_code** - Initial of rarity: (S)tarter, (C)ommon, (U)ncommon, (R)are or (L)egendary
* **set_code** - Acronym of set code. For example, `"AW"` for Awakenings
* sides - If the card has a die, this represents the die faces. It is an array of exactly six elements, each of them comprised of (in order):
	* An optional plus (`+`) sign for sides that are modified values
	* An integer value for all of all side signs except Special and Blank. IF the sign is neither special nor blank, a value of 0 indicate a variable value (i.e., an `X` value)
	* The sign acronym. With:
		* `MD` - Melee damage
		* `RD` - Ranged damage
		* `F` - Focus
		* `Dr` - Disrupt
		* `Dc` - Discard
		* `Sh` - Shield
		* `R` - Resource
		* `Sp` - Special
		* '-' - Blank side
	* An optional resource cost
	So, for example, a side with a modified 2 ranged damage with 1 resource cost would be `+2RD1`.
* subtitle - Characters only (optional)
* subtype_code - Upgraded and Support. Usually, the lowercase of what is in printed on the card. For further reference, see `subtypes.json` file.
* text
* **ttscardid** - 4 digit card identifier for TableTop Simulator MOD created by IceKobra. Consists of two zero-padded numbers: first two digits are the `CustomDeck` identifier which is tied to the graphic for the face of the card, last two are position of the card within the on the graphic.
* **type_code** - Type of the card. Possible values: `"character"`, `"upgrade"`, `"support"`, `"event"`, `"battlefield"`

## JSON text editing tips

Full description of (very simple) JSON format can be found [here](http://www.json.org/), below there are a few tips most relevant to editing this repository.

#### Non-ASCII symbols

When symbols outside the regular [ASCII range](https://en.wikipedia.org/wiki/ASCII#ASCII_printable_code_chart) are needed, UTF-8 symbols come in play. These need to be escaped using `\u<4 letter hexcode>`.

To get the 4-letter hexcode of a UTF-8 symbol (or look up what a particular hexcode represents), you can use a UTF-8 converter, such as [this online tool](http://www.ltg.ed.ac.uk/~richard/utf-8.cgi).

#### Quotes and breaking text into multiple lines

To have text spanning multiple lines, use `\n` to separate them. To have quotes as part of the text, use `\"`.  For example, `"\"Orange and white: one of a kind.\" <cite>Poe Dameron</cite>"` results in following flavor text:

> *"Orange and white: one of a kind." Poe Dameron*

#### Star Wars Destiny symbols

These can be used in a card's `text` section.

 * `[melee]`
 * `[ranged]`
 * `[focus]`
 * `[discard]`
 * `[disrupt]`
 * `[shield]`
 * `[resource]`
 * `[special]`
 * `[blank]`

#### Translations

To merge new changes in default language in all locales, run the CoffeeScript script `update_locales`.

Pre-requisites:
 * `node` and `npm` installed
 * `npm -g install coffee-script`

Usage: `coffee update_locales.coffee [language code]`

(NOTE: a folder with the language code must exists in `translations` folder)
