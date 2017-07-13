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

conf_fname = '/home/oracle/powerm/config/powerm.conf'

def chk_inst_status():
    try:
        db = cx_Oracle.connect('/',mode=cx_Oracle.SYSDBA) 
    except Exception,e:
        alert_info = "chk_inst_status:数据库连接失败!请检查"
        wr_alert(alert_info)
        return 1
    cursor = db.cursor()
#检查实例状态
    cursor.execute('select DATABASE_ROLE from v$database')
    rs = cursor.fetchone()
    dbrole = rs[0]
    #print dbrole
    cursor.execute('select instance_name,status from v$instance')
    rs = cursor.fetchone()
    if dbrole == 'PRIMARY' and rs[1] != 'OPEN':
        alert_info = '数据库实例' + rs[0] + '状态异常,当前状态为' + rs[1] + ',正常状态为OPEN' 
        wr_alert(alert_info)
    elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY') and rs[1] == 'MOUNTED':
        print '数据库实例' + rs[0] + '状态正常,STANDBY数据库,当前状态为' + rs[1]
    else:
        print '数据库实例' + rs[0] + '状态正常,当前状态为' + rs[1]
#检查数据库状态
    cursor.execute('select name,OPEN_MODE from v$database')
    rs = cursor.fetchone()
    if dbrole == 'PRIMARY' and rs[1] != 'READ WRITE':
        alert_info = '数据库' + rs[0] + '状态异常,当前状态为' + rs[1] + ',正常状态为READ WRITE'
        wr_alert(alert_info)
    elif (dbrole == 'PHYSICAL STANDBY'):
        print '数据库' + rs[0] + '为STANDBY数据库'
    else:
        print '数据库' + rs[0] + '状态正常,当前状态为' + rs[1]
#数据库归档模式检查
    cursor.execute("select schedule from v$archive_dest where status='VALID' and dest_id=1")
    rs = cursor.fetchone()
    if dbrole == 'PRIMARY' and rs[0] != 'ACTIVE':
        alert_info = '数据库为非归档模式,正常为归档模式'
        wr_alert(alert_info)
    elif dbrole == 'PHYSICAL STANDBY':
        print '数据库为STANDBY数据库'
    else:
        print '数据库归档模式正常'
#数据库实例监听注册检查
##获取数据库实例列表
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
            alert_info = '数据库实例'  + i + '未在监听中注册'
            wr_alert(alert_info)
        else:
            print i + "已注册"

#数据库表空间状态检查
    try:
        if dbrole == 'PRIMARY':
            cursor.execute('select tablespace_name,status from dba_tablespaces')
            rs = cursor.fetchall()
            for line in rs:
                if line[1] != 'ONLINE':
                    alert_info = '表空间' + line[0] + '状态异常，正常状态为ONLINE'
                    wr_alert(alert_info)
                else:
                    print '表空间' + line[0] + '状态正常，为' + line[1]
        elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
            print '数据库表空间状态检查:数据库为standby数据库,不适用.'
        else:
            pass
    except Exception,e:
        alert_info = '查询数据库表空间状态失败,请确认数据库实例是否为open状态'
        wr_alert(alert_info)

#数据文件状态检查
    if dbrole == 'PRIMARY':
        cursor.execute('''
		select name,status from v$datafile where status not in('ONLINE','SYSTEM')
		union all
		select name,status from v$tempfile where status <> 'ONLINE'
        ''')
        rs = cursor.fetchall()
        if len(rs) > 0:
            for line in rs:
                alert_info = '数据文件' + line[0] + '状态异常,当前状态为' + line[1]
                wr_alert(alert_info)
        else:
            print '数据库所有数据文件状态正常!'
    elif (dbrole == 'PHYSICAL STANDBY' or dbrole == 'LOGICAL STANDBY'):
        print '数据库数据文件状态检查:数据库为standby数据库,不适用.'
    else:
        pass

#控制文件状态检查
    cursor.execute('select name,status from v$controlfile where status is not null')
    rs = cursor.fetchall()
    if len(rs) > 0:
        for line in rs:
            alert_info = '控制文件' + line[0] + '状态异常,当前状态为' + line[1]
            wr_alert(alert_info)
    else:
        print '数据库所有控制文件状态正常!'

