import os
from uuid import uuid4
from io import BytesIO
from django.conf import settings
from django.core.files.storage import Storage
from supabase import create_client
from PIL import Image

class SupabaseStorage(Storage):
    def __init__(self):
        cfg = settings.SUPABASE_STORAGE
        self.client = create_client(cfg["url"], cfg["service_role_key"])
        self.bucket = cfg["bucket"]
        self.base_path = cfg.get("base_path", "products")

    def _save(self, name, content):
        filename = os.path.basename(name)
        name_wo_ext, _ = os.path.splitext(filename)
        key = f"{self.base_path}/{uuid4().hex}-{name_wo_ext}.webp"

        content.seek(0)
        raw = content.read()

        # Intentar convertir a WEBP
        try:
            img = Image.open(BytesIO(raw))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            out = BytesIO()
            img.save(out, format="WEBP", quality=85, method=6)
            out.seek(0)
            file_data = out.read()
            content_type = "image/webp"
        except Exception:
            # Si no es imagen válida, subir como binario
            file_data = raw
            content_type = getattr(content, "content_type", "application/octet-stream")
            key = f"{self.base_path}/{uuid4().hex}-{filename}"

        self.client.storage.from_(self.bucket).upload(
            key,
            file_data,
            {"content-type": content_type},
        )
        return key

    def url(self, name):
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/{self.bucket}/{name}"

    def delete(self, name):
        if name:
            self.client.storage.from_(self.bucket).remove([name])

    def copy(self, name):
        if not name:
            return ""
        filename = os.path.basename(name)
        new_key = f"{self.base_path}/{uuid4().hex}-{filename}"
        try:
            self.client.storage.from_(self.bucket).copy(name, new_key)
        except Exception:
            data = self.client.storage.from_(self.bucket).download(name)
            self.client.storage.from_(self.bucket).upload(new_key, data)
        return new_key