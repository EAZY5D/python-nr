# nr.cli

Install this module if you need access to any of the command-line tools
provided by `nr` namespace packages.

### Example Usage

```
usage: nr [-h] [-l] [COMMAND [ARGS...]

options:
  -h, --help   display this help message
  -l, --list-packages
               display a list of packages that may contain additional
               command-line tools and can be installed via Pip.
```

### Changes

#### v1.0.1 (2018-07-05)

* Tidy help output
* Update the way module names with `main()` function members are turned
  into command names (specifically, prevent modules like `nr.git_worklog.main`
  to cause a "main" command)
* Add -l, --list-packages

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
