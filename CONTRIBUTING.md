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
repository's [issues section](https://github.com/itsthejoker/TranscribersOfReddit/issues).
Please, be kind and search through both open and closed issues to make sure your question
or bug report hasn't already been posted and resolved.

## Development

After checking out the repo, run `bin/run setup` to install native dependencies.

To install this package locally, setup a virtualenv environment and run `pip install --process-dependency-links -e .`
from the project root. To make sure you have everything setup correctly, run `bin/run test`
and it _should_ pass entirely.

In case you get tired of prefixing `bin/` to the `run` script here, [Tim Pope's method](https://twitter.com/tpope/status/165631968996900865)
of safely adding a script to your PATH is recommended.

## Testing

This project has (some) automated test coverage, so be sure to check that tests are passing
_before_ you begin development. Our emphasis is on stability here, so if tests aren't passing,
that's a bug.

### Stability

As noted before, make sure tests are passing before starting. If you have difficulty getting
to that stable, initial state, reach out by opening an issue (see [Issues](#Issues) above).
This is considered a failing by the maintainers if instructions are less than absolutely
clear. Any feedback is helpful here!

### Writing tests

Tests are written using `unittest` because it is sufficient for our needs at this time and
it is part of the standard library in Python. We invoke the full test suite by calling
`bin/run test`.

At the moment, the test suite should run very quickly, but that won't always be the case.
Running individual tests with `python path/to/test/file.py` is also acceptable while
actively developing. Note that a pull request should always have a fully passing test suite.

## Pull Requests

If you're unfamiliar with the process, see [Github's helpful documentation](https://help.github.com/articles/about-pull-requests/)
on creating pull requests.

We try to keep parity of at least one issue in each pull request. This is so we can discuss the
big-picture plans in the issue, hopefully before actual development begins. This helps keep
wasted time to a minimum.

### "[WIP]" Requests

Sometimes there are changes that might not be finished, but require periodic feedback--which
is recommended for large changes. If this is the case, add `[WIP]` to the start of the title
of the pull request when opening it, or edit the existing pull request title to include it.
For example:

```
TITLE: [WIP] Convert from Redis to Cassandra

Some description here

- [ ] To do list item
- [ ] Other to do list item
- [x] Completed to do list item

I'm looking for feedback on what I've added so far.
```

## Changelog

We follow the practices defined on [Keep A Changelog](http://keepachangelog.com), keeping
our changelog in [`CHANGELOG.md`](/CHANGELOG.md)

The gist of it is:

- Add line items with a very short summary of changes to `CHANGELOG.md` under the `UNRELEASED` section as they are created
- Add `(credit: @your_username)` at the end of each line item added
- (_When releasing a new version_) Replace `UNRELEASED` section title with the version number of the release, then create a new header above it named `UNRELEASED`
