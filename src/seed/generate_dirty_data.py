"""
Generador de datos sucios para SocialLab.

Simula la exportación de una red social que cerró.
Los datos tienen problemas INTENCIONADOS que los estudiantes
deben resolver con Spark ETL.

Uso:
    python -m src.seed.generate_dirty_data

Genera archivos en data/raw/:
    - users.json       (usuarios con duplicados, encoding roto, campos faltantes)
    - posts.json       (posts con 5 formatos de fecha, hashtags inconsistentes, spam)
    - likes.json       (likes con referencias huérfanas)
    - follows.json     (follows circulares y a usuarios borrados)
"""

import json
import random
import string
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import RAW_PATH

random.seed(42)

# --- Config ---
NUM_USERS = 3000
NUM_POSTS = 80000
NUM_LIKES = 200000
NUM_FOLLOWS = 50000
SPAM_USER_RATIO = 0.05  # 5% son bots/spam
DUPLICATE_USER_RATIO = 0.08  # 8% usuarios duplicados
ORPHAN_RATIO = 0.03  # 3% referencias a IDs que no existen
MISSING_FIELD_RATIO = 0.04  # 4% con campos faltantes

# --- Vocabulario ---
TOPICS = {
    "tech": ["IA", "machinelearning", "python", "bigdata", "spark", "mongodb", "neo4j",
             "deeplearning", "cloud", "devops", "api", "docker", "kubernetes", "datos"],
    "social": ["actualidad", "politica", "economia", "educacion", "salud", "medioambiente",
               "igualdad", "cultura", "sociedad", "derechos"],
    "entertainment": ["musica", "cine", "series", "gaming", "deportes", "futbol",
                      "libros", "arte", "fotografia", "viajes"],
    "academic": ["universidad", "investigacion", "ciencia", "estadistica", "matematicas",
                 "tesis", "paper", "conferencia", "laboratorio"],
}

NAMES_FIRST = [
    "María", "Pablo", "Lucía", "Carlos", "Ana", "David", "Laura", "Javier",
    "Carmen", "Daniel", "Sara", "Andrés", "Elena", "Miguel", "Sofía", "Jorge",
    "Paula", "Alejandro", "Marta", "Raúl", "Claudia", "Fernando", "Irene",
    "Diego", "Nuria", "Álvaro", "Patricia", "Sergio", "Rosa", "Adrián",
    "Valentina", "Gabriel", "Camila", "Mateo", "Isabella", "Sebastián",
    "Mariana", "Santiago", "Andrea", "Nicolás",
]

NAMES_LAST = [
    "García", "Rodríguez", "Martínez", "López", "González", "Hernández",
    "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera", "Gómez",
    "Díaz", "Cruz", "Morales", "Reyes", "Gutiérrez", "Ortiz", "Ruiz",
    "Delgado", "Vargas", "Castillo", "Mendoza", "Rojas",
]

POST_TEMPLATES = [
    "Acabo de descubrir {hashtag}, increíble lo que se puede hacer",
    "Alguien más está usando {hashtag}? Quiero saber opiniones",
    "Hoy en clase hablamos de {hashtag} y me voló la cabeza",
    "{hashtag} es el futuro, cambien mi opinión",
    "No entiendo por qué la gente no habla más de {hashtag}",
    "Thread sobre {hashtag}: lo que necesitas saber 🧵",
    "Mi experiencia con {hashtag} después de 3 meses",
    "Recomiendo a todos que prueben {hashtag}",
    "Unpopular opinion: {hashtag} está sobrevalorado",
    "Qué recursos recomiendan para aprender {hashtag}?",
    "Buenos días! Hoy toca trabajar con {hashtag}",
    "No puedo creer lo rápido que avanza {hashtag}",
    "{hashtag} + {hashtag2} = 🔥",
    "Publicando mi primer proyecto con {hashtag}",
    "Alguien quiere colaborar en un proyecto de {hashtag}?",
]

