import io
import urllib.request
import numpy as np
from PIL import Image


def _load_image(image_source):
    """
    Safely loads an image from a URL, local file, stream, or Django ImageField
    and converts it into an RGB numpy array resized to 1024px max bound.
    """
    try:
        import face_recognition
    except Exception:
        raise RuntimeError("face_recognition is not installed or cannot be imported")

    try:
        img = None

        # Handle Django ImageField / FieldFile or objects with URLs
        if hasattr(image_source, "url"):
            url = image_source.url
            # Fix duplicated ImageKit domain prefix if present
            if url.count("https://") > 1:
                url = "https://" + url.split("https://")[-1]

            try:
                image_source.open()
                image_source.seek(0)
                img = Image.open(image_source)
            except Exception:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    img = Image.open(io.BytesIO(resp.read()))

        # Handle stream objects / BytesIO
        elif hasattr(image_source, "read"):
            try:
                image_source.seek(0)
            except (AttributeError, ValueError):
                pass
            img = Image.open(io.BytesIO(image_source.read()))

        # Handle file paths or raw URL strings
        elif isinstance(image_source, str):
            if image_source.count("https://") > 1:
                image_source = "https://" + image_source.split("https://")[-1]

            if image_source.startswith("http://") or image_source.startswith("https://"):
                req = urllib.request.Request(image_source, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    img = Image.open(io.BytesIO(resp.read()))
            else:
                img = Image.open(image_source)

        elif isinstance(image_source, Image.Image):
            img = image_source

        if img is None:
            raise ValueError("Could not load image source.")

        if img.mode != 'RGB':
            img = img.convert('RGB')

        img.thumbnail((1024, 1024))
        return np.array(img)

    except Exception:
        if hasattr(image_source, "read"):
            try:
                image_source.seek(0)
            except (AttributeError, ValueError):
                pass
            return face_recognition.load_image_file(io.BytesIO(image_source.read()))
        return face_recognition.load_image_file(image_source)


def _detect_face_locations(image):
    """
    Detects face locations using HOG first, falling back to CNN or upsampling.
    """
    import face_recognition

    locations = face_recognition.face_locations(image, model="hog")
    if locations:
        return locations

    try:
        locations = face_recognition.face_locations(image, model="cnn")
        if locations:
            return locations
    except Exception:
        pass

    return face_recognition.face_locations(image, number_of_times_to_upsample=2)


def get_face_encoding(image_source):
    """
    Processes an image source and returns a 128D face encoding array (or list).
    """
    try:
        import face_recognition
    except Exception:
        return None

    try:
        image = _load_image(image_source)
    except Exception:
        return None

    if image is None:
        return None

    try:
        locations = _detect_face_locations(image)
        if not locations:
            return None

        # Pick the largest face if multiple faces are detected
        if len(locations) > 1:
            locations = [max(locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))]

        encodings = face_recognition.face_encodings(image, known_face_locations=locations)
        if encodings:
            return encodings[0].tolist() if hasattr(encodings[0], 'tolist') else encodings[0]

        return None
    except Exception:
        return None


def compare_encoding(unknown_encoding, people, tolerance=0.6):
    """
    Compares unknown_encoding vector against a list/queryset of people instances.
    Returns (matched_person, confidence_score, best_distance).
    """
    try:
        import face_recognition
    except ImportError:
        return None, None, None

    candidates = [(person, np.array(person.face_encoding)) for person in people if person.face_encoding]
    if not candidates:
        return None, None, None

    known_encodings = [encoding for _, encoding in candidates]
    unknown_vec = np.array(unknown_encoding)

    distances = face_recognition.face_distance(known_encodings, unknown_vec)
    best_index = int(np.argmin(distances))
    best_distance = float(distances[best_index])

    if best_distance > tolerance:
        return None, None, best_distance

    confidence = round(max(0.0, min(1.0, 1.0 - best_distance)), 4)
    return candidates[best_index][0], confidence, best_distance