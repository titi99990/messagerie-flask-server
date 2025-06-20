from flask import Flask, request, jsonify, Response
import time

app = Flask(__name__)
MESSAGES = []
BANS = {}

HTML_CODE = '''
<!DOCTYPE html>
<html lang='fr'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>Messagerie MagiCuile</title>
  <style>
    body { font-family: monospace; background-color: #121212; color: #0f0; padding: 20px; }
    #chat { border: 1px solid #0f0; padding: 10px; height: 300px; overflow-y: auto; background: #000; }
    #messageInput, #keyInput, #username {
      width: 100%; margin-top: 10px; padding: 8px;
      background: #222; color: #0f0; border: 1px solid #0f0;
    }
    button { margin-top: 10px; padding: 8px; background: #0f0; color: #000;
      border: none; font-weight: bold; cursor: pointer; }
    .decrypted { animation: fadeIn 0.5s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    #ban-screen {
      display: none; position: fixed; top: 0; left: 0;
      width: 100vw; height: 100vh; background: red; color: white;
      font-size: 30px; text-align: center; padding-top: 20%;
      z-index: 9999; animation: shake 1s infinite alternate;
    }
    @keyframes shake { from { transform: rotate(-2deg); } to { transform: rotate(2deg); } }
  </style>
</head>
<body>
  <div id="ban-screen">🚫 Banni !<br>Tu as saisi un mauvais mot de passe trop de fois.<br>Accès refusé 🔒</div>
  <h1>Bienvenue dans la messagerie MagiCuile 💚</h1>
  <div>
    <input id="username" placeholder="Ton nom (sera chiffré)" />
    <input id="keyInput" placeholder="MiniClé MagiCuile (12 caractères min)" type="password" />
    <div id="chat"></div>
    <textarea id="messageInput" placeholder="Tape ton message..."></textarea>
    <button onclick="sendMessage()">Envoyer (chiffré)</button>
  </div>
  <script>
    let aesKey = null;
    let failedAttempts = localStorage.getItem("banAttempts") || 0;
    let banTimestamp = localStorage.getItem("banUntil") || 0;

    if (parseInt(banTimestamp) > Date.now()) {
      document.getElementById("ban-screen").style.display = "block";
    }

    async function sha256(str) {
      const buffer = new TextEncoder().encode(str);
      const digest = await crypto.subtle.digest("SHA-256", buffer);
      return crypto.subtle.importKey("raw", digest, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
    }

    async function encrypt(text, key) {
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const encoded = new TextEncoder().encode(text);
      const cipher = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, encoded);
      return btoa(JSON.stringify({ iv: Array.from(iv), data: Array.from(new Uint8Array(cipher)) }));
    }

    async function decrypt(cipherText, key) {
      const decoded = JSON.parse(atob(cipherText));
      const iv = new Uint8Array(decoded.iv);
      const data = new Uint8Array(decoded.data);
      const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, data);
      return new TextDecoder().decode(decrypted);
    }

    function transformSpecialCharacters(text) {
      const map = {
        'A': '@','B': 'β','C': '©','D': 'Ð','E': '€','F': 'ƒ','G': '§','H': '#','I': '!','J': '♣',
        'K': '₭','L': '£','M': 'ℓ','N': 'ñ','O': '°','P': '¶','Q': 'φ','R': '®','S': '$','T': '†',
        'U': 'µ','V': '√','W': 'ω','X': '☓','Y': '¥','Z': 'ζ','?': '¿','!': '‼','...': '…','.' : '•',
        ',': '‚',':': '∶',';': '⁏','\'': '‘','"': '“','(':'⦅',')':'⦆','-':'—','_':'‗','+':'±','=':'≡',
        '/':'÷','\\':'∖','*':'✱','&':'∧','%':'‰','@':'☯','#':'♯','$':'₪','^':'Ɐ','~':'⁓'
      };
      return text.split('').map(char => map[char] || map[char.toUpperCase()] || char).join('');
    }

    function autoTransform(id) {
      document.getElementById(id).addEventListener("input", function(event) {
        const cursorPos = this.selectionStart;
        const transformed = transformSpecialCharacters(this.value);
        this.value = transformed;
        this.selectionEnd = this.selectionStart = cursorPos;
      });
    }

    autoTransform("messageInput");
    autoTransform("username");

    async function sendMessage() {
      const username = document.getElementById("username").value;
      let message = document.getElementById("messageInput").value;
      const secret = document.getElementById("keyInput").value;
      if (secret.length < 12) return alert("MiniClé trop courte !");
      if (!aesKey) aesKey = await sha256(secret);

      const symbols = ["✨", "🔥", "💬", "🧙‍♂️", "🔐", "💚"];
      message += " " + symbols[Math.floor(Math.random() * symbols.length)];

      const encryptedName = await encrypt(username, aesKey);
      const encryptedMsg = await encrypt(message, aesKey);

      const payload = JSON.stringify({ name: encryptedName, message: encryptedMsg });
      await fetch("/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload
      });

      document.getElementById("messageInput").value = "";
      loadMessages();
    }

    async function loadMessages() {
      const res = await fetch("/messages");
      const msgs = await res.json();
      const chat = document.getElementById("chat");
      chat.innerHTML = "";
      for (const m of msgs) {
        const div = document.createElement("div");
        const btn = document.createElement("button");
        btn.textContent = "Déchiffrer";
        btn.onclick = function() {
          decryptMsg(btn, m.name, m.message);
        };
        div.appendChild(btn);
        chat.appendChild(div);
      }
    }

    async function decryptMsg(button, encryptedName, encryptedMessage) {
      const secret = document.getElementById("keyInput").value;
      if (secret.length < 12) return alert("MiniClé trop courte !");
      if (!aesKey) aesKey = await sha256(secret);
      try {
        const name = await decrypt(encryptedName, aesKey);
        const msg = await decrypt(encryptedMessage, aesKey);
        const div = document.createElement("div");
        div.classList.add("decrypted");
        div.innerHTML = '<b>' + name + '</b>: ' + msg;
        button.replaceWith(div);
      } catch (e) {
        let fails = parseInt(localStorage.getItem("banAttempts") || 0) + 1;
        localStorage.setItem("banAttempts", fails);
        if (fails >= 6) {
          localStorage.setItem("banUntil", Date.now() + 100 * 365 * 24 * 60 * 60 * 1000);
        } else if (fails >= 3) {
          localStorage.setItem("banUntil", Date.now() + 48 * 60 * 60 * 1000);
        }
        alert("MiniClé incorrecte ! Tentative " + fails);
        document.getElementById("ban-screen").style.display = "block";
      }
    }

    setInterval(loadMessages, 3000);
    loadMessages();
  </script>
</body>
</html>
'''

@app.route("/")
def home():
    return Response(HTML_CODE, mimetype="text/html")

@app.route("/send", methods=["POST"])
def send():
    ip = request.remote_addr
    if ip in BANS and time.time() < BANS[ip]:
        return jsonify({"status": "banned"}), 403

    data = request.get_json()
    if not data or "name" not in data or "message" not in data:
        return jsonify({"status": "error", "message": "Champs manquants"}), 400

    MESSAGES.append({
        "name": data["name"],
        "message": data["message"],
        "timestamp": time.time()
    })
    return jsonify({"status": "ok"})

@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify(MESSAGES[-50:])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81)
