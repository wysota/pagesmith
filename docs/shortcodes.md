# Shortcodes

Shortcodes embed media or reuse content from Markdown. They are processed before
Markdown conversion, so use them directly in your content files.

Two forms are supported:

```jinja
{% name "positional" key="value" %}          {# self-closing #}
{% name key="value" %}content{% endname %}   {# block #}
```

## `youtube`

Embed a YouTube video.

```jinja
{% youtube id='dQw4w9WgXcQ' %}
{% youtube 'dQw4w9WgXcQ' %}
```

## `figure`

Embed an image with an optional caption. `src` is relative to the page.

```jinja
{% figure src='/images/photo.png' alt='A photo' caption='Figure 1' class='my-figure' %}
```

| Argument | Description |
|---|---|
| `src` | Image source (required). |
| `alt` | Alt text (defaults to the caption). |
| `caption` | Optional caption. |
| `class` | Wrapper CSS class (default `shortcode-figure`). |

## `highlight`

Render an escaped code block with optional language class.

```jinja
{% highlight lang='python' %}
def hello():
    print("world")
{% endhighlight %}
```

## `gist`

Embed a GitHub Gist.

```jinja
{% gist id='abc123xyz' %}
{% gist id='abc123xyz' file='main.py' %}
{% gist 'abc123xyz' %}
```

## `emoji`

Insert an emoji by name. You can also use `:name:` shorthand directly in Markdown
(see [Features](features.md#emoji)).

```jinja
{% emoji 'rocket' %}
{% emoji name='thumbsup' %}
```

Names come from the emoji map (for example `rocket`, `fire`, `thumbsup`,
`checkmark`, `warning`).

## `compiler_explorer`

Embed a [Compiler Explorer](https://godbolt.org/) entry.

```jinja
{% compiler_explorer id='z6xnBq' %}
{% compiler_explorer id='z6xnBq' height='600' width='100%' %}
```

| Argument | Default |
|---|---|
| `id` | — (required) |
| `height` | `500` |
| `width` | `100%` |

## `data`

Look up a value from the site's `data/*.yaml` files.

```jinja
{% data 'site.name' %}
{% data 'team.author.email' %}
```

## `download`

Create a download link or card for a file in the site's `files/` directory. The
file size is read at build time.

```jinja
{% download file='archive.zip' label='Download' style='button' %}
{% download file='data.csv' label='Data' description='Raw export' style='link' %}
```

## `child_link`

Link to a direct child page, using the child's title by default.

```jinja
{% child_link 'observer' %}
{% child_link 'observer' label='The Observer Pattern' %}
{% child_link 'design_patterns/observer' %}
```

## `children`

List child pages of the current page. Match a subset with a shell-style pattern.

```jinja
{% children %}
{% children pattern='services-*' %}
{% children template='custom' %}
```

Custom templates receive `children`, `parent_name`, and `current_page`.

## `mermaid`

Render a [Mermaid](https://mermaid.js.org/) diagram to SVG. See
[Features](features.md#mermaid-diagrams) for setup.

```jinja
{% mermaid %}
graph TD
  A[Start] --> B[End]
{% endmermaid %}
```

```jinja
{% mermaid file='flow.mmd' theme='dark' caption='Build flow' %}
```

A fenced ` ```mermaid ` code block is equivalent to the block shortcode.

## Writing your own

A shortcode handler is a callable `handler(args=None, kwargs=None, content=None)`
registered with `ShortcodeProcessor.register(name, handler)`. Plugins can add
markdown extensions and shortcodes — see the plugin examples and the source under
`src/pagesmith/plugins/` and `src/pagesmith/shortcodes/`.
