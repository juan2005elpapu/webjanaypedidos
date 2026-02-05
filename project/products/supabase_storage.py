import os
from uuid import uuid4
from django.conf import settings
from django.core.files.storage import Storage
from supabase import create_client

class SupabaseStorage(Storage):
    def __init__(self):
        cfg = settings.SUPABASE_STORAGE
        self.client = create_client(cfg["url"], cfg["service_role_key"])
        self.bucket = cfg["bucket"]
        self.base_path = cfg.get("base_path", "products")

    def _save(self, name, content):
        filename = os.path.basename(name)
        key = f"{self.base_path}/{uuid4().hex}-{filename}"
        content.seek(0)
        self.client.storage.from_(self.bucket).upload(
            key,
            content.read(),
            {"content-type": getattr(content, "content_type", "application/octet-stream")},
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