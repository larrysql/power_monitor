#!/usr/local/bin/python
# -*- coding: utf-8
import logging  
import ConfigParser


cf = ConfigParser.ConfigParser()
cf.read("../agent/config/powerm.conf")
logfile = cf.get("log", "log_file")
logging.basicConfig(level=logging.DEBUG,  
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',  
                    datefmt='%a, %d %b %Y %H:%M:%S',  
                    filename=logfile,  
                    filemode='a')     
  
logging.info('first info message')  
logging.debug('first debug message')  
