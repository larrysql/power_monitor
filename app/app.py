#!/usr/local/bin/python
# -*- coding: utf-8
from flask import Flask
import views.oracle
import views.user
import views.test
from flask.ext.login import LoginManager
from flask import Blueprint
import chartkick
import os

app = Flask(__name__)
app.debug = True
app.register_blueprint(views.user.mod)
app.register_blueprint(views.oracle.mod)
app.register_blueprint(views.test.mod)

ck = Blueprint('ck_page', __name__, static_folder=chartkick.js(), static_url_path='/static/Scripts')
app.register_blueprint(ck, url_prefix='/ck')
app.jinja_env.add_extension("chartkick.ext.charts")

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.session_protection = "strong" #这里指定为strong，默认为'basic'
login_manager.login_view = "login.login_page" #login view的名字
login_manager.login_message = u'提示信息。'

if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run(host='0.0.0.0',threaded=True)
