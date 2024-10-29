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


class PlayerLoadError(Exception):
    pass

class ConnectionType(Enum):
    PRODUCTION  = 0
    TEST        = 1

class State(Enum):
    DISCONNECT  = 1
    CONNECTED   = 2


CONNECTIONS = set()
#VALIDRECCMDS =  set(['echo', 'saveplayer', 'loadplayer'])
VALIDSENDCMDS = set(['heartbeat', 'echo', 'savedplayer','loadedplayer', 'error'])


#VALIDSENDCMDS = {'heartbeat', 'echo', 'savedplayer','loadedplayer'}


VALIDRECCMDS =  {'echo':'run_cmd_echo', 'saveplayer':'run_cmd_saveplayer', 'loadplayer':'run_cmd_loadplayer'}



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

    async def recv(self) -> str:
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
                self.db_conn = await asyncpg.connect(**dblogin.DBCRED)
            else:
                self.db_conn = await asyncpg.connect(**dblogin.TESTDBCRED)

            for type in ("json", "jsonb"):
                await self.db_conn.set_type_codec(type, encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

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
        
        # Connect to the database
        await self.connect_to_db()

        # Spin off the listener to a continuously running task
        asyncio.get_event_loop().create_task(self.listener())

        return True
    
    async def listener(self):
        """This is our main listener thread for our clients"""

        try:
            async for message in self.websocket:
                
                # Split the message into COMMAND + ARGS
                cmdpack = ((message).strip()).split('λ')
                
                # Test if the message received is valid 
                if len(cmdpack) != 2 or cmdpack[0] not in VALIDRECCMDS.keys():
                    continue

                # Fetch the command from self
                run_cmd = getattr(self, VALIDRECCMDS[cmdpack[0]], "Invalid")
                
                # Won't get here if the if is true but just in case
                if run_cmd == "Invalid":
                    continue
                
                # Run the command
                await run_cmd(cmdpack[1])
                
        except (ValueError, TypeError):
            await self.send('errorλValueTypeError')
        
        except PlayerLoadError:
            await self.send("loadedplayerλerror")
                
        except websockets.exceptions.ConnectionClosed:
            await aprint(f'connection closed')
            await unregister_client(self)

        except:
            traceback.print_exc()
            await unregister_client(self)
            
            
    async def run_cmd_echo(self, args):
        return


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

    
    async def check_valid_packet(string, length=2) -> bool:
        """Checks if the Command received is valid"""
        
        pack = len(string.split('-'))

        return ((pack[0] in VALIDRECCMDS) and len(pack) == length)
    


    # ============================== Database Commands ==============================

    async def run_cmd_echo(self, args):
        """This the echo command, just send back what the client said"""

        await self.send(f"echoλ{args}")
        return

    async def run_cmd_saveplayer(self, args):
        """Save player data to database"""

        pack = args.split('-')

        await aprint("")

        #round(answer, 2))

        return

    async def run_cmd_loadplayer(self, player_id):
        """Read player data from database"""

        # ===== If player does not exist, create them and return to Resonite with 
        if not await self.db_conn.fetchval(pgCmds.PLAYER_EXISTS, player_id):

            # === If the reso ID is not formatted correctly
            if not (player_id.lower()).startswith('u-'):
                raise PlayerLoadError

            # === Create player
            await self.db_conn.execute(pgCmds.CREATE_PLAYER, player_id) 

            # === Tell resonite that we have created a player
            await self.send(f"loadedplayerλ1λ{player_id}")

            # === Return to Resonite 
            return
        



        wdata = await self.db_conn.fetchrow(pgCmds.FETCH_WORLD_DATA, player_id)

        # ===== If world data for player does not exist, ask resonite for it
        if wdata is None or self.worldname not in wdata:

            # === Send Resonite loadedplayer message 2
            await self.send(f"loadedplayerλ2λ{player_id}")

            # === Wait for response from Resonite
            data = await self.recv()
            await aprint(data)

            # === X - Y - Z
            xpos, ypos, zpos = data.split(',')

        # ===== Else there is data and we must fetch it
        else:
            xpos, ypos, zpos = wdata[self.worldname]


        

        # Maybe send player inventory here?



        # ===== Fetch the normal player data
        ply_name, ply_profession, pre_world, max_health, health, hit_multi, level, agility = await self.db_conn.fetchrow(pgCmds.FETCH_PLAYER_DATA, player_id)

        # ===== Do some rounding, for now
        max_health= round(max_health,4)
        health =    round(health,4)
        hit_multi = round(hit_multi,4)

        # ===== Send Player Data
        await self.send(f"loadedplayerλ3λ{player_id},{ply_name},{ply_profession},{pre_world},[{xpos};{ypos};{zpos}],{max_health},{health},{hit_multi},{agility},{level}")

        return







## Websockets does a fun register handler thing so we need to run them in an infinite loop else they will close
async def register_client(websocket, _):
    """
    Register our newly connect client, this will basically spin up a new websocket server just for the client
    Doing it this way helps save on managing client ID-ing
    """

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
                await connection.send('heartbeat-heartbeat')

        await asyncio.sleep(15)


