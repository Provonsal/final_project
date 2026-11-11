# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


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

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

# Napoleon
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_custom_sections = [
    ("Аргументы", "params_style"),
    ("Возвращает", "returns_style"),
    ("Исключения", "params_style"),
    ("Требования", "returns_style"),
    ("Поведение", "other"),
    ("Побочные эффекты", "other"),
    ("Замечание", "other"),
    ("Замечания", "other"),
]

# Autodoc
autodoc_class_signature = "separated"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Не тянем реальную БД при импорте (на случай, если env не задан)
# Если задали DATABASE_URL в CI — можно убрать. Оставьте как страховку.
autodoc_mock_imports = []

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

# Подавить шум от SQLAlchemy type hints
suppress_warnings = [
    "sphinx_autodoc_typehints.guarded_import",
    "sphinx_autodoc_typehints.forward_reference",
]

# Тема
html_theme = "furo"  # или твоя
html_static_path = ["_static"]  # папку создали
