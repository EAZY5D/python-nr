# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0.3'

import misaka
import re
import sys


def import_class(name):
  module, class_ = name.rpartition('.')[::2]
  return getattr(__import__(module, fromlist=[None]), class_)


class Markdown(misaka.Markdown):

  EXTENSIONS = {
    'inside-html': __name__ + '.InsideHtmlExtension',
    'smartypants': __name__ + '.SmartypantsExtension',
    'pygments': __name__ + '.PygmentsExtension',
    'url-transform': __name__ + '.UrlTransformExtension',
    'toc': __name__ + '.TocExtension'
  }

  DEFAULT_EXTENSIONS = [
    'tables', 'fenced-code', 'autolink', 'strikethrough', 'underline',
    'quote', 'superscript'
  ] + list(EXTENSIONS.keys())

  def __init__(self, options=None, extensions=None):
    if extensions is None:
      extensions = self.DEFAULT_EXTENSIONS
    misaka_exts = []
    python_exts = []
    for ext in extensions:
      if isinstance(ext, str) and ext in self.EXTENSIONS:
        ext = import_class(self.EXTENSIONS[ext])()
      if isinstance(ext, str):
        misaka_exts.append(ext)
      else:
        python_exts.append(ext)

    super().__init__(_ExtensionHtmlRenderer(python_exts), misaka_exts)

    if options is None:
      options = {}

    self.options = options

  def __call__(self, text):
    self.renderer.init(self)
    text = self.renderer.preprocess(text)
    text = super().__call__(text)
    text = self.renderer.postprocess(text)
    return text


class _ExtensionHtmlRenderer(misaka.HtmlRenderer):

  def __init__(self, extensions):
    super().__init__()
    self.extensions = list(extensions)
    self.extensions.append(FallbackHtmlRendererExtension())
    self.md = None

  def init(self, md):
    self.md = md
    for ext in self.extensions:
      ext.run('init', md)

  def __call_extensions(self, method, **kwargs):
    kwargs['md'] = self.md
    for ext in self.extensions:
      result = ext.run(method, kwargs)
      if result is not None:
        break
    else:
      result = ''
    kwargs['return'] = result
    for ext in self.extensions:
      ext.run('post_' + method, kwargs)
    return kwargs

  def preprocess(self, body):
    return self.__call_extensions('preprocess', body=body)['body']

  def postprocess(self, body):
    return self.__call_extensions('postprocess', body=body)['body']

  def make_caller(method, *argnames):
    def function(self, *args):
      kwargs = dict(zip(argnames, args))
      return self.__call_extensions(method, **kwargs)['return']
    function.__name__ = method
    function.__qualname__ = method
    return function

  blockcode = make_caller('blockcode', 'text', 'lang')
  blockquote = make_caller('blockquote', 'content')
  header = make_caller('header', 'content', 'level')
  hrule = make_caller('hrule')
  list = make_caller('list', 'content', 'is_ordered', 'is_block')
  listitem = make_caller('listitem', 'content', 'is_ordered', 'is_block')
  paragraph = make_caller('paragraph', 'content')
  table = make_caller('table', 'content')
  table_header = make_caller('table_header', 'content')
  table_body = make_caller('table_body', 'content')
  table_row = make_caller('table_row', 'content')
  table_cell = make_caller('table_cell', 'content')
  footnotes = make_caller('footnotes', 'content')
  footnote_def = make_caller('footnote_def', 'content', 'num')
  footnote_ref = make_caller('footnote_ref', 'num')
  blockhtml = make_caller('blockhtml', 'content')
  autolink = make_caller('autolink', 'link', 'is_email')
  codespan = make_caller('codespan', 'text')
  double_emphasis = make_caller('double_emphasis', 'content')
  emphasis = make_caller('emphasis', 'content')
  underline = make_caller('underline', 'content')
  highlight = make_caller('highlight', 'content')
  quote = make_caller('quote', 'content')
  image = make_caller('image', 'link', 'title', 'alt')
  linebreak = make_caller('linebreak')
  link = make_caller('link', 'content', 'link', 'title')
  triple_emphasis = make_caller('triple_emphasis', 'content')
  strikethrough = make_caller('strikethrough', 'content')
  superscript = make_caller('superscript', 'content')
  math = make_caller('math', 'text', 'displaymode')
  raw_html = make_caller('raw_html', 'text')
  entity = make_caller('entity', 'text')
  normal_text = make_caller('normal_text', 'text')
  doc_header = make_caller('doc_header', 'inline_render')
  doc_footer = make_caller('doc_footer', 'inline_render')

  del make_caller


