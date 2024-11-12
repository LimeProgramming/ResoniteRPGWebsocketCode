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

    #test_data = """[{"UUID": "c-6470b785-9358-49dc-a852-72efdf1db046", "elements": [{"UUID": "c-0557cec6-451c-45e4-8934-3f3fedc21d5b", "elements": [{"UUID": "I-58aa5374-59eb-4e7c-a8ef-6c0da03e5232", "data": {"Float1": 5.5556 ,"test": false ,"test3": false }},{"UUID": "i-206a9122-5537-4c33-a5ce-a0639a22f531", "data": {"gggg": false ,"hhhh": "hhyy" ,"hhyy": "" ,"ggggg": "jgjgjgjg" }},{"UUID": "I-49711bda-c2fc-4b6e-a4b7-07fded56421f", "data": {}},{"UUID": "I-82864ef2-3972-4f30-8223-7932ba0f1862", "data": {}}]}, {"UUID": "c-8eaec9b5-1926-4543-9688-0d3797d6422e", "elements": [{"UUID": "I-c6900b63-f084-4000-8d89-6479455fbe00", "data": {}}]}, {"UUID": "c-6bea58b3-38ff-4c86-8d8c-74fc8cdf2d4b", "elements": [{"UUID": "I-38e18230-b1c0-4edd-9070-caac44d89c94", "data": {}}]}]},{"UUID": "c-8ff528de-22d3-4062-b943-e73a2482cad9", "elements": [{"UUID": "c-c12fb0ef-0cb7-4791-ba93-63783d745306", "elements": [{"UUID": "I-bc913285-9f3d-4070-850e-90d4fd65a473", "data": {}}]}, {"UUID": "c-58ae3fe6-3576-4b83-b12f-269c1e3cd590", "elements": [{"UUID": "I-f86d06f3-6549-4799-85bd-d9f2fd640db9", "data": {}}]}]},{"UUID": "c-e437ad2d-bd54-4dd3-8c9b-af65e9f2eb0c", "elements": [{"UUID": "I-ea04827f-d271-4b85-91a5-fee2cba2e6f5", "data": {}}]}]"""

    #test_dict = json.loads(test_data)

    #await db_conn_test.execute("UPDATE public.players SET inventory = $1::JSONB WHERE reso_id = $2", test_dict, 'U-Calamity-Lime')


    records = await db_conn_test.fetch(pgCmds.FETCH_INV_ITEMS, 'U-Calamity')

    #<Record uuid='c-0557cec6-451c-45e4-8934-3f3fedc21d5b' elements=
    #   [
    #       {'UUID': 'I-58aa5374-59eb-4e7c-a8ef-6c0da03e5232', 'data': {'test': False, 'test3': False, 'Float1': 5.5556}}, 
    #       {'UUID': 'i-206a9122-5537-4c33-a5ce-a0639a22f531', 'data': {'gggg': False, 'hhhh': 'hhyy', 'hhyy': '', 'ggggg': 'jgjgjgjg'}}, 
    #       {'UUID': 'I-49711bda-c2fc-4b6e-a4b7-07fded56421f', 'data': {}}, 
    #       {'UUID': 'I-82864ef2-3972-4f30-8223-7932ba0f1862', 'data': {}}
    #   ]>

    #print(len(records))



    data = ''

    for record in records:

        for item in record['elements']:
            data = ''

            if len(item['data']) > 0:
                data = ':>'.join([f'{key}:~{value}' for key, value in item['data'].items()])

            print(':¬'.join([record['uuid'], item['UUID'], data]))

            



#children_uuids = ",".join(child['UUID'] for child in record['elements'])

    print("End test")
    return False
    
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

    await db_conn.close()


    print("End test")
    return False


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
