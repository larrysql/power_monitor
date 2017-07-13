#!/usr/local/bin/python
#coding=utf-8
from __future__ import division
import cx_Oracle
import sys
import urllib
import os
import time
import datetime
import string
from  utils.utility import *

slptime = 10

def mon_load():
    d = get_inst_info()
    inst_id = d['inst_id']
    sql_load = '''
              select case name 
		when 'session logical reads' then 'session_logical_reads'
		when 'db block changes' then 'db_block_changes' 
		when 'physical reads' then 'physical_reads'
		when 'redo size' then 'redo_size'
		when 'execute count' then 'execute_count'
		when 'parse count (total)' then 'parse_count_total'
		when 'parse count (hard)' then 'parse_count_hard'
		when 'user commits' then 'user_commits'
		when 'user rollbacks' then 'user_rollbacks'
		when 'physical writes' then 'physical_writes'
		when 'physical reads direct' then 'physical_reads_direct'
		when 'physical reads direct (lob)' then 'physical_reads_direct_lob'
		when 'redo log space requests' then 'redo_log_space_requests'
		when 'redo entries' then 'redo_entries'
		when 'parse time cpu' then 'parse_time_cpu'
		when 'parse time elapsed' then 'parse_time_elapsed'
		when 'CPU used by this session' then 'CPU_used_by_this_session'
		when 'sorts (memory)' then 'sorts_memory'
		when 'sorts (disk)' then 'sorts_disk'
		end,
		value from v$sysstat 
             where 
            name in('session logical reads','physical reads','redo size','execute count','parse count (total)',
            'parse count (hard)','user commits','user rollbacks','physical writes','db block changes','physical reads direct'
			,'physical reads direct (lob)','redo log space requests','redo entries','parse time cpu','parse time elapsed',
			'CPU used by this session','sorts (memory)','sorts (disk)') 
			'''
    eventsql='''SELECT STAT_NAME EVENT,NULL TOTAL_WAITS,VALUE TIME_WAITED,NULL WAIT_CLASS 
	            FROM V$SYS_TIME_MODEL WHERE STAT_NAME ='DB CPU'         
				UNION ALL        
				SELECT EVENT,TOTAL_WAITS,TIME_WAITED,WAIT_CLASS FROM V$SYSTEM_EVENT WHERE WAIT_CLASS <> 'Idle' '''
    timemodsql='''select stat_name,round(value/1000000) from v$sys_time_model order by stat_name'''
    btop_sql = '''select sql_id,plan_hash_value,sql_text,disk_reads,buffer_gets,cpu_time,elapsed_time,user_io_wait_time,executions,
		rows_processed from v$sqlstats'''
    etop_sql = '''select sql_id,plan_hash_value,sql_text,disk_reads,buffer_gets,cpu_time,elapsed_time,user_io_wait_time,executions,
                rows_processed from v$sqlstats where LAST_ACTIVE_TIME>=sysdate-'''+str(slptime)+'''/86400'''
    try:
        db = ora_conn()
        cursor = db.cursor()
        mydb = connectDB()
        mydb.set_character_set('utf8')
        mycursor = mydb.cursor()
    except StandardError,e:
        print str(e)
    bload = ()
    while True:
#获取数据库load
        if len(bload) == 0:
            bload = cursor.execute(sql_load).fetchall()
            print '*************first*******************'
        else:
            bload = eload
            print '*************continue****************'
#获取数据库等待事件数据        #bload = cursor.execute(sql_load).fetchall()
        bevent = cursor.execute(eventsql).fetchall()
        btimemod = cursor.execute(timemodsql).fetchall()
#获取top sql信息
        brssqlstat = cursor.execute(btop_sql).fetchall()
#将数据库负载数据转换为字典
        bd = {}
        #snap_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        for line in bload:
            statname,value = line[0],line[1]
            bd[statname] = value
        #print 'bl=======',bd
#开始休眠------------------------------------------
        time.sleep(slptime)
#开始处理负载数据------------------------------------------
        eload = cursor.execute(sql_load).fetchall()
        ed = {}
        snap_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        for line in eload:
            statname,value = line[0],line[1]
            ed[statname] = value
        d = {}
        for k in ed:
            d[k] = [ed[k],(ed[k] - bd[k])/slptime]
        l = []
        #Buffer Hit %
        if d['session_logical_reads'][1] == 0:
            d['session_logical_reads'][1] = 1
        d['buff_hit_ratio'] = [0,(1 - (d['physical_reads'][1]-d['physical_reads_direct_lob'][1]-d['physical_reads_direct'][1])/d['session_logical_reads'][1])*100]
        #Redo NoWait %
        if d['redo_entries'][1] == 0:
            d['redo_nowait_ratio'] = [0,100]
        else:
            d['redo_nowait_ratio'] = [0,100*(d['redo_entries'][1] - d['redo_log_space_requests'][1])/d['redo_entries'][1]]
        #In-memory Sort %
        if (d['sorts_memory'][1] + d['sorts_disk'][1]) == 0:
            d['in_memory_sort'] = [0,1]
        else:
            d['in_memory_sort'] = [0,100*(d['sorts_memory'][1]/(d['sorts_memory'][1] + d['sorts_disk'][1]))]
        print '**************sorts_memory***************',d['sorts_memory'],'*********sorts_disk**************',d['sorts_disk']
        for k in d:
            l.append((inst_id,k,d[k][0],d[k][1],snap_time))
        #print 'l===================',l
        mycursor.executemany('''insert into ora_sysstat(inst_id,stat_name,value,value_delta,snap_time) values(%s,%s,%s,%s,%s) ''',l);
        print "inst_id = ",inst_id
        mycursor.execute('''delete from ora_sysstat_tmp where inst_id = %s''',str(inst_id))
        #mycursor.execute('''delete from ora_sysstat_tmp where inst_id = 4''')
        mycursor.executemany('''insert into ora_sysstat_tmp(inst_id,stat_name,value,value_delta,snap_time) values(%s,%s,%s,%s,%s) ''',l);
        mydb.commit()