SPAM_TEMPLATES = [
    "GANA DINERO DESDE CASA!!!! {hashtag} {hashtag} {hashtag}",
    "Compra ya!!!! Oferta increíble {hashtag}",
    "CLICK AQUÍ para ganar 1000€ gratis {hashtag}",
    "No creerás lo que pasó!!!! {hashtag} {hashtag}",
    "SORTEO GRATIS {hashtag} {hashtag} {hashtag} {hashtag}",
    "Sígueme y te sigo!!!! {hashtag}",
]

DOMAINS = ["gmail.com", "hotmail.com", "yahoo.es", "outlook.com", "universidad.edu",
           "mail.com", "protonmail.com", "edu.es"]

FEATURED_INFLUENCERS = [
    ("ibai", "Ibai Demo", "entertainment", ["gaming", "deportes", "futbol"]),
    ("knekro", "Knekro Demo", "entertainment", ["gaming", "series", "cine"]),
    ("shakira", "Shakira Demo", "entertainment", ["musica", "cultura", "viajes"]),
    ("rosalia", "Rosalia Demo", "entertainment", ["musica", "arte", "cultura"]),
    ("ibaboreal", "Ibai Boreal Demo", "entertainment", ["gaming", "deportes", "futbol"]),
    ("auronplay", "Auronplay Demo", "entertainment", ["gaming", "series", "humor"]),
    ("elrubius", "Rubius Demo", "entertainment", ["gaming", "internet", "humor"]),
    ("vegetta777", "Vegetta Demo", "entertainment", ["gaming", "minecraft", "series"]),
    ("cristiano", "Cristiano Demo", "entertainment", ["deportes", "futbol", "salud"]),
    ("leomessi", "Leo Messi Demo", "entertainment", ["deportes", "futbol", "viajes"]),
    ("elonmusk", "Elon Musk Demo", "tech", ["IA", "cloud", "datos"]),
    ("taylorswift", "Taylor Swift Demo", "entertainment", ["musica", "arte", "cultura"]),
    ("jbalvin", "J Balvin Demo", "entertainment", ["musica", "viajes", "cultura"]),
    ("badbunny", "Bad Bunny Demo", "entertainment", ["musica", "arte", "cultura"]),
    ("karolg", "Karol G Demo", "entertainment", ["musica", "cultura", "viajes"]),
    ("aitana", "Aitana Demo", "entertainment", ["musica", "arte", "series"]),
    ("bizarrap", "Bizarrap Demo", "entertainment", ["musica", "tech", "arte"]),
    ("maria_becerra", "Maria Becerra Demo", "entertainment", ["musica", "cultura", "viajes"]),
    ("lola_indigo", "Lola Indigo Demo", "entertainment", ["musica", "arte", "deportes"]),
    ("david_bisbal", "David Bisbal Demo", "entertainment", ["musica", "cultura", "viajes"]),
    ("paulo_londra", "Paulo Londra Demo", "entertainment", ["musica", "arte", "cultura"]),
    ("misterjagger", "Mister Jagger Demo", "entertainment", ["humor", "internet", "series"]),
    ("thegrefg", "TheGrefg Demo", "entertainment", ["gaming", "deportes", "internet"]),
    ("willyrex", "Willyrex Demo", "entertainment", ["gaming", "minecraft", "internet"]),
    ("alexelcapo", "Alexelcapo Demo", "entertainment", ["gaming", "series", "cine"]),
    ("illojuan", "IlloJuan Demo", "entertainment", ["gaming", "humor", "cultura"]),
    ("mangelrogel", "Mangel Demo", "entertainment", ["humor", "gaming", "internet"]),
    ("cristininik", "Cristinini Demo", "entertainment", ["gaming", "deportes", "series"]),
    ("gemita", "Gemita Demo", "entertainment", ["gaming", "internet", "viajes"]),
    ("messi_fanlab", "Messi FanLab Demo", "entertainment", ["futbol", "deportes", "datos"]),
    ("mrbeast", "MrBeast Demo", "entertainment", ["internet", "videos", "retos"]),
    ("mkbhd", "MKBHD Demo", "tech", ["tech", "IA", "cloud"]),
    ("lexfridman", "Lex Fridman Demo", "tech", ["IA", "ciencia", "podcast"]),
    ("sama", "Sam Altman Demo", "tech", ["IA", "startup", "datos"]),
    ("yannlecun", "Yann LeCun Demo", "tech", ["IA", "deeplearning", "ciencia"]),
    ("feifeili", "Fei-Fei Li Demo", "tech", ["IA", "investigacion", "ciencia"]),
    ("barackobama", "Obama Demo", "social", ["politica", "sociedad", "educacion"]),
    ("greta", "Greta Demo", "social", ["medioambiente", "sociedad", "derechos"]),
    ("nasa", "NASA Demo", "academic", ["ciencia", "datos", "investigacion"]),
    ("cern", "CERN Demo", "academic", ["ciencia", "laboratorio", "investigacion"]),
    ("mit", "MIT Demo", "academic", ["universidad", "ciencia", "datos"]),
    ("stanford", "Stanford Demo", "academic", ["universidad", "IA", "investigacion"]),
]

