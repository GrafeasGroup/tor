[![Waffle.io - Columns and their card count](https://badge.waffle.io/TranscribersOfReddit/TranscribersOfReddit.svg?columns=all)](http://waffle.io/TranscribersOfReddit/TranscribersOfReddit)

# Contributing

Here is a short checklist of what we strive for in a well-formed code contribution:

- [ ] Commit log is clean and devoid of "debugging" types of commits
- [ ] Entry into [`CHANGELOG.md`](/CHANGELOG.md) with `(credit: @username)` (see **Changelog** below)
- [ ] Pull request is associated with at least 1 issue
- [ ] Virtualenv files are not included in the commit log

Do your best to check as many of these boxes as you can and everything will be fine!

## Issues

Any bugs you find, features you want to request, or questions you have should go in the
repository's [issues section](https://github.com/TranscribersOfReddit/TranscribersOfReddit/issues).
Please, be kind and search through both open and closed issues to make sure your question
or bug report hasn't already been posted and resolved.

## Development

Initial setup:

```bash
# Clone the repository
$ git clone git@github.com:TranscribersOfReddit/TranscribersOfReddit.git tor
$ cd ./tor

# Setup sandbox
$ virtualenv --no-site-packages --python=python3 venv
$ source ./venv/bin/activate

# Install the project in "editable" mode
$ pip install --process-dependency-links -e .[dev]
```

In case there are any tests, they would be run by calling `python setup.py test`.

## Testing

This project is expected to have automated test coverage, so be sure to check that tests
are passing _before_ you begin development. Our emphasis is on stability here, so if tests
aren't passing, that's a bug.

### Stability

As noted before, make sure tests are passing before starting. If you have difficulty getting
to that stable, initial state, reach out by opening an issue (see [Issues](#Issues) above).
This is considered a failure by the maintainers if instructions are less than absolutely
clear. Feedback is very helpful here!

### Writing tests

Tests are written using `pytest` for a variety of reasons. Some of which are:

- easy assertions that an exception will be thrown and the message it contains
- skipping some tests for stated reasons
- marking some tests as expected to fail
- colorized output compared to `unittest`

We should be able to invoke the full test suite by calling either `python setup.py test` or
`pytest` from the terminal.

The test suite should run quickly at the moment, but that won't always be the case. Running
individual tests with `pytest path/to/test/file.py` is also acceptable while actively
developing.

> **NOTE:** a pull request should always have a fully passing test suite.

## Pull Requests

If you're unfamiliar with the process, see [Github's helpful documentation](https://help.github.com/articles/about-pull-requests/)
on creating pull requests.

We try to keep parity of at least one issue in each pull request. This is so we can discuss the
big-picture plans in the issue, preferrably before actual development begins. This helps keep
wasted time to a minimum.

### "[WIP]" Requests

Sometimes there are changes that are unfinished, but require periodic feedback--which is recommended
for large changes. If this is the case, add `[WIP]` to the start of the title of the pull request
when opening it, or edit the existing pull request title to include it. For example:

```
TITLE: [WIP] Convert from Redis to Cassandra

Some description here

- [ ] To do list item
- [ ] Other to do list item
- [x] Completed to do list item

I'm looking for feedback on what I've added so far.
```

## Changelog

We follow the practices defined on [Keep A Changelog](http://keepachangelog.com), keeping our
changelog in [`CHANGELOG.md`](/CHANGELOG.md)

The gist of it is:

- Add line items with a short summary of changes to `CHANGELOG.md` under the `UNRELEASED` section as they are created
- Add `(credit: @your_username)` at the end of each line item added
- (_When releasing a new version_) Replace `UNRELEASED` section title with the version number of the release, then create a new header above it named `UNRELEASED`
