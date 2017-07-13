#!/usr/local/bin/python
# -*- coding: utf-8
import sys,os
sys.path.append("..")
from utils.conn_mysql import *
from flask import Flask,url_for,jsonify
from flask import render_template,Blueprint,abort
from flask import request,session
from jinja2 import TemplateNotFound
import chartkick
import json
import time,random,datetime
reload(sys)
sys.setdefaultencoding('utf-8')
os.environ["NLS_LANG"] = ".UTF8"

mod = Blueprint('oracle', __name__,template_folder='templates')
#============================================获取数据库实例列表===================================================
@mod.route('/ora_inst_list')
def ora_inst_list():
    if session.get('logged_in'):
        username = session['username']
        db = conn_mysql()
        cursor = db.cursor()
        sql = 'select i.id,i.host_name,i.ip_addr,i.inst_name,i.db_name,i.db_type,g.gname' \
              ' from ora_inst i,app_group g' \
              ' where i.gid = g.id order by gname,inst_name'
        cursor.execute(sql)
        entries = cursor.fetchall()
        print(entries)
        cursor.close()
        db.close()
        return render_template('oracle/ora_inst_list.html',entries = entries)
    else:
        return render_template('login.html')

@mod.route('/ora_inst_detail')
def ora_inst_detail():
    inst_id = request.args.get('inst_id')
    return render_template('oracle/ora_inst_detail.html',inst_id=inst_id)