#控制文件数量检查
    cursor.execute('select count(*) from v$controlfile where status is null')
    rs = cursor.fetchone()
    if rs[0] < 2:
        alert_info = '控制文件数量异常,当前数量为' + rs[0] + '正常数量为>=2'
    else:
        print '数据库控制文件数量正常'

#重做日志文件状态检查
    cursor.execute('''
    select f.member,f.type,f.status from v$logfile f,v$log l
	where f.group# = l.group#
	and f.type <>'ONLINE'
	or f.status in ('INVALID','DELETED')
	''')
    rs = cursor.fetchall()
    if len(rs) > 0:
        for line in rs:
            alert_info = 'redo日志文件状态异常:' + line[0] + '状态为' + line[1]
            wr_alert(alert_info)
    else:
        print 'redo日志文件状态正常'
#重做日志文件组数检查
    lim_val = get_conf_val(conf_fname,'REDO','GROUP')
    if lim_val is None:
        lim_val = 3
    else:
        lim_val = int(lim_val)
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
        if line[0] < lim_val:
            alert_info = 'REDO日志组数量异常,当前REDO日志组数为:' + line[0] + ',告警阈值<=' + str(lim_val)
            wr_alert(alert_info)
        else:
            print 'REDO日志组数为' + str(line[0]) + '数量正常'

#重做日志文件成员数检查
    lim_val = get_conf_val(conf_fname,'REDO','MEMBER')
    if lim_val is None:
        lim_val = 2
    else:
        lim_val = int(lim_val)
    sql = "select count(*) from v$log where members <> 2"
    cursor.execute(sql)
    rs = cursor.fetchone()
    if rs[0] > 0:
        alert_info = 'REDO日志组成员数量异常,当前REDO日志有:' + line[0] + '组成员数异常,正常成员数为' + str(lim_val)
        wr_alert(alert_info)
    else:
        print 'REDO日志组成员数量正常'

#重做日志文件大小一致性检查
    sql = "select count(distinct bytes) discnt from v$log"
    cursor.execute(sql)
    rs = cursor.fetchone()
    if rs[0] > 1:
        alert_info = 'REDO日志文件大小存在不一致,请检查!'
        wr_alert(alert_info)
    else:
        print 'REDO日志文件大小一致'
#数据文件自动扩展检查
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
        alert_info = '数据文件自动扩展告警:' + f + '是自动扩展的,请检查'
        wr_alert(alert_info)
    else:
        print '数据文件自动扩展检查正常'
#作业状态检查
    sql = '''
            select what,failures,'dba_jobs' from dba_jobs 
			where failures >0
			union all
			select PROGRAM_NAME,FAILURE_COUNT,'DBA_SCHEDULER_JOBS' FROM DBA_SCHEDULER_JOBS 
			WHERE FAILURE_COUNT>0
        '''
    cursor.execute(sql)
    rs = cursor.fetchall()
    if len(rs) > 0:
        f = ''
        for line in rs:
            f = f + line[0] + line[2] + '\n'
        alert_info = '数据库job执行失败告警:' + f 
        wr_alert(alert_info)
    else:
        print '数据库job执行正常'
#无效索引检查
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
    if len(rs) > 0:
        alert_info = '数据库索引失效告警:有' + rs[1] + '等' + str(rs[0]) + '个索引失效'
        wr_alert(alert_info)
    else:
        print '数据库中无失效索引'
#并行度非1表检查
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
    if len(rs) > 0:
        alert_info = '数据库表并行度异常告警:有' + rs[1] + '等' + str(rs[0]) + '个表并行度大于1'
        wr_alert(alert_info)
    else:
        print '数据库表并行度检查正常'
#并行度非1索引检查
    sql = '''
        select count(*) cnt,nvl(max(owner||'.'||index_name),' ') index_name
        from dba_indexes 
        where degree not in ('1','0')
        and   owner||'.'||index_name<>'SYS.UTL_RECOMP_SORT_IDX1'
        '''
    cursor.execute(sql)
    rs = cursor.fetchone()
    if len(rs) > 0:
        alert_info = '数据库索引并行度异常告警:有' + rs[1] + '等' + str(rs[0]) + '个索引并行度大于1'
        wr_alert(alert_info)
    else:
        print '数据库索引并行度检查正常'