#开始处理等待事件
        eevent = cursor.execute(eventsql).fetchall()
        etimemod = cursor.execute(timemodsql).fetchall()
        #print 'bebent============',bevent,'eevent=======================',eevent
        dbevent = {}
        deevent = {}
        devent = {}
        for x in bevent:
            dbevent[x[0]] = (x[1],x[2],x[3])
        for x in eevent:
            deevent[x[0]] = (x[1],x[2],x[3])
#求两个结果集的差值,结果放在deventtime中
        for z in deevent:
            if deevent[z][0] is not None:
                devent[z]=(deevent[z][0],deevent[z][1],deevent.get(z,(0,0,0))[0]-dbevent.get(z,(0,0,0))[0],(deevent.get(z,(0,0,0))[1]-dbevent.get(z,(0,0,0))[1])/100,deevent[z][2])        
            else: 
                devent[z]=('None',deevent[z][1],'None',(deevent[z][1]-dbevent[z][1])/1000000,'None')
        #print 'devent==============================',devent
        snap_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        levent = []
        for k in devent:
            if devent[k][0] == 'None':
                levent.append((inst_id,k,snap_time,0,devent[k][1],0,devent[k][3],'None'))
            else:
                levent.append((inst_id,k,snap_time,devent[k][0],devent[k][1],devent[k][2],devent[k][3],devent[k][4]))
        #print  'levent========================',levent
        mycursor.executemany('''insert into ora_sys_event(inst_id,event_name,snap_time,total_waits,time_waited,total_waits_delta,
		total_waited_delta,wait_class) values (%s,%s,%s,%s,%s,%s,%s,%s)''',levent)
        mycursor.execute('''delete from ora_sys_event_tmp where inst_id = %s''',str(inst_id))
        mycursor.executemany('''insert into ora_sys_event_tmp(inst_id,event_name,snap_time,total_waits,time_waited,total_waits_delta,
		total_waited_delta,wait_class) values (%s,%s,%s,%s,%s,%s,%s,%s)''',levent)
        mydb.commit()
        #开始处理top sql信息
        erssqlstat = cursor.execute(etop_sql).fetchall()
        dbsqlstat = {}
        desqlstat = {}
        for x in brssqlstat:
            dbsqlstat[x[0]] = [x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8],x[9]]
        for x in erssqlstat:
            desqlstat[x[0]] = [x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8],x[9]]
       #计算两次结果集的差值,并将记录放到列表中
        l_rec = []
        for key in desqlstat:
            dkr_delta = desqlstat[key][2] - dbsqlstat.get(key,['','',0,0,0,0,0,0,0])[2]
            bfg_delta = desqlstat[key][3] - dbsqlstat.get(key,['','',0,0,0,0,0,0,0])[3]
            ct_delta = desqlstat[key][4] - dbsqlstat.get(key,['','',0,0,0,0,0,0,0])[4]
            elt_delta = desqlstat[key][5] - dbsqlstat.get(key,['','',0,0,0,0,0,0,0])[5]
            uiow_delta = desqlstat[key][6] - dbsqlstat.get(key,['','',0,0,0,0,0,0,0])[6]
            exec_delta = desqlstat[key][7] - dbsqlstat.get(key,['','',0,0,0,0,0,0,0])[7]
            rwp_delta = desqlstat[key][8] - dbsqlstat.get(key,['','',0,0,0,0,0,0,0])[8]
            if key == '7b2twsn8vgfsc':
                print key,'||dkr_delta==',dkr_delta,' bfg_delta==',bfg_delta,'||cpu_time==',ct_delta,'||exec_delta==',exec_delta,'||rwp_delta==',rwp_delta
            l_rec.append([inst_id,key,desqlstat[key][0],desqlstat[key][1],desqlstat[key][2],dkr_delta,desqlstat[key][3],bfg_delta,\
            desqlstat[key][4],ct_delta,desqlstat[key][5],elt_delta,desqlstat[key][6],uiow_delta,desqlstat[key][7],exec_delta,\
            desqlstat[key][8],rwp_delta,snap_time])
        mycursor.executemany('''insert into ora_top_sql(inst_id,sql_id,phv,sql_text,disk_reads,disk_reads_delta,buffer_gets,\
        buffer_gets_delta,cpu_time,cpu_time_delta,elapsed_time,elapsed_time_delta,user_io_wait_time,user_id_wait_time_delta,\
        executions,executions_delta,rows_processed,rows_processed_delta,snap_time) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
        %s,%s,%s,%s,%s,%s,%s,%s,%s) ''',l_rec);
        mycursor.execute('''delete from ora_top_sql_tmp where inst_id = %s''',str(inst_id))
        mycursor.executemany('''insert into ora_top_sql_tmp(inst_id,sql_id,phv,sql_text,disk_reads,disk_reads_delta,buffer_gets,\
        buffer_gets_delta,cpu_time,cpu_time_delta,elapsed_time,elapsed_time_delta,user_io_wait_time,user_id_wait_time_delta,\
        executions,executions_delta,rows_processed,rows_processed_delta,snap_time) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,\
        %s,%s,%s,%s,%s,%s,%s,%s,%s) ''',l_rec);
        mydb.commit()
        #for i in  l_rec:
            #print i,'\n****************************************************************************************************'
if __name__=='__main__':
    mon_load()
 