#============================================获取数据库实例详细信息===================================================
@mod.route('/ora_inst_detail_info',methods=['GET','POST'])
def ora_inst_detail_info():
    if request.method == 'GET':
        inst_id = request.args.get('inst_id')
        info_name = request.args.get('info_name')
        try:
            db = conn_ora(inst_id)
            cursor = db.cursor()
            if info_name == "'main_info'":
            #实例信息
                cursor.execute('''select e.host_name,e.instance_name,e.INSTANCE_ROLE,e.version,e.uptime,
                                e.status,e.logins,a.cnt_all,b.cnt_active,c.cnt_wait,d.cnt_enq
                            from
	                        (select count(*) cnt_all from v$session) a,
	                        (select count(*) cnt_active from v$session where status = 'ACTIVE' and username is not null) b,
	                        (select count(*) cnt_wait from v$session where wait_class <>'Idle') c,
	                        (select count(*) cnt_enq from v$session where event like 'enq%') d,
							(select instance_name,INSTANCE_ROLE,host_name,
							 version,TO_CHAR(startup_time,'yyyy-mm-dd HH24:MI:SS') ,
							 ROUND(TO_CHAR(SYSDATE-startup_time), 2) uptime,parallel,status,logins
							 from v$instance
							 ) e''')
                rs_inst = rows_to_dict_list(cursor)
                print(rs_inst)
            #数据库信息
                cursor.execute('''select name,dbid,db_unique_name,TO_CHAR(created, 'yyyy-mm-dd HH24:MI:SS')
                            ,platform_name,log_mode,open_mode,force_logging,flashback_on,DATABASE_ROLE from v$database''')
                rs_db = cursor.fetchall()
            #控制文件信息
                cursor.execute('''select name,decode(status,null,'VALID',status) status,
                                TO_CHAR(block_size *  file_size_blks, '999,999,999,999') file_size
                                from v$controlfile''')
                rs_ctlfile = cursor.fetchall()
            #REDO日志信息
                cursor.execute('''
                SELECT i.instance_name ,i.thread#, f.group#,f.member, f.type                                                                                           redo_file_type
		        , DECODE(l.status, 'CURRENT',l.status,l.status) log_status, l.bytes
		        ,l.archived archived
                FROM gv$logfile  f, gv$log      l, gv$instance i
                WHERE
                f.group#  = l.group# AND l.thread# = i.thread# AND i.inst_id = f.inst_id AND f.inst_id = l.inst_id
                ORDER BY i.instance_name , f.group#, f.member''')
                rs_redo = cursor.fetchall()

                tag='数据库信息'
            #数据库参加参数信息
                cursor.execute('''SELECT p.name, i.instance_name ,decode(p.value,null,'none',p.value),p.isdefault,p.issys_modifiable
                                FROM gv$parameter p, gv$instance  i
                              WHERE p.inst_id = i.inst_id and p.ISDEFAULT='FALSE'
                              ORDER BY isdefault, p.name, i.instance_name
                            ''')
                rs_para = cursor.fetchall()
            #表空间信息
                sql = '''select * from (
		                SELECT
		                	DECODE(   d.status
		                			, 'OFFLINE'
		                			, d.status
		                			, d.status) status
		                , d.tablespace_name name
		                , d.contents                                          type
		                , d.extent_management                                 extent_mgt
		                , d.segment_space_management                          segment_mgt
		                , round(NVL(a.bytes, 0),0)                            ts_size
		                , round(NVL(f.bytes, 0))                              free
		                , round(NVL(a.bytes - NVL(f.bytes, 0), 0))            used
		                , DECODE (
		                			(1-SIGN(1-SIGN(TRUNC(NVL((a.bytes - NVL(f.bytes, 0)) / a.bytes * 100, 0)) - 90)))
		                			, 1
		                			, TO_CHAR(TRUNC(NVL((a.bytes - NVL(f.bytes, 0)) / a.bytes * 100, 0)))
		                			, TO_CHAR(TRUNC(NVL((a.bytes - NVL(f.bytes, 0)) / a.bytes * 100, 0)))
		                		) pct_used
		                FROM
		                	sys.dba_tablespaces d
		                , ( select tablespace_name, sum(bytes)/1024/1024 bytes
		                	from dba_data_files
		                	group by tablespace_name
		                	) a
		                , ( select tablespace_name, sum(bytes)/1024/1024 bytes
		                	from dba_free_space
		                	group by tablespace_name
		                	) f
		                WHERE
		                	d.tablespace_name = a.tablespace_name(+)
		                AND d.tablespace_name = f.tablespace_name(+)
		                AND NOT (
		                	d.extent_management like 'LOCAL'
		                	AND
		                	d.contents like 'TEMPORARY'
		                )
		                UNION ALL
		                SELECT
		                	DECODE(   d.status
		                			, 'OFFLINE'
		                			, d.status
		                			, d.status) status
		                ,d.tablespace_name name
		                , d.contents                                   type
		                , d.extent_management                          extent_mgt
		                , d.segment_space_management                   segment_mgt
		                , NVL(a.bytes, 0)                              ts_size
		                , NVL(a.bytes - NVL(t.bytes,0), 0)             free
		                , NVL(t.bytes, 0)                              used
		                , DECODE (
		                			(1-SIGN(1-SIGN(TRUNC(NVL(t.bytes / a.bytes * 100, 0)) - 90)))
		                			, 1
		                			, TO_CHAR(TRUNC(NVL(t.bytes / a.bytes * 100, 0)))
		                			,TO_CHAR(TRUNC(NVL(t.bytes / a.bytes * 100, 0)))
		                		) pct_used
		                FROM
		                	sys.dba_tablespaces d
		                , ( select tablespace_name, sum(bytes)/1024/1024 bytes
		                	from dba_temp_files
		                	group by tablespace_name
		                	) a
		                , ( select tablespace_name, sum(bytes_cached)/1024/1024 bytes
		                	from v$temp_extent_pool
		                	group by tablespace_name
		                	) t
		                WHERE
		                	d.tablespace_name = a.tablespace_name(+)
		                AND d.tablespace_name = t.tablespace_name(+)
		                AND d.extent_management like 'LOCAL'
		                AND d.contents like 'TEMPORARY'
		                )
                    order by to_number(pct_used) desc'''
                cursor.execute(sql)
                rs_tbs_usage = cursor.fetchall()
            #数据文件信息
                sql = '''SELECT d.tablespace_name, d.file_name, round(d.bytes/1024/1024),d.autoextensible autoextensible,
                    		d.increment_by * e.value increment_by, round(d.maxbytes/1024/1024) max_size
                    FROM
                        sys.dba_data_files d, v$datafile v
                    	, (SELECT value
                         FROM v$parameter
                         WHERE name = 'db_block_size') e
                    WHERE
                      (d.file_name = v.name)
                    UNION ALL
                    SELECT d.tablespace_name, d.file_name, round(d.bytes/1024/1024),d.autoextensible autoextensible, d.increment_by * e.value, d.maxbytes                                                          maxbytes
                    FROM sys.dba_temp_files d
                      , (SELECT value
                         FROM v$parameter
                         WHERE name = 'db_block_size') e'''
                cursor.execute(sql)
                rs_tbs_datafile = cursor.fetchall()
            #数据库用户信息
                sql = '''select username,account_status,DEFAULT_TABLESPACE,TEMPORARY_TABLESPACE,CREATED,PROFILE from dba_users'''
                cursor.execute(sql)
                rs_user = cursor.fetchall()
            elif info_name == "'parameter'":
                pass
        except Exception,e:
            rs_inst,rs_db,rs_ctlfile,rs_redo,rs_para,rs_tbs_datafile,rs_user,rs_tbs_datafile = [],[],[],[],[],[],[],[]
        return render_template('oracle/ora_inst_detail_info.html',**locals())
    elif request.method == 'POST':
        return 'error!'




