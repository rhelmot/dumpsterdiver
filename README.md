god I hate that I had to write this

# Dumpster Dive dot py

This is a library for interactively exploring the heap of a python program to track down leaks.
The basic intuition is that you _know_ that your program shouldn't be taking 2 gigabytes of memory at this point, and it's probably a bunch of objects of a single type taking up all that memory.
But how do you figure out who's holding the references to them?

Python's built in `gc` module gives you the tools to figure it out, but it's a tedious process and if you do it in an interactive session you're going to be generating a bunch of additional references that will complicate your search pretty drastically.
This tool was built after several hours of frustration with this!

Then, to detox, I learned `prompt_toolkit` and made the prompt pretty.

# Installation

`pip install dive`

# Usage

```python
import dive
dive.start()
```

This will start an interactive session in which you will be empowered to traverse the heap, scanning for references to your least favorite objects.

If you already know what objects are the culprit you can start with `dive.search(name)`, where name is a substring matching the type names you're interested in.

## Traversal

At every point, you'll be shown a list of objects, and asked to pick a command to run on one of them.
You are shown the first 10 items by default, you can show more by running `list` or `list n` to jump to position `n` in the list.

- Running `return n` will return the object at index n from the initial call into dive.
- Running `refs n` will let you explore a list of all the objects referring to the object at index n.
- Running `down n` will let you explore all the objects that the object at index n refers to.
- Running `up` will pop you up a level of exploration.

Run `help` for more help.
