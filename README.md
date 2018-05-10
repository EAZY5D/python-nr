## The `nr` namespace package

This repository contains the `nr` Python namespace package. This package
has no contents besides the common search path extension code, which is
also placed in the `__init__.py` of every submodule/subpackage:

```python
try:
  from pkg_resources import declare_namespace
  declare_namespace(__name__)
except ImportError:
  import pkgutil
  __path__ = pkgutil.extend_path(__path__, __name__)
```

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
