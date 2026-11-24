import os, json, time
from google import genai
from supabase import create_client

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def ilani_temizle(aciklama: str) -> dict:
    prompt = f"""
    Bu ikinci el araç ilan metninden hasar ve donanım bilgilerini çıkar.
    Sadece şu anahtarlara sahip geçerli bir JSON döndür:
    boya_sayisi (int), degisen_sayisi (int), agir_hasar (bool), tramer (int), ekstralar (list of strings).
    İlan: {aciklama}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

def main():
    # İlk test için örnek ilanlar (daha sonra buraya canlı veri kaynağını bağlayacağız)
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
        temiz = ilani_temizle(ilan["aciklama"])
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
        print(f"Güncellendi: {ilan['marka']} {ilan['model']}")
        time.sleep(1)

if __name__ == "__main__":
    main()