class Extension(object):

  def run(self, method, context):
    if hasattr(self, method):
      return getattr(self, method)(context)


class FallbackHtmlRendererExtension(Extension):
  """
  This is the fallback extension that renders the plain HTML code.
  """

  def blockcode(self, context):
    text = misaka.escape_html(context['text'])
    return '\n<pre><code>{}</pre></code>'.format(text)

  def blockquote(self, context):
    return '\n<blockquote>{}</blockquote>'.format(context['content'])

  def header(self, context):
    m = re.search(r'{:([\w\d_\-\.]+)}\s*$', context['content'])
    if m:
      header_id = m.group(1)
      context['content'] = context['content'][:m.start()].rstrip()
    else:
      header_id = re.sub(r'[^\w\d_\.]+', '-', context['content']).strip('-')
    header_prefix = context['md'].options.get('header_prefix')
    if header_prefix:
      header_id = header_prefix + header_id
    context['header_id'] = header_id
    return '<h{level} id="{header_id}">{content}</h{level}>'.format(**context)

  def hrule(self, context):
    return '\n<hr/>'

  def list(self, context):
    tag = 'ol' if context['is_ordered'] else 'ul'
    return '\n<{}>{}</{}>'.format(tag, context['content'], tag)

  def listitem(self, context):
    return '\n<li>{}</li>'.format(context['content'])

  def paragraph(self, context):
    return '\n<p>{}</p>'.format(context['content'])

  def table(self, context):
    return '\n<table>{}</table>'.format(context['content'])

  def table_header(self, context):
    return '<thead>{}</thead>'.format(context['content'])

  def table_body(self, context):
    return '\n<tbody>{}</tbody>'.format(context['content'])

  def table_row(self, context):
    return '\n<tr>{}</tr>'.format(context['content'])

  def table_cell(self, context):
    return '<td>{}</td>'.format(context['content'])

  def footnotes(self, context):
    return '\n<div class="footnotes">{}</div>'.format(context['content'])

  def footnote_def(self, context):
    s = '<p class="footnote" id="footnote-{}"><span class="num">{}</span><span class="content">{}</span></p>'
    return s.format(context['num'], context['content'], context['num'])

  def footnote_ref(self, context):
    return '<a href="footnote-{0}">{0}</a>'.format(context['num'])

  def blockhtml(self, context):
    return context['content']

  def autolink(self, context):
    return '<a href="{0}">{0}></a>'.format(context['link'])

  def codespan(self, context):
    return '<code class="codespan">{}</code>'.format(context['text'])

  def double_emphasis(self, context):
    return '<strong><em>{}</em></strong>'.format(context['content'])

  def emphasis(self, context):
    return '<em>{}</em>'.format(context['content'])

  def underline(self, context):
    return '<u>{}</u>'.format(context['content'])

  def highlight(self, context):
    # TODO: Not sure what to do with this.
    return context['content']

  def quote(self, context):
    return '<q>{}</q>'.format(context['content'])

  def image(self, context):
    return '<img src="{}" alt="{}">'.format(context['link'], context['alt'])

  def linebreak(self, context):
    return '<br/>\n'

  def link(self, context):
    return '<a href="{}">{}</a>'.format(context['link'], context['content'])

  def triple_emphasis(self, context):
    return '<u><strong><em>{}</em></strong></u>'.format(context['content'])

  def strikethrough(self, context):
    return '<strike>{}</strike>'.format(context['content'])

  def superscript(self, context):
    return '<sup>{}</sup>'.format(context['content'])

  def math(self, context):
    return '<script type="math/tex">{}</script>'.format(context['text'])

  def raw_html(self, context):
    return misaka.escape_html(context['text'])

  def entity(self, context):
    return context['text']

  def normal_text(self, context):
    return context['text']

  def doc_header(self, context):
    return ''

  def doc_footer(self, context):
    return ''


