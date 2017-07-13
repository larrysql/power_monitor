#!/usr/local/bin/python
# -*- coding: utf-8
import sys
sys.path.append("..")
from utils.conn_mysql import conn_mysql,conn_mysql_l
from flask import Flask,url_for,jsonify
from flask import render_template,Blueprint,abort
from flask import request
from jinja2 import TemplateNotFound
reload(sys)
sys.setdefaultencoding('utf-8')

mod = Blueprint('test', __name__,template_folder='templates')

@mod.route('/_add_numbers')
def add_numbers():
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    return jsonify(result=a + b)


@mod.route('/chart')
def index():
    value = {'Chrome': 52.9, 'Opera': 1.6, 'Firefox': 27.7}
    return render_template('oracle/ora_load_detail.html',data=value)

@mod.route('/test_hc')
def test_hc():
    return render_template('oracle/test_hc.html')

