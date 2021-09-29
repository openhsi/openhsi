# How to contribute

## How to get started

Clone the repository
```
git clone https://github.com/YiweiMao/openhsi
cd openhsi
```

You will need to install `nbdev` to extract the library and produce the documentation files from the notebooks. To upload to PyPi, you will need to install `twine` (so far, only yours truely can do this).
```
pip install nbdev
pip install twine
```

Before anything else, please install the git hooks that run automatic scripts during each commit and merge to strip the notebooks of superfluous metadata (and avoid merge conflicts). After cloning the repository, run the following command inside it:
```
nbdev_install_git_hooks
```

## A note on how the automation tools are set up

Any cell in the notebook marked with `#export` in the first line, will be extracted to generate the library. All other cells are used to create the documentation and to define tests. 

To hide cells from appearing in the documentation, mark the cell with `#hide` in the first line. That's it!

## Extracting Library
Any cells you mark as `#export` in the first line is automatically extracted. All other cells will appear in the documentation. If you don't want cells to appear in the documentation, mark the first line with `#hide`. To extract the library, the terminal command is
```
make openhsi
```

## Documentation

Docs are automatically created from the notebooks. The terminal command is
```
make docs
```

## Uploading to PyPi

Version number is automatically incremented and uploaded to PyPi so people can `pip install openhsi`. To set this up, you first need to make an account on PyPi, then create a file `~/.pypirc` with the contents
```
[pypi]
username = your_pypi_username
password = your_pypi_password
```

To upload to PyPi, enter
```
make release
```
into the terminal. If you don't want to increment the version number, use `make pypi` instead.

Settings such as dependencies, licence, version number, status, etc, can be changed in the `settings.ini` file.

To include calibration files in the PyPi install, you need to add the file to the `MANIFEST.in` file. 


## Updating changes to GitHub

First fastforward your copy to include the latest change.
```
git pull
```

Push your changes as usual.
```
git add .
git commit -m "commit message"
git push
```


## Did you find a bug?

* Ensure the bug was not already reported by searching on GitHub under Issues.
* If you're unable to find an open issue addressing the problem, open a new one. Be sure to include a title and clear description, as much relevant information as possible, and a code sample or an executable test case demonstrating the expected behavior that is not occurring.
* Be sure to add the complete error messages.

#### Did you write a patch that fixes a bug?

* Open a new GitHub pull request with the patch.
* Ensure that your PR includes a test that fails without your patch, and pass with it.
* Ensure the PR description clearly describes the problem and solution. Include the relevant issue number if applicable.

## PR submission guidelines

* Keep each PR focused. While it's more convenient, do not combine several unrelated fixes together. Create as many branches as needing to keep each PR focused.
* Do not mix style changes/fixes with "functional" changes. It's very difficult to review such PRs and it most likely get rejected.
* Do not add/remove vertical whitespace. Preserve the original style of the file you edit as much as you can.
* Do not turn an already submitted PR into your development playground. If after you submitted PR, you discovered that more work is needed - close the PR, do the required work and then submit a new PR. Otherwise each of your commits requires attention from maintainers of the project.
* If, however, you submitted a PR and received a request for changes, you should proceed with commits inside that PR, so that the maintainer can see the incremental fixes and won't need to review the whole PR again. In the exception case where you realize it'll take many many commits to complete the requests, then it's probably best to close the PR, do the work and then submit it again. Use common sense where you'd choose one way over another.



