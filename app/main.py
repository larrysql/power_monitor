#!/usr/local/bin/python
# -*- coding: utf-8
from utils.conn_mysql import conn_mysql
from flask import Flask,url_for
from flask import render_template
from flask import request
from flask import request
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

app = Flask(__name__)
app.debug = True

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/ora_alert')
def ora_alert():
    db = conn_mysql()
    cursor = db.cursor()
    sql = '''select i.id,i.host_name,i.ip_addr,i.inst_name,i.db_name,i.db_type,g.gname,
				sum(case a.`level` when 1 then 1 else 0 end) sum_lv1,
				sum(case a.`level` when 2 then 1 else 0 end) sum_lv2,
				sum(case a.`level` when 3 then 1 else 0 end) sum_lv3
            from ora_inst i,ora_alert_info a ,app_group g
            where
                a.inst_id = i.id
                and i.gid = g.id
            group by i.host_name,i.ip_addr,i.inst_name,i.db_name,i.db_type,g.gname;'''
    cursor.execute(sql)
    entries = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('oracle/ora_alert.html',entries = entries)

@app.route('/ora_alert_detail/',methods=['GET','POST'])
def ora_alert_detail():
    if request.method == 'GET':
        inst_id = request.args.get('inst_id')
        #print 'inst_id ================================' + inst_id
        db = conn_mysql()
        cursor = db.cursor()
        sql = '''select i.id,i.host_name,i.ip_addr,i.inst_name,i.db_name,left(a.alert_info,200) alert_info,a.create_time,a.level
                 from ora_inst i,ora_alert_info a
                 where
                    a.inst_id = i.id
                    and i.id = ''' + inst_id + '''
                 order by id,level
              '''
        cursor.execute(sql)
        entries = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('oracle/ora_alert_detail.html',entries = entries)

if __name__ == '__main__':
    app.run(host='0.0.0.0')







