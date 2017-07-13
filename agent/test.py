#!/usr/bin/python
#coding=utf-8
import sys,os
reload(sys)
sys.setdefaultencoding('utf8')
import MySQLdb

def connectDB(host = '192.168.137.1',username = 'powerm',password = 'powerm',dbname = 'powerdb',port = 3306,charset="utf8"):
    db = MySQLdb.connect(host,username,password,dbname)
    return db

conn = connectDB()
conn.set_character_set('utf8')
cursor = conn.cursor()
#cursor.execute('SET NAMES utf8;')
#cursor.execute('SET CHARACTER SET utf8;')
#cursor.execute('SET character_set_connection=utf8;')

s = '你好'
try:
    cursor.execute('insert into test values \'(%s)',s)
    conn.commit()
except Exception,e:
    print e
    
print 'continue'
