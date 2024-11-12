"""
-Lime
"""

class DatabaseCmds(object):

    # ============================== PLAYERS TABLE ==============================
    CREATE_PLRS_TABLE =""" 
        CREATE TABLE IF NOT EXISTS players (
            ply_num         BIGSERIAL   PRIMARY KEY,
            reso_id         VARCHAR     NOT NULL,
            ply_name        VARCHAR     NOT NULL    DEFAULT 'Alex Morgan',
            ply_profession  VARCHAR     NOT NULL    DEFAULT 'Observer',
            ply_lvl         SMALLINT    NOT NULL    DEFAULT 1,
            inventory       JSONB       NOT NULL    DEFAULT '{}'::jsonb,
            world_data      JSONB       NOT NULL    DEFAULT '{}'::jsonb,
            max_health      REAL        NOT NULL    DEFAULT 10,
            health          REAL        NOT NULL    DEFAULT 10,
            hit_multi       REAL        NOT NULL    DEFAULT 1,
            agility         REAL        NOT NULL    DEFAULT 1,
            timestamp       TIMESTAMP   NOT NULL    DEFAULT (NOW() AT TIME ZONE 'utc'),
            pre_world       VARCHAR     NOT NULL    DEFAULT 'void',
            CONSTRAINT player_unique UNIQUE (reso_id)
            ); 

        COMMENT ON TABLE players IS                     'Store the player information here';
        COMMENT ON COLUMN players.world_data IS         'Hold unique data for the player in regards to each world here.'; 
        COMMENT ON COLUMN players.inventory IS          'A players inventory';
        COMMENT ON COLUMN players.ply_lvl IS            'A Players Level';
        COMMENT ON COLUMN players.ply_name IS           'A Players Character name';
        COMMENT ON COLUMN players.reso_id IS            'Players Resonite ID, usually formatted as U-randomstring. Should always be unique if Resonite developers are not completely incompetent, I mean they are pretty bad but failing at this one this would be pretty bloody pathetic';
        COMMENT ON COLUMN players.ply_profession IS     'Players Characters profession';
        COMMENT ON COLUMN players.timestamp IS          'Timestamp of when a player joined the RPG world stored as utc time';
        COMMENT ON COLUMN players.ply_num IS            'A players serial number in the database, this could be fun down the line to show a players number.';
        """

    EXISTS_PLRS_TABLE=          "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE UPPER(table_name) = 'PLAYERS');"

    # ========== PLAYER DATA ==========
    ADD_OR_UPDATE_PLAYER =""" 
        INSERT INTO players(
            reso_id, ply_name, ply_profession, ply_lvl, inventory, world_data, max_health, health, hit_multi, agility, pre_world
            )
        VALUES( 
            CAST($1 AS VARCHAR), 
            CAST($2 AS VARCHAR), 
            CAST($3 AS VARCHAR), 
            CAST($4 AS SMALLINT), 
            $5::JSONB, 
            $6::JSONB, 
            CAST($7 AS REAL), 
            CAST($8 AS REAL), 
            CAST($9 AS REAL), 
            CAST($10 AS REAL),
            CAST($11 AS VARCHAR),
            )
        ON CONFLICT (reso_id)
            DO
            UPDATE SET 
                ply_name        CAST($2 AS VARCHAR), 
                ply_profession  CAST($3 AS VARCHAR), 
                ply_lvl         CAST($4 AS SMALLINT), 
                inventory       $5::JSONB, 
                world_data      $6::JSONB, 
                max_health      CAST($7 AS REAL), 
                health          CAST($8 AS REAL), 
                hit_multi       CAST($9 AS REAL), 
                agility         CAST($10 AS REAL),
                pre_world       CAST($11 AS VARCHAR),
        """

    # ===== This will create a player with generic data as set by the tables defaults
    PLAYER_EXISTS =             "SELECT EXISTS(SELECT ply_num FROM public.players WHERE reso_id = CAST($1 AS VARCHAR));"

    CREATE_PLAYER = """
        INSERT INTO players(
            reso_id
            )
        VALUES(
            CAST($1 AS VARCHAR)
            )
        ON CONFLICT (reso_id)
            DO NOTHING;
    """

    FETCH_PLAYER_DATA = """
        SELECT  
            ply_name, ply_profession, pre_world, max_health, health, hit_multi, ply_lvl, agility 
        FROM public.players
        WHERE 
            reso_id = CAST($1 AS VARCHAR)
    """



    EXISTS_PLAYER_WORLD_DATA =         "SELECT hasWorldInfo(CAST($1 AS VARCHAR), CAST($2 AS VARCHAR));"

    FETCH_PLAYER_WORLD_DATA =          "SELECT getWorldInfo(CAST($1 AS VARCHAR), CAST($2 AS VARCHAR));"

    STORE_PLAYER_WORLD_DATA = """
        UPDATE
            players
        SET
            world_data = CAST($2 AS jsonb)
        WHERE
            reso_id = CAST($1 as VARCHAR);
    """


    EXISTS_PLAYER_INVENTORY =           "SELECT EXISTS(SELECT 1 FROM public.players WHERE reso_id = CAST($1 AS VARCHAR) AND inventory != '{}'::jsonb);"

    FETCH_PLAYER_INVENTORY =            "SELECT inventory FROM public.players WHERE reso_id = CAST($1 as VARCHAR);"

    STORE_PLAYER_WORLD_DATA = """
        UPDATE
            players
        SET
            inventory = CAST($2 AS jsonb)
        WHERE
            reso_id = CAST($1 as VARCHAR);
    """



    FETCH_PLAYER_ALL =          "SELECT * FROM public.players WHERE reso_id = CAST($1 AS VARCHAR);"


    STORE_PLAYER_INVENTORY = """
        UPDATE 
            players
        SET
            inventory = CAST($2 AS jsonb)
        WHERE
            reso_id = CAST($1 AS VARCHAR);
    """



    DEBUG_RESET_PLAYER = """
        UPDATE players
        SET
            ply_name = DEFAULT,
            ply_profession = DEFAULT,
            ply_lvl = DEFAULT,
            inventory = DEFAULT,
            world_data = DEFAULT,
            max_health = DEFAULT,
            health = DEFAULT,
            hit_multi = DEFAULT,  
            agility = DEFAULT,
            timestamp = DEFAULT,
            pre_world = DEFAULT
        WHERE
            reso_id = CAST($1 AS VARCHAR);
    """

    DEBUG_REMOVE_PLAYER = """
        DELETE 
        FROM
            players
        WHERE 
            reso_id = CAST($1 AS VARCHAR);
    """




    # ============================== ~~~~~~~~~ ==============================
    # ============================== FUNCTIONS ==============================
    # ============================== ~~~~~~~~~ ==============================
    
    
    # -------------------- HAS WORLD INFO --------------------
    CREATE_FUNC_HASWORLDINFO = """
    DO
    $do$
    BEGIN
        IF NOT EXISTS(
            SELECT 1 FROM pg_proc WHERE prorettype <> 0 AND proname = 'hasworldinfo'
        ) THEN 
            CREATE FUNCTION hasWorldInfo(player_id VARCHAR, world VARCHAR) 
            RETURNS BOOLEAN AS
            $$
            BEGIN
                RETURN EXISTS(
                    SELECT 1 FROM public.players 
                    WHERE reso_id = player_id
                    AND world_data->>world IS NOT NULL
                );
            END;
            $$ LANGUAGE plpgsql COST 100;
        END IF;
    END
    $do$
    """

    EXISTS_FUNC_HASWORLDINFO= "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE prorettype <> 0 AND proname = 'hasworldinfo');"

    # -------------------- GET WORLD INFO --------------------
    CREATE_FUNC_GETWORLDINFO = """
    DO
    $do$
    BEGIN
        IF NOT EXISTS(
            SELECT 1 FROM pg_proc WHERE prorettype <> 0 AND proname = 'getworldinfo'
        )THEN 
            CREATE FUNCTION getWorldInfo(player_id VARCHAR, world VARCHAR) 
            RETURNS JSONB AS
            $$
            BEGIN
                RETURN (
                    SELECT world_data->>world 
                    FROM public.players
                    WHERE reso_id = player_id
                    );
            END;
            $$ LANGUAGE plpgsql COST 100;
        END IF;
    END
    $do$
    """

    EXISTS_FUNC_GETWORLDINFO= "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE prorettype <> 0 AND proname = 'getworldinfo');"





    # ---------------
    FETCH_INV_ITEMS = """
    WITH RECURSIVE elements_tree AS (
        -- Initial query to find the top-level element within the inventory array with a UUID that matches the given UUID
        SELECT 
            jsonb_array_elements(inventory) AS element
        FROM 
            players
        WHERE 
            reso_id = CAST($1 AS VARCHAR)
        
        UNION ALL
        
        -- Recursive part to iterate over "elements" within each matching element
        SELECT 
            jsonb_array_elements(elements_tree.element->'elements') AS element
        FROM 
            elements_tree
    )
    -- Final selection to get UUID and nested elements of each child
    SELECT 
        element->>'UUID' AS UUID,
        element->'elements' as ELEMENTS
    FROM 
        elements_tree
    WHERE
        LOWER(element->>'UUID') NOT LIKE 'i-%' AND
        NOT EXISTS (
            SELECT 1
            FROM jsonb_array_elements(element->'elements') AS child
            WHERE LOWER(child->>'UUID') LIKE 'c-%'  -- Exclude if any child doesn't start with 'i-'
        );
    """