class InsideHtmlExtension(Extension):

  TAGS = set(['td', 'th', 'p', 'a', 'details', 'summary', 'blockquote', 'div', 'span'])

  @staticmethod
  def parse(html):
    import bs4
    parser_module = 'html.parser' if sys.version_info[0] == 3 else 'HTMLParser'
    return bs4.BeautifulSoup(html, parser_module)

  def preprocess(self, context):
    body = context['body']

    # Replace characters that may indicate a blockquote with a temporary
    # string that the HTML parser will not misinterpret and convert to &gt;.
    body = re.sub('^(?<!<).*?(>)', '&blockquoteindicator;', body, flags=re.M)

    soup = self.parse(body)
    self.__process_recursively(context['md'], soup)
    body = str(soup)

    body = body.replace('&blockquoteindicator;', '>')
    return body

  def __process_recursively(self, md, node):
    inside_html_tags = md.options.get('inside_html_tags')
    if inside_html_tags is None:
      inside_html_tags = self.TAGS

    import bs4
    if isinstance(node, bs4.element.NavigableString) and node.parent.name in inside_html_tags:
      # Render the content of the string again with the markdown renderer.
      content = self.parse(md(str(node)))
      # Unpack single paragraphs.
      children = list(content.children)
      if sum(1 for x in children if x.name == 'p') == 1 and \
         sum(1 for x in children if x.name is None) == len(children) - 1:
        next(x for x in children if x.name == 'p').unwrap()
      node.replace_with(content)

    elif isinstance(node, bs4.element.Tag):
      for child in node.children:
        self.__process_recursively(md, child)


class SmartypantsExtension(Extension):

  def postprocess(self, context):
    context['body'] = misaka.smartypants(context['body'])


class UrlTransformExtension(Extension):

  def __callback(self, content, is_image_src, key='link'):
    callback = content['md'].options.get('url_transform_callback')
    if callback:
      content[key] = callback(content[key], is_image_src)

  def image(self, content):
    self.__callback(content, True)

  def link(self, content):
    self.__callback(content, False)

  def autolink(self, content):
    self.__callback(content, False)


class PygmentsExtension(Extension):
  """
  This extension uses the Python Pygments module to parse blockcode and
  highlight it.
  """

  def blockcode(self, context):
    from pygments import highlight
    from pygments.formatters import HtmlFormatter, ClassNotFound
    from pygments.lexers import get_lexer_by_name

    try:
      lexer = get_lexer_by_name(context['lang'], stripall=True)
    except ClassNotFound:
      return None

    formatter = HtmlFormatter()
    return '\n' + highlight(context['text'], lexer, formatter)


class TocExtension(Extension):

  class TocItem(object):
    def __init__(self, parent, header_id, level, content):
      self.parent = parent
      self.header_id = header_id
      self.level = level
      self.content = content
      self.children = []
    def __repr__(self):
      return 'TocItem(content={!r}, header_id={!r}, level={!r}, depth={!r})'.format(
        self.content, self.header_id, self.level, self.depth)
    def __str__(self):
      return self.format()
    @property
    def depth(self):
      count = 0
      while self:
        count += 1
        self = self.parent
      return count - 1
    def format(self, div_class='toc', href_prefix=''):
      if self.parent is None:
        return '<div class="{}"><ul>'.format(div_class) + ''.join(x.format() for x in self.children) + '</ul></div>'
      else:
        result = '<li><a href="{}#{}">{}</a>'.format(href_prefix, self.header_id, self.content)
        if self.children:
          result += '<ul>' + ''.join(x.format() for x in self.children) + '</ul>'
        return result + '</li>'
    def unwrap(self):
      if len(self.children) == 1:
        item = self.children[0]
        item.parent = None
        return item
      return self

  def init(self, md):
    md.toc = self.TocItem(None, None, 0, None)
    self.previous = md.toc

  def post_header(self, context):
    parent = self.previous
    while parent.level >= context['level']:
      parent = parent.parent
    item = self.TocItem(parent, context['header_id'], context['level'], context['content'])
    parent.children.append(item)
    self.previous = item


def html(text, options=None, extensions=None):
  return Markdown(options, extensions)(text)
