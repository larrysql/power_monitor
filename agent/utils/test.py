#/usr/bin/python
import ConfigParser
import string, os, sys
cf = ConfigParser.ConfigParser()
cf.read("../config/powerm.conf")
#read by type
db_host = cf.get("db", "host")
db_port = cf.getint("db", "port")
db_user = cf.get("db", "user")
db_pass = cf.get("db", "passwd")
db_name = cf.get("db","dbname")
print "db_host = ",db_host
print "db_port = ",db_port
print "db_user = ",db_user
print "db_pass = ",db_pass
print "db_name = ",db_name