#===============================================获取数据库告警信息=====================================================
@mod.route('/ora_alert')
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
    return render_template('oracle/ora_alert.html',entries = entries,tag='监控告警')

@mod.route('/ora_alert_detail/',methods=['GET','POST'])
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

#============================================获取数据库负载信息================================================
@mod.route('/ora_load')
def ora_load():
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute('select id from ora_inst')
    rs_inst = cursor.fetchall()
    l = []
    for id in rs_inst:
        sql = '''select s.inst_id,i.host_name,i.inst_name,s.stat_name,s.value_delta,s.snap_time
                from ora_sysstat_tmp s,ora_inst i
                where s.inst_id = i.id and i.id = ''' + str(id[0]) + '''
              '''
        cursor.execute(sql)
        rs = cursor.fetchall()
        if len(rs) >= 10:
            d = {}
            for x in rs:
                d['inst_id'],d['host_name'],d['inst_name'],d[x[3]],d['snap_time'] = x[0],x[1],x[2],x[4],x[5]
            l.append(d)
    #print l
    cursor.close()
    db.close()
    return render_template('oracle/ora_load.html',entries=l,tag='负载监控')
    #return jsonify(result = l)
#===============================获取数据库详细负载信息=================================================================
@mod.route('/ora_load_detail',methods = ['GET', 'POST'])
def ora_load_detail():
    if request.method == 'GET':
        inst_id = request.args.get('inst_id', 0, type=int)
        period = request.args.get('period', 0, type=int)
        if period == 1:
            tick = 0.1
        elif period == 24:
            tick = 1
        elif period == 168:
            tick = 10
        else:
            tick = 1
        #print period
        return render_template('oracle/ora_load_detail.html',inst_id=inst_id,tag='实时负载监控',period=period,tick=tick)
    elif request.method == 'POST':
        inst_id,begin_date,end_date = request.form.get('inst_id'),request.form.get('begin_date'),request.form.get('end_date')
        period = begin_date + '|' + end_date
        print(period)
        tick = 1
        #return 'period = ' + period
        return render_template('oracle/ora_load_range.html',inst_id=inst_id,tag='负载范围监控',period=period,tick=tick)
    else:
        return 'error request!'

def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj
#================================初始化数据库负载信息=================================================================
@mod.route('/ora_load_json_init')
def ora_load_json_init():
    inst_id = request.args.get('id')
    period = request.args.get('period')
    #print 'period==============',period
    stat_name = request.args.get('stat_name')
    if '|' in period:
        begin_date,end_date = period.split('|')[0],period.split('|')[1]

        sql ='''select date_format(snap_time,'%Y/%m/%d %H:%i:%s') snap_time,value_delta value
                from ora_sysstat
                where inst_id = ''' + str(inst_id) + ''' and stat_name = ''' + stat_name + '''
                    and snap_time>=str_to_date(\'''' + begin_date + '''\','%Y-%m-%d %H:%i:%s')
                    and snap_time<=str_to_date(\'''' + end_date + '''\','%Y-%m-%d %H:%i:%s')
	            order by snap_time
            '''
    else:
        sql = ''' select date_format(snap_time,'%Y/%m/%d %H:%i:%s') snap_time,value_delta value
                from ora_sysstat where inst_id = ''' + str(inst_id) + ''' and stat_name = ''' + stat_name + '''
                and snap_time > date_sub(now(),interval ''' + period + ''' hour) order by snap_time
                '''
    print(sql)
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute(sql)
    rs = cursor.fetchall()
    if len(rs) >10:
        l = []
        for x in rs:
            l.append([time.mktime(time.strptime(x[0],'%Y/%m/%d %H:%M:%S'))*1000,x[1]])
        #print l
    else:
        from utils.tools import init_data
        l = init_data(1)
    d = json.dumps(l)
    #print d
    return d
