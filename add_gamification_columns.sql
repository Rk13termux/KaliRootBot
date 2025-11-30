-- Add gamification columns to usuarios table
ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS level INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS subscription_tier TEXT DEFAULT 'novato', -- 'novato', 'pentester', 'elite'
ADD COLUMN IF NOT EXISTS streak_days INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_active_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS completed_modules JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS badges JSONB DEFAULT '[]'::jsonb;

-- Function to add XP and check for level up (simple logic: level = 1 + xp / 1000)
CREATE OR REPLACE FUNCTION add_xp(uid BIGINT, amount INTEGER)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    current_xp INTEGER;
    current_level INTEGER;
    new_xp INTEGER;
    new_level INTEGER;
    user_exists BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM usuarios WHERE user_id = uid) INTO user_exists;
    IF NOT user_exists THEN
        RETURN jsonb_build_object('success', false, 'message', 'User not found');
    END IF;

    SELECT xp, level INTO current_xp, current_level FROM usuarios WHERE user_id = uid;
    
    new_xp := current_xp + amount;
    new_level := 1 + (new_xp / 1000); -- Example formula
    
    UPDATE usuarios 
    SET xp = new_xp, 
        level = new_level,
        last_active_date = NOW()
    WHERE user_id = uid;
    
    RETURN jsonb_build_object(
        'success', true, 
        'old_level', current_level, 
        'new_level', new_level, 
        'xp_gained', amount,
        'total_xp', new_xp
    );
END;
$$;
