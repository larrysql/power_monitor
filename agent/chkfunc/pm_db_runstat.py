#!/usr/local/bin/python
# -*- coding: utf-8
from __future__ import division
import cx_Oracle
import sys
import urllib
import types
import os
import subprocess
import commands
import time
import string
import datetime
from  utils.utility import *

#conf_fname = '/home/oracle/powerm/config/powerm.conf'

def chk_inst_status():
    d = get_inst_info()
    if d:
        inst_id = d['inst_id']
    else:
        funcName = sys._getframe().f_code.co_name
        print funcName + ':该实例没有在监控系统中注册！'
        return 1
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA) 
    except Exception,e:
        content = "chk_inst_status:数据库连接失败!请检查" + str(e)
        msg = funcName + ':' + content 
        wr_log('warning',msg)
        alert_id = inst_id
        lv = 3
        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
        wr_alert(alert_info)
        return 1
    cursor = db.cursor()
#检查实例状态
    funcName = sys._getframe().f_code.co_name
    msg = funcName + ':开始执行实例状态检查'
    wr_log('info',msg)
    cursor.execute('select DATABASE_ROLE from v$database')
    rs = cursor.fetchone()
    dbrole = rs[0]
    #print dbrole
    d = get_lim_val(inst_id,'runstat','instance','status')
    if d is None or d[4] == 0:    
        msg = funcName + ':实例状态检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        cursor.execute('select instance_name,status from v$instance')
        rs = cursor.fetchone()
        if dbrole == 'PRIMARY' and rs[1] != 'OPEN':
            content = '数据库实例' + rs[0] + '状态异常,当前状态为' + rs[1] + ',正常状态为OPEN' 
            alert_id = d[3]
            lv = 3
            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
            wr_alert(alert_info)
        elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY') and rs[1] == 'MOUNTED':
            msg = funcName + '数据库实例' + rs[0] + '状态正常,STANDBY数据库,当前状态为' + rs[1]
            wr_log('info',msg)
        else:
            msg = funcName + '数据库实例' + rs[0] + '状态正常,当前状态为' + rs[1]
            wr_log('info',msg)
#检查数据库状态
    msg = funcName + ':开始执行数据库状态检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','database','open_mode')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库状态检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        cursor.execute('select name,OPEN_MODE from v$database')
        rs = cursor.fetchone()
        if dbrole == 'PRIMARY' and rs[1] != 'READ WRITE':
            content = '数据库' + rs[0] + '状态异常,当前状态为' + rs[1] + ',正常状态为READ WRITE'
            lv = 3
            alert_id = d[3]
            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
            wr_alert(alert_info)
        elif (dbrole == 'PHYSICAL STANDBY'):
            msg = funcName + '数据库' + rs[0] + '为STANDBY数据库'
            wr_log('info',msg)
        else:
            msg = funcName + '数据库' + rs[0] + '状态正常,当前状态为' + rs[1]
            wr_log('info',msg)
#数据库归档模式检查
    msg = funcName + ':开始执行数据库归档模式检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','archivelog','log_mode')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库归档模式检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        cursor.execute("select schedule from v$archive_dest where status='VALID' and dest_id=1")
        rs = cursor.fetchone()
        if dbrole == 'PRIMARY' and rs[0] != 'ACTIVE':
            content = '数据库为非归档模式,正常为归档模式'
            lv = 1
            alert_id = d[3]
            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
            wr_alert(alert_info)
        elif dbrole == 'PHYSICAL STANDBY':
            msg = funcName + '数据库' + rs[0] + '为STANDBY数据库'
            wr_log('info',msg)
        else:
            msg = funcName + '数据库归档模式正常'
            wr_log('info',msg)
