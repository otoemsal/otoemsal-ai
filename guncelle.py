import os, json, time
from google import genai
from supabase import create_client

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def aktif_modelleri_bul():
    adaylar = []
    for m in client.models.list():
        ad = m.name.replace("models/", "")
        if "gemini" in ad and "flash" in ad and not any(x in ad for x in ["tts", "image", "audio", "live", "embedding", "lite"]):
            adaylar.append(ad)
    adaylar.sort(reverse=True)
    return adaylar[:3]

def ilani_temizle(aciklama: str, modeller: list) -> dict:
    prompt = f"""
    Bu ikinci el araç ilan metninden hasar ve donanım bilgilerini çıkar.
    Sadece şu anahtarlara sahip geçerli bir JSON döndür:
    boya_sayisi (int), degisen_sayisi (int), agir_hasar (bool), tramer (int), ekstralar (list of strings).
    İlan: {aciklama}
    """
    son_hata = None
    for model_adi in modeller:
        print(f"Deneniyor: {model_adi}", flush=True)
        try:
            response = client.models.generate_content(
                model=model_adi,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            print(f"Başarılı model: {model_adi}", flush=True)
            return json.loads(response.text)
        except Exception as e:
            print(f"{model_adi} hata verdi: {e}", flush=True)
            son_hata = e
    raise son_hata

def main():
    modeller = aktif_modelleri_bul()
    print("Seçilen modeller:", modeller, flush=True)

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
