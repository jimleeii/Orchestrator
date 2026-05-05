# Rules

This document contains a description of all rules, what they are checking for,
as well as examples of documents that break the rule and corrected
versions of the examples.

<a name="md001"></a>

## `MD001` - Heading levels should only increment by one level at a time

Tags: `headings`

Aliases: `heading-increment`

Parameters:

- `front_matter_title`: RegExp for matching title in front matter (`string`,
  default `^\s*title\s*[:=]`)

This rule is triggered when you skip heading levels in a Markdown document, for
example:

```markdown
# Heading 1

### Heading 3

We skipped out a 2nd level heading in this document
```

When using multiple heading levels, nested headings should increase by only one
level at a time:

```markdown
# Heading 1

## Heading 2

### Heading 3

#### Heading 4

## Another Heading 2

### Another Heading 3
```

If [YAML](https://en.wikipedia.org/wiki/YAML) front matter is present and
contains a `title` property (commonly used with blog posts), this rule treats
that as a top level heading and will report a violation if the actual first
heading is not a level 2 heading. To use a different property name in the
front matter, specify the text of a regular expression via the
`front_matter_title` parameter. To disable the use of front matter by this
rule, specify `""` for `front_matter_title`. When front matter is not present,
the first heading can be any level.

Rationale: Headings represent the structure of a document and can be confusing
when skipped - especially for accessibility scenarios. More information:
<https://www.w3.org/WAI/tutorials/page-structure/headings/>.

<a name="md003"></a>

## `MD003` - Heading style

Tags: `headings`

Aliases: `heading-style`

Parameters:

- `style`: Heading style (`string`, default `consistent`, values `atx` /
  `atx_closed` / `consistent` / `setext` / `setext_with_atx` /
  `setext_with_atx_closed`)

This rule is triggered when different heading styles are used in the same
document:

```markdown
# ATX style H1

## Closed ATX style H2 ##

Setext style H1
===============
```

To fix the issue, use consistent heading styles throughout the document:

```markdown
# ATX style H1

## ATX style H2
```

The `setext_with_atx` and `setext_with_atx_closed` settings allow ATX-style
headings of level 3 or more in documents with setext-style headings (which only
support level 1 and 2 headings):

```markdown
Setext style H1
===============

Setext style H2
---------------

### ATX style H3
```

Note: The configured heading style can be a specific style to require (`atx`,
`atx_closed`, `setext`, `setext_with_atx`, `setext_with_atx_closed`), or can
require that all heading styles match the first heading style via `consistent`.

Note: The placement of a horizontal rule directly below a line of text can
trigger this rule by turning that text into a level 2 setext-style heading:

```markdown
A line of text followed by a horizontal rule becomes a heading
---
```

Rationale: Consistent formatting makes it easier to understand a document.

<a name="md004"></a>

## `MD004` - Unordered list style

Tags: `bullet`, `ul`

Aliases: `ul-style`

Parameters:

- `style`: List style (`string`, default `consistent`, values `asterisk` /
  `consistent` / `dash` / `plus` / `sublist`)

Fixable: Some violations can be fixed by tooling

This rule is triggered when the symbols used in the document for unordered
list items do not match the configured unordered list style:

```markdown
* Item 1
+ Item 2
- Item 3
```

To fix this issue, use the configured style for list items throughout the
document:

```markdown
* Item 1
* Item 2
* Item 3
```

The configured list style can ensure all list styling is a specific symbol
(`asterisk`, `plus`, `dash`), ensure each sublist has a consistent symbol that
differs from its parent list (`sublist`), or ensure all list styles match the
first list style (`consistent`).

For example, the following is valid for the `sublist` style because the
outer-most indent uses asterisk, the middle indent uses plus, and the inner-most
indent uses dash:

```markdown
* Item 1
  + Nested Item 1
    - Nested Item 3
  + Nested Item 4
* Item 4
  + Nested Item 5
```

Rationale: Consistent formatting makes it easier to understand a document.

<a name="md005"></a>

## `MD005` - Inconsistent indentation for list items at the same level

Tags: `bullet`, `indentation`, `ul`

Aliases: `list-indent`

Fixable: Some violations can be fixed by tooling

This rule is triggered when list items are parsed as being at the same level,
but don't have the same indentation:

```markdown
* Item 1
  * Nested Item 1
  * Nested Item 2
   * A misaligned item
```

Usually, this rule will be triggered because of a typo. Correct the indentation
for the list to fix it:

```markdown
* Item 1
  * Nested Item 1
  * Nested Item 2
  * Nested Item 3
```

Sequentially-ordered list markers are usually left-aligned such that all items
have the same starting column:

```markdown
...
8. Item
9. Item
10. Item
11. Item
...
```

This rule also supports right-alignment of list markers such that all items have
the same ending column:

```markdown
...
 8. Item
 9. Item
10. Item
11. Item
...
```

Rationale: Violations of this rule can lead to improperly rendered content.

<a name="md007"></a>

## `MD007` - Unordered list indentation

Tags: `bullet`, `indentation`, `ul`

Aliases: `ul-indent`

Parameters:

- `indent`: Spaces for indent (`integer`, default `2`)
- `start_indent`: Spaces for first level indent (when start_indented is set)
  (`integer`, default `2`)
- `start_indented`: Whether to indent the first level of the list (`boolean`,
  default `false`)

Fixable: Some violations can be fixed by tooling

This rule is triggered when list items are not indented by the configured
number of spaces (default: 2).

Example:

```markdown
* List item
   * Nested list item indented by 3 spaces
```

Corrected Example:

```markdown
* List item
  * Nested list item indented by 2 spaces
```

Note: This rule applies to a sublist only if its parent lists are all also
unordered (otherwise, extra indentation of ordered lists interferes with the
rule).

The `start_indented` parameter allows the first level of lists to be indented by
the configured number of spaces rather than starting at zero. The `start_indent`
parameter allows the first level of lists to be indented by a different number
of spaces than the rest (ignored when `start_indented` is not set).

Rationale: Indenting by 2 spaces allows the content of a nested list to be in
line with the start of the content of the parent list when a single space is
used after the list marker. Indenting by 4 spaces is consistent with code blocks
and simpler for editors to implement. Additionally, this can be a compatibility
issue for other Markdown parsers, which require 4-space indents. More
information: [Markdown Style Guide][markdown-style-guide].

Note: See [Prettier.md](Prettier.md) for compatibility information.

[markdown-style-guide]: https://cirosantilli.com/markdown-style-guide#indentation-of-content-inside-lists
