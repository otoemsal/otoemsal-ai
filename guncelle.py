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
        if "generateContent" in destek and "gemini" in ad and "flash" in ad:
            if not any(x in ad for x in ["preview", "tts", "image", "audio", "live", "embedding"]):
                modeller.append(ad)
    modeller.sort(reverse=True)
    # En kararlı ve hızlı flash modellerini başa al
    oncelikli = [m for m in modeller if "lite" in m or "2.5" in m or "latest" in m]
    diger = [m for m in modeller if m not in oncelikli]
    secilen = (oncelikli + diger)[:5]
    print("Kararlı modeller:", secilen, flush=True)
    return secilen

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
    for deneme in range(2):
        for model_adi in modeller:
            print(f"Deneniyor: {model_adi} (Deneme {deneme + 1})", flush=True)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_adi}:generateContent?key={GEMINI_KEY}"
            try:
                r = requests.post(url, json=payload, timeout=25)
                if r.status_code == 200:
                    print(f"Başarılı: {model_adi}", flush=True)
                    metin = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(metin)
                if r.status_code in (429, 503):
                    print(f"{model_adi} kota/yoğunluk (Kod {r.status_code}), 10 sn bekleniyor...", flush=True)
                    time.sleep(10)
                    continue
                print(f"{model_adi} atlandı (Kod {r.status_code})", flush=True)
            except Exception as e:
                print(f"{model_adi} zaman aşımı/hata: {e}", flush=True)
                time.sleep(4)
    raise RuntimeError("Tüm modeller şu an meşgul veya kota dolu.")

def main():
    modeller = aktif_modelleri_bul()

    mevcut_idler = set()
    try:
        res = supabase.table("arac_ilanlari").select("ilan_id").execute()
        for row in (res.data or []):
            if row.get("ilan_id"):
                mevcut_idler.add(row["ilan_id"])
    except Exception as e:
        print("Mevcut kayıtlar okunurken uyarı:", e, flush=True)

    ham_ilanlar = [
        {
            "ilan_id": "emsal-egea-001",
            "marka": "Fiat",
            "model": "Egea Sedan",
            "paket": "1.3 Multijet Urban",
            "yil": 2021,
            "km": 78000,
            "fiyat": 945000,
            "il": "Ankara",
            "aciklama": "Sadece sağ arka kapı lokal boyalı, değişen yok. 9.000 TL tramer var. Geri görüş kamerası ve hız sabitleyici mevcut."
        },
        {
            "ilan_id": "emsal-egea-002",
            "marka": "Fiat",
            "model": "Egea Sedan",
            "paket": "1.4 Fire Urban",
            "yil": 2022,
            "km": 42000,
            "fiyat": 885000,
            "il": "Eskişehir",
            "aciklama": "Hatasız boyasız değişensiz, tramer 0 TL. İlk sahibinden servis bakımlı."
        },
        {
            "ilan_id": "emsal-clio-001",
            "marka": "Renault",
            "model": "Clio",
            "paket": "1.0 TCe Touch X-Tronic",
            "yil": 2022,
            "km": 54000,
            "fiyat": 1065000,
            "il": "Bursa",
            "aciklama": "Boyasız değişensiz, tramer 0 TL. CarPlay ekran ve park sensörü var."
        },
        {
            "ilan_id": "emsal-megane-001",
            "marka": "Renault",
            "model": "Megane",
            "paket": "1.3 TCe Joy EDC",
            "yil": 2021,
            "km": 69000,
            "fiyat": 1240000,
            "il": "İzmir",
            "aciklama": "Sol ön çamurluk boyalı, değişen yok. 16.000 TL tramer var. Otomatik vites, bakımlı."
        },
        {
            "ilan_id": "emsal-passat-001",
            "marka": "Volkswagen",
            "model": "Passat",
            "paket": "1.5 TSI Impression",
            "yil": 2020,
            "km": 85000,
            "fiyat": 1580000,
            "il": "Ankara",
            "aciklama": "Sadece sağ ön çamurluk lokal boyalı, değişen yok. 14.500 TL yeni tarihli tramer var. Cam tavan ve hayalet ekran mevcut."
        },
        {
            "ilan_id": "emsal-passat-002",
            "marka": "Volkswagen",
            "model": "Passat",
            "paket": "1.6 TDI Business DSG",
            "yil": 2019,
            "km": 112000,
            "fiyat": 1460000,
            "il": "İstanbul",
            "aciklama": "1 parça boya, 1 değişen, 22.000 TL tramer var. DSG bakımları yeni yapıldı."
        },
        {
            "ilan_id": "emsal-corolla-001",
            "marka": "Toyota",
            "model": "Corolla",
            "paket": "1.6 Vision Multidrive S",
            "yil": 2021,
            "km": 63000,
            "fiyat": 1340000,
            "il": "Konya",
            "aciklama": "Hatasız boyasız değişensiz, tramer 0 TL. Şerit takip ve adaptif hız sabitleyici mevcut."
        },
        {
            "ilan_id": "emsal-corolla-002",
            "marka": "Toyota",
            "model": "Corolla Hybrid",
            "paket": "1.8 Hybrid Dream e-CVT",
            "yil": 2022,
            "km": 48000,
            "fiyat": 1560000,
            "il": "Antalya",
            "aciklama": "Boyasız değişensiz, tramer 0 TL. Yetkili servis hibrit sağlık raporu mevcut."
        },
        {
            "ilan_id": "emsal-civic-001",
            "marka": "Honda",
            "model": "Civic",
            "paket": "1.6 i-VTEC Eco Elegance LPG",
            "yil": 2020,
            "km": 74000,
            "fiyat": 1420000,
            "il": "Ankara",
            "aciklama": "Boyasız değişensiz, tramer 0 TL. Fabrika çıkış LPG, sunroof ve koltuk ısıtma var."
        },
        {
            "ilan_id": "emsal-duster-001",
            "marka": "Dacia",
            "model": "Duster",
            "paket": "1.0 TCe Eco-G Journey",
            "yil": 2022,
            "km": 46000,
            "fiyat": 1220000,
            "il": "Kayseri",
            "aciklama": "Boyasız değişensiz, tramer 0 TL. LPG'li, 360 kamera ve çelik jant mevcut."
        },
        {
            "ilan_id": "emsal-tiggo7-001",
            "marka": "Chery",
            "model": "Tiggo 7 Pro",
            "paket": "1.6 TGDI Excellent DCT",
            "yil": 2023,
            "km": 31000,
            "fiyat": 1740000,
            "il": "İstanbul",
            "aciklama": "Boyasız değişensiz, tramer 0 TL. Panoramik cam tavan ve 360 kamera mevcut."
        },
        {
            "ilan_id": "emsal-togg-001",
            "marka": "Togg",
            "model": "T10X V2 Uzun Menzil",
            "paket": "V2 Uzun Menzil",
            "yil": 2024,
            "km": 22000,
            "fiyat": 2080000,
            "il": "İstanbul",
            "aciklama": "Boyasız değişensiz, tramer 0 TL. Cam tavan ve Meridian ses sistemi mevcut."
        }
    ]

    for ilan in ham_ilanlar:
        if ilan["ilan_id"] in mevcut_idler:
            print(f"Zaten kayıtlı, atlandı: {ilan['ilan_id']}", flush=True)
            continue
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
        time.sleep(5)

if __name__ == "__main__":
    main()