#================================数据库负载范围查询信息=================================================================
@mod.route('/ora_load_json_range')
def ora_load_json_range():
    inst_id = request.args.get('id')
    period = request.args.get('period')
    #print 'period==============',period
    stat_name = request.args.get('stat_name')
    if '|' in period:
        begin_date,end_date = period.split('|')[0],period.split('|')[1]

        sql ='''select date_format(snap_time,'%Y/%m/%d %H:%i:%s') snap_time,value_delta value
                from ora_sysstat
                where inst_id = ''' + str(inst_id) + ''' and stat_name = ''' + stat_name + '''
                    and snap_time>=str_to_date(\'''' + begin_date + '''\','%Y-%m-%d %H:%i:%s')
                    and snap_time<=str_to_date(\'''' + end_date + '''\','%Y-%m-%d %H:%i:%s')
	            order by snap_time
            '''
    else:
        sql = ''' select date_format(snap_time,'%Y/%m/%d %H:%i:%s') snap_time,value_delta value
                from ora_sysstat where inst_id = ''' + str(inst_id) + ''' and stat_name = ''' + stat_name + '''
                and snap_time > date_sub(now(),interval ''' + period + ''' hour) order by snap_time
                '''
    print(sql)
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute(sql)
    rs = cursor.fetchall()
    if len(rs) >10:
        l = []
        for x in rs:
            l.append([time.mktime(time.strptime(x[0],'%Y/%m/%d %H:%M:%S'))*1000,x[1]])
        #print l
    else:
        from utils.tools import init_data
        l = init_data(1)
    d = json.dumps(l)
    #print d
    return d
#====================================实时获取数据库负载信息===============================================================
@mod.route('/ora_load_json')
def ora_load_json():
    inst_id = request.args.get('id')
    stat_name = request.args.get('stat_name')
    sql = '''select date_format(snap_time,'%Y/%m/%d %H:%i:%s') snap_time,value_delta value
            from ora_sysstat_tmp where inst_id = ''' + str(inst_id) + '''
            and snap_time > date_sub(now(),interval 60 second) and stat_name = ''' + stat_name
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute(sql)
    rs = cursor.fetchall()
    if len(rs) > 0:
        l = [rs[0][0],rs[0][1]]
        l[0] = time.mktime(time.strptime(l[0],'%Y/%m/%d %H:%M:%S'))*1000
        d = json.dumps(l)
    else:
        ISOTIMEFORMAT='%Y/%m/%d %X'
        snap_time = time.strftime(ISOTIMEFORMAT, time.localtime())
        snap_time = time.mktime(time.strptime(snap_time,'%Y/%m/%d %H:%M:%S'))*1000
        #value = int(random.uniform(3000000,4000000))
        value = int(0)
        d = json.dumps([snap_time,value])
    return d

#===========================================等待事件监控==========================================================
@mod.route('/ora_event')
def ora_event():
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute('select id from ora_inst')
    rs_inst = cursor.fetchall()
    l_out = []
    for id in rs_inst:
        sql = '''select e.inst_id,i.host_name,i.inst_name,event_name,snap_time,total_waited_delta,wait_class
                from ora_sys_event_tmp e,ora_inst i
                where e.inst_id = i.id and i.id = ''' + str(id[0]) + '''
                order by total_waited_delta desc limit 5
              '''
        cursor.execute(sql)
        rs = cursor.fetchall()
        cursor.execute("select sum(total_waited_delta) from ora_sys_event_tmp e where e.inst_id = " + str(id[0]))
        rs2 = cursor.fetchall()
        total_waited = rs2[0][0]
        if total_waited ==0:
            total_waited = 1
        if len(rs) > 0:
            l_in = []
            for x in rs:
                d = {}
                waited_pct = str(round(x[5]*100/total_waited,2)) + '%'
                d['inst_id'],d['host_name'],d['inst_name'],d['event_name'] = x[0],x[1],x[2],x[3]
                d['snap_time'],d['total_waited_delta'],d['wait_class'],d['waited_pct']= x[4],x[5],x[6],waited_pct
                #print 'd=====================================',d
                l_in.append(d)
            l_out.append(l_in)
    cursor.close()
    db.close()
    return render_template('oracle/ora_event.html',entries=l_out,tag='等待事件')
    #return jsonify(result = l)
#===============================获取数据库实时等待事件信息=================================================================
@mod.route('/ora_event_detail')
def ora_event_detail():
    inst_id = request.args.get('inst_id', 0, type=int)
    tag = '等待事件'
    return render_template('oracle/ora_event_detail.html',**locals())
