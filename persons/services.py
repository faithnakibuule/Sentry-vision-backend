import io

import numpy as np


def _load_image(image_source):
    import face_recognition

    if hasattr(image_source, "read"):
        try:
            image_source.seek(0)
        except (AttributeError, ValueError):
            pass
        return face_recognition.load_image_file(io.BytesIO(image_source.read()))
    return face_recognition.load_image_file(image_source)


def get_face_encoding(image_source):
    import face_recognition

    image = _load_image(image_source)
    locations = face_recognition.face_locations(image)
    if not locations:
        return None
    if len(locations) > 1:
        locations = [max(locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))]
    encodings = face_recognition.face_encodings(image, known_face_locations=locations)
    return encodings[0] if encodings else None


def compare_encoding(unknown_encoding, people, tolerance):
    import face_recognition

    candidates = [(person, np.array(person.face_encoding)) for person in people if person.face_encoding]
    if not candidates:
        return None, None, None

    distances = face_recognition.face_distance([encoding for _, encoding in candidates], unknown_encoding)
    best_index = int(np.argmin(distances))
    best_distance = float(distances[best_index])
    if best_distance > tolerance:
        return None, None, best_distance
    confidence = round(max(0.0, min(1.0, 1.0 - best_distance)), 4)
    return candidates[best_index][0], confidence, best_distance
