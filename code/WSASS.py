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
from util import aprint, lprint, dprint, eprint
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
    

    # ============================== Core Functions ==============================

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


    
    # ============================== Listeners ==============================

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

        # Poor mans logging
        await lprint("Client {} Connected".format(len(CONNECTIONS) + 1))

        # Spin off the listener to a continuously running task
        asyncio.get_event_loop().create_task(self.listener())

        return True
    

    async def listener(self):
        """This is our main listener thread for our clients"""

        #valid, command, args = [None, None, None]

        try:
            async for message in self.websocket:

                #await dprint(f"message {message}")
                
                # Test if the message received is valid + Split the message into COMMAND + ARGS
                valid, command, args = await self.cmd_packet_analysis((message.strip()), delim='λ')

                #await dprint(f"ret {valid}, {command}, {args}")

                # If it is not a valid command
                if not valid or command not in VALIDRECCMDS.keys():
                    continue
                
                # Fetch the command from self
                run_cmd = getattr(self, VALIDRECCMDS[command], "Invalid")    

                # Won't get here if the if is true but just in case
                if run_cmd == "Invalid":
                    continue
                
                try: 
                    # 5 Second Timeout
                    async with asyncio.timeout(1):

                        # Run the command
                        await run_cmd(args)
                
                except (ValueError, TypeError):
                    await self.send('errorλValueTypeError')
                
                except PlayerLoadError:
                    await self.send("errorλ1λerror")
                    #await self.send("loadedplayerλ10λeerror")
                
                except asyncio.TimeoutError:
                    await self.send("errorλ1λerror")
                    #await self.send("loadedplayerλ10λeerror")
                    await lprint(f"Timeout Error on: {VALIDRECCMDS[command]}")

        # ===== Header Try     
        except websockets.exceptions.ConnectionClosed:
            await aprint(f'connection closed')
            await unregister_client(self)

        except:
            traceback.print_exc()
            await unregister_client(self)
            


    # ============================== RPG Loader Commands ==============================
    
    async def run_cmd_echo(self, args):
        """This the echo command, just send back what the client said"""

        await self.send(f"echoλ{args}")

        return


    async def run_cmd_saveplayer(self, player_id):
        """Save player data to database"""

        # ====================
        # Save player Step 1
        # Test if player exists in Database and Create them if not

        # ===== If player does not exist, create them and return to Resonite with 
        if not await self.db_conn.fetchval(pgCmds.PLAYER_EXISTS, player_id):

            # === If the reso ID is not formatted correctly
            if not (player_id).startswith('U-'):
                raise PlayerLoadError

            # === Create player
            await self.db_conn.execute(pgCmds.CREATE_PLAYER, player_id) 
        


        # ====================
        # Save player Step 2
        # Save World Data
        # Theres a bit of back and forth with Resonite here. 

        # ===== Tell Resonite to Serialise Player Data
        await self.send(f"saveplayerλ1λ{player_id}")

        # ===== Await Resonite to send serialised played data
        ret =  await self.recv()

        # ===== Try to load the data from Resonite as a data dictionary with Json.loads
        # If this errors it means the data we got from Resonite is Faulty
        try:
            retdict = json.loads(ret)
        except ValueError:
            await eprint(f"Error parsing Player Data: {ret}")
            return #ToDo Error Handling
        
        # ===== Handle writing world specific data back to the database
        playerWorldData = {}

        # If this world has data in the database, fetch it
        if (await self.db_conn.fetchval(pgCmds.EXISTS_PLAYER_ANY_WORLD_DATA, player_id)):
            playerWorldData = await self.db_conn.fetch(pgCmds.FETCH_PLAYER_ALL_WORLD_DATA, player_id)

        # Update field with new data
        playerWorldData[self.worldname] = retdict['Position']


        

        # ====================
        # Save player Step 3
        # Save Player Inventory

        # ===== Tell Resonite to serialise the players inventory
        await self.send(f"saveplayerλ2λ{player_id}")

        # ===== await Resonite sending us the players inventory
        rawplayerinv = await self.recv()

        # ===== Try to load the data from Resonite as a data dictionary with Json.loads
        # If this errors it means the data we got from Resonite is Faulty
        # If this errors, We tell Resonite to Sanitize the players inventory and resend

        try:
            playerinvdict = json.loads(rawplayerinv)
        except ValueError:

            # === Tell Resonite to Sanitize the Players Inventory
            await self.send(f"saveplayerλ3λ{player_id}")

            # === Wait for Resonite to resend us the Players Inventory
            rawplayerinv = await self.recv()

            try:
                playerinvdict = json.loads(rawplayerinv)

            except ValueError:

                await eprint(f"Error parsing Player Inventory: {rawplayerinv}")
                return #ToDo Error Handling
        


        # ====================
        # Save player Step 4
        # Commit To Database

        # ===== Write the bulk of the world data to the database
        await self.db_conn.execute(pgCmds.STORE_PLAYER_DATA, retdict['Player_Name'], retdict['Player_Profession'], retdict['Player_Level'], retdict['Max_Health'], retdict['Health'], retdict['Hit_Multi'], retdict['Agility'], self.worldname)

        # ===== Commit World Data to Database
        await self.db_conn.execute(pgCmds.STORE_PLAYER_WORLD_DATA, player_id, playerWorldData)

        # ===== Commit Player inventory to Database
        await self.db_conn.execute(pgCmds.STORE_PLAYER_INVENTORY, player_id, playerinvdict)
        
        return


    async def run_cmd_loadplayer(self, player_id):
        """Read player data from database"""

        # ====================
        # Load player Step 1
        # Test if player exists in Database and Create them if not

        # ===== If player does not exist, create them and return to Resonite with 
        if not await self.db_conn.fetchval(pgCmds.PLAYER_EXISTS, player_id):

            # === If the reso ID is not formatted correctly
            if not (player_id).startswith('U-'):
                raise PlayerLoadError

            # === Create player
            await self.db_conn.execute(pgCmds.CREATE_PLAYER, player_id) 
        



        # ====================
        # Load player Step 2
        # Does player have any world data? Fetch from Resonite if not

        # ===== If world data is there, we must fetch it
        if await self.db_conn.fetchval(pgCmds.EXISTS_PLAYER_THIS_WORLD_DATA, player_id, self.worldname):
            xpos, ypos, zpos = (await self.db_conn.fetchval(pgCmds.FETCH_PLAYER_THIS_WORLD_DATA, player_id, self.worldname)).values()

        # ===== Else world data for player does not exist, ask resonite for it
        else:
            # === Send Resonite loadedplayer message 2
            await self.send(f"loadedplayerλ1λ{player_id}")

            # === Wait for response from Resonite
            data = await self.recv()

            # === X - Y - Z
            xpos, ypos, zpos = data.split(',')

        

        # ====================
        # Load player Step 3
        # Set up Player Inventory

        # ===== Tell resonite to generate a blank inventory
        await self.send(f"loadedplayerλ2λ")

        bangbang = await self.recv()

        bangbang = (bangbang.strip()).lower()

        if bangbang == "error":
            return #ToDo Error Handling


        # ===== Fetch Player inventory items from Websocket
        # Data comes in with the Parent Class, Item ID and Item data

        records = await self.db_conn.fetch(pgCmds.FETCH_PLAYER_INVENTORY_ITEMS, player_id)

        if len(records) > 0:

            for record in records:

                for item in record['elements']:
                    data = ''

                    if len(item['data']) > 0:
                        data = ':>'.join([f'{key}:~{value}' for key, value in item['data'].items()])

                    await self.send(f"loadedplayerλ3λ{':¬'.join([record['uuid'], item['UUID'], data])}")

                    
                    
        # ====================
        # Load player Step 4
        # Fetch and Send Player Data

        # ===== Fetch the normal player data
        ply_name, ply_profession, level, max_health, health, hit_multi, agility, pre_world = await self.db_conn.fetchrow(pgCmds.FETCH_PLAYER_DATA, player_id)

        # ===== Do some rounding, for now
        max_health= round(max_health,4)
        health =    round(health,4)
        hit_multi = round(hit_multi,4)

        # ===== Send Player Data
        await self.send(f"loadedplayerλ4λ{player_id},{ply_name},{ply_profession},{pre_world},[{xpos};{ypos};{zpos}],{max_health},{health},{hit_multi},{agility},{level}")

        return


    async def cmd_packet_analysis(self, msg, length=2, delim=None) -> tuple:
        """
        Checks if the Command received is valid

        Returns:
            tuple: (is_valid (bool), command (str), argument (str))
        """
        
        cmdpack = [x for x in msg.split(delim) if x]

        if len(cmdpack) == length:
            return True, cmdpack[0], cmdpack[1] 
        else:
            return False, cmdpack[0], ''
        


    # ============================== Untility Functions ==============================

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



# ===============================================================================
#                    ~~~~~~~~~~~~~~~ End Of Class ~~~~~~~~~~~~~~~ 
# ===============================================================================




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

        await asyncio.sleep(30)


