"""
Websocket Server aimed to work with an RPG world on Resonite

- Calamity Lime
"""

# ~~~===== Python imports =====~~~ #
import csv
import json
import asyncio
import asyncpg
import websockets
import traceback


# ~~~===== Custom lib imports =====~~~ #
import dblogin
from util import aprint, lprint
from databasecmds import DatabaseCmds as pgCmds
from WSASS import register_client, ws_heartbeat



# ======================================== Database Setup========================================
async def pgdb_setup_database() -> bool:

    # ===== My precious variables
    db_conn         = None
    db_conn_test    = None

    # ===== Our try and catch for connections to the database
    try:
        # === PROD
        db_conn = await asyncpg.connect(**dblogin.DBCRED)

        for type in ("json", "jsonb"):
            await db_conn.set_type_codec(type, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

        # === TEST
        db_conn_test = await asyncpg.connect(**dblogin.TESTDBCRED)

        for type in ("json", "jsonb"):
            await db_conn_test.set_type_codec(type, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

    except Exception as e:
        await aprint("Failed to connect to database")
        await aprint(e)
        traceback.print_exc()
        return False


    # ============================== INIT TABLES ==============================


    # ===== CREATE DATABASE TABLES AT STARTUP
    database_tables = [
        {'exists':'EXISTS_PLRS_TABLE',          'create':'CREATE_PLRS_TABLE',           'log':'Created Players table.'}
    ]

    database_functions = [
        {'exists':'EXISTS_FUNC_GETWORLDINFO',   'create':'CREATE_FUNC_GETWORLDINFO',    'log':'Created GET WORLD INFO Function.'},
        {'exists':'EXISTS_FUNC_HASWORLDINFO',   'create':'CREATE_FUNC_HASWORLDINFO',    'log':'Created HAS WORLD INFO Function.'}
    ]


    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ### ===== Production Database
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    ### ===== Create Tables
    for dbTables in database_tables:
        if not await db_conn.fetchval(getattr(pgCmds, dbTables['exists'])):
            await db_conn.execute(getattr(pgCmds, dbTables['create']))
            await aprint(f" {dbTables['log']}")

    
     ### ===== Create Functions
    for dbfuncs in database_functions:
        if not await db_conn.fetchval(getattr(pgCmds, dbfuncs['exists'])):
            await db_conn.execute(getattr(pgCmds, dbfuncs['create']))
            await aprint(f" {dbfuncs['log']}")



    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ### ===== Test Database
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    ### === Create Tables
    for dbTables in database_tables:
        if not await db_conn_test.fetchval(getattr(pgCmds, dbTables['exists'])):
            await db_conn_test.execute(getattr(pgCmds, dbTables['create']))
            await aprint(f" {dbTables['log']}")
            

     ### ===== Create Functions
    for dbfuncs in database_functions:
        if not await db_conn_test.fetchval(getattr(pgCmds, dbfuncs['exists'])):
            await db_conn_test.execute(getattr(pgCmds, dbfuncs['create']))
            await aprint(f" {dbfuncs['log']}")


    
    # ============================== BLOATED TEST CODE ==============================

    
    return True

    data = {
        'test1': {
            'x': 5,
            'y': 0,
            'z': 5
        }
    }
    
    await db_conn_test.execute("UPDATE public.players SET world_data = $1::JSONB WHERE reso_id = $2", data, 'U-Calamity-Lime')


    #testval = await db_conn_test.fetchval("SELECT hasWorldInfo($1, $2);", 'U-Calamity-Lime', 'test1')


    testval = await db_conn_test.fetchval(pgCmds.EXISTS_WORLD_DATA, 'U-Calamity-Lime', 'test1')


    print(testval)


    xpos, ypos, zpos = (await db_conn_test.fetchval(pgCmds.FETCH_WORLD_DATA, 'U-Calamity-Lime', 'test1')).values()

    print(xpos)
    print(ypos)
    print(zpos)


    data = {
        'horny_meadow': {
            'x': 0,
            'y': 1,
            'z': 2
        },
        'horny_field': {
            'x': 3,
            'y': 4,
            'z': 5
        }
    }


    #res = await db_conn.execute(ADD_MSG, "U-Medra", data, 20, 1)

    
    #ply_num, user, client, health, hit_multi, timestamp = await db_conn.fetchrow("SELECT * FROM public.player WHERE reso_id = CAST($1 AS VARCHAR)", "U-Medra")


    #if 'horny_hill' not in client:
    #    client['horny_hill'] = {'x' : 6, 'y' : 7, 'z' : 8}
        
    #    await db_conn.execute("UPDATE public.player SET client_data = $1::JSONB WHERE reso_id = $2", client, 'U-Medra')

    #print(client['horny_field']['x'])


    await db_conn.close()


    print("End test")
    return False


    return True






# ======================================== MAIN ========================================
# ======================================== MAIN ========================================
# ======================================== MAIN ========================================

async def main():


    # ---------- CONNECT TO AND PRIME THE POSTGRESQL DATABASE ----------
    try:
        if not (await pgdb_setup_database()):
            return
    except Exception as e:
        print(e)
        return



    # ==============================
    # put some database setup stuff here
    # ==============================


    # Start the WebSocket server and await its completion
    server = await websockets.serve(register_client, "localhost", 8765) 

    # Create task for heartbeat monitoring
    heartbeat = asyncio.create_task( ws_heartbeat() )
    
    # Use `gather` to run both the WebSocket server and the heartbeat task
    await asyncio.gather(heartbeat, server.wait_closed())



if __name__ == '__main__':
    asyncio.run(main())
