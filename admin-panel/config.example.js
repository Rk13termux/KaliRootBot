/**
 * KaliRoot Admin Panel - Configuration File
 * 
 * ⚠️ IMPORTANTE: Este archivo contiene credenciales sensibles.
 * NO lo subas a repositorios públicos.
 * Añádelo a .gitignore
 * 
 * Instrucciones:
 * 1. Renombra este archivo de config.example.js a config.js
 * 2. Completa las credenciales abajo
 * 3. El Admin Panel cargará automáticamente sin pedir login
 */

const ADMIN_CONFIG = {
    // ===== SUPABASE =====
    supabase_url: '',           // Ej: https://xxxxx.supabase.co
    supabase_key: '',           // Tu service_role key (secret)

    // ===== TELEGRAM BOT =====
    bot_token: '',              // Ej: 123456789:AAxxxxxxxxxx

    // ===== TELEGRAM API (opcional) =====
    telegram_api_id: '',        // Ej: 12345678
    telegram_api_hash: '',      // Ej: 0123456789abcdef...
    telegram_app_title: 'kaliroot',
    telegram_short_name: 'kaliroot',

    // ===== OTRAS CONFIGURACIONES =====
    auto_login: true,           // true = login automático, false = mostrar formulario
    default_credits: 20,
    subscription_days: 30
};

// No modificar esta línea
if (typeof window !== 'undefined') {
    window.ADMIN_CONFIG = ADMIN_CONFIG;
}
