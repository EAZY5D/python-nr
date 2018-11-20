# nr.gitignore

A simple `.gitignore` pattern parser and matcher.

### Example Usage

```python
import os
import nr.gitignore
patterns = nr.gitignore.parse()
for root, dirs, files in nr.gitignore.walk(patterns, '.'):
  # ...
```

```python
import nr.gitignore
ignore = nr.gitignore.IgnoreList()
ignore.parse(['__pycache__', 'dist'])
assert ignore.match('./dist/module-1.0.0.tar.gz') == nr.gitignore.MATCH_IGNORE
```

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
