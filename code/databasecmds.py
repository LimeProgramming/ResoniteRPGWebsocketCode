"""
-Lime
"""

class DatabaseCmds(object):

    # ============================== PLAYERS TABLE ==============================
    CREATE_PLRS_TABLE =""" 
        CREATE TABLE IF NOT EXISTS players (
            ply_num         BIGSERIAL   PRIMARY KEY,
            reso_id         VARCHAR     NOT NULL,
            ply_name        VARCHAR     NOT NULL    DEFAULT('Alex Morgan'),
            ply_profession  VARCHAR     NOT NULL    DEFAULT('Observer'),
            ply_lvl         SMALLINT    NOT NULL    DEFAULT(1),
            inventory       JSONB,
            world_data      JSONB,
            max_health      REAL        NOT NULL    DEFAULT(10),
            health          REAL        NOT NULL    DEFAULT(10),
            hit_multi       REAL        NOT NULL    DEFAULT(1),
            agility         REAL        NOT NULL    DEFAULT(1),
            timestamp       TIMESTAMP   NOT NULL    DEFAULT (NOW() AT TIME ZONE 'utc'),
            pre_world       VARCHAR     NOT NULL    DEFAULT('void'),
            CONSTRAINT player_unique UNIQUE (reso_id)
            ); 

        COMMENT ON TABLE players is                  'Store the player information here';
        COMMENT ON COLUMN players.world_data is      'Hold unique data for the player in regards to each world here.'; 
        """

    EXISTS_PLRS_TABLE=          "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE UPPER(table_name) = 'PLAYERS');"

    # ========== PLAYER DATA ==========
    ADD_OR_UPDATE_PLAYER =""" 
        INSERT INTO players(
            reso_id, ply_name, ply_profession, ply_lvl, world_data, max_health, health, hit_multi, agility, pre_world
            )
        VALUES( 
            CAST($1 AS VARCHAR), 
            CAST($2 AS VARCHAR), 
            CAST($3 AS VARCHAR), 
            CAST($4 AS SMALLINT), 
            $5::JSONB, 
            CAST($6 AS REAL), 
            CAST($7 AS REAL), 
            CAST($8 AS REAL), 
            CAST($9 AS REAL),
            CAST($10 AS VARCHAR),
            )
        ON CONFLICT (reso_id)
            DO
            UPDATE SET 
                ply_name        CAST($2 AS VARCHAR), 
                ply_profession  CAST($3 AS VARCHAR), 
                ply_lvl         CAST($4 AS SMALLINT), 
                world_data      $5::JSONB, 
                max_health      CAST($6 AS REAL), 
                health          CAST($7 AS REAL), 
                hit_multi       CAST($8 AS REAL), 
                agility         CAST($9 AS REAL),
                pre_world       CAST($10 AS VARCHAR),
        """

    # ===== This will create a player with generic data as set by the tables defaults
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
            LOWER(reso_id) = LOWER(CAST($1 AS VARCHAR))
    """

    WORLD_DATA_EXISTS =         "SELECT EXISTS(SELECT world_data->>LOWER(CAST($1 AS VARCHAR)) FROM public.players WHERE LOWER(reso_id) = LOWER(CAST($2 AS VARCHAR)));"
    FETCH_WORLD_DATA =          "SELECT world_data FROM public.players WHERE LOWER(reso_id) = LOWER(CAST($1 AS VARCHAR));"
    PLAYER_EXISTS =             "SELECT EXISTS(SELECT ply_num FROM public.players WHERE LOWER(reso_id) = LOWER(CAST($1 AS VARCHAR)));"





    FETCH_PLAYER_INVENTORY =    "SELECT inventory FROM public.players WHERE reso_id = CAST($1 as VARCHAR);"
    FETCH_PLAYER_ALL =          "SELECT * FROM public.players WHERE reso_id = CAST($1 AS VARCHAR);"
    FETCH_PLAYER =              "SELECT reso_id, world_data, health, hit_multi, attack, agility FROM public.players WHERE reso_id = CAST($1 AS VARCHAR);"
