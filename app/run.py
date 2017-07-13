#!/usr/local/bin/python
# -*- coding: utf-8
from flask import Flask, jsonify, render_template, request
import chartkick
app = Flask(__name__, static_folder=chartkick.js())
app.jinja_env.add_extension("chartkick.ext.charts")

@app.route('/')
@app.route('/index')
def index():
	data = {'Chrome': 52.9, 'Opera': 1.6, 'Firefox': 27.7}
	return render_template('index.html', data=data)

if __name__ == "__main__":
	app.run(debug=True)