SPAMMER_PERSONAS = [
    ("ofertas_flash_24h", "Ofertas Flash 24h"),
    ("cripto_gana_ya", "Cripto Gana Ya"),
    ("sorteos_gratis_vip", "Sorteos Gratis VIP"),
    ("trabaja_desde_casa_777", "Trabaja Desde Casa"),
    ("seguidores_baratos", "Seguidores Baratos"),
    ("premios_click_aqui", "Premios Click Aqui"),
    ("cupones_milagro", "Cupones Milagro"),
    ("dinero_rapido_app", "Dinero Rapido App"),
    ("bot_inversion_segura", "Inversion Segura Bot"),
    ("mega_descuentos_now", "Mega Descuentos Now"),
    ("regalos_por_dm", "Regalos Por DM"),
    ("casino_bonus_total", "Casino Bonus Total"),
    ("nft_rocket_club", "NFT Rocket Club"),
    ("iphone_gratis_real", "iPhone Gratis Real"),
    ("viraliza_tu_cuenta", "Viraliza Tu Cuenta"),
    ("prestamos_sin_banco", "Prestamos Sin Banco"),
    ("alerta_oferton", "Alerta Oferton"),
    ("drop_shipping_pro", "Drop Shipping Pro"),
    ("followers_boost_ai", "Followers Boost AI"),
    ("crypto_airdrop_bot", "Crypto Airdrop Bot"),
]

INFLUENCER_POST_TEMPLATES = [
    "Hoy toca directo sobre #{tag} y comunidad, se viene tarde larga",
    "Me flipa ver como crece #{tag}; gracias por estar ahi",
    "Nuevo proyecto mezclando #{tag} con #{tag2}, necesito opiniones",
    "Pregunta seria: que creador deberia invitar para hablar de #{tag}?",
    "Estoy preparando contenido de #{tag}; mandad dudas para el proximo directo",
    "La comunidad de #{tag} esta en otro nivel esta semana",
]

SPAM_BURST_TEXTS = [
    "GANA DINERO YA!!!! #dinero #gratis #oferta",
    "CLICK AQUI premio seguro #gratis #sorteo #oferta",
    "Multiplica tus ingresos hoy #cripto #dinero #urgente",
    "Seguidores reales en minutos #followers #gratis #viral",
]


def _random_id(prefix: str, n: int = 8) -> str:
    return f"{prefix}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=n))}"


def _broken_encoding(text: str) -> str:
    """Simula encoding roto: á→Ã¡, é→Ã©, etc."""
    replacements = {
        "á": "Ã¡", "é": "Ã©", "í": "Ã\xad", "ó": "Ã³", "ú": "Ãº",
        "ñ": "Ã±", "ü": "Ã¼", "Á": "Ã\x81", "É": "Ã\x89",
    }
    for orig, broken in replacements.items():
        text = text.replace(orig, broken)
    return text


