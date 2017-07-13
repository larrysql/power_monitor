declare
id number;
begin
while 1=1 loop
select count(*) into id from test; 
delete from test where rownum<=10;
insert into test select * from test where rownum<=10;
commit;
dbms_lock.sleep(0.01);
end loop;
end;
/
