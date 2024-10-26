"""
-Lime
"""

class DatabaseCmds(object):

    # ============================== PLAYERS TABLE ==============================
    CREATE_PLRS_TABLE =""" 
        CREATE TABLE IF NOT EXISTS players (
            ply_num         BIGSERIAL   PRIMARY KEY,
            reso_id         VARCHAR     NOT NULL,
            client_data     JSONB,
            health          REAL        NOT NULL    DEFAULT(0),
            hit_multi       REAL        NOT NULL    DEFAULT(1),
            attack          REAL        NOT NULL    DEFAULT(1),
            agility         REAL        NOT NULL    DEFAULT(1),
            timestamp       TIMESTAMP   NOT NULL    DEFAULT (NOW() AT TIME ZONE 'utc'),
            CONSTRAINT player_unique UNIQUE (reso_id)
            ); 

        COMMENT ON TABLE players is                  'Store the player information here';
        COMMENT ON COLUMN players.client_data is     'Hold unique data for the player in regards to each world here.'; 
        """


    ADD_OR_UPDATE_PLAYER =""" 
        INSERT INTO players(
            reso_id, client_data, health, hit_multi,attack, agility
            )
        VALUES( 
            CAST($1 AS VARCHAR), $2::JSONB, CAST($3 AS REAL), CAST($4 AS REAL), CAST($5 AS REAL), CAST($6 AS REAL)
            )
        ON CONFLICT (reso_id)
            DO
            UPDATE SET 
                client_data = $2::JSONB,
                health      = CAST($3 AS REAL),
                hit_multi   = CAST($4 AS REAL),
                attack      = CAST($5 AS REAL),
                agility     = CAST($6 AS REAL);
        """
    

    FETCH_PLAYER_ALL =          "SELECT * FROM public.player WHERE reso_id = CAST($1 AS VARCHAR);"
    FETCH_PLAYER =              "SELECT reso_id, client_data, health, hit_multi, attack, agility FROM public.player WHERE reso_id = CAST($1 AS VARCHAR);"
    EXISTS_PLRS_TABLE=          "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE upper(table_name) = 'PLAYERS');"