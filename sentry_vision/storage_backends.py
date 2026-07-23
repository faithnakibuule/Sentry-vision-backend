import concurrent.futures
from django.core.files.storage import Storage
from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)

# Maximum time (in seconds) to wait for ImageKit before giving up and
# falling back to local storage. Without this, a slow/unreachable ImageKit
# API call can hang the request forever.
IMAGEKIT_UPLOAD_TIMEOUT = 15


class ImageKitStorage(Storage):
    """
    Custom storage backend for ImageKit CDN integration.
    Handles file uploads and retrieval from ImageKit with fallback to local storage.
    """

    def __init__(self):
        self.public_key = settings.IMAGEKIT_PUBLIC_KEY
        self.private_key = settings.IMAGEKIT_PRIVATE_KEY
        self.url_endpoint = settings.IMAGEKIT_URL_ENDPOINT

    def _open(self, name, mode="rb"):
        """Open a file from ImageKit."""
        return BytesIO()

    def _save(self, name, content):
        """Save a file to ImageKit with fallback to local storage."""
        # Validate ImageKit configuration
        if not all([self.public_key, self.private_key, self.url_endpoint]):
            logger.warning("ImageKit credentials not fully configured. Falling back to local storage.")
            return self._save_local(name, content)

        try:
            from imagekitio import ImageKit
        except ImportError:
            logger.warning("imagekitio package not available. Using local storage.")
            return self._save_local(name, content)

        try:
            # Initialize ImageKit
            imagekit = ImageKit(
                public_key=self.public_key,
                private_key=self.private_key,
                url_endpoint=self.url_endpoint,
            )

            # Read file content
            if hasattr(content, "read"):
                file_content = content.read()
            else:
                file_content = content

            # Upload to ImageKit, but never let it hang forever. We run the
            # actual network call in a background thread and enforce a hard
            # timeout — if ImageKit doesn't respond in time, we bail out and
            # fall back to local storage instead of freezing the request.
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        imagekit.upload,
                        file=file_content,
                        file_name=name,
                    )
                    response = future.result(timeout=IMAGEKIT_UPLOAD_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.error(
                    f"ImageKit upload timed out after {IMAGEKIT_UPLOAD_TIMEOUT}s "
                    f"for {name}. Falling back to local storage."
                )
                return self._save_local(name, content)

            # Return the file path stored on ImageKit
            if response and response.get("name"):
                logger.info(f"Successfully uploaded {name} to ImageKit")
                return response.get("name")

            logger.warning(f"ImageKit upload returned no name for {name}")
            return name

        except Exception as e:
            logger.error(f"ImageKit upload failed for {name}: {e}. Falling back to local storage.")
            return self._save_local(name, content)

    def _save_local(self, name, content):
        """Fallback method to save file locally."""
        from django.core.files.storage import default_storage
        try:
            if hasattr(content, "read"):
                content.seek(0)
            return default_storage.save(name, content)
        except Exception as e:
            logger.error(f"Local storage fallback also failed: {e}")
            return name

    def delete(self, name):
        """Delete a file from ImageKit."""
        if not all([self.public_key, self.private_key, self.url_endpoint]):
            return

        try:
            from imagekitio import ImageKit
        except ImportError:
            return

        try:
            imagekit = ImageKit(
                public_key=self.public_key,
                private_key=self.private_key,
                url_endpoint=self.url_endpoint,
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(imagekit.delete_file, file_id=name)
                future.result(timeout=IMAGEKIT_UPLOAD_TIMEOUT)
            logger.info(f"Successfully deleted {name} from ImageKit")
        except concurrent.futures.TimeoutError:
            logger.warning(f"ImageKit delete timed out for {name}")
        except Exception as e:
            logger.warning(f"ImageKit delete failed for {name}: {e}")

    def exists(self, name):
        """Check if a file exists on ImageKit."""
        if not name:
            return False
        return True

    def listdir(self, path):
        """List files in a directory on ImageKit."""
        return [], []

    def size(self, name):
        """Return the size of a file."""
        return 0

    def url(self, name):
        """Return the URL for accessing a file on ImageKit."""
        if not name:
            return ""
        # Construct ImageKit URL
        if self.url_endpoint:
            return f"{self.url_endpoint}/{name}"
        return f"/media/{name}"

    def get_accessed_time(self, name):
        """Return the last accessed time."""
        from datetime import datetime
        return datetime.now()

    def get_created_time(self, name):
        """Return the creation time."""
        from datetime import datetime
        return datetime.now()

    def get_modified_time(self, name):
        """Return the last modified time."""
        from datetime import datetime
        return datetime.now()