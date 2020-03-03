# Contributing

Here is a short checklist of what we strive for in a well-formed code contribution:

- [ ] Commit log is clean and devoid of "debugging" types of commits
- [ ] Entry into [`CHANGELOG.md`](/CHANGELOG.md) with `(credit: @username)` (see **Changelog** below)
- [ ] Pull request is associated with at least 1 issue
- [ ] Automated tests are passing
- [ ] Static analysis (`mypy` and `flake8`) should succeed

Do your best to check as many of these boxes as you can and everything will be fine!

## Issues

Any bugs you find, features you want to request, or questions you have should go in the
repository's [issues section](https://github.com/GrafeasGroup/tor/issues).
Please, be kind and search through both open and closed issues to make sure your question
or bug report hasn't already been posted and resolved.

## Development

Initial setup:

```bash
# Clone the repository
$ git clone git@github.com:GrafeasGroup/tor.git tor
$ cd ./tor

$ poetry install
$ poetry run pytest
```

## Testing

This project has automated tests. Be sure to check that tests are passing _before_ you
begin development. Our emphasis is on stability here, so if tests aren't passing, that's
a bug.

```bash
$ poetry run mypy .
$ poetry run flake8 .
$ poetry run pytest
```

If you have difficulty getting to that stable, initial state, reach out by opening an
issue (see [Issues](#Issues) above). This is considered a failure by the maintainers if
instructions are less than absolutely clear. Feedback is very helpful here!

### Writing tests

Tests are written using `pytest` for a variety of reasons. Some of which are:

- standard lib `unittest` tests are supported, should you choose to write those instead
- Python keyword `assert` may be used, which pytest supplements with context supporting _why_ the assertion failed
- test control mechanisms such as skipping with stated reason or marking tests as expected to fail
- colorized output
- code coverage reports (via `pytest-cov`) indicating which lines of app code were never executed in tests

The full test suite may be executed using `poetry run pytest`. Individual tests may be
specified by method name (`poetry run pytest -k test_method_name`) or by filename
(`poetry run pytest ./path/to/test_file.py`).

## Pull Requests

If you're unfamiliar with the process, see [Github's helpful documentation](https://help.github.com/articles/about-pull-requests/)
on creating pull requests (PR).

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

Alternatively, when creating a pull request, GitHub allows you to create it as a Draft PR. This is
also a valid way to indicate it is a work-in-progress. The drawbacks to this approach are twofold:

1. Option to create a Draft PR is only presented when opening the PR
2. Once created as a Draft PR and submitted as ready for consideration, there is no way to go back to that Draft PR state

For these reasons, both the `[WIP]` option and the Draft PR option are acceptable. The title of a
PR may be modified at any time to revert back to it being a work-in-progress.

## Changelog

We follow the practices defined on [Keep A Changelog](http://keepachangelog.com), keeping our
changelog in [`CHANGELOG.md`](/CHANGELOG.md)

The gist of it is:

- Add line items with a short summary of changes to `CHANGELOG.md` under the `UNRELEASED` section as they are created
- Add `(credit: @your_username)` at the end of each line item added
- (_When releasing a new version_) Replace `UNRELEASED` section title with the version number of the release, then create a new header above it named `UNRELEASED`

## Releasing the Code

Assuming there is a new release that needs to be published...

1. Consider the changelog entries since the last release. According to [Semantic Versioning](https://www.semver.org/), what should the new version be?
2. Change the `UNRELEASED` title to say the new version and the current ISO-8601 year, month, and date. Create a new `UNRELEASED` section with `_Nothing yet..._` under it
3. Update the version in `pyproject.toml` and `tor/__init__.py` to be the new version
4. Stage and commit all of the files modified above on the `master` branch
5. Create a git tag (if releasing version 3.2.2, create tag named `v3.2.2`) based off of the commit to `master`
6. Push the commit and the tag to GitHub (e.g., `git push origin master --tags`)

From here there is automation to pick up that a new tag was pushed. That automation will package the
python code into the appropriate formats and upload them to the associated GitHub Release page for that
tag. If, for some reason that does not occur, it may also be done manually:

1. Select the pushed tag in [the releases section](https://github.com/GrafeasGroup/tor/releases)
2. Click to "draft new release"
3. Attach files from `./dist/` which were created by running `poetry build` in your local repository
4. Click to publish the release

As soon as code is released, we should deploy it to the server that runs these bots. See private docs
for handling that.
