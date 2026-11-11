# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

project = 'Employees control system'
copyright = '2026, Provonsal'
author = 'Provonsal'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',       # Автоматически извлекает докстринги
    'sphinx.ext.napoleon',      # Позволяет Sphinx понимать Google/NumPy стиль докстрингов
    'sphinx.ext.viewcode',      # Добавляет ссылки на исходный код
    'sphinx.ext.intersphinx',   # Позволяет ссылаться на документацию Python и других проектов
    'sphinx_autodoc_typehints', # Корректно отображает аннотации типов
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']
napoleon_google_docstring = True
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}