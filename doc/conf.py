#
# LISA documentation build configuration file, created by
# sphinx-quickstart on Tue Dec 13 14:20:00 2016.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import logging
import os
import re
import subprocess
import sys
import unittest
import textwrap
import json
import functools
import inspect
import importlib
import types
import contextlib

from sphinx.domains.python import PythonDomain

# This shouldn't be needed, as using a virtualenv + setup.py should set up the
# sys.path correctly. However that seems to be half broken on ReadTheDocs, so
# manually set it here
sys.path.insert(0, os.path.abspath('../'))

# Import our packages after modifying sys.path
import lisa
from lisa.utils import LISA_HOME, import_all_submodules, sphinx_nitpick_ignore
from lisa._doc.helpers import (
    autodoc_process_test_method, autodoc_process_analysis_events,
    autodoc_process_analysis_plots, autodoc_process_analysis_methods,
    autodoc_skip_member_handler,
    DocPlotConf, get_xref_type,
)


# This ugly hack is required because by default TestCase.__module__ is
# equal to 'case', so sphinx replaces all of our TestCase uses to
# unittest.case.TestCase, which doesn't exist in the doc.
for name, obj in vars(unittest).items():
    try:
        m = obj.__module__
        obj.__module__ = 'unittest' if m == 'unittest.case' else m
    except Exception:
        pass

RTD = (os.getenv('READTHEDOCS') == 'True')

def prepare():

    def run(cmd, **kwargs):
        return subprocess.run(
            cmd,
            cwd=LISA_HOME,
            **kwargs,
        )

    # In case we have a shallow clone, make sure to have the whole
    # history to be able to generate breaking change list and any other
    # git-based documentation
    run(['git', 'fetch', '--unshallow'], check=False)
    run(['git', 'fetch', '--tags'], check=False)

    # Ensure we have the changelog notes that supplement commit messages, as
    # sometimes the markers such as FEATURE were forgotten and later added
    # using git notes.
    run(['git', 'fetch', 'origin', 'refs/notes/changelog'])

    source_env = {
        **os.environ,
        # LISA_USE_VENV=0 will avoid re-installing LISA automatically,
        # which would be useless.
        'LISA_USE_VENV': '0',
    }
    # If LISA_HOME is set, sourcing the script won't work
    source_env.pop('LISA_HOME', None)

    script = textwrap.dedent(
        """
        source init_env >&2 &&
        python -c 'import os, json; print(json.dumps(dict(os.environ)))'
        """
    )
    out = subprocess.check_output(
        ['bash', '-c', script],
        cwd=LISA_HOME,
        # Reset the environment, including LISA_HOME to allow sourcing without
        # any issue
        env=source_env,
    )
    os.environ.update(json.loads(out))

# Only the top-level import has the "builtins" __name__. This prevents
# re-running prepare() when conf.py is imported by the processes spawned by
# sphinx
if __name__ == 'builtins':
    prepare()

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.inheritance_diagram',
    'sphinxcontrib.plantuml',
    'nbsphinx',
]

# Fix for the broken flyout ReadTheDocs menu as recommended here:
# https://github.com/readthedocs/sphinx_rtd_theme/issues/1452#issuecomment-1490504991
# https://github.com/readthedocs/readthedocs.org/issues/10242
# https://github.com/readthedocs/sphinx_rtd_theme/issues/1452
# https://github.com/readthedocs/sphinx_rtd_theme/pull/1448
if RTD:
    extensions.append(
        "sphinxcontrib.jquery"
    )

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'LISA'
copyright = '2017, ARM-Software'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
version = str(lisa.__version__)
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = 'en'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'


# Allow interactive bokeh plots in the documentation
try:
    import bokeh.resources
except ImportError:
    pass
else:
    html_js_files = bokeh.resources.CDN.js_files
    html_css_files = bokeh.resources.CDN.css_files

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'LISAdoc'

rst_prolog = """
.. attention::

    .. raw:: html

        <div style="background-color: #f44336; color: #ffffff;">

    This documentation was obtained by building the "master" git branch.
    LISA project has moved to the "main" branch.
    The "master" branch is now a mirror of "main" but will eventually be abandonned, please see the `latest documentation <https://lisa-linux-integrated-system-analysis.readthedocs.io/en/latest/>`_.

    .. raw:: html

        </div>
"""



# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    # 'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', 'LISA.tex', 'LISA Documentation',
   'ARM-Software', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'lisa', 'LISA Documentation',
     ['ARM-Software'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'LISA', 'LISA Documentation',
   'ARM-Software', 'LISA', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'holoviews': ('https://holoviews.org/', None),
    # XXX: Doesn't seem to work, might be due to how devlib doc is generated
    'devlib': ('https://devlib.readthedocs.io/en/latest/', None),
    'wa': ('https://workload-automation.readthedocs.io/en/latest/', None),
    'ipywidgets': ('https://ipywidgets.readthedocs.io/en/latest/', None),
    'IPython': ('https://ipython.readthedocs.io/en/stable/', None),
    'typeguard': ('https://typeguard.readthedocs.io/en/stable/', None),
}

manpages_url = "https://manpages.debian.org/{path}"

#
# Fix autodoc
#

# Include __init__ docstrings (obviously)
autoclass_content = 'both'

autodoc_member_order = 'bysource'

autodoc_default_options = {
    # Show parent class
    'show-inheritance': None,
    # Show members even if they don't have docstrings
    'undoc-members': None,
    # Show special methods such as __and__
    'special-members': None,
    # Note: we make use of it in our custom autodoc-skip-member hook to ensure
    # it is always honored, even when some members are explicitly excluded.
    # On top of that, some functions are always excluded (see the hook
    # implementation for the details).
    'exclude-members': ','.join([
        # All the classes in lisa have their __init__ signature documented in
        # the class docstring
        '__init__',

        # Uninteresting
        '__weakref__',
        '__module__',
        '__abstractmethods__',
        '__slotnames__',
        '__eq__',
        '__str__',
        '__repr__',
        '__iter__',
        '__len__',
        '__dict__',
    ])
}
autodoc_inherit_docstrings = True

ignored_refs = {
    # They don't have a doc on RTD yet
    r'lisa_tests.*',

    # gi.repository is strangely laid out, and the module in which Variant
    # (claims) to actually be defined in is not actually importable it seems
    r'gi\..*',

    # Devlib does not use autodoc (for now) and does not use module.qualname
    # names, which makes all xref to it fail
    r'devlib.*',
    r'docutils\.parsers.*',
    r'ipywidgets.*',

    # Since trappy is not always installed, just hardcode the references we
    # have since there wont be more in the future.
    r'trappy.*',

    # All private "things": either having a ._ somewhere in their full name or
    # starting with an underscore
    r'(.*\._.*|_.*)',

    # Various LISA classes that cannot be crossed referenced successfully but
    # that cannot be fixed because of Sphinx limitations and external
    # constraints on names.
    r'ITEM_CLS',

    # Python <= 3.8 has a formatting issue in typing.Union[..., None] that
    # makes it appear as typing.Union[..., NoneType], leading to a broken
    # reference since the intersphinx inventory of the stdlib does not provide
    # any link for NoneType.
    r'NoneType',

    # Sphinx currently fails at finding the target for references like
    # :class:`typing.List[str]` since it does not seem to have specific support
    # for the bracketed syntax in that role.
    r'typing.*',
}
ignored_refs.update(
    re.escape(f'{x.__module__}.{x.__qualname__}')
    for x in sphinx_nitpick_ignore()
)
ignored_refs = set(map(re.compile, ignored_refs))


class CustomPythonDomain(PythonDomain):
    def find_obj(self, env, modname, classname, name, type, searchmode=0):
        refs = super().find_obj(env, modname, classname, name, type, searchmode)
        if len(refs) == 1:
            return refs
        elif any(
            regex.match(name)
            for regex in ignored_refs
        ):
            refs = super().find_obj(env, modname, classname, 'lisa._doc.helpers.PlaceHolderRef', 'class', 0)
            assert refs
            return refs
        else:
            return refs


def setup(app):
    app.add_domain(CustomPythonDomain, override=True)

    plot_conf_path = os.path.join(LISA_HOME, 'doc', 'plot_conf.yml')
    plot_conf = DocPlotConf.from_yaml_map(plot_conf_path)
    autodoc_process_analysis_plots_handler = functools.partial(
        autodoc_process_analysis_plots,
        plot_conf=plot_conf,
    )

    app.connect('autodoc-process-docstring', autodoc_process_test_method)
    app.connect('autodoc-process-docstring', autodoc_process_analysis_events)
    app.connect('autodoc-process-docstring', autodoc_process_analysis_methods)
    app.connect('autodoc-skip-member',       autodoc_skip_member_handler)
    if int(os.environ.get('LISA_DOC_BUILD_PLOT', '1')):
        app.connect('autodoc-process-docstring', autodoc_process_analysis_plots_handler)

# vim :set tabstop=4 shiftwidth=4 textwidth=80 expandtab:
