-- Tabla para niveles y aprendizaje de usuarios
CREATE TABLE IF NOT EXISTS user_learning_levels (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL,
    nivel integer NOT NULL DEFAULT 1,
    experiencia integer NOT NULL DEFAULT 0,
    lecciones_completadas integer NOT NULL DEFAULT 0,
    fecha_ultimo_nivel timestamp,
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now()
);

-- Índice para búsquedas rápidas por usuario
CREATE INDEX idx_user_id ON user_learning_levels(user_id);