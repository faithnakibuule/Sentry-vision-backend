import concurrent.futures
import logging
from io import BytesIO
from django.core.files.storage import Storage, FileSystemStorage
from django.conf import settings

logger = logging.getLogger(__name__)

IMAGEKIT_UPLOAD_TIMEOUT = 10  # Seconds before fallback triggers


class ImageKitStorage(Storage):
    """
    Custom storage backend for ImageKit CDN integration.
    Handles file uploads and retrieval from ImageKit with fallback to local FileSystemStorage.
    """

    def __init__(self):
        self.public_key = getattr(settings, "IMAGEKIT_PUBLIC_KEY", None)
        self.private_key = getattr(settings, "IMAGEKIT_PRIVATE_KEY", None)
        self.url_endpoint = getattr(settings, "IMAGEKIT_URL_ENDPOINT", None)

    def _open(self, name, mode="rb"):
        return BytesIO()

    def _get_imagekit_client(self):
        """Instantiate ImageKit client handling SDK signatures."""
        from imagekitio import ImageKit

        # Modern SDK instantiation
        try:
            return ImageKit(
                private_key=self.private_key,
                public_key=self.public_key,
                url_endpoint=self.url_endpoint,
            )
        except TypeError:
            pass

        # Fallback for SDK versions taking only private_key
        try:
            return ImageKit(private_key=self.private_key)
        except TypeError:
            pass

        # Positional fallback
        return ImageKit(self.private_key, self.public_key, self.url_endpoint)

    def _save(self, name, content):
        """Save a file to ImageKit with fallback to local disk storage."""
        if not all([self.public_key, self.private_key, self.url_endpoint]):
            logger.warning("ImageKit credentials incomplete. Falling back to local storage.")
            return self._save_local(name, content)

        try:
            from imagekitio import ImageKit
        except ImportError:
            logger.warning("imagekitio package not installed. Using local storage.")
            return self._save_local(name, content)

        # Extract raw bytes safely
        try:
            if hasattr(content, "read"):
                content.seek(0)
                file_content = content.read()
            else:
                file_content = content
        except Exception as e:
            logger.error(f"Error reading file stream for {name}: {e}")
            return self._save_local(name, content)

        try:
            imagekit = self._get_imagekit_client()

            def do_upload():
                # 1. Modern SDK: imagekit.files.upload(...)
                if hasattr(imagekit, "files") and hasattr(imagekit.files, "upload"):
                    res = imagekit.files.upload(
                        file=file_content,
                        file_name=name,
                    )
                # 2. Legacy SDK v2: imagekit.upload_file(...)
                elif hasattr(imagekit, "upload_file"):
                    res = imagekit.upload_file(
                        file=file_content,
                        file_name=name,
                    )
                # 3. Legacy SDK v1: imagekit.upload(...)
                elif hasattr(imagekit, "upload"):
                    res = imagekit.upload(
                        options={
                            "file": file_content,
                            "file_name": name,
                        }
                    )
                else:
                    raise AttributeError("Could not locate valid upload method on ImageKit client.")

                # Extract file identifier/name safely from Response / Object / Dict
                if isinstance(res, dict):
                    return res.get("name") or res.get("filePath") or res.get("file_id") or name
                
                return getattr(res, "name", getattr(res, "file_path", getattr(res, "file_id", name)))

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(do_upload)
                uploaded_name = future.result(timeout=IMAGEKIT_UPLOAD_TIMEOUT)

            logger.info(f"✅ Successfully uploaded {name} to ImageKit")
            return str(uploaded_name)

        except concurrent.futures.TimeoutError:
            logger.error(
                f"⏰ ImageKit upload timed out after {IMAGEKIT_UPLOAD_TIMEOUT}s for {name}. "
                f"Falling back to local storage."
            )
            return self._save_local(name, content)

        except Exception as e:
            logger.error(f"❌ ImageKit upload failed for {name}: {e}. Falling back to local storage.")
            return self._save_local(name, content)

    def _save_local(self, name, content):
        """Fallback method using FileSystemStorage directly."""
        try:
            local_storage = FileSystemStorage()
            if hasattr(content, "seek"):
                content.seek(0)
            return local_storage.save(name, content)
        except Exception as e:
            logger.error(f"Local storage fallback failed for {name}: {e}")
            return name

    def delete(self, name):
        """Delete a file from ImageKit."""
        if not all([self.public_key, self.private_key, self.url_endpoint]):
            return

        try:
            imagekit = self._get_imagekit_client()
            delete_func = None
            
            if hasattr(imagekit, "files") and hasattr(imagekit.files, "delete"):
                delete_func = lambda: imagekit.files.delete(file_id=name)
            elif hasattr(imagekit, "delete_file"):
                delete_func = lambda: imagekit.delete_file(file_id=name)

            if delete_func:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(delete_func)
                    future.result(timeout=IMAGEKIT_UPLOAD_TIMEOUT)
                logger.info(f"Successfully deleted {name} from ImageKit")
        except Exception as e:
            logger.warning(f"ImageKit delete skipped/failed for {name}: {e}")

    def exists(self, name):
        return False

    def url(self, name):
        """Return the URL for accessing a file."""
        if not name:
            return ""
        if name.startswith("http://") or name.startswith("https://"):
            return name
        if self.url_endpoint:
            endpoint = self.url_endpoint.rstrip("/")
            return f"{endpoint}/{name.lstrip('/')}"
        return f"/media/{name}"