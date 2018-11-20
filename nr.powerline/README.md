# nr.powerline

Simple powerline module. Use with [NerdFonts](https://nerdfonts.com/#downloads)

![](https://i.imgur.com/BNpDHhZ.png)

__Todolist__

- Truecolor support

### Plugins

The entry point for powerline plugins is `nr.powerline.plugins`. Entry points
must inherit from the `nr.powerline.plugins.Plugin` class.

### Configuration

The powerline can be configured with environment variables.

| Variable | Description |
| -------- | ----------- |
| `NR_POWERLINE_SCRIPT` | Path to a Python script that uses the `nr.powerline` API to render a powerline to stdout. |
| `NR_POWERLINE_CODE` | Actual Python code that uses the `nr.powerline` API to render a powerline to stdout. |

Check the default configuration in `src/nr/powerline/main.py` for an example script.