#数据库实例监听注册检查
##获取数据库实例列表
    msg = funcName + ':开始执行监听注册检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','list_reg','is_reg')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库监听注册状态检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        l_inst = []
        f = subprocess.Popen('ps -ef|grep ora_smon|grep -v grep',shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        for line in f.stdout.readlines():
            inst_name = line.split()[-1].split('_')[-1]
            l_inst.append(inst_name)
    ##获取listener名称列表
        l_lsnr = []
        f = subprocess.Popen('ps -ef|grep tnslsnr|grep -v grep',shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        for line in f.stdout.readlines():
            lsnr_name = line.split()[-2]
            l_lsnr.append(lsnr_name)  
    ##检查数据库实例是否注册到listener中
        for i in l_inst:
            i_flag = 1
            for l in l_lsnr:
                f = subprocess.Popen('lsnrctl status ' + l,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                for line in f.stdout.readlines():
                    if i in(line):
                        i_flag = 0
            if i_flag == 1:
                content = '数据库实例'  + i + '未在监听中注册'
                lv = 1
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg =funcName + '监听' + i + "已注册"
                wr_log('info',msg)

#数据库表空间状态检查
    msg = funcName + ':开始执行表空间状态检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','tablespace','status')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库表空间状态检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        try:
            if dbrole == 'PRIMARY':
                cursor.execute('select tablespace_name,status from dba_tablespaces')
                rs = cursor.fetchall()
                for line in rs:
                    if line[1] != 'ONLINE':
                        content = '表空间' + line[0] + '状态异常，正常状态为ONLINE'
                        alert_id = d[3]
                        lv = 2
                        alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                        wr_alert(alert_info)
                    else:
                        msg = funcName + '表空间' + line[0] + '状态正常，为' + line[1]
                        wr_log('info',msg)
            elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
                msg = funcName + '数据库表空间状态检查:数据库为standby数据库,不适用.'
                wr_log('info',msg)
            else:
                pass
        except Exception,e:
            content = '查询数据库表空间状态失败:' + str(e)
            msg = funcName + ':' + content
            alert_id = d[3]
            wr_log('warning',msg)
            lv = 2
            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
            wr_alert(alert_info)

#数据文件状态检查
    msg = funcName + ':开始执行数据文件状态检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','datafile','status')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库数据文件状态检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        if dbrole == 'PRIMARY':
            cursor.execute('''
    		select name,status from v$datafile where status not in('ONLINE','SYSTEM')
    		union all
    		select name,status from v$tempfile where status <> 'ONLINE'
            ''')
            rs = cursor.fetchall()
            if len(rs) > 0:
                for line in rs:
                    content = '数据文件' + line[0] + '状态异常,当前状态为' + line[1]
                    alert_id = d[3]
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
            else:
                msg = funcName + '数据库所有数据文件状态正常!' 
                wr_log('info',msg)
        elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
            msg = funcName + '数据库数据文件状态检查:数据库为standby数据库,不适用.'
            wr_log('info',msg)
        else:
            pass
    
#控制文件状态检查
    msg = funcName + ':开始执行控制文件状态检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','controfile','status')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库控制文件状态检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        cursor.execute('select name,status from v$controlfile where status is not null')
        rs = cursor.fetchall()
        if len(rs) > 0:
            for line in rs:
                content = '控制文件' + line[0] + '状态异常,当前状态为' + line[1]
                lv = 2
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
        else:
            msg = funcName + ':数据库控制文件状态正常'
            wr_log('info',msg)
#控制文件数量检查
    msg = funcName + ':开始执行控制文件数量检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','controfile','count')
    #print '控制文件数据量检查:d=============',d
    if d is None or d[4] == 0:
        msg = funcName + ':数据库控制文件数量检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        lim_val = d[0]
        cursor.execute('select count(*) from v$controlfile where status is null')
        rs = cursor.fetchone()
        if rs[0] < int(lim_val):
            content = '控制文件数量异常,当前数量为' + str(rs[0])+ '正常数量为>=' + lim_val
            alert_id = d[3]
            lv = 1
            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
            wr_alert(alert_info)
        else:
            msg = funcName + ':数据库控制文件数量正常'
            wr_log('info',msg)
    
