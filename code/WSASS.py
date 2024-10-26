"""
Websocket Server aimed to work with an RPG world on Resonite

- Calamity Lime
"""

# ~~~===== Python imports =====~~~ #
import json
import asyncio
import asyncpg
import websockets
import traceback
from enum import Enum

from concurrent.futures import TimeoutError as ConnectionTimeoutError

# ~~~===== Custom lib imports =====~~~ #
import dblogin
from util import aprint
from databasecmds import DatabaseCmds as pgCmds



class ConnectionType(Enum):
    PRODUCTION  = 0
    TEST        = 1

class State(Enum):
    DISCONNECT  = 1
    CONNECTED   = 2


CONNECTIONS = set()



class WebsocketServerAssignee:
    """CONNECTION HANDLER CLASS"""

    db_conn = None
    websocket = None
    worldname = None
    connection_type = None
    state = State.DISCONNECT
    

    def __init__(self, websocket):
        self.websocket = websocket

    async def send(self, message):
        """Send messages to our clients"""

        try:
            await self.websocket.send(message)
        except:
            traceback.print_exc()

    async def recv(self):
        """Get messages from our clients"""

        try:
            message = await self.websocket.recv()
            return message
        except:
            traceback.print_exc()

    async def connect_to_db(self):
        """Establish a connection to the PostgreSQL database when a client connects."""

        try:
            if self.connection_type == ConnectionType.PRODUCTION:
                db_conn = await asyncpg.connect(**dblogin.DBCRED)
            else:
                db_conn = await asyncpg.connect(**dblogin.TESTDBCRED)

            for type in ("json", "jsonb"):
                await db_conn.set_type_codec(type, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

        except Exception as e:
            traceback.print_exc()
            await aprint("Failed to connect to database")
            await aprint(e)
            return False
        
        return True


    async def welcome(self) -> bool:
        """First function called when a new client connects to our server. 

        Process Client Handshake
        """
        
        # ===== Capture client handshake message received 
        client_handshake = ((await self.recv()).lower()).strip() 
        
        # ===== Split the client handshake into parts
        # ORDER: client type -~~- dupes allowed -~~- world connection
        handshake_part = client_handshake.split(',')


        # ---------- Connection Type Setting ----------
        # Check that the client type is expected.
        if      handshake_part[0] == "test":
            self.connection_type = ConnectionType.TEST
        elif    handshake_part[0] == "production":
            self.connection_type = ConnectionType.PRODUCTION
        else:
            return False


        # ---------- Duplicate Connection testing ----------
        # Basically check if duplicate connection trusting client to allow to deny a duplicate connection

        if handshake_part[1] == 'unique':

            world = handshake_part[2]       # World Connection as part of handshake
            undecided = True         
            conflict = False

            while undecided:

                for con in CONNECTIONS:
                    if world == con.worldname and self.connection_type == con.connection_type:
                        conflict = True

                undecided = conflict

                if undecided:
                    await self.send("ERROR0x01")
                    world = ((await self.recv()).lower()).strip()  

            self.worldname = world
        
        else: # END if handshake_part[1] == 'unique':
            self.worldname = handshake_part[2]


        # ---------- END handshaking ----------
        # Set State to Connected    
        self.state = State.CONNECTED

        # Tell Client it is connected
        await self.send('LOG0x01')

        # Spin off the listener to a continuously running task
        asyncio.get_event_loop().create_task(self.listener())

        return True
    

    async def listener(self):
        """This is our main listener thread for our clients 
        
        It's a little dodgy but look, it'll do
        """
        try:
            async for message in self.websocket:

                message = (message.lower()).strip() 

                if message.startswith("echo-"):
                    await self.send(message)
                elif message.startswith("save-"):
                    asyncio.sleep(0)
                elif message.startswith("load-"):
                    asyncio.sleep(0)
                
        except websockets.exceptions.ConnectionClosed:
            print(f'connection closed')
            await unregister_client(self)
        except:

            traceback.print_exc()
            await unregister_client(self)
            

    async def close(self):
        """Close the client connection and the database connection"""

        self.state = State.DISCONNECT
        try:
            # Close the database connection
            if self.db_conn: 
                await self.db_conn.close()

            # Close the websocket
            await self.websocket.close()
        except:
            traceback.print_exc()






## Websockets does a fun register handler thing so we need to run them in an infinite loop else they will close
async def register_client(websocket, _):
    connection = WebsocketServerAssignee(websocket)
    done = False

    while True:
        if not done:
            if await connection.welcome():
                CONNECTIONS.add(connection)
                done = True

        await asyncio.sleep(0.001)


async def unregister_client(connection):
    """Close a websocket client and remove from our connections set"""

    await connection.close()

    try:
        CONNECTIONS.remove(connection)
    except:
        traceback.print_exc()

    return

async def ws_heartbeat():
    """Heartbeat pulse we can send to our websocket clients for very important purposes"""

    while True:

        for connection in CONNECTIONS:
            if connection.state == State.CONNECTED and connection.connection_type == ConnectionType.PRODUCTION:
                await connection.send('heartbeat')

        await asyncio.sleep(15)


