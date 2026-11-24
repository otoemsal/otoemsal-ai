import os, json, time, requests
from supabase import create_client

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def aktif_modelleri_bul():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    modeller = []
    for m in r.json().get("models", []):
        ad = m["name"].replace("models/", "")
        destek = m.get("supportedGenerationMethods", [])
        # Preview ve medya modellerini ele, sadece kararlı Flash modellerini al
        if "generateContent" in destek and "gemini" in ad and "flash" in ad:
            if not any(x in ad for x in ["preview", "tts", "image", "audio", "live", "embedding"]):
                modeller.append(ad)
    modeller.sort(reverse=True)
    print("Kararlı modeller:", modeller[:5], flush=True)
    return modeller[:5]

def ilani_temizle(aciklama: str, modeller: list) -> dict:
    prompt = f"""
    Bu ikinci el araç ilan metninden hasar ve donanım bilgilerini çıkar.
    Sadece şu anahtarlara sahip geçerli bir JSON döndür:
    boya_sayisi (int), degisen_sayisi (int), agir_hasar (bool), tramer (int), ekstralar (list of strings).
    İlan: {aciklama}
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    for model_adi in modeller:
        print(f"Deneniyor: {model_adi}", flush=True)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_adi}:generateContent?key={GEMINI_KEY}"
        try:
            r = requests.post(url, json=payload, timeout=20)
            if r.status_code == 200:
                print(f"Başarılı: {model_adi}", flush=True)
                metin = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(metin)
            print(f"{model_adi} atlandı (Kod {r.status_code})", flush=True)
        except Exception as e:
            print(f"{model_adi} zaman aşımı/hata: {e}", flush=True)
        time.sleep(2)
    raise RuntimeError("Tüm modeller şu an meşgul veya kota dolu.")

def main():
    modeller = aktif_modelleri_bul()

    ham_ilanlar = [
        {
            "ilan_id": "test-passat-001",
            "marka": "Volkswagen",
            "model": "Passat",
            "paket": "1.5 TSI Impression",
            "yil": 2020,
            "km": 85000,
            "fiyat": 1360000,
            "il": "Ankara",
            "aciklama": "Sadece sağ ön çamurluk lokal boyalı, değişen yok. 14.500 TL yeni tarihli tramer var. Cam tavan ve hayalet ekran mevcut."
        },
        {
            "ilan_id": "test-egea-002",
            "marka": "Fiat",
            "model": "Egea Sedan",
            "paket": "1.4 Fire Urban",
            "yil": 2022,
            "km": 42000,
            "fiyat": 885000,
            "il": "Eskişehir",
            "aciklama": "Hatasız boyasız değişensiz, tramer 0 TL. İlk sahibinden servis bakımlı."
        }
    ]

    for ilan in ham_ilanlar:
        temiz = ilani_temizle(ilan["aciklama"], modeller)
        kayit = {
            "ilan_id": ilan["ilan_id"],
            "marka": ilan["marka"],
            "model": ilan["model"],
            "paket": ilan["paket"],
            "yil": ilan["yil"],
            "km": ilan["km"],
            "fiyat": ilan["fiyat"],
            "il": ilan["il"],
            **temiz
        }
        supabase.table("arac_ilanlari").upsert(kayit, on_conflict="ilan_id").execute()
        print(f"Supabase'e yazıldı: {ilan['marka']} {ilan['model']}", flush=True)
        time.sleep(1)

if __name__ == "__main__":
    main()
