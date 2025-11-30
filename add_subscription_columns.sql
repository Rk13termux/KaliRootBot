-- Add subscription columns to usuarios table
ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS subscription_status text DEFAULT 'inactive',
ADD COLUMN IF NOT EXISTS subscription_expiry_date timestamp with time zone,
ADD COLUMN IF NOT EXISTS nowpayments_invoice_id text;

-- Index for faster queries on subscription status
CREATE INDEX IF NOT EXISTS idx_usuarios_subscription_status ON usuarios(subscription_status);