#重做日志文件状态检查
    msg = funcName + ':开始执行重做日志文件状态检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','redo','status')
    #print '控制文件数据量检查:d=============',d
    if d is None or d[4] == 0:
        msg = funcName + ':数据库重做日志文件状态检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        cursor.execute('''
        select f.member,f.type,f.status from v$logfile f,v$log l
    	where f.group# = l.group#
    	and f.type <>'ONLINE'
    	or f.status in ('INVALID','DELETED')
    	''')
        rs = cursor.fetchall()
        if len(rs) > 0:
            for line in rs:
                content = 'redo日志文件状态异常:' + line[0] + '状态为' + line[1]
                lv = 1
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
        else:
            msg = funcName + ':redo日志文件状态正常'
            wr_log('info',msg)
#重做日志文件组数检查
    msg = funcName + ':开始执行重做日志文件组数检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','redo','groups')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库重做日志文件组数检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        if d[0] is None:
            lim_val = 3
        else:
            lim_val = d[0]
        sql = '''
        select groups from (select thread#
          ,count(distinct group#) groups
         from v$log
        where thread#=(select instance_number from v$instance)
        group by thread#)
        '''
        cursor.execute(sql)
        rs = cursor.fetchall()
        for line in rs:
            print 'line[0]===',line[0],'int(lim_val)===',str(lim_val)
            if line[0] < int(lim_val):
                lv = 1
                content = 'REDO日志组数量异常,当前REDO日志组数为:' + str(line[0]) + ',正常数量为>=' + str(lim_val)
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg = funcName + ':REDO日志组数为' + str(line[0]) + '数量正常'
                wr_log('info',msg)
    
#重做日志文件成员数检查
    msg = funcName + ':开始执行重做日志文件成员数量检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','redo','member')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库重做日志文件成员数量检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        if d[0] is None:
            lim_val = 2
        else:
            lim_val = d[0]
        sql = "select count(*) from v$log where members <> " + str(lim_val)
        cursor.execute(sql)
        rs = cursor.fetchone()
        if rs[0] > 0:
            lv = 1
            alert_id =d[3]
            content = 'REDO日志组成员数量异常,当前REDO日志有:' + str(line[0]) + '组成员数异常,正常成员数为' + str(lim_val)
            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
            wr_alert(alert_info)
        else:
            msg = funcName + ':REDO日志组成员数量' + str(line[0]) + ',数量正常'
            wr_log('info',msg)
    
#重做日志文件大小一致性检查
    msg = funcName + ':开始执行重做日志文件大小一致性检查'
    wr_log('info',msg)
    d = get_lim_val(inst_id,'runstat','redo','same_size')
    if d is None or d[4] == 0:
        msg = funcName + ':数据库重做日志文件大小一致性检查已屏蔽，略过检查'
        wr_log('info',msg)
    else:
        sql = "select count(distinct bytes) discnt from v$log"
        cursor.execute(sql)
        rs = cursor.fetchone()
        if rs[0] > 1:
            lv = 1
            content = 'REDO日志文件大小存在不一致,请检查!'
            alert_id = d[3]
            alert_info = {'alert_id':alert_id,'content':content,'level':lv}
            wr_alert(alert_info)
        else:
            msg = funcName + ':EDO日志文件大小一致，检查正常'
            wr_log('info',msg)
#数据文件自动扩展检查
    msg = funcName + ':开始执行数据文件自动扩展检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','redo','same_size')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库数据文件自动扩展检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            sql = '''
            select file_name,autoextensible from dba_data_files where autoextensible = 'YES'
            union all
            select file_name,autoextensible from dba_temp_files where autoextensible = 'YES'
            '''
            cursor.execute(sql)
            rs = cursor.fetchall()
            if len(rs) > 0:
                f = ''
                for line in rs:
                    f = f + ',' + line[0] 
                content = '数据文件自动扩展告警:' + f + '是自动扩展的,请检查'
                lv = 1
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg = funcName + ':数据文件自动扩展检查正常'
                wr_log('info',msg)
    elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
        msg = funcName + '数据库数据文件状态检查:数据库为standby数据库,不适用.'
        wr_log('info',msg)
    else:
        pass
#作业状态检查
    msg = funcName + ':开始执行作业状态检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','job','status')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库JOB状态检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            sql = '''
                    select what,failures,'dba_jobs' from dba_jobs 
        			where failures >0
        			union all
        			select JOB_NAME,FAILURE_COUNT,'DBA_SCHEDULER_JOBS' FROM DBA_SCHEDULER_JOBS 
        			WHERE FAILURE_COUNT>0
                '''
            cursor.execute(sql)
            rs = cursor.fetchall()
            if len(rs) > 0:
                f = ''
                for line in rs:
                    print 'line=====',line
                    f = f + line[0] + line[2] + '\n'
                content = '数据库job执行失败告警:' + f 
                lv = 1
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg = funcName + ':数据库job执行正常'
                wr_log('info',msg)
    elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
        msg = funcName + '数据库作业状态检查:数据库为standby数据库,不适用.'
        wr_log('info',msg)
    else:
        pass
#无效索引检查
    msg = funcName + ':开始执行无效索引检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','job','status')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库无效索引检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            sql = '''
                select sum(cnt) cnt,nvl(max(index_name),' ') index_name
                from 
                (select count(*) cnt,max(owner||'.'||index_name) index_name
                from dba_indexes
                where status not in ('VALID', 'N/A')
                union all
                select count(*) cnt,max(b.owner||'.'||b.index_name) index_name
                from dba_ind_partitions a,
                     dba_indexes        b
                where a.index_name=b.index_name
                and   a.index_owner=b.owner
                and   a.status not in ('N/A', 'USABLE')
                union all
                select count(*) cnt,max(b.owner||'.'||b.index_name) index_name
                from dba_ind_subpartitions a,
                     dba_indexes           b
                where a.index_name=b.index_name
                and   a.index_owner=b.owner
                and   a.status not in ('USABLE'))
                '''
            cursor.execute(sql)
            rs = cursor.fetchone()
            if rs[0] > 0:
                content = '数据库索引失效告警:有' + rs[1] + '等' + str(rs[0]) + '个索引失效'
                lv = 1
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg = funcName + ':数据库中无失效索引'
                wr_log('info',msg)
    elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
        msg = funcName + '数据库失效索引检查:数据库为standby数据库,不适用.'
        wr_log('info',msg)
    else:
        pass
#并行度非1表检查
    msg = funcName + ':开始执行并行度大于1的表检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','table','degree')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库并行度大于1的表检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            sql = '''
                select count(*) cnt,nvl(max(a.owner||'.'||a.table_name),' ') table_name
                from dba_tables a,dba_objects b
                where a.owner=b.owner
                and   a.table_name=b.object_name
                and   b.object_type='TABLE'
                and   a.degree<>'         1' 
                '''
            cursor.execute(sql)
            rs = cursor.fetchone()
            if rs[0] > 0:
                content = '数据库表并行度异常告警:有' + rs[1] + '等' + str(rs[0]) + '个表并行度大于1'
                lv = 1
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg = funcName + ':数据库表并行度检查正常'
                wr_log('info',msg)
    elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
        msg = funcName + '数据库表并行度检查:数据库为standby数据库,不适用.'
        wr_log('info',msg)
    else:
        pass
#并行度非1索引检查
    msg = funcName + ':开始执行并行度大于1的索引检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','index','degree')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库并行度大于1的表检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            sql = '''
                select count(*) cnt,nvl(max(owner||'.'||index_name),' ') index_name
                from dba_indexes 
                where degree not in ('1','0')
                and   owner||'.'||index_name<>'SYS.UTL_RECOMP_SORT_IDX1'
                '''
            cursor.execute(sql)
            rs = cursor.fetchone()
            if rs[0] > 0:
                content = '数据库索引并行度异常告警:有' + rs[1] + '等' + str(rs[0]) + '个索引并行度大于1'
                lv = 1
                alert_id = d[3]
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg = funcName + ':数据库索引并行度检查正常'
                wr_log('info',msg)
    elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
        msg = funcName + '数据库并行度非1索引检查:数据库为standby数据库,不适用.'
        wr_log('info',msg)
    else:
        pass
#process数量检查
    msg = funcName + ':开始执行process数量检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','process','used_pct')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库process检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            sql = '''
    			   select limit,used,round(100*used/limit) used_pct
    			   from (select count(*) used from v$process)
    				,(select to_number(value) limit from v$parameter 
    				  where name='processes')
                  ''' 
            cursor.execute(sql)
            rs = cursor.fetchone()
            lv1,lv2,lv3 = float(d[0]),float(d[1]),float(d[2])
            alert_id = d[3]
            if rs[2] >= lv1 and rs[2] <lv2:
                content = '数据库进程数告警:当前已process已使用' + str(rs[2]) + '%,process已使用' + str(rs[1]) + '最大process数' + str(rs[0])
                lv = 1
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            elif rs[2] >= lv2 and rs[2] < lv3:
                lv = 2
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            elif rs[2] >= lv3:
                lv = 3
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg = funcName + ':数据库process使用数量检查正常'
                wr_log('info',msg)
    elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
        msg = funcName + '数据库process数量检查:数据库为standby数据库,不适用.'
        wr_log('info',msg)
    else:
        pass
#并行进程使用率检查
    msg = funcName + ':开始执行并行进程使用率检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','parallel_max_servers','used_pct')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库并行进程使用率检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            sql = '''
    		select limit,used,round(100*used/limit)
    		from 
    			(select current_utilization used,to_number(initial_allocation) limit
    			from v$resource_limit
    			where 
    			resource_name='parallel_max_servers'
    			 )
                '''
            cursor.execute(sql)
            rs = cursor.fetchone()
            lv1,lv2,lv3 = float(d[0]),float(d[1]),float(d[2])
            alert_id = d[3]
            if rs[2] >= lv1 and rs[2] <lv2:
                content = '数据库并行进程数告警:当前并行进程已使用' + str(rs[2]) + '%,process已使用' + str(rs[1]) + '最大process数' + str(rs[0])
                lv = 1
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            elif rs[2] >= lv2 and rs[2] < lv3:
                lv = 2
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            elif rs[2] >= lv3:
                lv = 3
                alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                wr_alert(alert_info)
            else:
                msg = funcName + ':并行进程数量检查正常'
                wr_log('info',msg)
    else:
        msg = funcName + ':standby数据库,略过此项检查'
        wr_log('info',msg)
#序列使用率检查
    msg = funcName + ':开始执行序列使用率检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','sequence','used_pct')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库序列使用率检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            sql = '''
           select sequence_name,max_value,last_number,round(100*ABS(LAST_NUMBER-MIN_VALUE)/(MAX_VALUE-MIN_VALUE)) 
		   from dba_sequences
            '''  
            cursor.execute(sql)
            rs = cursor.fetchall()
            lv1,lv2,lv3 = float(d[0]),float(d[1]),float(d[2])
            alert_id = d[3]
            print 'lv==============',lv1,'   ',lv2,'   ',lv3
            fg = 0
            for row in rs:
                if (row[3] >= lv1 and row[2] <lv2):
                    content = '数据库序列使用率告警:序列' + row[0] + '已使用' + str(row[3]) + '%'
                    lv = 1
                    fg = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}      
                    wr_alert(alert_info)
                elif (row[3] >= lv2 and row[2] <lv3):
                    content = '数据库序列使用率告警:序列' + row[0] + '已使用' + str(row[3]) + '%'
                    lv = 2
                    fg = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif row[3] >= lv3:
                    print rs[3],'____',lv3
                    content = '数据库序列使用率告警:序列' + row[0] + '已使用' + str(row[3]) + '%'
                    lv = 3
                    fg = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
            if fg == 0:
                msg = funcName + ':数据库序列使用率检查正常'
                wr_log('info',msg)
            else:
                pass
    else:
        msg = funcName + ':standby数据库,略过此项检查'
        wr_log('info',msg)
#数据库坏块检查
    msg = funcName + ':开始执行数据库坏块检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','block','badblock')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库序坏块检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            try:
                sql = 'select count(*) cnt from v$database_block_corruption'
                cursor.execute(sql)
                rs = cursor.fetchall()
                if rs[0][0] > 0:
                    content = '数据库坏块检查告警:当前数据库中有' + str(rs[0][0]) + '个坏块,请检查'
                    lv = 2
                    alert_id = d[3]
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':数据库坏块检查:正常'
                    wr_log('info',msg)
            except Exception,e:
                content = '数据库检查失败,请检查数据库状态' 
                lv = 3
                alert_info = {'alert_id':inst_id,'content':content,'level':lv}
                wr_alert(alert_info)
                msg = funcName + ':' + content
                wr_log('info',msg)
    else:
        msg = funcName + ':standby数据库,略过此项检查'
        wr_log('info',msg)
#数据库文件数使用率检查
    msg = funcName + ':开始执行数据库文件使用率检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        d = get_lim_val(inst_id,'runstat','dbfiles','used_pct')
        if d is None or d[4] == 0:
            msg = funcName + ':数据库序文件使用率检查已屏蔽，略过检查'
            wr_log('info',msg)
        else:
            try:
                sql = '''
    		select used,round(100*used/limit) used_pct,limit
            from  
    	        (select count(*) used
    			from 
    		    dba_data_files
    		    )
            ,(select to_number(value) limit 
    	      from v$parameter 
    	      where name='db_files'
    	      )	
            '''
                cursor.execute(sql)
                rs = cursor.fetchone()
                lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
                alert_id = d[3]
                if rs[1]>=lv1 and rs[1]<lv2:
                    content = '数据库数据文件数量使用率告警，当前数据文件数量' + str(rs[0]) + ',已使用' + str(rs[1]) + '%'
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif rs[1]>=lv2 and rs[1]<lv3:
                    content = '数据库数据文件数量使用率告警，当前数据文件数量' + str(rs[0]) + ',已使用' + str(rs[1]) + '%'
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif rs[1]>=lv3:
                    content = '数据库数据文件数量使用率告警，当前数据文件数量' + str(rs[0]) + ',已使用' + str(rs[1]) + '%'
                    lv = 3
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':数据库数据文件数量检查正常'
                    wr_log('info',msg)
            except Exception,e:
                content = '数据库数据文件数量检查失败,请检查数据库状态' + str(e)
                lv = 3
                alert_info = {'alert_id':inst_id,'content':content,'level':lv}
                wr_alert(alert_info)
                msg = funcName + ':' + content
                wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#大事务检查
    msg = funcName + ':开始执行数据库大事务检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            sql = 'select nvl(max(used_urec),0) used_rec from v$transaction'
            d = get_lim_val(inst_id,'runstat','undo','undorecord')
            if d is None or d[4] == 0:
                msg = funcName + ':数据库大事务检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                cursor.execute(sql)
                rs = cursor.fetchone()
                alert_id = d[3]
                lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
                if rs[0] >= lv1 and rs[0] < lv2:
                    content = '数据库大事务告警:当前数据库中大事务记录数' + str(rs[0]) + ',告警阈值' + str(lv1)
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif rs[0] >= lv2 and rs[0] < lv3:
                    content = '数据库大事务告警:当前数据库中大事务记录数' + str(rs[0]) + ',告警阈值' + str(lv2)
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif rs[0] >= lv3:
                    content = '数据库大事务告警:当前数据库中大事务记录数' + str(rs[0]) + ',告警阈值' + str(lv3)
                    lv = 3
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':数据库大事务检查:正常'
                    wr_log('info',msg)
        except Exception,e:
            content = '数据库大事务检查失败,请检查数据库状态' + str(e)
            lv = 3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#长时间执行sql检查
    msg = funcName + ':开始执行长时间执行SQL检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','sql','elap_time')
            lv1,lv2,lv3 = float(d[0]),float(d[1]),float(d[2])
            if d is None or d[4] == 0:
                msg = funcName + ':数据库长时间执行SQL检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                sql = '''select a.sql_id,nvl(last_call_et,0) elas
						from 
						v$session a, v$sql b
						where 
						status = 'ACTIVE'
						and username is not null
						and a.sql_id = b.sql_id
						and a.sql_child_number = b.child_number
						and a.last_call_et > 
                     ''' + str(lv1)
                cursor.execute(sql)
                rs = cursor.fetchall()
                alert_id = d[3]
                if len(rs) > 0:
                    content = 'sql执行时间过长告警:'
                    for line in rs:
                        content = content + line[0] + '执行耗时' + str(line[1]) + '秒,'
                    content = content + '告警阈值' + str(lv1) + '秒'
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':数据库长时间执行sql检查正常'
                    wr_log('info',msg)
        except Exception,e:
            content = '数据库长时间执行sql检查失败,请检查数据库状态' + str(e)
            lv = 2
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#未归档日志组数量检查
    msg = funcName + ':开始执行未归档日志组数量检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','unarch','count')
            lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
            if d is None or d[4] == 0:
                msg = funcName + ':数据库未归档日志组数量检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                sql = '''select sum(decode(archived,'YES',1,1)) total_logs
		 	 ,sum(decode(archived,'YES',0,1)) unarch_logs
			 from v$log
			 where thread#=(select instance_number from v$instance)
        	      '''
                cursor.execute(sql)
                rs = cursor.fetchone()
                alert_id = d[3]
                if rs[1] >= lv1 and rs[1] < lv2:
                    content = '未归档日志组数量告警:当前有' + str(rs[1]) + '组日志未归档,请检查,告警阈值' + str(lv1)
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif rs[1] >= lv2 and rs[1] < lv3:
                    content = '未归档日志组数量告警:当前有' + str(rs[1]) + '组日志未归档,请检查,告警阈值' + str(lv2)
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif rs[1] >= lv3:
                    content = '未归档日志组数量告警:当前有' + str(rs[1]) + '组日志未归档,请检查,告警阈值' + str(lv3)
                    lv = 3
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':未归档日志组数量检查正常'
                    wr_log('info',msg)
        except Exception,e:
            content = '未归档日志组数量检查失败,请检查数据库状态' + str(e)
            lv = 2
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#未备份数据文件检查
    msg = funcName + ':开始执行未备份数据文件检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','unback','datafile')
            lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
            if d is None or d[4] == 0:
                msg = funcName + ':数据库未备份数据文件检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                sql = '''with backdbf as (
					   select count(*) backdbfs
						from (select file#,count(*) from  v$backup_datafile 
								where completion_time >= sysdate-''' + str(lv1) + '''
								 and file#>0 group by file#)),
						alldbf as (
						select count(file#) alldbfs from v$datafile
						where CREATION_TIME <= sysdate-1)
						select alldbfs,backdbfs,alldbfs-backdbfs unbackdbfs
						from backdbf,alldbf'''
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[2] > 0:
                    content = '未备份数据文件检查告警:当前有' + str(rs[2]) + '个数据文件在最近' + str(lv1) + '天内未备份'
                    lv = 1
                    alert_info = {'alert_id':inst_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':未备份数据文件检查正常'
                    wr_log('info',msg)
        except Exception,e:
            content = '未备份数据文件检查失败,请检查数据库状态' + str(e)
            lv = 3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#未备份归档日志数检查
    msg = funcName + ':开始执行未备份归档日志检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','unback','arch')
            lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
            if d is None or d[4] == 0:
                msg = funcName + ':数据库未备份归档日志检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                sql = '''select count(*) cnt
				from v$archived_log a,v$archive_dest b
				where a.dest_id=b.dest_id
				--and   b.status='VALID'
				and   b.target='PRIMARY'
				and   thread#=(select instance_number from v$instance) 
				and   completion_time <= sysdate-''' + str(lv1) + ''' 
				and   completion_time >= sysdate-30
				and   a.status='A'
				and   backup_count=0'''
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[0] > 0:
                    alert_id = d[3]
                    content = '未备份归档日志数量告警:当前有' + str(rs[0]) + '个归档日志在最近' + str(lv1) + '天前未备份'
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':未备份归档日志检查正常'
                    wr_log('info',msg)
        except Exception,e:
            content = '未备份归档日志数量检查失败,请检查数据库状态' + str(e)
            lv = 3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#备份缺失归档日志检查
    msg = funcName + ':开始执行缺失归档日志检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','misback','arch')
            lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
            if d is None or d[4] == 0:
                msg = funcName + ':数据库缺失归档日志检查已屏蔽，略过检查'
                wr_log('info',msg)
            else: 
                sql = '''select cnt
				from (
				select count(*) cnt
				from v$archived_log a,v$archive_dest b
				where a.dest_id=b.dest_id
				and   b.status='VALID'
				and   b.target='PRIMARY'
				and   thread#=(select instance_number from v$instance) 
				and   completion_time >= sysdate- ''' + str(lv1) + '''  
				and   completion_time <= sysdate-1
				and   (a.deleted='YES' or a.status<>'A')
				and   backup_count=0)'''
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[0] > 0:
                    content = '备份缺失归档日志检查告警:最近' + str(lv1) + '天内有' + str(rs[0]) + '个归档日志备份缺失'
                    lv = 1
                    alert_id = d[3]
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                    msg = funcName + ':' + content
                    wr_log('info',msg)
                else:
                    msg = funcName + ':缺失归档日志检查正常'
                    wr_log('info',msg)
        except Exception,e:
            content = '备份缺失归档日志检查失败,请检查数据库状态' + str(e)
            lv = 3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#PGA内存使用检查
    msg = funcName + ':开始执行PGA内存使用检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','pga','pct_used')
            lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
            if d is None or d[4] == 0:
                msg = funcName + ':数据库PGA内存使用检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                sql = '''select round(100*pga_alloc/pga_target) pga_pct
				from (
				select value pga_alloc
				from v$pgastat
				where name='total PGA allocated'),
				(select value pga_target
				from v$pgastat
				where name='aggregate PGA target parameter')'''
                cursor.execute(sql)
                rs = cursor.fetchone()
                alert_id = d[3]
                if rs[0] >= lv1 and rs[0] < lv2:
                    content = 'PGA内存使用告警:当前PGA使用率' + str(rs[0]) + '%,告警阈值' + str(lv1) + '%'
                    lv = 1
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif rs[0] >= lv2 and rs[0] < lv3:
                    content = 'PGA内存使用告警:当前PGA使用率' + str(rs[0]) + '%,告警阈值' + str(lv1) + '%'
                    lv = 2
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                elif rs[0] >= lv3:
                    content = 'PGA内存使用告警:当前PGA使用率' + str(rs[0]) + '%,告警阈值' + str(lv1) + '%'
                    lv = 3
                    alert_info = {'alert_id':inst_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':PGA使用检查正常'
                    wr_log('info',msg)
        except Exception,e:
            content = 'PGA内存使用检查失败，请检查数据库状态' + str(e)
            lv = 3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#数据库参数修改检查
    msg = funcName + ':开始执行数据库参数修改使用检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','parameter','has_moded')
            if d is None or d[4] == 0:
                msg = funcName + ':数据库参数修改检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                sql = '''select nvl(min(snap_id),0),nvl(max(snap_id),0)
    				from dba_hist_snapshot
    				where instance_number=(select instance_number from v$instance)
    				and   begin_interval_time >= sysdate-1'''
                cursor.execute(sql)
                rs = cursor.fetchone()
                min_sid = rs[0]
                max_sid = rs[1]
                sql = '''with bpara as (
    				select instance_number inst_id
    					,snap_id
    					,parameter_name name
    					,isdefault
    					,ismodified
    					,trim(lower(value)) value
    				from dba_hist_parameter
    				where instance_number=(select instance_number from v$instance)
    				and   snap_id= ''' + str(min_sid) + '''),
    				epara as (
    				select instance_number inst_id
    					,snap_id
    					,parameter_name name
    					,isdefault
    					,ismodified
    					,trim(lower(value)) value
    				from dba_hist_parameter
    				where instance_number=(select instance_number from v$instance)
    				and   snap_id= ''' + str(max_sid) + ''')
    				select b.name,b.value b_value,e.value e_value
    				from bpara b,epara e
    				where b.inst_id=e.inst_id
    				and   b.name=e.name
    				and   b.name not in ('service_names','resource_manager_plan')
    				and   b.value<>e.value'''
                cursor.execute(sql)
                rs = cursor.fetchall()
                if len(rs) > 0:
                    content = '数据库参数修改检查告警:数据库参数'
                    for line in rs:
                        content = content + line[0] + ','
                    content = content[:-1] + '被修改,请检查'
                    lv = 1
                    alert_id = d[3]
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':数据库参数修改检查正常'
                    wr_log('info',msg)
        except Exception,e:
            content = '数据库参数修改检查失败' + str(e)
            lv = 3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#审计表大小检查
    msg = funcName + ':开始执行数据库审计表大小检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','aud','size')
            if d is None or d[4] == 0:
                msg = funcName + ':数据库审计表大小检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
                sql = '''select sum(bytes)/1024/1024 aud_size from dba_segments where owner='SYS' and segment_name='AUD$' '''
                cursor.execute(sql)
                rs =  cursor.fetchone()
                if rs[0] >= lv1:
                    content = '审计表大小检查告警:数据库AUD$表过大，当前大小' + str(rs[0]) + 'MB,告警阈值' + str(lv1) + 'MB'
                    lv = 1
                    alert_id = d[3]
                    alert_info = {'alert_id':alert_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':审计表大小检查正常'
                    wr_log('info',msg)
        except Exception,e: 
            content = '审计表大小检查失败,请检查数据库状态' + str(e) 
            lv = 3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#统计信息自动收集作业检查
    msg = funcName + ':开始执行数据库统计信息自动收集作业检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','statistics','collect_job')
            if d is None or d[4] == 0:
                msg = funcName + ':数据库统计信息自动收集作业检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                sql = 'select substr(version,1,6) from v$instance'
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[0] == '11.2.0':
                    sql = '''select count(*) jobstatus
    			from 
    			(select job_name
    					,enabled job_enabled
    					,state   job_status
    					,failure_count fail_cnt
    					,to_char(last_start_date,'mm/dd_hh24:mi') last_run
    			from dba_scheduler_jobs
    			where job_name='BSLN_MAINTAIN_STATS_JOB') x,
    			(select client_name task_name
    					,status      task_status
    			from dba_autotask_task
    			where client_name='auto optimizer stats collection') y
    			where x.job_enabled='TRUE' 
    			and   x.job_status ='SCHEDULED'
    			and   y.task_status='ENABLED'
                '''
                    cursor.execute(sql)
                    rs = cursor.fetchone()
                    if rs[0] > 0:
                        sql = '''select count(*) cnt
    				from dba_autotask_task        a,
    					dba_autotask_job_history b
    				where a.client_name=b.client_name
    				and   a.client_name='auto optimizer stats collection'
    				and   b.job_start_time >= sysdate-7
    				and   b.job_status<>'SUCCEEDED' 
                    '''
                        cursor.execute(sql)
                        rs = cursor.fetchone()
                        if rs[0] > 0:
                            content = '统计信息自动收集作业检查告警:有' + str(rs[0]) + '次作业不成功'
                            lv = 1
                            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
                            wr_alert(alert_info)
                        else:
                            msg = funcName + ':统计信息自动收集作业检查正常'
                            wr_log('info',msg)
                    else:
                        pass
                else:
                    msg =funcName + ':数据库版本低于11.2.0，略过检查'
                    wr_log('info',msg)
        except Exception,e:
            content = '计信息自动收集作业检查失败,请检查数据库状态' + str(e)
            lv =3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)
#统计信息为空对象检查
    msg = funcName + ':开始执行数据库统计信息为空对象检查'
    wr_log('info',msg)
    if dbrole == 'PRIMARY':
        try:
            d = get_lim_val(inst_id,'runstat','statistics','null_count')
            lv1,lv2,lv3 = int(d[0]),int(d[1]),int(d[2])
            if d is None or d[4] == 0:
                msg = funcName + ':数据库统计信息为空对象检查已屏蔽，略过检查'
                wr_log('info',msg)
            else:
                sql ='''with seg as (
					select /*+ materialize */owner,segment_name,partition_name,bytes
					from dba_segments
					where bytes > ''' + str(lv1) + '''*1024*1024
					and owner not in 
					('SYSTEM','SYS','OUTLN','ORACLE_OCM','DBSNMP','APPQOSSYS','WMSYS','DIP','TSMSYS',
					'EXFSYS','XDB','ANONYMOUS','MDSYS','ORDPLUGINS','ORDSYS','SI_INFORMTN_SCHEMA',
					'SYSMAN','MGMT_VIEW','XS$NULL','ORDDATA','FLOWS_FILES','DMSYS','CTXSYS','OLAPSYS',
					'MDDATA')
					)
					select cnt
					from (
					select count(*) cnt
					from (
					select /*+ rule */
						a.owner||'.'||a.table_name object_name
						,'N/A' part_name
						,'N/A' subpart_name
						,'Table' Type
						,to_char(c.created,'yymmdd_hh24:mi') Create_Time
						,nvl(round(b.bytes/1024/1024),0) size_m
					from dba_tables  a,
						seg         b,
						dba_objects  c
					where a.owner=b.owner
					and   a.table_name=b.segment_name
					and   a.owner=c.owner
					and   a.table_name=c.object_name
					and   c.object_type='TABLE'
					and   a.partitioned='NO'
					and   a.temporary='N'
					and   a.num_rows is null
					and   a.last_analyzed is null
					union all
					select /*+ rule */ 
						a.table_owner||'.'||a.table_name object_name
						,a.partition_name part_name
						,'N/A' subpart_name
						,'TabPart' Type
						,to_char(c.created,'yymmdd_hh24:mi') Create_Time
						,nvl(round(b.bytes/1024/1024),0) size_m
					from dba_tab_partitions a,
						seg                b,
						dba_objects        c
					where a.table_owner=b.owner
					and   a.table_name=b.segment_name
					and   a.partition_name=b.partition_name
					and   a.table_owner=c.owner
					and   a.table_name=c.object_name
					and   a.partition_name=c.subobject_name
					and   c.object_type='TABLE PARTITION'
					and   a.subpartition_count=0
					and   a.num_rows is null
					and   a.last_analyzed is null
					union all
					select /*+ rule */ 
						a.table_owner||'.'||a.table_name object_name
						,a.partition_name part_name
						,a.subpartition_name subpart_name
						,'TabSubPart' Type
						,to_char(c.created,'yymmdd_hh24:mi') Create_Time
						,nvl(round(b.bytes/1024/1024),0) size_m
					from dba_tab_subpartitions a,
						seg         b,
						dba_objects           c
					where a.table_owner=b.owner
					and   a.table_name=b.segment_name
					and   a.subpartition_name=b.partition_name
					and   a.table_owner=c.owner
					and   a.table_name=c.object_name
					and   a.partition_name=c.subobject_name
					and   c.object_type='TABLE PARTITION'
					and   a.num_rows is null
					and   a.last_analyzed is null
					union all
					select /*+ rule */
						a.owner||'.'||a.index_name object_name
						,'N/A' part_name
						,'N/A' subpart_name
						,'Index' Type
						,to_char(c.created,'yymmdd_hh24:mi') Create_Time
						,nvl(round(b.bytes/1024/1024),0) size_m
					from dba_indexes  a,
						seg         b,
						dba_objects  c
					where a.owner=b.owner
					and   a.index_name=b.segment_name
					and   a.owner=c.owner
					and   a.index_name=c.object_name
					and   c.object_type='INDEX'
					and   a.partitioned='NO'
					and   a.temporary='N'
					and   a.num_rows is null
					and   a.last_analyzed is null
					union all
					select /*+ rule */ 
						a.index_owner||'.'||a.index_name object_name
						,a.partition_name part_name
						,'N/A' subpart_name
						,'IndPart' Type
						,to_char(c.created,'yymmdd_hh24:mi') Create_Time
						,nvl(round(b.bytes/1024/1024),0) size_m
					from dba_ind_partitions a,
						seg         b,
						dba_objects        c
					where a.index_owner=b.owner
					and   a.index_name=b.segment_name
					and   a.partition_name=b.partition_name
					and   a.index_owner=c.owner
					and   a.index_name=c.object_name
					and   a.partition_name=c.subobject_name
					and   c.object_type='INDEX PARTITION'
					and   a.subpartition_count=0
					and   a.num_rows is null
					and   a.last_analyzed is null
					union all
					select /*+ rule */ 
						a.index_owner||'.'||a.index_name object_name
						,a.partition_name part_name
						,a.subpartition_name subpart_name
						,'IndSubPart' Type
						,to_char(c.created,'yymmdd_hh24:mi') Create_Time
						,nvl(round(b.bytes/1024/1024),0) size_m
					from dba_ind_subpartitions a,
						seg         b,
						dba_objects           c
					where a.index_owner=b.owner
					and   a.index_name=b.segment_name
					and   a.subpartition_name=b.partition_name
					and   a.index_owner=c.owner
					and   a.index_name=c.object_name
					and   a.partition_name=c.subobject_name
					and   c.object_type='INDEX PARTITION'
					and   a.num_rows is null
					and   a.last_analyzed is null
					))''' 
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[0] > 0:
                    content = '统计信息为空对象告警:数据库中有' + str(rs[0]) + '个对象统计信息为空'
                    lv = 1
                    alert_info = {'alert_id':inst_id,'content':content,'level':lv}
                    wr_alert(alert_info)
                else:
                    msg = funcName + ':统计信息为空对象检查正常'
                    wr_log('info',msg)
        except Exception,e:
            content = '统计信息对象为空检查失败，请检查数据库状态' + str(e)
            lv = 3
            alert_info = {'alert_id':inst_id,'content':content,'level':lv}
            wr_alert(alert_info)
            msg = funcName + ':' + content
            wr_log('info',msg)
    else:
        msg = funcName + ':standby 数据库,略过检查'
        wr_log('info',msg)