#process数量检查
    if dbrole == 'PRIMARY':
        lim_val = get_conf_val(conf_fname,'PROCESS','USED_PCT')
        if lim_val is None:
            lim_val = 90
        sql = '''
			   select limit,used,round(100*used/limit) used_pct
			   from (select count(*) used from v$process)
				,(select to_number(value) limit from v$parameter 
				  where name='processes')
              ''' 
        cursor.execute(sql)
        rs = cursor.fetchone()
        if rs[2] > lim_val:
            alert_info = '数据库进程数告警:当前已process已使用' + str(rs[2]) + '%,process已使用' + str(rs[1]) + '最大process数' + str(rs[0])
            wr_alert(alert_info)
        else:
            print '数据库process使用正常'
    else:
        print 'standby数据库,略过此项检查'
#并行进程使用率检查
    if dbrole == 'PRIMARY':
        lim_val = get_conf_val(conf_fname,'PSERVER','USED_PCT')
        if lim_val is None:
            lim_val = 90
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
        if rs[2] > lim_val:
            alert_info = '数据库并行进程数量告警:并行进程使用率' + str(rs[2]) + '%,已使用' + str(rs[1]) + '最大并行进程数' + str(rs[2])
            wr_alert(alert_info)
        else:
            print '并行进程数量检查正常'
    else:
        print 'standby数据库,略过此项检查'
#序列使用率检查
    if dbrole == 'PRIMARY':
        lim_val = get_conf_val(conf_fname,'SEQUENCE','USED_PCT')
        if lim_val is None:
            lim_val = 90
        sql = '''
           select sequence_name,max_value,last_number,round(100*ABS(LAST_NUMBER)/(MAX_VALUE-MIN_VALUE)) 
		   from dba_sequences
		   where 100*ABS(LAST_NUMBER)/(MAX_VALUE-MIN_VALUE) >
            ''' + str(lim_val) 
        cursor.execute(sql)
        rs = cursor.fetchall()
        if len(rs) > 0:
            alert_info = '数据库序列使用率告警:序列'
            for line in rs:
                alert_info = alert_info + line[0] + '已使用' + str(line[3]) + '%,'
            alert_info = alert_info + '告警阈值' + str(lim_val) 
            wr_alert(alert_info)
        else:
            print '数据库序列使用正常'
    else:
        print 'standby 数据库,略过检查'
#数据库坏块检查
    try:
        sql = 'select count(*) cnt from v$database_block_corruption'
        cursor.execute(sql)
        rs = cursor.fetchall()
        if rs[0][0] > 0:
            alert_info = '数据库坏块检查告警:当前数据库中有' + str(rs[0][0]) + '个坏块,请检查'
            wr_alert(alert_info)
        else:
            print '数据库坏块检查:正常'
    except Exception,e:
        alert_info = '数据库检查失败,请检查数据库状态' 
        wr_alert(alert_info)
#数据库文件数使用率检查
    if dbrole == 'PRIMARY':
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
            lim_val = get_conf_val(conf_fname,'DBFILES','USED_PCT')
            if lim_val is None:
                lim_val = 90
            cursor.execute(sql)
            rs = cursor.fetchone()
            if rs[1] > int(lim_val):
                alert_info = '数据库数据文件数量使用率告警，当前数据文件数量' + str(rs[0]) + ',已使用' + str(rs[1]) + '%'
                wr_alert(alert_info)
            else:
                print '数据库数据文件数量检查:正常'
        except Exception,e:
            alert_info = '数据库检查失败,请检查数据库状态' + e
            wr_alert(alert_info)
    else:
            print 'standby 数据库,略过检查'
