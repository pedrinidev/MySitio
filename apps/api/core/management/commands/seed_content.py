"""Carga el contenido inicial del portafolio a partir del CV.

Idempotente: se puede ejecutar cuantas veces haga falta. Usa
`update_or_create` con el slug como clave, así que re-ejecutarlo actualiza
en vez de duplicar. Un comando de carga que solo funciona sobre una base
vacía es un comando que nadie se atreve a ejecutar.

    python manage.py seed_content
    python manage.py seed_content --reset   # borra el contenido primero
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from modules.blog.models import Category, Post, Tag
from modules.games.models import Game, GameKind, QuizOption, QuizQuestion
from modules.projects.models import Project, Technology
from modules.site.models import ExperienceItem, Profile, Skill, SkillGroup, SocialLink

# Imágenes que viajan CON el repositorio, para que un despliegue limpio
# reproduzca el sitio completo y no solo sus textos.
SEED_ASSETS = Path(__file__).resolve().parent.parent / "seed_assets"

TECHNOLOGIES = [
    ("Kotlin", "kotlin", "mobile", "#7F52FF"),
    ("Android SDK", "android-sdk", "mobile", "#3DDC84"),
    ("React Native", "react-native", "mobile", "#61DAFB"),
    ("Node.js", "nodejs", "backend", "#5FA04E"),
    ("Express", "express", "backend", "#444444"),
    ("Python", "python", "backend", "#3776AB"),
    ("Django", "django", "backend", "#092E20"),
    ("PostgreSQL", "postgresql", "database", "#4169E1"),
    ("MySQL", "mysql", "database", "#4479A1"),
    ("MongoDB", "mongodb", "database", "#47A248"),
    ("TypeScript", "typescript", "frontend", "#3178C6"),
    ("JavaScript", "javascript", "frontend", "#F7DF1E"),
    ("HTML & CSS", "html-css", "frontend", "#E34F26"),
    ("React", "react", "frontend", "#61DAFB"),
    ("Angular", "angular", "frontend", "#DD0031"),
    ("Astro", "astro", "frontend", "#FF5D01"),
    ("Electron", "electron", "frontend", "#47848F"),
    ("Docker", "docker", "devops", "#2496ED"),
    ("Linux", "linux", "devops", "#FCC624"),
    ("Nginx", "nginx", "devops", "#009639"),
    ("GitHub Actions", "github-actions", "devops", "#2088FF"),
    ("Git", "git", "devops", "#F05032"),
    ("Figma", "figma", "design", "#F24E1E"),
]

SKILL_GROUPS = [
    (
        "Mobile",
        "Mobile",
        [("Kotlin", 5, True), ("Android SDK", 5, True), ("React Native", 3, False)],
    ),
    ("Backend", "Backend", [("Node.js", 4, True), ("Express", 4, False), ("Python", 4, True)]),
    (
        "Bases de datos",
        "Databases",
        [("PostgreSQL", 4, False), ("MySQL", 4, False), ("MongoDB", 3, False)],
    ),
    (
        "Herramientas",
        "Tooling",
        [("Git", 5, True), ("GitHub", 5, False), ("Docker", 4, True), ("Linux", 4, True)],
    ),
    (
        "Frontend",
        "Frontend",
        [
            ("TypeScript", 4, False),
            ("React", 4, False),
            ("Angular", 3, False),
            ("Electron", 4, False),
        ],
    ),
    ("Diseño", "Design", [("Figma", 4, False), ("Illustrator", 3, False), ("Photoshop", 3, False)]),
    (
        "Redes y soporte",
        "Networking & support",
        [
            ("Redes LAN", 4, False),
            ("Cableado estructurado", 4, False),
            ("Windows / Ubuntu", 4, False),
        ],
    ),
]

PROJECTS = [
    {
        "slug": "isabosk",
        "title_es": "Ediciones IsaBosk",
        "title_en": "Ediciones IsaBosk",
        "tagline_es": "Sitio institucional de una editorial de textos escolares de El Alto.",
        "tagline_en": "Institutional site for a school-textbook publisher in El Alto.",
        "summary_es": (
            "Sitio público para Ediciones IsaBosk: catálogo de textos por nivel educativo, "
            "descarga de catálogos, ubicación y formulario de contacto. Entregado y en "
            "producción bajo su propio dominio."
        ),
        "summary_en": (
            "Public site for Ediciones IsaBosk: a textbook catalogue by school level, "
            "downloadable catalogues, location and a contact form. Delivered and live "
            "under the client's own domain."
        ),
        "body_md_es": (
            "## El encargo\n\n"
            "Una editorial de textos escolares que vendía por catálogo impreso y WhatsApp "
            "necesitaba un sitio donde los colegios pudieran ver el fondo editorial completo "
            "sin llamar a nadie.\n\n"
            "## Lo que construí\n\n"
            "Catálogo navegable por nivel —inicial, primaria, secundaria— con las colecciones "
            "bilingües y de artes separadas, descarga de catálogos en PDF, ubicación del local "
            "y formulario de contacto que llega al correo de la editorial.\n\n"
            "## Decisiones\n\n"
            "**Sin gestor de contenidos.** El catálogo cambia una o dos veces al año. Montar "
            "WordPress habría significado dejarle a la editorial un sistema que actualizar, "
            "parchear y pagar para resolver un problema que no tienen.\n\n"
            "**Sin framework.** HTML, CSS y JavaScript, minificados. La página abre rápido "
            "incluso con la conexión de un colegio, que es donde de verdad se va a abrir.\n\n"
            "**Tema claro y oscuro**, porque el sitio se consulta tanto de día en una "
            "dirección como de noche desde un teléfono."
        ),
        "body_md_en": (
            "## The brief\n\n"
            "A school-textbook publisher selling through printed catalogues and WhatsApp "
            "needed a site where schools could browse the full list without phoning anyone.\n\n"
            "## What I built\n\n"
            "A catalogue browsable by school level — early years, primary, secondary — with "
            "the bilingual and arts collections separated, PDF catalogue downloads, the shop "
            "location and a contact form that reaches the publisher's inbox.\n\n"
            "## Decisions\n\n"
            "**No CMS.** The catalogue changes once or twice a year. Standing up WordPress "
            "would have handed the client a system to update, patch and pay for, to solve a "
            "problem they don't have.\n\n"
            "**No framework.** HTML, CSS and JavaScript, minified. The page opens fast even "
            "on a school's connection, which is where it will actually be opened.\n\n"
            "**Light and dark themes**, because the site gets read both from an office by day "
            "and from a phone at night."
        ),
        "role_es": "Desarrollo y entrega completos",
        "role_en": "Built and delivered end to end",
        "year": 2026,
        "featured": True,
        "live_url": "https://isabosk.com/",
        "techs": ["html-css", "javascript"],
        "metrics": [("Cliente", "Ediciones IsaBosk"), ("Estado", "En producción")],
    },
    {
        "slug": "mentepro",
        "title_es": "MentePro",
        "title_en": "MentePro",
        "tagline_es": (
            "Aplicación Android de entrenamiento de cálculo mental, " "publicada en Google Play."
        ),
        "tagline_en": "Android mental-math training app, live on Google Play.",
        "summary_es": (
            "Aplicación de entrenamiento de cálculo mental publicada y disponible en Google Play. "
            "Desarrollo completo a mi cargo: diseño de interfaz, lógica de "
            "ejercicios, persistencia "
            "local y publicación en la tienda."
        ),
        "summary_en": (
            "Mental-math training app published and available on Google Play. Built end to end: "
            "interface design, exercise logic, local persistence and store release."
        ),
        "body_md_es": (
            "## El problema\n\n"
            "Practicar cálculo mental requiere constancia, y la constancia necesita fricción cero: "
            "abrir la app y estar resolviendo en menos de dos segundos.\n\n"
            "## Lo que construí\n\n"
            "- Motor de ejercicios con dificultad progresiva.\n"
            "- Persistencia local del progreso, sin cuenta ni conexión obligatoria.\n"
            "- Interfaz diseñada para sesiones cortas y repetidas.\n\n"
            "## El ciclo completo de publicación\n\n"
            "La parte que más enseña no es escribir el código, sino todo lo que viene después: "
            "generar la clave de firma, construir el *bundle*, preparar la ficha de la tienda y "
            "pasar la revisión de Google Play Console. Ese proceso —el que separa un proyecto de "
            "un producto— lo hice de principio a fin."
        ),
        "body_md_en": (
            "## The problem\n\n"
            "Practising mental arithmetic takes consistency, and consistency needs zero friction: "
            "open the app and be solving within two seconds.\n\n"
            "## What I built\n\n"
            "- Exercise engine with progressive difficulty.\n"
            "- Local progress persistence — no account, no mandatory connection.\n"
            "- Interface designed for short, repeated sessions.\n\n"
            "## The full release cycle\n\n"
            "The most instructive part is not writing the code but everything that comes after: "
            "generating the signing key, building the bundle, preparing the store listing and "
            "passing Google Play Console review. I did that end to end."
        ),
        "role_es": "Desarrollo completo a cargo",
        "role_en": "Sole developer",
        "year": 2025,
        "featured": True,
        "store_url": "https://play.google.com/store/apps/details?id=com.pedrini.mentepro",
        "techs": ["kotlin", "android-sdk"],
        "metrics": [("Estado", "En Google Play"), ("Alcance", "Desarrollo completo")],
    },
    {
        "slug": "manipdf",
        "title_es": "ManiPDF",
        "title_en": "ManiPDF",
        "tagline_es": "Lector y editor de PDF de escritorio, multiplataforma.",
        "tagline_en": "Cross-platform desktop PDF reader and editor.",
        "summary_es": (
            "Aplicación de escritorio multiplataforma para lectura y edición de documentos PDF, "
            "con renderizado mediante pdf.js e integración de Ghostscript para el procesamiento "
            "y la compresión de archivos."
        ),
        "summary_en": (
            "Cross-platform desktop application for reading and editing PDF documents, rendering "
            "through pdf.js and integrating Ghostscript for file processing and compression."
        ),
        "body_md_es": (
            "## Por qué\n\n"
            "Las herramientas de PDF decentes son de pago o suben tus documentos a un servidor "
            "ajeno. ManiPDF hace el trabajo **en tu máquina**: ningún archivo sale del equipo.\n\n"
            "## Decisiones técnicas\n\n"
            "- **pdf.js** para el renderizado: el mismo motor que usa Firefox, probado contra "
            "  PDFs del mundo real, que rara vez cumplen la especificación al pie de la letra.\n"
            "- **Ghostscript** para comprimir y reprocesar. Integrar un binario externo dentro de "
            "  Electron obliga a resolver empaquetado por plataforma y gestión de procesos hijos.\n"
            "- **TypeScript** en todo el proyecto, porque un editor de documentos que corrompe un "
            "  archivo por un `undefined` no tiene perdón."
        ),
        "body_md_en": (
            "## Why\n\n"
            "Decent PDF tools are either paid or upload your documents to someone else's server. "
            "ManiPDF does the work **on your machine**: no file ever leaves the computer.\n\n"
            "## Technical decisions\n\n"
            "- **pdf.js** for rendering: the same engine Firefox uses, battle-tested against "
            "  real-world PDFs, which rarely follow the spec closely.\n"
            "- **Ghostscript** for compression and reprocessing. Bundling an external binary "
            "  inside Electron means solving per-platform packaging and child-process handling.\n"
            "- **TypeScript** throughout, because a document editor that corrupts a file over an "
            "  `undefined` is unforgivable."
        ),
        "role_es": "Desarrollo completo a cargo",
        "role_en": "Sole developer",
        "year": 2026,
        "featured": True,
        "video_url": "https://www.youtube.com/watch?v=rL27xHTDxtI",
        "techs": ["electron", "react", "typescript"],
        "metrics": [("Privacidad", "Procesamiento local"), ("Plataformas", "Windows · Linux")],
    },
    {
        "slug": "manifarm",
        "title_es": "ManiFarm",
        "title_en": "ManiFarm",
        "tagline_es": "Control simultáneo de varios dispositivos Android desde una sola interfaz.",
        "tagline_en": "Control several Android devices at once from a single interface.",
        "summary_es": (
            "Herramienta de escritorio para controlar y reflejar varios dispositivos Android a la "
            "vez mediante ADB, pensada para pruebas y operación en paralelo "
            "desde una sola interfaz."
        ),
        "summary_en": (
            "Desktop tool to mirror and control multiple Android devices simultaneously over ADB, "
            "built for parallel testing and operation from one interface."
        ),
        "body_md_es": (
            "## El problema\n\n"
            "Probar una aplicación Android en cinco dispositivos significa cinco cables, cinco "
            "ventanas y repetir cada gesto cinco veces.\n\n"
            "## La solución\n\n"
            "ManiFarm habla **ADB** con todos los dispositivos conectados y refleja sus pantallas "
            "en una sola ventana, con la opción de propagar la misma entrada a todos a la vez.\n\n"
            "## Lo difícil\n\n"
            "No es la interfaz: es la gestión de procesos. Cada dispositivo es un proceso hijo con "
            "su propio flujo de video que hay que iniciar, vigilar y —sobre todo— cerrar bien "
            "cuando se desconecta el cable. Los procesos huérfanos se acumulan en silencio hasta "
            "que la máquina se arrastra."
        ),
        "body_md_en": (
            "## The problem\n\n"
            "Testing an Android app on five devices means five cables, five windows and repeating "
            "every gesture five times.\n\n"
            "## The solution\n\n"
            "ManiFarm speaks **ADB** to every connected device and mirrors their screens in a "
            "single window, optionally broadcasting the same input to all of them at once.\n\n"
            "## The hard part\n\n"
            "It isn't the interface — it's process management. Each device is a child process with "
            "its own video stream to start, supervise and, above all, shut down cleanly when the "
            "cable is unplugged. Orphaned processes pile up silently until the machine crawls."
        ),
        "role_es": "Desarrollo completo a cargo",
        "role_en": "Sole developer",
        "year": 2026,
        "featured": True,
        "techs": ["electron", "typescript", "android-sdk"],
        "metrics": [("Protocolo", "ADB"), ("Uso", "Pruebas en paralelo")],
    },
    {
        "slug": "cifrado-cesar",
        "title_es": "Cifrado César",
        "title_en": "Caesar Cipher",
        "tagline_es": "Un disco giratorio que enseña el cifrado César mientras lo usás.",
        "tagline_en": "A rotating disc that teaches the Caesar cipher while you use it.",
        "summary_es": (
            "Herramienta web con un disco de dos alfabetos que gira con la clave elegida, "
            "cifrando y descifrando a la vez. Todo ocurre en el navegador: el texto "
            "nunca sale del dispositivo."
        ),
        "summary_en": (
            "Web tool built around a two-alphabet disc that rotates with the chosen shift, "
            "encrypting and decrypting at once. Everything happens in the browser: the "
            "text never leaves the device."
        ),
        "body_md_es": (
            "## Qué es\n\n"
            "El cifrado César desplaza cada letra un número fijo de posiciones en el alfabeto. "
            "Es el cifrado por sustitución más antiguo que se conoce y hoy no protege nada, "
            "pero es la puerta de entrada a entender qué significa cifrar.\n\n"
            "## Por qué lo hice\n\n"
            "Porque explicar un algoritmo con palabras es mucho más difícil que dejar que "
            "alguien mueva la clave y vea girar el disco. La pieza central no es el "
            "campo de texto: es el disco, porque es donde se entiende **por qué** sale "
            "esa letra y no otra.\n\n"
            "## Decisiones\n\n"
            "**Sin backend.** No hay servidor que pueda leer lo que escribís: el algoritmo son "
            "unas pocas líneas de JavaScript y corren en tu propio navegador. Para una "
            "herramienta que manipula texto del usuario, no tener servidor no es una "
            "limitación — es la característica.\n\n"
            "**Sin framework.** HTML, CSS y JavaScript. Cargar React para desplazar letras "
            "sería multiplicar por cien el peso de la página a cambio de nada."
        ),
        "body_md_en": (
            "## What it is\n\n"
            "The Caesar cipher shifts every letter a fixed number of positions through the "
            "alphabet. It is the oldest known substitution cipher and protects nothing today, "
            "but it is the doorway to understanding what encryption means.\n\n"
            "## Why I built it\n\n"
            "Because explaining an algorithm in words is far harder than letting someone drag "
            "the shift and watch the disc turn. The centrepiece isn't the text field — "
            "it's the disc, because that is where you see **why** one letter becomes "
            "another.\n\n"
            "## Decisions\n\n"
            "**No backend.** There is no server that could read what you type: the algorithm is "
            "a handful of lines of JavaScript running in your own browser. For a tool that "
            "handles the user's text, having no server isn't a limitation — it's the feature.\n\n"
            "**No framework.** HTML, CSS and JavaScript. Loading React to shift letters would "
            "multiply the page weight a hundredfold for nothing."
        ),
        "role_es": "Desarrollo completo a cargo",
        "role_en": "Sole developer",
        "year": 2026,
        "featured": False,
        "live_url": "https://cifrado-cesa.netlify.app/",
        "techs": ["javascript"],
        "metrics": [("Privacidad", "Todo en el navegador"), ("Dependencias", "Ninguna")],
    },
]

QUIZ_QUESTIONS = [
    {
        "es": "¿Qué ocurre si un contenedor Docker escribe datos fuera de un volumen?",
        "en": "What happens if a Docker container writes data outside a volume?",
        "difficulty": 2,
        "options_es": [
            ("Se pierden al eliminar el contenedor", True),
            ("Se guardan en el host automáticamente", False),
            ("Docker los replica a un registro", False),
            ("Se comprimen dentro de la imagen", False),
        ],
        "options_en": [
            ("They are lost when the container is removed", True),
            ("They are saved to the host automatically", False),
            ("Docker replicates them to a registry", False),
            ("They are compressed into the image", False),
        ],
        "explanation_es": (
            "La capa de escritura de un contenedor muere con él. Todo dato que deba sobrevivir "
            "va en un volumen o en un bind mount."
        ),
        "explanation_en": (
            "A container's writable layer dies with the container. Anything that must survive "
            "belongs in a volume or a bind mount."
        ),
    },
    {
        "es": "En SQLite, ¿para qué sirve activar el modo WAL?",
        "en": "In SQLite, what does enabling WAL mode achieve?",
        "difficulty": 3,
        "options_es": [
            ("Permite leer mientras hay una escritura en curso", True),
            ("Cifra la base de datos en disco", False),
            ("Habilita replicación entre servidores", False),
            ("Comprime automáticamente las tablas", False),
        ],
        "options_en": [
            ("It allows reads while a write is in progress", True),
            ("It encrypts the database on disk", False),
            ("It enables server-to-server replication", False),
            ("It compresses tables automatically", False),
        ],
        "explanation_es": (
            "Write-Ahead Logging separa las escrituras del archivo principal, de modo que los "
            "lectores no quedan bloqueados. Es la diferencia entre un sitio que responde durante "
            "una edición y uno que se congela."
        ),
        "explanation_en": (
            "Write-Ahead Logging separates writes from the main file so readers are never blocked. "
            "It is the difference between a site that responds during an edit and one that freezes."
        ),
    },
    {
        "es": "¿Por qué un Dockerfile multi-etapa produce imágenes más pequeñas?",
        "en": "Why does a multi-stage Dockerfile produce smaller images?",
        "difficulty": 2,
        "options_es": [
            ("La imagen final solo copia los artefactos, sin el compilador", True),
            ("Docker comprime las capas intermedias", False),
            ("Se eliminan los logs de construcción", False),
            ("Las capas se deduplican entre imágenes", False),
        ],
        "options_en": [
            ("The final image copies only artifacts, leaving the toolchain behind", True),
            ("Docker compresses intermediate layers", False),
            ("Build logs are stripped out", False),
            ("Layers are deduplicated across images", False),
        ],
        "explanation_es": (
            "La cadena de compilación (gcc, headers, paquetes -dev) puede pesar cientos de MB. "
            "Con multi-etapa se queda en la etapa builder y nunca llega a producción."
        ),
        "explanation_en": (
            "A build toolchain (gcc, headers, -dev packages) can weigh hundreds of MB. With "
            "multi-stage builds it stays in the builder stage and never reaches production."
        ),
    },
    {
        "es": (
            "¿Qué cabecera debe reenviar Nginx para que Django sepa que la "
            "petición llegó por HTTPS?"
        ),
        "en": "Which header must Nginx forward so Django knows the request arrived over HTTPS?",
        "difficulty": 3,
        "options_es": [
            ("X-Forwarded-Proto", True),
            ("X-Real-IP", False),
            ("X-Frame-Options", False),
            ("Strict-Transport-Security", False),
        ],
        "options_en": [
            ("X-Forwarded-Proto", True),
            ("X-Real-IP", False),
            ("X-Frame-Options", False),
            ("Strict-Transport-Security", False),
        ],
        "explanation_es": (
            "Nginx termina el TLS y habla HTTP con Django. Sin X-Forwarded-Proto y el ajuste "
            "SECURE_PROXY_SSL_HEADER, Django cree que la conexión es insegura y entra en un bucle "
            "de redirecciones."
        ),
        "explanation_en": (
            "Nginx terminates TLS and speaks plain HTTP to Django. Without X-Forwarded-Proto and "
            "the SECURE_PROXY_SSL_HEADER setting, Django thinks the connection is insecure and "
            "enters a redirect loop."
        ),
    },
    {
        "es": "¿Para qué sirve el swap en un servidor con poca RAM?",
        "en": "What is swap for on a low-RAM server?",
        "difficulty": 1,
        "options_es": [
            ("Usar disco como memoria de emergencia y evitar que el kernel mate procesos", True),
            ("Acelerar la lectura de archivos", False),
            ("Duplicar la RAM disponible sin penalización", False),
            ("Guardar copias de seguridad automáticas", False),
        ],
        "options_en": [
            ("Use disk as emergency memory so the kernel does not kill processes", True),
            ("Speed up file reads", False),
            ("Double available RAM at no cost", False),
            ("Store automatic backups", False),
        ],
        "explanation_es": (
            "El swap es un colchón, no memoria extra: es órdenes de magnitud más lento que la RAM. "
            "Evita el OOM killer, pero si el sistema vive en swap, el problema es otro."
        ),
        "explanation_en": (
            "Swap is a cushion, not extra memory: it is orders of magnitude slower than RAM. It "
            "prevents the OOM killer, but if a system lives in swap, the real problem is elsewhere."
        ),
    },
    {
        "es": "¿Por qué no conviene ejecutar procesos como root dentro de un contenedor?",
        "en": "Why should you avoid running processes as root inside a container?",
        "difficulty": 2,
        "options_es": [
            ("Una fuga del contenedor daría privilegios elevados en el host", True),
            ("Los contenedores no arrancan como root", False),
            ("Consume más memoria", False),
            ("Docker lo bloquea por defecto", False),
        ],
        "options_en": [
            ("A container escape would grant elevated privileges on the host", True),
            ("Containers cannot start as root", False),
            ("It uses more memory", False),
            ("Docker blocks it by default", False),
        ],
        "explanation_es": (
            "El aislamiento de contenedores es bueno, no perfecto. Correr sin privilegios hace "
            "que una vulnerabilidad de escape aterrice en un usuario sin permisos y no en root."
        ),
        "explanation_en": (
            "Container isolation is good, not perfect. Running unprivileged means an escape "
            "vulnerability lands on an unprivileged user rather than on root."
        ),
    },
    {
        "es": "¿Qué problema resuelve `--max-requests` en Gunicorn?",
        "en": "What problem does Gunicorn's `--max-requests` solve?",
        "difficulty": 3,
        "options_es": [
            ("Recicla los workers periódicamente y neutraliza fugas de memoria lentas", True),
            ("Limita las peticiones por segundo de cada cliente", False),
            ("Define el tamaño máximo del cuerpo de la petición", False),
            ("Controla cuántos workers se crean", False),
        ],
        "options_en": [
            ("It recycles workers periodically, neutralising slow memory leaks", True),
            ("It rate-limits requests per client", False),
            ("It sets the maximum request body size", False),
            ("It controls how many workers are spawned", False),
        ],
        "explanation_es": (
            "Un worker que atiende millones de peticiones acumula memoria que nunca se libera del "
            "todo. Reiniciarlo cada N peticiones convierte una fuga lenta en un no-problema."
        ),
        "explanation_en": (
            "A worker serving millions of requests accumulates memory that is never fully "
            "released. Restarting it every N requests turns a slow leak into a non-issue."
        ),
    },
    {
        "es": (
            "En CI/CD, ¿por qué es mala idea construir imágenes Docker en el "
            "propio servidor de producción?"
        ),
        "en": "In CI/CD, why is building Docker images on the production server a bad idea?",
        "difficulty": 2,
        "options_es": [
            ("Consume RAM y disco que el servicio en vivo necesita", True),
            ("Docker no permite construir en producción", False),
            ("Las imágenes resultantes son incompatibles", False),
            ("Obliga a exponer el puerto del registro", False),
        ],
        "options_en": [
            ("It consumes RAM and disk the live service needs", True),
            ("Docker forbids building in production", False),
            ("The resulting images are incompatible", False),
            ("It forces you to expose the registry port", False),
        ],
        "explanation_es": (
            "Compilar es la operación más cara del ciclo. Hacerlo en un droplet de 512 MB compite "
            "directamente con el servicio que está atendiendo visitantes."
        ),
        "explanation_en": (
            "Building is the most expensive step of the cycle. Doing it on a 512 MB droplet "
            "competes directly with the service that is serving visitors."
        ),
    },
]


class Command(BaseCommand):
    help = "Carga el contenido inicial del portafolio (perfil, proyectos, blog y juegos)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra el contenido existente antes de cargar. No toca usuarios ni mensajes.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        # Portadas repuestas en esta pasada. Se informa aparte porque es lo
        # que distingue un despliegue limpio de uno que ya tenía imágenes.
        self.portadas = 0

        if options["reset"]:
            self.stdout.write(self.style.WARNING("Borrando contenido existente…"))
            Project.objects.all().delete()
            Post.objects.all().delete()
            Game.objects.all().delete()
            Profile.objects.all().delete()
            Technology.objects.all().delete()

        technologies = self._seed_technologies()
        profile = self._seed_profile()
        self._seed_projects(technologies)
        self._seed_blog()
        self._seed_games()

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Contenido cargado para {profile.full_name}\n"
                f"  {Technology.objects.count()} tecnologías · "
                f"{Project.objects.count()} proyectos · "
                f"{Post.objects.count()} posts · "
                f"{Game.objects.count()} juegos · "
                f"{QuizQuestion.objects.count()} preguntas"
                + (
                    f"\n  {self.portadas} portadas repuestas desde el repositorio"
                    if self.portadas
                    else ""
                )
            )
        )

    # ── perfil ────────────────────────────────────────────────

    def _seed_profile(self) -> Profile:
        profile, _created = Profile.objects.update_or_create(
            pk=Profile.objects.values_list("pk", flat=True).first() or None,
            defaults={
                "full_name": "PedriniDev",
                "role_es": "Desarrollo de Software · Mobile · Backend",
                "role_en": "Software Development · Mobile · Backend",
                "headline_es": "Construyo software y opero la infraestructura donde vive.",
                "headline_en": "I build software and run the infrastructure it lives on.",
                "bio_es": (
                    "Estudiante de Ingeniería de Sistemas en la Universidad Pública de El Alto, "
                    "en noveno semestre, con una aplicación Android **publicada en producción** y "
                    "varios proyectos propios de escritorio y web.\n\n"
                    "Combino el desarrollo de software con experiencia práctica en redes y soporte "
                    "técnico, lo que me permite aportar tanto en un equipo de desarrollo como en "
                    "una unidad de TI.\n\n"
                    "Este sitio es, además de un portafolio, una demostración: está contenerizado, "
                    "se despliega solo con GitHub Actions y corre en un servidor mínimo que "
                    "podés ver monitorizado en vivo más abajo."
                ),
                "bio_en": (
                    "Systems Engineering student at Universidad Pública de El Alto, ninth "
                    "semester, with an Android app **live in production** and several personal "
                    "desktop and web projects.\n\n"
                    "I combine software development with hands-on experience in networking and "
                    "technical support, which lets me contribute both to a development team and "
                    "to an IT unit.\n\n"
                    "This site is a demonstration as much as a portfolio: it is containerised, "
                    "deploys itself through GitHub Actions and runs on a minimal server you can "
                    "watch live below."
                ),
                "email": "contacto@pedrinidev.com",
                # El teléfono NO va en el código. Se carga desde el Admin.
                #
                # El correo sí se queda: es la vía de contacto principal y ya
                # está en el CV que se reparte. El número es distinto — un
                # repositorio público lo vuelve trivial de recolectar en masa,
                # y un móvil recolectado no se puede filtrar como un correo.
                #
                # La página de contacto solo dibuja el bloque de WhatsApp si
                # hay número, así que sin él no se rompe nada: simplemente no
                # aparece hasta que lo cargues en el Admin.
                "phone": "",
                "location_es": "El Alto — La Paz, Bolivia",
                "location_en": "El Alto — La Paz, Bolivia",
                "availability_es": "Tiempo completo · Incorporación inmediata · El Alto o La Paz",
                "availability_en": "Full time · Available immediately · El Alto or La Paz",
            },
        )

        for order, (name, url, icon) in enumerate(
            [
                ("GitHub", "https://github.com/pedrinidev", "github"),
                ("LinkedIn", "https://linkedin.com/in/pedromamans", "linkedin"),
                ("Correo", "mailto:contacto@pedrinidev.com", "mail"),
            ]
        ):
            SocialLink.objects.update_or_create(
                profile=profile,
                name=name,
                defaults={"url": url, "icon": icon, "order": order},
            )

        for group_order, (name_es, name_en, skills) in enumerate(SKILL_GROUPS):
            group, _ = SkillGroup.objects.update_or_create(
                profile=profile,
                name_es=name_es,
                defaults={"name_en": name_en, "order": group_order},
            )
            for skill_order, (skill_name, level, primary) in enumerate(skills):
                Skill.objects.update_or_create(
                    group=group,
                    name=skill_name,
                    defaults={"level": level, "is_primary": primary, "order": skill_order},
                )

        ExperienceItem.objects.update_or_create(
            profile=profile,
            role_es="Pasante de Soporte Técnico",
            organization="Gobierno Autónomo Municipal de El Alto",
            defaults={
                "role_en": "Technical Support Intern",
                "start_date": date(2024, 10, 1),
                "end_date": date(2024, 11, 30),
                "description_es": (
                    "Apoyo al área de soporte en el mantenimiento del parque de equipos de la "
                    "institución."
                ),
                "description_en": (
                    "Supported the IT help desk in maintaining the institution's computer fleet."
                ),
                "highlights_es": (
                    "Mantenimientos preventivos y correctivos sobre equipos de cómputo\n"
                    "Atención de incidencias reportadas por usuarios\n"
                    "Instalación y configuración de Windows y Linux\n"
                    "Apoyo en cableado y conectividad de red"
                ),
                "highlights_en": (
                    "Preventive and corrective maintenance on workstations\n"
                    "Handling of user-reported incidents\n"
                    "Windows and Linux installation and configuration\n"
                    "Support with cabling and network connectivity"
                ),
                "order": 0,
            },
        )
        return profile

    # ── tecnologías y proyectos ───────────────────────────────

    def _seed_technologies(self) -> dict[str, Technology]:
        created: dict[str, Technology] = {}
        for order, (name, slug, category, color) in enumerate(TECHNOLOGIES):
            tech, _ = Technology.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": category,
                    "color": color,
                    "icon": slug,
                    "order": order,
                },
            )
            created[slug] = tech
        return created

    def _attach_cover(self, project: Project) -> bool:
        """Pone la portada que viene en el repositorio, si aún no tiene.

        Las imágenes se suben desde el Admin y viven en MEDIA_ROOT, que está
        fuera del control de versiones. En un servidor recién creado ese
        directorio está vacío: sin esto, un despliegue limpio levantaría el
        sitio con las cinco tarjetas de proyecto mostrando iniciales en vez
        de capturas, y habría que volver a subirlas a mano una por una.

        Solo actúa si el proyecto NO tiene portada: nunca pisa una imagen
        que se haya subido después desde el Admin.
        """
        if project.cover:
            return False
        origen = SEED_ASSETS / "projects" / f"{project.slug}-cover.png"
        if not origen.exists():
            return False
        with origen.open("rb") as fh:
            project.cover.save(origen.name, File(fh), save=True)
        return True

    def _seed_projects(self, technologies: dict[str, Technology]) -> None:
        from modules.projects.models import ProjectMetric

        for order, data in enumerate(PROJECTS):
            techs = data.pop("techs")
            metrics = data.pop("metrics")
            project, _ = Project.objects.update_or_create(
                slug=data["slug"],
                defaults={**data, "status": "published", "order": order},
            )
            if self._attach_cover(project):
                self.portadas += 1
            project.technologies.set([technologies[slug] for slug in techs])
            for metric_order, (label, value) in enumerate(metrics):
                ProjectMetric.objects.update_or_create(
                    project=project,
                    label_es=label,
                    defaults={"label_en": label, "value": value, "order": metric_order},
                )

    # ── blog ──────────────────────────────────────────────────

    def _seed_blog(self) -> None:
        category, _ = Category.objects.update_or_create(
            slug="infraestructura",
            defaults={
                "name_es": "Infraestructura",
                "name_en": "Infrastructure",
                "description_es": "Servidores, contenedores y despliegue.",
                "description_en": "Servers, containers and deployment.",
                "order": 0,
            },
        )
        tags = []
        for slug, es, en in [
            ("docker", "Docker", "Docker"),
            ("digitalocean", "DigitalOcean", "DigitalOcean"),
            ("optimizacion", "Optimización", "Optimisation"),
        ]:
            tag, _ = Tag.objects.update_or_create(
                slug=slug, defaults={"name_es": es, "name_en": en}
            )
            tags.append(tag)

        post, _ = Post.objects.update_or_create(
            slug="portafolio-en-512-mb-de-ram",
            defaults={
                "title_es": "Cómo hacer caber un portafolio completo en 512 MB de RAM",
                "title_en": "Fitting a complete portfolio into 512 MB of RAM",
                "excerpt_es": (
                    "512 MB de RAM obligan a tomar decisiones. Estas son las que tomé, con sus "
                    "números."
                ),
                "excerpt_en": (
                    "512 MB of RAM forces decisions. These are the ones I made, with their "
                    "numbers."
                ),
                "body_md_es": (
                    "## El presupuesto\n\n"
                    "Un droplet de 512 MB no es un servidor pequeño: es un servidor **lleno** "
                    "antes de que despliegues nada.\n\n"
                    "| Componente | RAM |\n|---|---|\n"
                    "| Ubuntu 24.04 | ~130 MB |\n| Docker daemon | ~70 MB |\n"
                    "| Gunicorn + Django | ~150 MB |\n| Nginx | ~15 MB |\n"
                    "| **Total** | **~365 MB** |\n\n"
                    "Quedan unos 145 MB de margen. Todo lo que sigue se deriva de ese número.\n\n"
                    "## Regla 1: el servidor no compila\n\n"
                    "Un build de Astro pide entre 400 y 800 MB de pico. Ejecutarlo aquí significa "
                    "*thrashing* de swap durante diez minutos o, directamente, un OOM kill.\n\n"
                    "```bash\n"
                    "# Esto es lo único que corre el servidor:\n"
                    "docker compose pull && docker compose up -d\n"
                    "```\n\n"
                    "El build vive en GitHub Actions, que además es gratis para repos públicos.\n\n"
                    "## Regla 2: nada de Redis, ni Postgres, ni Node\n\n"
                    "Cada uno cuesta entre 40 y 120 MB. En su lugar: caché en memoria del proceso, "
                    "SQLite en modo WAL y HTML estático servido por Nginx.\n\n"
                    "## Regla 3: rotar los logs de Docker\n\n"
                    "La causa de caída más común en droplets pequeños no es la RAM: es el disco "
                    "lleno de logs JSON que nadie configuró para rotar.\n\n"
                    "```json\n"
                    '{ "log-driver": "json-file",\n'
                    '  "log-opts": { "max-size": "10m", "max-file": "3" } }\n'
                    "```\n\n"
                    "El dashboard de métricas de este sitio muestra el resultado en vivo."
                ),
                "body_md_en": (
                    "## The budget\n\n"
                    "A 512 MB droplet is not a small server: it is a **full** server before you "
                    "deploy anything.\n\n"
                    "| Component | RAM |\n|---|---|\n"
                    "| Ubuntu 24.04 | ~130 MB |\n| Docker daemon | ~70 MB |\n"
                    "| Gunicorn + Django | ~150 MB |\n| Nginx | ~15 MB |\n"
                    "| **Total** | **~365 MB** |\n\n"
                    "That leaves roughly 145 MB of headroom. Everything below follows from it.\n\n"
                    "## Rule 1: the server does not compile\n\n"
                    "An Astro build peaks at 400—800 MB. Running it here means ten minutes of swap "
                    "thrashing or an outright OOM kill.\n\n"
                    "```bash\n"
                    "# This is all the server ever runs:\n"
                    "docker compose pull && docker compose up -d\n"
                    "```\n\n"
                    "## Rule 2: no Redis, no Postgres, no Node\n\n"
                    "Each costs 40—120 MB. Instead: in-process cache, SQLite in WAL mode and "
                    "static HTML served by Nginx.\n\n"
                    "## Rule 3: rotate Docker logs\n\n"
                    "The most common cause of failure on small droplets is not RAM — it is a disk "
                    "filled with JSON logs nobody configured to rotate."
                ),
                "category": category,
                "status": "published",
            },
        )
        post.tags.set(tags)

    # ── juegos ────────────────────────────────────────────────

    def _seed_games(self) -> None:
        quiz, _ = Game.objects.update_or_create(
            slug="devops-quiz",
            defaults={
                "kind": GameKind.QUIZ,
                "name_es": "Quiz DevOps",
                "name_en": "DevOps Quiz",
                "description_es": "Ocho preguntas sobre contenedores, servidores y despliegue.",
                "description_en": "Eight questions on containers, servers and deployment.",
                "icon": "terminal",
                # Desactivado a propósito, no borrado: las ocho preguntas
                # bilingües y la corrección en servidor siguen intactas y
                # vuelven al sitio con una casilla en el Admin.
                "enabled": False,
                "order": 0,
                "max_plausible_score": 240,
            },
        )
        for order, item in enumerate(QUIZ_QUESTIONS):
            question, _ = QuizQuestion.objects.update_or_create(
                game=quiz,
                text_es=item["es"],
                defaults={
                    "text_en": item["en"],
                    "difficulty": item["difficulty"],
                    "explanation_es": item["explanation_es"],
                    "explanation_en": item["explanation_en"],
                    "enabled": True,
                    "order": order,
                },
            )
            question.options.all().delete()
            for opt_order, ((text_es, correct), (text_en, _c)) in enumerate(
                zip(item["options_es"], item["options_en"], strict=True)
            ):
                QuizOption.objects.create(
                    question=question,
                    text_es=text_es,
                    text_en=text_en,
                    is_correct=correct,
                    order=opt_order,
                )

        Game.objects.update_or_create(
            slug="snake",
            defaults={
                "kind": GameKind.ARCADE,
                "name_es": "Snake",
                "name_en": "Snake",
                "description_es": "El clásico, con controles táctiles y estética del sitio.",
                "description_en": "The classic, with touch controls and the site's aesthetic.",
                "icon": "snake",
                "enabled": True,
                "order": 1,
                "max_plausible_score": 5_000,
                "min_duration_ms": 3_000,
            },
        )
