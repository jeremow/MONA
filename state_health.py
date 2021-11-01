import cx_Oracle

dsn_tns = cx_Oracle.makedsn('Host Name', 'Port Number', service_name='Service Name')
conn = cx_Oracle.connect(user=r'User Name', password='Personal Password', dsn=dsn_tns)

c = conn.cursor()
c.execute('select * from database.table') # use triple quotes if you want to spread your query across multiple lines
for row in c:
    print (row[0], '-', row[1])
#conn.close()