#================================初始化数据库等待事件信息=================================================================
@mod.route('/ora_event_json_init')
def ora_event_json_init():
    inst_id = request.args.get('id')
    chart_type = request.args.get('chart_type')
    #print 'begin_date======================',inst_id,'chart_type=====================',chart_type
    sql = ''' select event_name,total_waited_delta,date_format(snap_time,'%Y/%m/%d %H:%i:%s') from ora_sys_event_tmp
              where inst_id = ''' + str(inst_id) + ''' order by total_waited_delta desc limit 5'''
    #print sql
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute(sql)
    rs = cursor.fetchall()
    cursor.execute("select sum(total_waited_delta) from ora_sys_event_tmp e where e.inst_id = " + str(inst_id))
    rs2 = cursor.fetchall()
    total_waited = rs2[0][0]
    l = []
    if chart_type == "'pie'":
        for x in rs:
            if total_waited == 0:
                total_waited = 1
            #print "x[1]====",x[1],"total_waited=====",total_waited
            waited_pct = round(x[1]/total_waited*100,2)
            #l.append([x[0],x[1],x[2],time.mktime(time.strptime(x[3],'%Y/%m/%d %H:%M:%S'))*1000])
            l.append([(x[0] + '  ' + str(x[1]) + 's'),waited_pct,x[2]])
            #print l
    elif chart_type == "'column'":
        for x in rs:
            l.append([x[0],x[1]])
    else:
        pass
    d = json.dumps(l)
    #print d
    return d

#===========================查询某一时间段内的top 5等待事件================================================================
@mod.route('/ora_event_range', methods = ['GET', 'POST'])
def ora_event_range():
    if request.method == 'POST':
        inst_id,begin_date,end_date = request.form.get('inst_id'),request.form.get('begin_date'),request.form.get('end_date')
        return render_template('oracle/ora_event_range.html',**locals())
    elif request.method == 'GET':
        inst_id,period = request.args.get('inst_id'),request.args.get('period')
        end_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        begin_date = (datetime.datetime.now() - datetime.timedelta(minutes=int(period))).strftime('%Y-%m-%d %H:%M:%S')
        return render_template('oracle/ora_event_range.html',**locals())
        #return 'begin_time = ' + begin_date + 'end_time=' + end_date
    else:
        return 'error request!'

#===========================返回给定时间段内top 5等待事件信息的json函数==================================================
@mod.route('/ora_event_json_range')
def ora_event_json_range():
    inst_id = request.args.get('id')
    chart_type = request.args.get('chart_type')
    begin_date = request.args.get('begin_date')
    end_date = request.args.get('end_date')
    #print 'begin_date======================',inst_id,'chart_type=====================',chart_type
    sql = '''select  b.event_name,
                     case t.event_name when 'DB CPU' then (e.time_waited-b.time_waited)/1000000
                     else (e.time_waited-b.time_waited)/100 end as time_waited
            from  ora_sys_event b,
            		(select inst_id,event_name,min(snap_time) begin_time ,max(snap_time) end_time
            		from ora_sys_event
            		where
            				snap_time>=str_to_date(\'''' + begin_date + '''\','%Y-%m-%d %H:%i:%s')
            				and snap_time<=str_to_date(\'''' + end_date + '''\','%Y-%m-%d %H:%i:%s')
            				and inst_id = ''' + inst_id + '''
            		group by inst_id,event_name
            		 ) t,
            		ora_sys_event e
            where
            			b.event_name=t.event_name
            			and b.snap_time = t.begin_time
            			and b.inst_id = t.inst_id
            			and e.event_name=t.event_name
            			and e.snap_time=t.end_time
            			and e.inst_id=t.inst_id
            order by e.time_waited-b.time_waited desc limit 5 '''
    sql2 = '''select sum(time_waited)
                from
                	(select  b.event_name,b.snap_time begin_time,e.snap_time end_time,
                	case t.event_name when 'DB CPU' then (e.time_waited-b.time_waited)/1000000
                	else (e.time_waited-b.time_waited)/100 end as time_waited
                	from  ora_sys_event b,
                			(select inst_id,event_name,min(snap_time) begin_time ,max(snap_time) end_time
                			from ora_sys_event
                			where
                					snap_time>=str_to_date(\'''' + begin_date + '''\','%Y-%m-%d %H:%i:%s')
                            		and snap_time<=str_to_date(\'''' + end_date + '''\','%Y-%m-%d %H:%i:%s')
                            		and inst_id = ''' + inst_id + '''
                			group by inst_id,event_name
                			) t,
                			ora_sys_event e
                	where
                				b.event_name=t.event_name
                				and b.snap_time = t.begin_time
                				and b.inst_id = t.inst_id
                				and e.event_name=t.event_name
                				and e.snap_time=t.end_time
                				and e.inst_id=t.inst_id
                	) a'''
    #print sql
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute(sql)
    rs = cursor.fetchall()
    cursor.execute(sql2)
    rs2 = cursor.fetchall()
    total_waited = rs2[0][0]
    l = []
    if chart_type == "'pie'":
        for x in rs:
            if total_waited == 0:
                total_waited = 1
            waited_pct = round(x[1]/total_waited*100,2)
            #l.append([x[0],x[1],x[2],time.mktime(time.strptime(x[3],'%Y/%m/%d %H:%M:%S'))*1000])
            l.append([(x[0] + '  ' + str(x[1]) + 's'),waited_pct])
            #print l
    elif chart_type == "'column'":
        for x in rs:
            l.append([x[0],round(x[1],2)])
           #print "l=======================",l
    else:
        pass
    d = json.dumps(l)
    return d

