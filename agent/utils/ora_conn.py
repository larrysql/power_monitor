#!/usr/local/bin/python
#coding=utf-8
import cx_Oracle
import time

def connectDB(uname,pwd,hname='localhost',port='1521',dbname='test'):
	connstr = uname + '/' + pwd + '@' + hname + ':' + port + '/' + dbname
	db=cx_Oracle.connect(connstr)
	return db

def sqlSelect(sql,db):
#include:select
	cr=db.cursor()
	cr.execute(sql)
	rs=cr.fetchall()
	cr.close
	return rs

def sqlDML(sql,db):
#include:inesrt,update,deleter
	cr=db.cursor()
	cr.execute(sql)
	cr.close()
	db.commit

def sqlDDL(sql,db):
#include:create
	cr=db.cursor()
	cr.execute(sql)
	cr.close

def get_time(unit = 'day'):
	if unit=='second':
		return(time.strftime('%H:%M:%S',time.localtime(time.time())))
	if unit=='day':
		return(time.strftime('%Y-%m-%d',time.localtime(time.time())))
