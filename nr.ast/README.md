# `nr.ast`

&ndash; Stuff related to the Python AST and code evaluation.

## Changelog

### v1.1.0

* add missing dependency to `six` (close #1)
* remove `import * from nr.ast.dynamic_eval` in `nr.ast` module (close #2)
* make `DynamicMapping` class accessible through `nr.ast.dynamic_eval`
* remove `resolve`/`assign`/`delete` parameters to `dynamic_eval()` function
* fix `transform(data_var)` parameter usage