#列出所有实例TOP SQL
@mod.route('/ora_top_sql',methods = ['GET', 'POST'])
def ora_top_sql():
    #根据请求类型构建查询sql，如果是get，则列出所有实例
    if request.method == 'GET':
        sk1 = request.args.get('sk1')
        sk2 = request.args.get('sk2')
        s_id = request.args.get('s_id')
        if s_id is None:
            sql1 = '''select id,inst_name from ora_inst order by ''' + sk2
        else:
            sql1 = '''select id,inst_name from ora_inst where id in (''' + s_id + ''') order by ''' + sk2
    elif request.method == 'POST':
        sk1 = 'buffer_gets_delta'
        sk2 = 'inst_name'
        host_name = request.form.get('host_name')
        inst_name = request.form.get('inst_name')
        sql1 = '''select id,inst_name from ora_inst where host_name like  \'%''' + host_name + '''%\'\
                  and inst_name like \'%''' + inst_name + '''%\''''
    else:
        sk1 = 'buffer_gets_delta'
        sk2 = 'inst_name'
        sql1 = '''select id,inst_name from ora_inst order by ''' + sk2
    print('sort_key = ' + sk1)
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute(sql1)
    rs_inst = cursor.fetchall()
    l_out = []
    #获取所有实例名列表，填充到下拉列表中
    l_inst = []
    cursor.execute('''select inst_name from ora_inst''')
    rs_iname = cursor.fetchall()
    for x in rs_iname:
        l_inst.append(x[0])
    print(l_inst)
    #开始获取每个实例的top 5 sql
    l_id = []
    for id in rs_inst:
        l_id.append(id[0])
        sql2 = '''select i.id,i.host_name,i.inst_name,t.sql_id,t.sql_text,t.disk_reads_delta,
                t.buffer_gets_delta,t.cpu_time_delta,t.elapsed_time_delta,t.user_io_wait_time_delta,t.executions_delta,
                t.rows_processed_delta,t.snap_time from ora_inst i,ora_top_sql_tmp t
                where i.id = t.inst_id and i.id = ''' + str(id[0]) + ''' order by ''' + sk1 + ''' desc limit 5'''
        cursor.execute(sql2)
        rs = cursor.fetchall()
        if len(rs) == 0:
            #print('rs ========None')
            continue
        l_in = []
        for x in rs:
            d = {}
            d['inst_id'],d['host_name'],d['inst_name'],d['sql_id'],d['sql_text'] = x[0],x[1],x[2],x[3],x[4]
            d['disk_reads_delta'],d['buffer_gets_delta'],d['cpu_time_delta'] = x[5],x[6],x[7]
            d['elapsed_time_delta'],d['user_io_wait_time_delta'],d['executions_delta'] = x[8],x[9],x[10]
            d['rows_processed_delta'],d['snap_time'] = x[11],x[12]
            l_in.append(d)
        l_out.append(l_in)
    s_id = ''
    for i in l_id:
        s_id = s_id + str(i) + ','
    s_id = s_id[:-1]
    entries = l_out
    tag = 'TOP SQL'
    #return render_template('oracle/ora_top_sql.html', entries=l_out, tag='TOP SQL',sk1 = sk1,sk2 = sk2)
    return render_template('oracle/ora_top_sql.html', **locals())