#大事务检查
    if dbrole == 'PRIMARY':
        try:
            sql = 'select nvl(max(used_urec),0) used_rec from v$transaction'
            lim_val = get_conf_val(conf_fname,'TRANS','UREC')
            if lim_val is None:
                print '已略过数据库大事务检查' 
            else:
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[0] > int(lim_val):
                    alert_info = '数据库大事务告警:当前数据库中大事务记录数' + str(rs[0]) + ',告警阈值' + str(lim_val)
                    wr_alert(alert_info)
                else:
                    print '数据库大事务检查:正常'
        except Exception,e:
            alert_info = '数据库大事务检查失败,请检查数据库' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#长时间执行sql检查
    if dbrole == 'PRIMARY':
        try:
            lim_val = get_conf_val(conf_fname,'SQLELA','SQLELA')
            if lim_val is None:
                print '已略过长时间执行sql检查'
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
                     ''' + lim_val
                cursor.execute(sql)
                rs = cursor.fetchall()
                if len(rs) > 0:
                    alert_info = 'sql执行时间过长告警:'
                    for line in rs:
                        alert_info = alert_info + line[0] + '执行耗时' + str(line[1]) + '秒,'
                    alert_info = alert_info + '告警阈值' + lim_val + '秒'
                    wr_alert(alert_info)
                else:
                    print '数据库长时间执行sql检查:正常'
        except Exception,e:
            alert_info = '数据库长时间执行sql检查失败,请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#未归档日志组数量检查
    if dbrole == 'PRIMARY':
        try:
            lim_val = get_conf_val(conf_fname,'UNARCH','UNARCH')
            if lim_val is None:
                print '已略过未归档日志组数量检查'
            else:
                sql = '''
										select sum(decode(archived,'YES',1,1)) total_logs
		 						         ,sum(decode(archived,'YES',0,1)) unarch_logs
								    from v$log
								   where thread#=(select instance_number from v$instance)
								   '''
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[1] > int(lim_val):
                    alert_info = '未归档日志组数量告警:当前有' + str(rs[1]) + '组日志未归档,请检查,告警阈值' + lim_val
                    wr_alert(alert_info)
                else:
                    print '未归档日志组数量检查正常'
        except Exception,e:
            alert_info = '数据库长时间执行sql检查失败,请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#未备份数据文件检查
    if dbrole == 'PRIMARY':
        try:
            lim_val = get_conf_val(conf_fname,'UNBACK','DATAFILE')
            if lim_val is None:
                print '已略过未备份数据文件检查'
            else:
                sql = '''with backdbf as (
					   select count(*) backdbfs
						from (select file#,count(*) from  v$backup_datafile 
								where completion_time >= sysdate-''' + lim_val + '''
								 and file#>0 group by file#)),
						alldbf as (
						select count(file#) alldbfs from v$datafile
						where CREATION_TIME <= sysdate-1)
						select alldbfs,backdbfs,alldbfs-backdbfs unbackdbfs
						from backdbf,alldbf'''
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[2] > 0:
                    alert_info = '未备份数据文件检查告警:当前有' + str(rs[2]) + '个数据文件在最近' + lim_val + '天内未备份'
                    wr_alert(alert_info)
                else:
                    print '未备份数据文件检查正常'
        except Exception,e:
            alert_info = '未备份数据文件检查失败,请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#未备份归档日志数检查
    if dbrole == 'PRIMARY':
        try:
            lim_val = get_conf_val(conf_fname,'UNBACK','ARCH')
            if lim_val is None:
                print '已略过未备份归档日志检查'
            else:
                sql = '''select count(*) cnt
				from v$archived_log a,v$archive_dest b
				where a.dest_id=b.dest_id
				--and   b.status='VALID'
				and   b.target='PRIMARY'
				and   thread#=(select instance_number from v$instance) 
				and   completion_time <= sysdate-''' + lim_val + ''' 
				and   completion_time >= sysdate-30
				and   a.status='A'
				and   backup_count=0'''
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[0] > 0:
                    alert_info = '未备份归档日志数量告警:当前有' + str(rs[0]) + '个归档日志在最近' + lim_val + '天内未备份'
                    wr_alert(alert_info)
                else:
                    print '未备份归档日志数量检查正常'
        except Exception,e:
            alert_info = '未备份数据文件检查失败,请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#备份缺失归档日志检查
    if dbrole == 'PRIMARY':
        try:
            lim_val = get_conf_val(conf_fname,'MISBACK','ARCH')
            if lim_val is None:
                print '已略过备份缺失归档日志检查'
            else: 
                sql = '''select cnt
				from (
				select count(*) cnt
				from v$archived_log a,v$archive_dest b
				where a.dest_id=b.dest_id
				and   b.status='VALID'
				and   b.target='PRIMARY'
				and   thread#=(select instance_number from v$instance) 
				and   completion_time >= sysdate- ''' + lim_val + '''  
				and   completion_time <= sysdate-1
				and   (a.deleted='YES' or a.status<>'A')
				and   backup_count=0)'''
                cursor.execute(sql)
                rs = cursor.fetchone()
                if rs[0] > 0:
                    alert_info = '备份缺失归档日志检查告警:最近' + lim_val + '天内有' + str(rs[0]) + '个归档日志备份缺失'
                    wr_alert(alert_info)
                else:
                    print '备份缺失归档日志检查正常'
        except Exception,e:
            alert_info = '备份缺失归档日志检查失败,请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#PGA内存使用检查
    if dbrole == 'PRIMARY':
        try:
            lim_val = get_conf_val(conf_fname,'PGA','PGAPCT')
            if lim_val is None:
                print '已略过PGA内存使用检查'
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
                if rs[0] > int(lim_val):
                    alert_info = 'PGA内存使用告警:当前PGA使用率' + str(rs[0]) + '%,告警阈值' + lim_val + '%'
                    wr_alert(alert_info)
                else:
                    print 'PGA内存使用检查正常'
        except Exception,e:
            alert_info = 'PGA内存使用检查失败，请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#数据库参数修改检查
    if dbrole == 'PRIMARY':
        try:
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
                alert_info = '数据库参数修改检查告警:数据库参数'
                for line in rs:
                    alert_info = alert_info + line[0] + ','
                alert_info = alert_info[:-1] + '被修改,请检查'
                wr_alert(alert_info)
            else:
                print '数据库参数修改检查:正常'
        except Exception,e:
            alert_info = '数据库参数修改检查失败，请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#审计表大小检查
    if dbrole == 'PRIMARY':
        try:
            lim_val = get_conf_val(conf_fname,'AUDTAB','AUDTAB') 
            if lim_val is None:
                print '已略过审计表大小检查'
            else:
                sql = '''select sum(bytes)/1024/1024 aud_size from dba_segments where owner='SYS' and segment_name='AUD$' '''
                cursor.execute(sql)
                rs =  cursor.fetchone()
                if rs[0] > int(lim_val):
                    alert_info = '审计表大小检查告警:数据库AUD$表过大，当前大小' + str(rs[0]) + 'MB,告警阈值' + lim_val + 'MB'
                    wr_alert(alert_info)
                else:
                    print '审计表大小检查:正常'
        except Exception,e: 
            alert_info = '审计表大小检查失败,请检查数据库状态' + str(e) 
    else:
        print 'standby 数据库,略过检查'
#统计信息自动收集作业检查
    if dbrole == 'PRIMARY':
        try:
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
                        alert_info = '统计信息自动收集作业检查告警:有' + str(rs[0]) + '次作业不成功'
                        wr_alert(alert_info)
                    else:
                        print '统计信息自动收集作业检查:正常'
                else:
                    pass
            else:
                print '数据库版本低于11.2.0，略过检查'
        except Exception,e:
            alert_info = '计信息自动收集作业检查失败,请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby 数据库,略过检查'
#统计信息为空对象检查
    if dbrole == 'PRIMARY':
        try:
            lim_val = get_conf_val(conf_fname,'STATISTICS','NULL')
            if lim_val is None:
                print '已略过统计信息为空对象检查'
            else:
                sql ='''with seg as (
					select /*+ materialize */owner,segment_name,partition_name,bytes
					from dba_segments
					where bytes > ''' + lim_val + '''*1024*1024
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
                    alert_info = '统计信息为空对象告警:数据库中有' + str(rs[0]) + '个对象统计信息为空,告警阈值' + lim_val
                    wr_alert(alert_info)
                else:
                    print '统计信息为空对象检查:正常'
        except Exception,e:
            alert_info = '统计信息对象为空检查失败，请检查数据库状态' + str(e)
            wr_alert(alert_info)
    else:
        print 'standby数据库，略过检查'
