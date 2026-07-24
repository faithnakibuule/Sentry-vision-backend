import os
import time
import urllib.request
import django
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentry_vision.settings')
django.setup()

from persons.models import PersonOfInterest
from persons.services import get_face_encoding

def diagnose_pipeline():
    print("🚀 Starting Diagnostic Test...\n")

    # 1. Download image locally to memory
    test_url = "https://upload.wikimedia.org/wikipedia/commons/3/34/Elon_Musk_Royal_Society_%28crop2%29.jpg"
    print("1️⃣ Downloading image into local memory...")
    req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        image_bytes = resp.read()
    print("   └─ Download complete! Size:", len(image_bytes), "bytes")

    # 2. Test get_face_encoding standalone (No Database, No ImageKit)
    print("\n2️⃣ Testing face encoding locally in Python...")
    t0 = time.time()
    file_obj = ContentFile(image_bytes)
    encoding = get_face_encoding(file_obj)
    t1 = time.time()

    if encoding is not None:
        enc_list = encoding.tolist() if hasattr(encoding, "tolist") else encoding
        print(f"   └─ ✅ ENCODING SUCCESS in {round(t1 - t0, 2)} seconds!")
        print(f"   └─ Vector length: {len(enc_list)} dimensions")
    else:
        print("   └─ ❌ Face encoding returned None!")

    # 3. Test database object creation WITHOUT saving image to ImageKit storage yet
    print("\n3️⃣ Testing model save (triggers ImageKit upload)...")
    t2 = time.time()
    person = PersonOfInterest(full_name="Diagnostic Test Subject")
    person.photo.save("diagnostic_face.jpg", ContentFile(image_bytes), save=True)
    t3 = time.time()
    print(f"   └─ ✅ DB/ImageKit Save finished in {round(t3 - t2, 2)} seconds!")
    print(f"   └─ Photo URL: {person.photo.url if person.photo else 'None'}")

if __name__ == '__main__':
    diagnose_pipeline()