#############################################################################################################
#获取单个实例的top sql 实时数据
@mod.route('/ora_top_sql_detail',methods = ['GET', 'POST'])
def ora_top_sql_detail():
    #根据请求类型构建查询sql，如果是get，则列出所有实例
    if request.method == 'GET':
        sk1 = request.args.get('sk1')
        sk2 = request.args.get('sk2')
        inst_id = request.args.get('inst_id')
        sql1 = '''select i.id,i.host_name,i.inst_name,t.sql_id,substring(t.sql_text,1,30) sql_text,
                t.disk_reads_delta,t.sql_text sql_full_text,
                t.buffer_gets_delta,round(t.cpu_time_delta/1000000,2) cpu_time_delta,round(t.elapsed_time_delta/1000000,2) elapsed_time_delta,t.user_io_wait_time_delta,t.executions_delta,
                t.rows_processed_delta,t.snap_time from ora_inst i,ora_top_sql_tmp t
                where i.id = t.inst_id and i.id = ''' + str(inst_id) + ''' order by ''' + sk1 + ''' desc limit 10'''
    elif request.method == 'POST':
        sk1 = 'buffer_gets_delta'
        sk2 = 'inst_name'
        inst_id = request.form.get('inst_id')
        sql1 = '''select i.id,i.host_name,i.inst_name,t.sql_id,substring(t.sql_text,1,30) sql_text,
            t.disk_reads_delta,t.sql_text sql_full_text,
            t.buffer_gets_delta,round(t.cpu_time_delta/1000000,2) cpu_time_delta,round(t.elapsed_time_delta/1000000,2) elapsed_time_delta,t.executions_delta,
            t.rows_processed_delta,t.snap_time from ora_inst i,ora_top_sql_tmp t
            where i.id = t.inst_id and i.id = ''' + str(inst_id) + ''' order by ''' + sk1 + ''' desc limit 5'''
    else:
        sk1 = 'buffer_gets_delta'
        sk2 = 'inst_name'
        sql1 = '''select id,inst_name from ora_inst order by ''' + sk2
    #print(sql1)
    db = conn_mysql()
    cursor = db.cursor()
    cursor.execute(sql1)
    rs = cursor.fetchall()
    tag,inst_name = 'TOP SQL',rs[0]['inst_name']
    #for k in rs:
        #print('key ===',k,'**********')
    return render_template('oracle/ora_top_sql_detail.html',**locals())
#############################################################################################################
#查询某一时间段内实例的top sql信息
@mod.route('/ora_top_sql_range', methods = ['GET', 'POST'])
def ora_top_sql_range():
    if request.method == 'POST':
        sk1 = request.form.get('sk1')
        sk2 = request.form.get('sk2')
        print("sk1=======",sk1,"sk2========",sk2)
        inst_id,begin_date,end_date = request.form.get('inst_id'),request.form.get('begin_date'),request.form.get('end_date')
        print('inst_id====',inst_id,'begin_date====',begin_date,'end_date=====',end_date)
    elif request.method == 'GET':
        sk1 = request.args.get('sk1')
        sk2 = request.args.get('sk2')
        period = request.args.get('period')
        begin_date = request.args.get('begin_date')
        end_date = request.args.get('end_date')
        print("sk1=======",sk1)
        inst_id,period = request.args.get('inst_id'),request.args.get('period')
        if period is not None and (begin_date is None and end_date is None):
            end_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            begin_date = (datetime.datetime.now() - datetime.timedelta(minutes=int(period))).strftime('%Y-%m-%d %H:%M:%S')
        #return 'begin_time = ' + begin_date + 'end_time=' + end_date
    else:
        return 'error request!'

    sql1 = '''select t.sql_id,substring(t.sql_text,1,30) sql_text,t.sql_text sql_full_text,
    sum(t.disk_reads_delta) disk_reads_delta,
    sum(t.buffer_gets_delta) buffer_gets_delta,round(sum(t.cpu_time_delta)/1000000,2) cpu_time_delta,
    round(sum(t.elapsed_time_delta)/1000000,2) elapsed_time_delta,sum(t.user_io_wait_time_delta) user_io_wait_time_delta,
    sum(t.executions_delta) executions_delta,
    sum(t.rows_processed_delta) rows_processed_delta from ora_top_sql t
    where t.inst_id = ''' + str(inst_id) + ''' and snap_time>=str_to_date(\'''' \
           + begin_date + '''\','%Y-%m-%d %H:%i:%s') and snap_time<=str_to_date(\'''' \
           + end_date + '''\','%Y-%m-%d %H:%i:%s') group by t.sql_id,substring(t.sql_text,1,40),t.sql_text \
    order by ''' + sk1 + ''' desc limit 10'''
    db = conn_mysql()
    cursor = db.cursor()
    cursor.execute(sql1)
    rs = cursor.fetchall()
    cursor.execute('select inst_name from ora_inst where id = ' + str(inst_id))
    rs2 = cursor.fetchall()
    inst_name = rs2[0]['inst_name']
    tag = 'TOP SQL'
    return render_template('oracle/ora_top_sql_detail_range.html', **locals())
