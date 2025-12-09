-- Tabla para recursos de descarga (administrada desde el panel admin)
CREATE TABLE IF NOT EXISTS download_resources (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    icon TEXT DEFAULT '📦',
    image_url TEXT,
    drive_file_id TEXT NOT NULL,
    file_size TEXT DEFAULT '0 MB',
    category TEXT DEFAULT 'general',
    is_active BOOLEAN DEFAULT true,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índice para búsqueda por categoría
CREATE INDEX IF NOT EXISTS idx_resources_category ON download_resources(category);
CREATE INDEX IF NOT EXISTS idx_resources_active ON download_resources(is_active);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_resources_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_resources_timestamp ON download_resources;
CREATE TRIGGER trg_update_resources_timestamp
    BEFORE UPDATE ON download_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_resources_timestamp();

-- Insertar algunos recursos de ejemplo
INSERT INTO download_resources (title, description, icon, drive_file_id, file_size, category) VALUES
('Kali Pack', 'Configuraciones y scripts esenciales', '🐉', 'REPLACE_WITH_REAL_ID', '2.3 GB', 'tools'),
('Termux Elite', 'Setup móvil completo para Android', '📱', 'REPLACE_WITH_REAL_ID', '450 MB', 'mobile'),
('WiFi Toolkit', 'Wordlists y scripts de auditoría WiFi', '📡', 'REPLACE_WITH_REAL_ID', '1.8 GB', 'wireless'),
('Web Pentest Pack', 'Payloads XSS, SQLi y más', '💉', 'REPLACE_WITH_REAL_ID', '320 MB', 'web')
ON CONFLICT DO NOTHING;

-- Función RPC para obtener recursos activos
CREATE OR REPLACE FUNCTION get_active_resources()
RETURNS TABLE (
    id INTEGER,
    title TEXT,
    description TEXT,
    icon TEXT,
    image_url TEXT,
    drive_file_id TEXT,
    file_size TEXT,
    category TEXT,
    download_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dr.id,
        dr.title,
        dr.description,
        dr.icon,
        dr.image_url,
        dr.drive_file_id,
        dr.file_size,
        dr.category,
        dr.download_count
    FROM download_resources dr
    WHERE dr.is_active = true
    ORDER BY dr.created_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Función para incrementar contador de descargas
CREATE OR REPLACE FUNCTION increment_download_count(resource_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE download_resources 
    SET download_count = download_count + 1 
    WHERE id = resource_id;
END;
$$ LANGUAGE plpgsql VOLATILE;
