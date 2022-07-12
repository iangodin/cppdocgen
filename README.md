# C++ Documentation Generator

Python program to parse C++ code and generate HTML documentation from it.
It uses Clang to parse C++, Markdown and Jinja to generate static HTML.

The main program can parse separate C++ files in parallel, putting all the information in an SQLite database.
Then a second program will read the database and generate the final static HTML files.

This is very early yet, and lots more to be done.
The goal is (eventually) to have a documentation system that is easy to customize by modifying Jinja templates along with CSS.

Packages required from pip:
libclang
pyyaml
markdown
markdown-blockdiag
pymdown-extensions
jinja2
