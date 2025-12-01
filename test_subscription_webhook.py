import requests
import hmac
import hashlib
import json
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

IPN_SECRET_KEY = os.getenv("IPN_SECRET_KEY")
# URL local por defecto (donde corre main.py)
API_URL = "https://kalirootbot.onrender.com/webhook/nowpayments"

def test_webhook(user_id, invoice_id="test_invoice_123"):
    if not IPN_SECRET_KEY:
        print("❌ Error: IPN_SECRET_KEY no encontrada en .env")
        print("Asegúrate de haber configurado tu clave secreta de NOWPayments.")
        return

    # Payload simulado de NOWPayments
    payload = {
        "payment_status": "finished",
        "payment_id": 123456789,
        "pay_address": "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
        "price_amount": 10,
        "price_currency": "usd",
        "pay_amount": 10,
        "pay_currency": "usdttrc20",
        "order_id": str(user_id),
        "invoice_id": invoice_id,
        "ipn_type": "invoice",
    }

    # Calcular firma HMAC-SHA512
    # 1. Filtrar x-nowpayments-sig (si existiera)
    params = {k: v for k, v in payload.items() if k != 'x-nowpayments-sig'}
    # 2. Ordenar alfabéticamente por clave
    sorted_params = sorted(params.items())
    # 3. Crear string key=value&key=value...
    msg = "&".join([f"{k}={v}" for k, v in sorted_params if v is not None])
    
    # 4. Firmar
    signature = hmac.new(
        IPN_SECRET_KEY.encode(),
        msg.encode(),
        hashlib.sha512
    ).hexdigest()

    # Headers requeridos
    headers = {
        "Content-Type": "application/json",
        "x-nowpayments-sig": signature
    }

    print(f"📡 Enviando webhook simulado a {API_URL}...")
    print(f"👤 Usuario ID: {user_id}")
    print(f"🧾 Factura ID: {invoice_id}")
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        
        print(f"\nRespuesta del Servidor:")
        print(f"Status Code: {response.status_code}")
        print(f"Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ ¡PRUEBA EXITOSA!")
            print("El servidor aceptó el pago y debería haber activado la suscripción.")
            print("Verifica en el bot enviando el comando: 🔑 Gestionar Suscripción")
        elif response.status_code == 401:
            print("\n❌ Error de Firma (401):")
            print("La IPN_SECRET_KEY del script no coincide con la del servidor.")
            print("Verifica que ambas sean idénticas en el archivo .env")
        else:
            print(f"\n❌ Error ({response.status_code}): El servidor rechazó la solicitud.")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error de Conexión:")
        print(f"No se pudo conectar a {API_URL}")
        print("Asegúrate de que el servidor esté corriendo con: python main.py")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        uid = sys.argv[1]
    else:
        print("--- Simulador de Pago NOWPayments ---")
        uid = input("Ingresa tu ID de Telegram (puedes verlo en el bot): ")
    
    if uid.strip():
        test_webhook(uid)
    else:
        print("ID de usuario inválido.")
