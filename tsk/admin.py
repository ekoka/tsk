# coding=utf-8
import os
import flask

"""
TODO:
-----
Authentication # works with cookies
- login
- logout

Pages
- listing
- edit
- delete
- add
"""

def create_app(import_module, *a, **kw):
    app = flask.Flask(import_module, *a, **kw)
    return app

def list_md_files(mdpath):
    for f in os.listdir(mdpath):
        pass


