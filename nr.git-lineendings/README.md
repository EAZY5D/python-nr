# nr.git-lineendings

Find issues with line-endings in your repository.

> `usage: nr git-lineutils [-h] {detect-change,show,check} ...`

```
usage: git-lineutils detect-change [-h] [--rev REV] file

positional arguments:
  file        The file to detect a change in line-endings for.

optional arguments:
  -h, --help  show this help message and exit
  --rev REV   Start searching from the specified revision.
```

```
usage: git-lineutils show [-h] [-b] [-a] [--unmerged UNMERGED] [--lf] [--crlf]
                          file [at]

positional arguments:
  file                 The file to show the line-endings for.
  at                   The revision at which to read the file from.

optional arguments:
  -h, --help           show this help message and exit
  -b, --branches       Show the line-endings in all branches.
  -a, --all            Include remote branches.
  --unmerged UNMERGED  Exclude branches that are merged into the specified
                       branch.
  --lf                 Only show branches with LF.
  --crlf               Only show branches with CRLF.
```

```
usage: git-lineutils check [-h]

Checks your Git configuration and makes suggestions.

optional arguments:
  -h, --help  show this help message and exit
```

### Examples

To find commits where a change from one line-ending format to another
occurred:

```
$ git lineutils detect-change myfile.py
3d18d03547bb130ab0d4afbd302adcbfda5ac5ba..5fac6a3b091d998515c570d103733157580c50d7 (LF..CRLF) merge-commit
bb42296118b9bd29c43da67ee209c18d8a042bcf..3a5607cd4bb220b7ac49f0931834bdb4471b434c (LF..CRLF) merge-commit
b4cfd807796bb22c08cc4a162c2324272f83fd47..ce65e90b050a0b985d34291b27b941eca3d964f9 (LF..CRLF) merge-commit
b4cfd807796bb22c08cc4a162c2324272f83fd47..e82dcaa5889b59138a66bc8a5fdc3cd8caa4284c (LF..CRLF) merge-commit
64f80bfe6f66edf98f7b11b8dc8e11669322e7c4..52bebb2c0fff0a735073ebbf26b9a11e6c1d6a89 (LF..CRLF) merge-commit
e43b352c4957eb9c3036a2ce16d7a0c85743f235..0d025846d088dcc4d8b0fafe4d27a2b8aec9ae4b (LF..CRLF) merge-commit
04af632704abcdaba61b7f3cd29cfa18c3f5a302..0dbe96c51ec3255498453393339ff139f779e0c1 (LF..CRLF) merge-commit
9571afd2e5d9f39f5a7c75fbbab7d678778dadbf..4d1540a1191d8d6e50a8685e862d3311ee60228d (LF..CRLF)
 306/708 (07d150671f9b8528438ce5e61378c01b4fb43294)
```

Note that the last commit returned by this command is usually where it started.

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
