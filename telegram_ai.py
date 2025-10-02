import os
import json
import requests
from telethon import TelegramClient, events
from dotenv import load_dotenv
from supabase import create_client, Client

# -------------------
# Cargar variables de entorno
# -------------------
load_dotenv()

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
chat_id = os.getenv("CHAT_ID")  # chat específico en supabase

supabase: Client = create_client(supabase_url, supabase_key)

# -------------------
# Prompt base
# -------------------
BASE_PROMPT = """
Responde siempre como si fueras Gaspar Cruañes Martínez en un chat privado con Henry Jones (fundador de TSQ Investment Group).

Contexto:
- Henry Jones siempre explica y comparte información sobre el proyecto TSQ, Hellobit, inversiones, filosofía del grupo, reglas y motivaciones.
- Tu papel es responder de forma cortés, breve y natural, sin entrar en detalles técnicos.
- Tus respuestas deben parecer humanas y coherentes, pero siempre muy concisas.

Formato de salida obligatorio:
Devuelve SIEMPRE en formato JSON válido con las siguientes claves:
{
  "respuesta": "...",
  "action": "RESPONDER" o "NO_RESPONDER"
}

Reglas:
- Si el mensaje de Henry está relacionado con el proyecto TSQ o con motivación/información del grupo y merece respuesta, devuelve algo breve como Gaspar:
  - "Gracias", "Muy interesante", "Perfecto", "Entendido", "Lo tengo en cuenta", "Gracias por la información", "Me alegra escucharlo".
  - action = "RESPONDER".
- Si el mensaje NO amerita respuesta (ejemplo: es trivial, repetido, o no añade nada nuevo), responde con:
  {
    "respuesta": "El mensaje no requiere respuesta porque no aporta nada nuevo o no es relevante al proyecto TSQ.",
    "action": "NO_RESPONDER"
  }
- Nunca inventes datos ni des explicaciones largas.
- Nunca digas que eres un asistente, IA o robot.
"""

# -------------------
# Inicializar cliente de Telegram
# -------------------
client = TelegramClient("mi_sesion", api_id, api_hash)

# -------------------
# Funciones auxiliares
# -------------------
def obtener_siguiente_orden_mensaje(chat_id):
    """Obtiene el siguiente número de orden para los mensajes de un chat"""
    try:
        # Obtener el máximo orden actual para este chat
        res = supabase.table("messages") \
            .select("id") \
            .eq("chat_id", chat_id) \
            .order("created_at", desc=True) \
            .limit(1).execute()

        if res.data and len(res.data) > 0:
            # Si hay mensajes, obtener el último por orden
            res_max = supabase.table("messages") \
                .select("message_order") \
                .eq("chat_id", chat_id) \
                .order("message_order", desc=True) \
                .limit(1).execute()

            if res_max.data and len(res_max.data) > 0:
                return (res_max.data[0]["message_order"] or 0) + 1

        return 1  # Si no hay mensajes, empezar desde 1
    except Exception:
        return 1  # En caso de error, empezar desde 1

def guardar_interaccion(chat_id, sender, mensaje_entrada, respuesta, action):
    """Guarda cada interacción para mantener registro sin usar historial en la IA"""
    # Obtener el siguiente número de orden para este chat
    orden_mensaje = obtener_siguiente_orden_mensaje(chat_id)

    # Crear contenido enriquecido con el mensaje y respuesta
    contenido_enriquecido = f"Mensaje: {mensaje_entrada}\nRespuesta: {respuesta}"

    supabase.table("messages").insert({
        "chat_id": chat_id,
        "sender": sender,
        "contenido": contenido_enriquecido,
        "action": action,
        "message_order": orden_mensaje
    }).execute()

def call_deepseek(user_message: str) -> dict:
    """Llama a la API de DeepSeek con contexto y devuelve JSON limpio"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-reasoner",
        "messages": [
            {"role": "system", "content": BASE_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.5,
    }

    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()

    # 🔹 Limpiar posibles envoltorios tipo ```json ... ```
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()

    try:
        return json.loads(content)  # debe devolver {"respuesta": "...", "action": "..."}
    except Exception:
        # fallback seguro: si no es JSON válido, forzamos
        return {"respuesta": content, "action": "RESPONDER"}


@client.on(events.NewMessage(chats=["@ainarafm"]))
async def handler(event):
    user_message = event.message.message
    sender = event.message.sender_id if event.message.sender else "unknown"
    print(f"📩 Mensaje recibido de Henry: {user_message}")

    try:
        result = call_deepseek(user_message)
        respuesta = result.get("respuesta", "").strip()
        action = result.get("action", "").strip()

        # Guardar la interacción completa
        guardar_interaccion(chat_id, sender, user_message, respuesta, action)

        if action == "RESPONDER" and respuesta:
            await event.reply(respuesta)   # 🔹 solo mandamos la respuesta limpia
            print(f"🤖 Respondido como Gaspar: {respuesta}")
        elif action == "NO_RESPONDER":
            print("🤖 Decisión: NO RESPONDER")
        else:
            print("⚠️ Acción desconocida o respuesta vacía, ignorado.")

    except Exception as e:
        print("❌ Error al procesar:", e)

# -------------------
# Main
# -------------------
if __name__ == "__main__":
    print("🚀 Iniciando cliente...")
    client.start()
    client.run_until_disconnected()
