# Changelog

We follow [Semantic Versioning](http://semver.org/) as a way of measuring stability of an update. This
means we will never make a backwards-incompatible change within a major version of the project.

## v2.7.1 (2017-07-01)

- Modify date logic and fix config loading for archivist bot
- adds css_flair dict for easier interaction with css (by @itsthejoker)

## v2.7.0 (2017-07-01)

- Adds `setup.py` for pip packaging
- Fixes linting errors
- Removes imports and non-essential, mutating functions from `tor/__init__.py`
- Adds automated testing, starting with configuration object
- Significant rewording of `README.md` for clarity
- Add `bin/run` as user-friendly editing for task runner (see [`.git/safe/../../bin` PATH protocol](https://twitter.com/tpope/status/165631968996900865))
- Basics for a bot automatically removing and archiving old posts (by @arfie)
- Updated `README.md` with information on u/ToR_archivist (by @arfie)

## v2.6.14 (2017-06-07)

- Started logging changes into CHANGELOG.md
- [Some changes before this point may not be included]
