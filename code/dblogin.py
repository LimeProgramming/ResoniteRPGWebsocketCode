"""
Basic info on how to connect to the PostgreSQL database backend. 

You will need two databases (for now) A production database and a testing database. 
 
- Calamity Lime
"""

_user = 'websock'
_pwrd = '12345678'
_name = 'neos2' 
_nametest = 'neos2_test'
_host = '192.168.1.12'
_port = 5432


# Our database login info thingie
DBCRED      = {"user": _user, "password": _pwrd, "database": _name,        "host": _host, "port": _port}
TESTDBCRED  = {"user": _user, "password": _pwrd, "database": _nametest,    "host": _host, "port": _port}