##############################################################################################################
#TOP sql 详情(sql执行计划，趋势分析)
@mod.route('/ora_top_sql_report', methods = ['GET', 'POST'])
def ora_top_sql_report():
    if request.method == 'GET':
        period = request.args.get('period')
        tick = request.args.get('tick')
        print('ora_top_sql_report:period========',period,tick)
        inst_id,sql_id = request.args.get('inst_id'),request.args.get('sql_id')
        print('sql_id========',sql_id)
        sql1 = ''' select sql_id,phv,sql_text,buffer_gets_delta,disk_reads_delta,
            cpu_time_delta,elapsed_time_delta,executions_delta,user_io_wait_time_delta,
            rows_processed_delta,snap_time from ora_top_sql
            where sql_id =\'''' + sql_id + '''\'
            and snap_time > date_sub(now(),interval ''' + period + ''' hour) order by snap_time desc'''
        sql2 = '''select * from
	            (select sql_id,child_number,row_number() over(partition by plan_hash_value
	             order by child_number) rn
	             from v$sql where sql_id=\'''' + sql_id + '''\')
                 where rn=1'''
        db = conn_mysql()
        cursor = db.cursor()
        cursor.execute(sql1)
        rs_td = cursor.fetchall()
        #连接到oracle数据库
        dbora = conn_ora(inst_id)
        curora = dbora.cursor()
        # 获取该sql不同plan_hash_value的child_number
        curora.execute(sql2)
        rs_chdno = curora.fetchall()
        #获取该sql所有执行计划
        l_plan = []
        for x in rs_chdno:
            l_rs = []
            sql_id,chdno= x[0],x[1]
            sql3 = '''select * from table(dbms_xplan.display_cursor(\'''' + sql_id + '''\',''' + str(chdno) + '''))'''
            #sql3 = '''select * from table(dbms_xplan.display_cursor('7b2twsn8vgfsc',0))'''
            curora.execute(sql3)
            rs_plan = curora.fetchall()
            #print('rs_plan**********&&&&&&&&&&&&&&&&',rs_plan)
            for x in rs_plan:
                l_rs.append(x[0].replace(' ','&nbsp;'))
                #l_rs.append(x[0])
            l_plan.append(l_rs)
        #获取相关对象(表和索引)的统计信息
        print(l_plan)
    return render_template('oracle/ora_top_sql_report.html', **locals())

##############################################################################################################
#获取sql执行趋势统计数据
@mod.route('/ora_top_sql_json')
def ora_top_sql_json():
    inst_id = request.args.get('id')
    period = request.args.get('period')
    sql_id = request.args.get('sql_id')
    if period == 'None':
        period = '1'
    stat_name = request.args.get('stat_name')
    #print('period==============************************', period,stat_name)
    if '|' in period:
        begin_date,end_date = period.split('|')[0],period.split('|')[1]

        sql ='''select date_format(snap_time,'%Y/%m/%d %H:%i:%s') snap_time,value_delta value
                from ora_sysstat
                where inst_id = ''' + str(inst_id) + ''' and stat_name = ''' + stat_name + '''
                    and snap_time>=str_to_date(\'''' + begin_date + '''\','%Y-%m-%d %H:%i:%s')
                    and snap_time<=str_to_date(\'''' + end_date + '''\','%Y-%m-%d %H:%i:%s')
	            order by snap_time
            '''
    else:
        sql = ''' select date_format(snap_time,'%Y/%m/%d %H:%i:%s') snap_time,''' + stat_name + ''' value
                from ora_top_sql where inst_id = ''' + str(inst_id) + ''' and sql_id = ''' + sql_id + '''
                and snap_time > date_sub(now(),interval ''' + period + ''' hour) order by snap_time
                '''
    db = conn_mysql_l()
    cursor = db.cursor()
    cursor.execute(sql)
    rs = cursor.fetchall()
    if len(rs) >1:
        l = []
        for x in rs:
            l.append([time.mktime(time.strptime(x[0],'%Y/%m/%d %H:%M:%S'))*1000,x[1]])
        #print l
    else:
        #from utils.tools import init_data
        #l = init_data(1)
        l = []
    d = json.dumps(l)
    #print d
    return d

##############################################################################################################
#监控指标管理
@mod.route('/ora_mon_target')
def ora_mon_target():
    if session.get('logged_in'):
        username = session['username']
        tag = '监控指标'
        db = conn_mysql()
        cursor = db.cursor()
        sql = '''select a.id,a.class,a.type,a.name,a.enable,a.level1,a.level2,a.level3,a.target_type
                from ora_alert_define a where inst_id=0 order by class,type'''
        cursor.execute(sql)
        entries = cursor.fetchall()
        print(entries)
        cursor.close()
        db.close()
        return render_template('oracle/ora_mon_target.html',**locals())
    else:
        return render_template('login.html')