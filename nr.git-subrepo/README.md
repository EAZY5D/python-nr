# nr.git-subrepo

The `nr git-subrepo` command is a tool to create a worktree of a remote Git
repository and tracking its files.

#### Advantages over submodules

* Avoid depending on the longevity of the submodule's remote repository
* Track changes to the sub repository in the parent

#### Installation

  [PyPI]: https://pypi.org/project/nr.git-subrepo

You can get the latest stable version from [PyPI]. We recommended creating
an alias in your Git configuration file so you can access the tool via the
`git` command-line.

    $ pip install nr.git-subrepo
    $ git config --global alias.subrepo '!nr git-subrepo'
    $ git subrepo --version
    1.0.0

You may choose to install the tool directly from the source repository. This
allows you to get the latest development version.

    $ pip install git+https://gitlab.niklasrosenstein.com/NiklasRosenstein/python/nr.git-subrepo.git
    $ git subrepo --version
    1.0.1-dev

#### Usage Example

Any time that you think about adding a Git submodule, you can add a sub
repository instead. The `git subrepo` tool allows you to conveniently add,
remove and stage sub repositories. It also provides you with a tool to convert
existing Git submodules to sub repositories.

To add a new sub repository:

    $ git subrepo add -s https://github.com/some/library.git

Similar to `git submodule`, the add command will use the basename of the
provided URL as the default path to place the Git worktree at. In the case
above, it will be `./library`.

    $ git -C library remote get-url origin
    https://github.com/some/library.git
    $ git status
    Changes to be committed:
        new file: .gitsubrepos
        new file: library/README.md

The `-s` option in the add command is used to automatically stage the added
sub repository. You can use the `git subrepo stage` command instead to
explicitly add all changes in the sub repository and the proper Git ref to
the `.gitsubrepos` file.

If you have uncommited changes in a sub repository, your changes will be
reflected for your sub repository only inside the parent repository. They will
not be reflected in the actual sub repository or its remote.

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
