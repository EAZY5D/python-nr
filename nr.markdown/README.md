## nr.markdown

  [Misaka]: https://github.com/FSX/misaka
  [Pygments]: http://pygments.org/

This Python library implements some missing features for the
[Misaka/Hoedown][Misaka] markdown parser and HTML renderer.

* Handles markdown inside HTML tags (`inside-html` extension)
* Can syntax highlight code blocks with [Pygments] (`pygments` extension)
* Produce a table of contents for the generated Markdown (`toc` extension)
* Allows you to transform URLs found in the Markdown and HTML tags (`url-transform` extension)
* Exposes "smartypants" HTML entity replacement as an extension (`smartypants` extension)
* Supports explicit header IDs syntax `# ... {:headerid}` (native)

All of the above features are enabled by default, plus the following
Misaka/Hoedown features: `tables`, `fenced-code`, `autolink`, `strikethrough`,
`underline`, `quote`, `superscript`.

Some of the above mentioned features take certain option values into account.

| Option | Description |
| ------ | ----------- |
| `header_prefix` | Used by the standard HTML header render code. Prefix for the ID of generated `<hX>` tags. |
| `inside_html_tags` | Used by the `inside-html` extension. Specifies the HTML tags of which the content will be parsed as Markdown. |
| `url_transform_callback` | Used by the `url-transform` extension. If this option is set, it must be a callable that accepts exactly two arguments `link` and `is_image_src`. |

__Motivation__

There are quite a lot of Markdown parsers to choose from in Python, but none
handle most complex Markdown edge cases I have encountered consistently. I
have found [Misaka] to be the most consistent choice, but it especially lacks
the capability of parsing markdown inside HTML tags.

__Usage__

`````python
from nr.markdown import html
print(html('''
<table>
  <tr><th>We **can** use Markdown here!</th></tr>
  <tr><td>
```python
print("Hello, World!")
```
  </td></tr>
</table>'''))
`````

__API__

`nr.markdown.html(text, options=None, extensions=None)`

> Renders the Markdown *text*. If specified, *options* must be a dictionary.
> *extensions* should be a list of strings and/or `nr.markdown.Extension`
> objects.

`nr.markdown.Extension`

> Base class for extensions. Check the [Misaka Docs] for the methods that
> can be overwritten, but note that all methods on this class must accept
> a `context` parameter that is a dictionary which contains the data for
> the callback. This data can either be modified by the extension or a
> resulting HTML string can be returned.

`nr.markdown.Markdown(options=None, extensions=None)`

> A subclass of `misaka.Markdown` that enables the use of the extension
> mechanism used by this library.

__Requirements__

* [Misaka]
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
* [Pygments]
