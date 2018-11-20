# nr.cli

Provides the `nr` command-line tool which provides access to the entry-points
registered to the `nr.cli:commands` group.


### Changes

#### v1.0.2

* Use setuptools entrypoints instead of discovering commands by
  walking the modules in the `nr` namespace.

#### v1.0.1 (2018-07-05)

* Tidy help output
* Update the way module names with `main()` function members are turned
  into command names (specifically, prevent modules like `nr.git_worklog.main`
  to cause a "main" command)
* Add -l, --list-packages

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
