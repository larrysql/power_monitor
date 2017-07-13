#!/usr/local/bin/python
# -*- coding: utf-8
from __future__ import division
import time
import socket
import datetime
import cx_Oracle
import MySQLdb
import subprocess
import sys
reload(sys)
sys.setdefaultencoding('utf8')
#获取到MYSQL数据库的cursor对象
def connectDB(host = '192.168.137.1',username = 'powerm',password = 'powerm',dbname = 'powerdb',port = 3306,charset='utf8'):
    db = MySQLdb.connect(host,username,password,dbname)
    return db 
def ora_conn():
    db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA)
    return db
#获取当前时间
def get_time(unit):
        if unit=='second':
                return(time.strftime('%Y%m%d %H:%M:%S',time.localtime(time.time())))
        if unit=='day':
                return(time.strftime('%Y%m%d',time.localtime(time.time())))

conf_fname = 'config/powerm.conf'
#获得多个监控项阈值,返回一个dict
def get_mul_lim_val(inst_id,cls,type):
    d = {}
    db = connectDB()
    db.set_character_set('utf8')    
    cursor = db.cursor()
    cursor.execute('select name,level1,level2,level3,id,enable from ora_alert_define where inst_id = ' + str(inst_id) + ' and class = \''
	+ cls + '\' and type = \'' + type + '\'')
    rs = cursor.fetchall()
    if len(rs) > 0:
        for line in rs:
            print line
            k = line[0]
            v = [line[1],line[2],line[3],line[4],line[5]]
            d[k] = v
    else:
        d = None
    return d

#写报警信息
def wr_alert(alert_info):
    d = get_inst_info()
    content = alert_info['content']
    print content
    alert_id = alert_info['alert_id']
    level = alert_info['level']
    if len(d) > 2:
        hostname = d['host']
        ip = d['ip_addr']
        instname = d['inst']
        inst_id = d['inst_id']
        today = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        values =[alert_id,level,inst_id,content,today]
        try:
            db = connectDB()
            db.set_character_set('utf8')
            cursor = db.cursor()
            cursor.execute('insert into ora_alert_info(alert_id,level,inst_id,alert_info,create_time) values(%s,%s,%s,%s,%s)',values)
            db.commit()
            cursor.close()
            db.close()
        except Exception,e:
            print str(e)
        #myfile.write(today + "||" + hostname + "||" + ip + "||" + "数据库实例:" + instname + "||" + alert_info + "\n")

#获取主机名和实例名
def get_inst_info():
    d = {}
    f = subprocess.Popen('env|grep ORACLE_SID',shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    inst = f.stdout.readlines()[0].split('=')[1].strip()
    if len(inst) > 0:
        d['inst'] = inst
    else:
        d['inst'] = 'not found'
    host = socket.gethostname()
    d['host'] = host
    if  d['inst'] != 'not found':
        try:
            db = connectDB()
            cursor = db.cursor()
            sql = 'select id,ip_addr,db_name from ora_inst where host_name = \'' + host + '\' and inst_name = \'' + inst + '\''
            cursor.execute(sql)
            rs = cursor.fetchone()
            if len(rs) > 0:
                inst_id = rs[0]
                ip_addr = rs[1]
                db_name = rs[2]
                d['inst_id'] = inst_id
                d['ip_addr'] = ip_addr
                d['db_name'] = db_name
        except Exception,e:
            print str(e)
    return d

#从MYSQL数据库中获取监控阈值
def get_lim_val(inst_id,cls,type,name):
    try:
        db = connectDB()
        cursor = db.cursor()
        sql = 'select level1,level2,level3,id,enable from ora_alert_define where inst_id = ' + str(inst_id) + ' and class = \'' + cls + '\' and type = \'' + type + '\' and name = \'' + name + '\''
        cursor.execute(sql)
        rs = cursor.fetchone()
        if len(rs) > 0:
            lim_val = [rs[0],rs[1],rs[2],rs[3],rs[4]]
        else:
            lim_val = None
        return lim_val
    except Exception,e:
        print str(e)
#发送告警邮件
def mailSend(mail):
		#设置邮件信息
        sender = 'aspire_point@aspirecn.com'
        tolist = ['liangshiqiang@aspirecn.com','ora_008@163.com','gudalin@aspirecn.com','zhangyongli@aspirecn.com','songxin_a@aspirecn.com','wuzhi_a@aspirecn.com']
        receiver = ''
        for item in tolist:
                receiver += item +','
        print receiver
        username = 'aspire_point'
        password = 'asp+888'
        subject = '每日报表'
		#实例化写邮件到正文区，邮件正文区需要以HTML文档形式写入
        msg = MIMEMultipart()
        #msg = MIMEText(mail,_subtype='html',_charset='gb2312')
		#输入主题
        msg['Subject'] = subject
        msg["From"] = sender
        msg["To"] = receiver
        msg.attach(MIMEText(mail,_subtype='html',_charset='gb2312'))
        smtpserver = 'mail.aspirecn.com'
        server_port = 587
		#print email_message
		#创建SMTP对象
        smtp = smtplib.SMTP(smtpserver,server_port)
        #smtp.set_debuglevel(1)
		#向mail发送SMTP "ehlo" 命令
        smtp.ehlo()
		#启动TLS模式，mail要求
        smtp.starttls()
		#用户验证
        smtp.login(username, password)
		#发送邮件
        smtp.sendmail(sender, tolist, msg.as_string())
		#退出
        smtp.quit()