def _random_timestamp(base: datetime) -> str:
    """Genera timestamp en 1 de 5 formatos diferentes (el problema gordo del ETL)."""
    dt = base + timedelta(
        days=random.randint(-180, 0),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    fmt = random.choice(["iso", "epoch", "us", "eu", "relative"])
    if fmt == "iso":
        return dt.isoformat()
    elif fmt == "epoch":
        return str(int(dt.timestamp()))
    elif fmt == "us":
        return dt.strftime("%m/%d/%Y %I:%M %p")
    elif fmt == "eu":
        return dt.strftime("%d-%m-%Y %H:%M")
    elif fmt == "relative":
        delta = datetime.now(timezone.utc) - dt
        if delta.days > 0:
            return f"hace {delta.days} días"
        else:
            return f"hace {delta.seconds // 3600} horas"


def _dirty_hashtag(tag: str) -> str:
    """Hashtag inconsistente: a veces con #, a veces sin, mayúsculas random."""
    choices = [
        f"#{tag}",
        tag,
        f"#{tag.upper()}",
        f"#{tag.capitalize()}",
        f" #{tag} ",
        f"#{tag}.",
    ]
    return random.choice(choices)


def _demo_timestamp(days_ago: int, minutes_offset: int = 0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago, minutes=minutes_offset)
    return dt.isoformat()


# --- Generators ---

def generate_users() -> list[dict]:
    """Genera usuarios con duplicados, encoding roto, campos faltantes."""
    users = []
    base_users = []

    for i, (username, display_name, topic, tags) in enumerate(FEATURED_INFLUENCERS):
        users.append({
            "_id": f"u_inf_{i:03d}",
            "username": username,
            "display_name": display_name,
            "email": f"{username}@influencers.demo",
            "bio": (
                "Cuenta demo inspirada en un perfil publico. "
                f"Contenido sobre {', '.join(tags[:3])}."
            ),
            "topic": topic,
            "is_spam": False,
            "created_at": _demo_timestamp(180 - (i % 80)),
            "origin": "seed",
        })

    for i, (username, display_name) in enumerate(SPAMMER_PERSONAS):
        users.append({
            "_id": f"u_spam_{i:03d}",
            "username": username,
            "display_name": display_name,
            "email": f"{username}@spam.demo",
            "bio": "FOLLOW ME!! BEST DEALS!! CLICK AQUI!!",
            "topic": "tech",
            "is_spam": True,
            "created_at": _demo_timestamp(30 + i),
            "origin": "seed",
        })

    for i in range(NUM_USERS):
        first = random.choice(NAMES_FIRST)
        last = random.choice(NAMES_LAST)
        topic = random.choice(list(TOPICS.keys()))
        is_spam = random.random() < SPAM_USER_RATIO

        username = f"{first.lower()}_{last.lower()}_{random.randint(1, 999)}"
        # Some usernames have spaces or special chars (dirty)
        if random.random() < 0.05:
            username = f"{first} {last} {random.randint(1, 99)}"

        user = {
            "_id": f"u_{i:05d}",
            "username": username,
            "display_name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}@{random.choice(DOMAINS)}",
            "bio": f"Fan de {topic}" if not is_spam else "FOLLOW ME!! BEST DEALS!!",
            "topic": topic,
            "is_spam": is_spam,
            "created_at": _random_timestamp(datetime.now(timezone.utc)),
            "origin": "seed",
        }

        # Missing fields (4%)
        if random.random() < MISSING_FIELD_RATIO:
            field_to_remove = random.choice(["email", "display_name", "bio"])
            user.pop(field_to_remove, None)

        # Broken encoding (10%)
        if random.random() < 0.10:
            for key in ["display_name", "bio"]:
                if key in user:
                    user[key] = _broken_encoding(user[key])

        users.append(user)
        base_users.append(user)

    # Generate duplicates (same email, different username or vice versa)
    num_dupes = int(NUM_USERS * DUPLICATE_USER_RATIO)
    for _ in range(num_dupes):
        original = random.choice(base_users)
        dupe = dict(original)
        dupe["_id"] = _random_id("u")

        if random.random() < 0.5:
            # Same email, different username
            dupe["username"] = _random_id("user")
        else:
            # Same username variant, different email
            dupe["email"] = f"{_random_id('x')}@{random.choice(DOMAINS)}"
            if "username" in original:
                dupe["username"] = original["username"].replace("_", ".")

        users.append(dupe)

    random.shuffle(users)
    return users


def generate_posts(users: list[dict]) -> list[dict]:
    """Genera posts con hashtags inconsistentes, timestamps variados, spam."""
    posts = []
    user_ids = [u["_id"] for u in users]
    spam_user_ids = [u["_id"] for u in users if u.get("is_spam", False)]
    normal_user_ids = [u["_id"] for u in users if not u.get("is_spam", False)]
    featured_users = [u for u in users if u["_id"].startswith("u_inf_")]
    demo_spammers = [u for u in users if u["_id"].startswith("u_spam_")]
    user_map = {u["_id"]: u for u in users}

    for i in range(NUM_POSTS):
        is_spam_post = random.random() < 0.06

        if is_spam_post and spam_user_ids:
            uid = random.choice(spam_user_ids)
            topic = random.choice(list(TOPICS.keys()))
            tags = random.choices(TOPICS[topic], k=random.randint(2, 5))
            text = random.choice(SPAM_TEMPLATES).format(
                hashtag=_dirty_hashtag(tags[0]),
                hashtag2=_dirty_hashtag(tags[-1]) if len(tags) > 1 else "",
            )
        else:
            uid = random.choice(normal_user_ids) if normal_user_ids else random.choice(user_ids)
            user = user_map.get(uid, {})
            topic = user.get("topic", random.choice(list(TOPICS.keys())))
            tags = random.choices(TOPICS[topic], k=random.randint(1, 3))
            text = random.choice(POST_TEMPLATES).format(
                hashtag=_dirty_hashtag(tags[0]),
                hashtag2=_dirty_hashtag(tags[-1]) if len(tags) > 1 else "",
            )

        hashtags = [_dirty_hashtag(t) for t in tags]

        post = {
            "_id": f"p_{i:06d}",
            "user_id": uid,
            "text": text,
            "hashtags": hashtags,
            "created_at": _random_timestamp(datetime.now(timezone.utc)),
            "likes_count": random.randint(0, 500),
            "origin": "seed",
        }

        # Missing user_id (creates orphan)
        if random.random() < MISSING_FIELD_RATIO:
            field = random.choice(["user_id", "text", "created_at"])
            if field == "user_id":
                post["user_id"] = _random_id("u_deleted")  # orphan reference
            elif field == "text":
                post.pop("text", None)
            else:
                post.pop("created_at", None)

        # Broken encoding in text
        if random.random() < 0.08 and "text" in post:
            post["text"] = _broken_encoding(post["text"])

        posts.append(post)

    # Spam burst: one bot posts 100 times in a row with same text
    if spam_user_ids:
        spammer = random.choice(spam_user_ids)
        burst_text = "GANA DINERO YA!!!! #dinero #gratis #oferta"
        base_time = datetime.now(timezone.utc) - timedelta(days=10)
        for j in range(100):
            posts.append({
                "_id": f"p_spam_{j:04d}",
                "user_id": spammer,
                "text": burst_text,
                "hashtags": ["#dinero", "GRATIS", " #oferta"],
                "created_at": (base_time + timedelta(seconds=j * 10)).isoformat(),
                "likes_count": 0,
                "origin": "seed",
            })

    for user in featured_users:
        idx = int(user["_id"].split("_")[-1])
        _, _, _, tags = FEATURED_INFLUENCERS[idx]
        for j in range(8):
            tag = tags[j % len(tags)]
            tag2 = tags[(j + 1) % len(tags)]
            text = random.choice(INFLUENCER_POST_TEMPLATES).format(tag=tag, tag2=tag2)
            posts.append({
                "_id": f"p_inf_{idx:03d}_{j:02d}",
                "user_id": user["_id"],
                "text": text,
                "hashtags": [_dirty_hashtag(tag), _dirty_hashtag(tag2)],
                "created_at": _demo_timestamp(days_ago=(j % 14) + 1, minutes_offset=idx * 3 + j),
                "likes_count": random.randint(800, 20000),
                "origin": "seed",
            })

    for user in demo_spammers:
        idx = int(user["_id"].split("_")[-1])
        repeated_text = SPAM_BURST_TEXTS[idx % len(SPAM_BURST_TEXTS)]
        base_time = datetime.now(timezone.utc) - timedelta(days=idx % 8)
        for j in range(14):
            text = repeated_text if j < 10 else random.choice(SPAM_TEMPLATES).format(
                hashtag="#gratis",
                hashtag2="#oferta",
            )
            posts.append({
                "_id": f"p_spammer_{idx:03d}_{j:02d}",
                "user_id": user["_id"],
                "text": text,
                "hashtags": ["#gratis", "#oferta", "#dinero", "#click"],
                "created_at": (base_time + timedelta(seconds=j * 15)).isoformat(),
                "likes_count": random.randint(0, 3),
                "origin": "seed",
            })

    random.shuffle(posts)
    return posts


def generate_likes(users: list[dict], posts: list[dict]) -> list[dict]:
    """Genera likes con algunos huérfanos (post_id que no existe)."""
    likes = []
    user_ids = [u["_id"] for u in users]
    post_ids = [p["_id"] for p in posts]
    author_by_post = {p["_id"]: p.get("user_id") for p in posts}

    for i in range(NUM_LIKES):
        like = {
            "_id": f"lk_{i:06d}",
            "user_id": random.choice(user_ids),
            "post_id": random.choice(post_ids),
            "created_at": _random_timestamp(datetime.now(timezone.utc)),
            "origin": "seed",
        }

        # Orphan likes (3%)
        if random.random() < ORPHAN_RATIO:
            like["post_id"] = _random_id("p_deleted")

        # Duplicate likes (same user, same post — should be caught in silver)
        if random.random() < 0.02:
            like["user_id"] = likes[-1]["user_id"] if likes else like["user_id"]
            like["post_id"] = likes[-1]["post_id"] if likes else like["post_id"]

        likes.append(like)

    featured_post_ids = [p["_id"] for p in posts if p["_id"].startswith("p_inf_")]
    like_idx = len(likes)
    for post_id in featured_post_ids:
        author = author_by_post.get(post_id)
        candidates = [uid for uid in user_ids if uid != author and not uid.startswith("u_spam_")]
        fan_count = random.randint(45, 180)
        for uid in random.sample(candidates, k=min(fan_count, len(candidates))):
            likes.append({
                "_id": f"lk_inf_{like_idx:06d}",
                "user_id": uid,
                "post_id": post_id,
                "created_at": _demo_timestamp(days_ago=random.randint(0, 10), minutes_offset=like_idx % 600),
                "origin": "seed",
            })
            like_idx += 1

    return likes


def generate_follows(users: list[dict]) -> list[dict]:
    """Genera follows con circulares, huérfanos, y self-follows."""
    follows = []
    user_ids = [u["_id"] for u in users]
    featured_ids = [u["_id"] for u in users if u["_id"].startswith("u_inf_")]
    spammer_ids = [u["_id"] for u in users if u["_id"].startswith("u_spam_")]
    normal_ids = [u["_id"] for u in users if not u["_id"].startswith("u_spam_")]

    for i in range(NUM_FOLLOWS):
        follower = random.choice(user_ids)
        following = random.choice(user_ids)

        follow = {
            "_id": f"fw_{i:06d}",
            "follower_id": follower,
            "following_id": following,
            "created_at": _random_timestamp(datetime.now(timezone.utc)),
            "origin": "seed",
        }

        # Self-follow (should be filtered in silver)
        if random.random() < 0.02:
            follow["following_id"] = follow["follower_id"]

        # Orphan (follow to deleted user)
        if random.random() < ORPHAN_RATIO:
            follow["following_id"] = _random_id("u_ghost")

        follows.append(follow)

    follow_idx = len(follows)

    # Hubs claros para que Neo4j muestre influencers reconocibles.
    for rank, influencer_id in enumerate(featured_ids):
        follower_goal = max(180, 1200 - rank * 22)
        candidates = [uid for uid in normal_ids if uid != influencer_id]
        for follower_id in random.sample(candidates, k=min(follower_goal, len(candidates))):
            follows.append({
                "_id": f"fw_inf_{follow_idx:06d}",
                "follower_id": follower_id,
                "following_id": influencer_id,
                "created_at": _demo_timestamp(days_ago=random.randint(1, 120), minutes_offset=follow_idx % 900),
                "origin": "seed",
            })
            follow_idx += 1

    # Los spammers siguen a muchísima gente y casi nadie les sigue.
    for spammer_id in spammer_ids:
        candidates = [uid for uid in user_ids if uid != spammer_id and not uid.startswith("u_spam_")]
        for following_id in random.sample(candidates, k=min(260, len(candidates))):
            follows.append({
                "_id": f"fw_spam_{follow_idx:06d}",
                "follower_id": spammer_id,
                "following_id": following_id,
                "created_at": _demo_timestamp(days_ago=random.randint(0, 20), minutes_offset=follow_idx % 900),
                "origin": "seed",
            })
            follow_idx += 1

    # Enlaza influencers entre si para que shortestPath y ego-network tengan caminos vistosos.
    for i, source in enumerate(featured_ids):
        for target in (featured_ids[(i + 1) % len(featured_ids)], featured_ids[(i + 5) % len(featured_ids)]):
            if source == target:
                continue
            follows.append({
                "_id": f"fw_hub_{follow_idx:06d}",
                "follower_id": source,
                "following_id": target,
                "created_at": _demo_timestamp(days_ago=3 + i, minutes_offset=follow_idx % 900),
                "origin": "seed",
            })
            follow_idx += 1

    return follows


def main():
    RAW_PATH.mkdir(parents=True, exist_ok=True)

    print("Generating dirty users...")
    users = generate_users()
    print(
        f"  {len(users)} users ({len(FEATURED_INFLUENCERS)} influencers demo, "
        f"{len(SPAMMER_PERSONAS)} spammers, {int(NUM_USERS * DUPLICATE_USER_RATIO)} duplicates)"
    )

    print("Generating dirty posts...")
    posts = generate_posts(users)
    print(f"  {len(posts)} posts (includes spam burst)")

    print("Generating dirty likes...")
    likes = generate_likes(users, posts)
    print(f"  {len(likes)} likes ({ORPHAN_RATIO*100:.0f}% orphans)")

    print("Generating dirty follows...")
    follows = generate_follows(users)
    print(f"  {len(follows)} follows (includes influencer hubs, self-follows & orphans)")

    # Write as NDJSON (one JSON per line — Spark friendly)
    for name, data in [("users", users), ("posts", posts), ("likes", likes), ("follows", follows)]:
        path = RAW_PATH / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            for record in data:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  Wrote {path} ({size_mb:.1f} MB)")

    print("\nDone! Raw data ready for Spark ETL.")
    print(f"  Path: {RAW_PATH}")
    print(f"\nProblems students must fix:")
    print(f"  - 5 timestamp formats")
    print(f"  - {int(NUM_USERS * DUPLICATE_USER_RATIO)} duplicate users")
    print(f"  - Inconsistent hashtags (# / no # / CAPS / spaces)")
    print(f"  - ~{int(NUM_POSTS * MISSING_FIELD_RATIO)} posts with missing fields")
    print(f"  - ~{int(NUM_LIKES * ORPHAN_RATIO)} orphan likes")
    print(f"  - Self-follows and ghost follows")
    print(f"  - Broken encoding (Ã¡ instead of á)")
    print(f"  - 100-post spam burst from one bot")
    print(f"  - {len(FEATURED_INFLUENCERS)} demo influencers with many followers")
    print(f"  - {len(SPAMMER_PERSONAS)} dedicated spammers with repeated posts")


if __name__ == "__main__":
    main()
