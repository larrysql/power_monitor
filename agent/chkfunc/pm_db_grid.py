#!/usr/local/bin/python
# -*- coding: utf-8
from __future__ import division
import cx_Oracle
import sys
import subprocess
import time
sys.path.append("..")
from  utils.utility import *

def chk_grid_status(cls,type):
    funcName = sys._getframe().f_code.co_name
    msg = funcName + ':*******************************开始集群状态检查.***************************************'
    wr_log('info',msg)
    d = get_inst_info()
    if d:
        inst_id = d['inst_id']
    else:
        funcName = sys._getframe().f_code.co_name
        msg = funcName + ':该实例没有在监控系统中注册！'
        wr_log('info',msg)
        return 1
    if os.path.isfile('/etc/oraInst.loc'):
        cmd = 'cat /etc/oraInst.loc|grep inventory_loc' 
        #cmd = 'cat /etc/oraInst.loc' 
        f = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.readlines()
        if f:
            inven_dir = f[0].split('=')[1].strip()
            xml = inven_dir + '/ContentsXML/inventory.xml'
            if os.path.isfile(xml):
                cmd = "cat " + xml + "|grep 'HOME NAME'|grep 'CRS='|grep 'true'"
                fg = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.readlines()
                if fg:
                    crshome = fg[0].split()[2].split('=')[1].strip('"')
                    crscnt = subprocess.Popen('ps -ef|grep crsd.bin|grep -v grep|wc -l',stdout=subprocess.PIPE,shell=True).stdout.readlines()[0].strip()
                    cssdcnt = subprocess.Popen('ps -ef|grep ocssd.bin|grep -v grep|wc -l',stdout=subprocess.PIPE,shell=True).stdout.readlines()[0].strip()
                    ##检查CRS服务状态
                    d = get_lim_val(inst_id,'grid','state','service')
                    if d is None or d[4] == 0:
                        funcName = sys._getframe().f_code.co_name
                        msg = funcName + ':CRS服务状态检查已屏蔽,略过检查'
                        wr_log('info',msg)
                    else:
                        if int(crscnt) == 0 or  int(cssdcnt) == 0:
                            content = 'crsd或cssd进程未启动'
                            lv = 3
                            alert_id = d[3]
                            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                            wr_alert(alert_info) 
                        else:
                            d = {}
                            l = []
                            cmd = crshome + '/bin/crs_stat'
                            for line in subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.readlines():
                                if line.split():
                                    d[line.split('=')[0]] = line.split('=')[1]
                                else:
                                    #print d
                                    l.append(d)
                                    d = {}
                            content = ''
                            for d in l:
                                if d['TARGET'].strip() == 'ONLINE' and  'ONLINE' not in d['STATE'].strip():
                                    content = content + d['NAME'].strip() + ':TARGET' + d['TARGET'].strip() + ':STATE:' + d['STATE'].strip() + '\n' 
                                    print d['NAME'].strip(),'||',d['TARGET'].strip(),'||',d['STATE'].strip()
                            if len(content) > 0:
                                lv = 3
                                content = 'CRS服务状态异常:' + content
                                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                                wr_alert(alert_info)
                            else:
                                msg = funcName + ':集群CRS服务状态检查:正常.'
                                wr_log('info',msg)
                    #检查OCR状态
                    d = get_lim_val(inst_id,'grid','state','ocr')
                    if d is None or d[4] == 0:
                        funcName = sys._getframe().f_code.co_name
                        msg = funcName + ':OCR状态检查已屏蔽,略过检查！'
                        wr_log('info',msg)
                    else:
                        if int(crscnt) == 0 or  int(cssdcnt) == 0:
                            pass 
                        else:
                            cmd1 = crshome + '''/bin/ocrcheck|grep "Cluster registry integrity check succeeded"|wc -l'''
                            cmd2 = crshome + '''/bin/ocrcheck|grep "File integrity check succeeded"|wc -l'''
                            succ_cnt = subprocess.Popen(cmd1,stdout=subprocess.PIPE,shell=True).stdout.readlines()[0].strip()
                            ocr_cnt = subprocess.Popen(cmd2,stdout=subprocess.PIPE,shell=True).stdout.readlines()[0].strip()
                            lim_val = int(d[0])
                            if int(succ_cnt) >= 1:
                                if int(ocr_cnt) >= lim_val:
                                    msg = funcName + ':OCR状态检查正常,已注册OCR个数' + ocr_cnt + '个,正常为' + str(lim_val) + '个'
                                    wr_log('info',msg)
                                else:
                                    lv = 3
                                    alert_id = d[3]
                                    content = 'CRS状态检查异常:已注册OCR个数:' + ocr_cnt + '个,正常为' + str(lim_val) + '个'
                                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                                    wr_alert(alert_info)
                            else:
                                lv = 3
                                alert_id = d[3]
                                content = 'CRS状态检查异常'
                                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                                wr_alert(alert_info)   
                    #OCR备份状态检查
                    d = get_lim_val(inst_id,'grid','state','ocrbak')
                    if d is None or d[4] == 0:
                        funcName = sys._getframe().f_code.co_name
                        msg = funcName + ':OCR备份检查已屏蔽,略过检查！'
                        wr_log('info',msg)
                    else:
                        if int(crscnt) == 0 or  int(cssdcnt) == 0:
                            pass
                        else:
                            cmd = crshome + '''/bin/ocrconfig -showbackup|grep ''' + crshome + '''|wc -l''' 
                            ocr_bak_cnt = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.readlines()[0].strip()
                            lim_val = int(d[0])
                            if int(ocr_bak_cnt) >= lim_val:
                                msg = funcName + ':OCR备份检查正常,当前OCR备份个数:' + ocr_bak_cnt + '个,正常个数为' + str(lim_val) + '个'
                                wr_log('info',msg)
                            else:
                                lv = 3
                                alert_id = d[3]
                                content = 'CRS备份检查异常,当前OCR备份个数:' + ocr_bak_cnt + '个,正常个数为' + str(lim_val) + '个'
                                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                                wr_alert(alert_info)
                    #votedisk状态检查
                    d = get_lim_val(inst_id,'grid','state','votedisk')
                    if d is None or d[4] == 0:
                        funcName = sys._getframe().f_code.co_name
                        msg = funcName + ':VOTE DISK状态检查已屏蔽,略过检查！'
                        wr_log('info',msg)
                    else:
                        if int(crscnt) == 0 or  int(cssdcnt) == 0:
                            pass
                        else:
                            cmd = crshome + '''/bin/crsctl query css votedisk|grep ONLINE|wc -l'''
                            vote_cnt = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).stdout.readlines()[0].strip()
                            lim_val = int(d[0])
                            if int(vote_cnt) >= lim_val:
                                msg = funcName + ':VOTE DISK检查正常,当前在线的VOTE DISK个数:' + vote_cnt + '个,正常个数为' + str(lim_val) + '个'
                                wr_log('info',msg)
                            else:
                                lv = 3
                                alert_id = d[3]
                                content = 'VOTE DISK检查异常,当前在线的VOTE DISK个数:' + vote_cnt + '个,正常个数为' + str(lim_val) + '个'
                                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                                wr_alert(alert_info)
                else:
                    msg = funcName + ':没有安装集群软件'
                    wr_log('info',msg)
    msg = funcName + ':*******************************结束集群状态检查.***************************************'
    wr_log('info',msg)
#if __name__=="__main__":
#    chk_grid_status('grid','state')
