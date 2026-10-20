# Tutorials

Tutorials are lessons. Each one walks you through building something small, from an empty
folder to a working result, and every step shows you what you should see. Follow them in
order, and type the code as you go.

A comment such as `# -> True` at the end of a `print` line shows the value that line
prints. A string is shown in quotes there, as Python writes it in a list or a tuple; on its
own, `print` shows it without them.

They teach by doing and do not stop to explain the design. When you want the reasons, the
[explanation](../explanation/index.md) section has them. When you know what you want to do
and need the steps, use the [how-to guides](../how-to/index.md).

[Your first permission check](first-check.md)
: Install the package, write a small schema, create a store on SQLite, record who can do
  what, and ask it questions. About ten minutes.

[Model a Drive-style app](drive-app.md)
: Build the permission model of a file-sharing app one rule at a time: owners, nested
  groups, folders that pass access on to their documents, public documents and a ban list.
  About twenty minutes.

```{toctree}
:maxdepth: 1
:hidden:

first-check
drive-app
```
