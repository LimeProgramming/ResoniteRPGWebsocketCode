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
from util import aprint
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


    ### ===== Production Database
    for dbTables in database_tables:
        if not await db_conn.fetchval(getattr(pgCmds, dbTables['exists'])):
            await db_conn.execute(getattr(pgCmds, dbTables['create']))
            await aprint(f" {dbTables['log']}")

    #### ===== Test Database
    for dbTables in database_tables:
        if not await db_conn_test.fetchval(getattr(pgCmds, dbTables['exists'])):
            await db_conn_test.execute(getattr(pgCmds, dbTables['create']))
            await aprint(f" {dbTables['log']}")



    # ============================== BLOATED TEST CODE ==============================

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

    
    ply_num, user, client, health, hit_multi, timestamp = await db_conn.fetchrow("SELECT * FROM public.player WHERE reso_id = CAST($1 AS VARCHAR)", "U-Medra")


    if 'horny_hill' not in client:
        client['horny_hill'] = {'x' : 6, 'y' : 7, 'z' : 8}
        
        await db_conn.execute("UPDATE public.player SET client_data = $1::JSONB WHERE reso_id = $2", client, 'U-Medra')

    print(client['horny_field']['x'])

    #client.keys()


    # ============================== MESSAGES TABLE ==============================
    CREATE_MSGS_TABLE =""" 
        CREATE TABLE IF NOT EXISTS messages (
            msg_id      BIGINT      PRIMARY KEY,
            ch_id       BIGINT      NOT NULL,
            guild_id    BIGINT      NOT NULL,
            auth_id     BIGINT,
            timestamp   TIMESTAMP   NOT NULL    DEFAULT (NOW() AT TIME ZONE 'utc'),
            num         BIGSERIAL
            ); 

        COMMENT ON TABLE messages is             'This table stores some basic information about messages sent on the server. It keeps a log of messages which have been deleted from the guild.';
        COMMENT ON COLUMN messages.msg_id is     'Discord id of the sent message.'; 
        COMMENT ON COLUMN messages.ch_id is      'Channel id of the message was posted in.';
        COMMENT ON COLUMN messages.guild_id is   'Note of the guild the message was posted in. Useful for API calls.';
        COMMENT ON COLUMN messages.auth_id is    'Discord id of the messages sender.';
        COMMENT ON COLUMN messages.timestamp is  'UTC timestamp of when the message was created.';
        COMMENT ON COLUMN messages.num is        'The serial number of the message id sent.';
        """ 
    

    #if not await db.fetchval(getattr(pgCmds, dbTables['exists'])):

    await db_conn.execute(CREATE_MSGS_TABLE)
    await db_conn.close()

    #await aprint("end of test")

    #return False

    return True






# ======================================== MAIN ========================================
# ======================================== MAIN ========================================
# ======================================== MAIN ========================================

async def main():


    # ---------- CONNECT TO AND PRIME THE POSTGRE DATABASE ----------
    try:
        if not (await pgdb_setup_database()):
            return
    except Exception as e:
        print(e)
        return

    await aprint("test")




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
