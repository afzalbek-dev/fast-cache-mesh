# ⚡ Fast Cache Mesh

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()

Python mikroservislari, API va yuqori yuklamali (high-load) tizimlar uchun ikki bosqichli keshlovchi (**L1 Xotira LRU + L2 SQLite Doimiy**) va kesh to'qnashuvlarini (Cache Stampede / Dogpile effect) to'liq oldini oluvchi **Single-Flight** arxitekturasi.

---

## 🌟 Muammo va Yechim

Ko'p tizimlarda kesh muddati (TTL) tugashi bilan bir vaqtda 1000 ta so'rov kelsa, ularning barchasi bir paytda og'ir ma'lumotlar bazasiga so'rov tashlaydi (**Cache Stampede**). Natijada baza "yiqiladi".

**Fast Cache Mesh yechimi:**
1. **Single-Flight Group:** Bitta kalit uchun minglab so'rovlar parallel kelsa ham, haqiqiy hisoblash/baza so'rovi **faqat 1 marta** bajariladi. Qolgan 999 ta so'rov ushbu yagona natijani kutib oladi.
2. **Ikki bosqichli Kesh (Two-Tier):**
   - **L1:** Eng tezkor xotira (RAM) LRU kesh.
   - **L2:** Diskdagi SQLite kesh (tizim qayta yuklanganda ham ma'lumot saqlanadi).
3. **TTL Jitter:** Barcha keshlar bir vaqtda eskirmasligi uchun kesh vaqtiga tasodifiy kichik foiz (jitter) qo'shiladi.

---

## 🚀 O'rnatish

```bash
git clone https://github.com/afzalbek-dev/fast-cache-mesh.git
cd fast-cache-mesh
pip install .
```

---

## 🛠️ Foydalanish

### 1. Dekorator usulida

```python
import asyncio
from fast_cache_mesh import cache_mesh

@cache_mesh(ttl=120, jitter=0.1)
async def fetch_user_dashboard(user_id: int):
    # Og'ir hisoblash yoki baza so'rovi
    await asyncio.sleep(1.0)
    return {"user_id": user_id, "balance": 1500000, "status": "active"}

async def main():
    # Birinchi chaqiruv hisoblaydi, keyingilari esa mikrosekundda keshdan qaytadi
    data1 = await fetch_user_dashboard(42)
    data2 = await fetch_user_dashboard(42)
    print(data1)

asyncio.run(main())
```

### 2. Dasturiy boshqaruv (Manual CacheMesh)

```python
import asyncio
from fast_cache_mesh import CacheMesh

async def main():
    mesh = CacheMesh(l1_maxsize=500, l2_db_path="cache.db")

    async def expensive_task():
        return {"report": "Q4 Analytics"}

    # Keshda bo'lsa darhol oladi, bo'lmasa yuklab keshga qo'yadi
    val = await mesh.get_or_set("analytics:q4", expensive_task, ttl=300)
    print("Natija:", val)
    print("Kesh statistikasi:", mesh.stats())

asyncio.run(main())
```

---

## 🧪 Testlash

```bash
python3 -m unittest discover tests -v
```

---

## 📄 Litsenziya

MIT License. Muallif: [Afzalbek](https://github.com/afzalbek-dev).
