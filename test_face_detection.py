import numpy as np
from PIL import Image
import face_recognition

path = "C:/Users/Dell/OneDrive/Desktop/sentryvision.jpeg"

img = Image.open(path)
if img.mode != 'RGB':
    img = img.convert('RGB')

arr = np.array(img)
print("Array shape:", arr.shape)

locations_hog = face_recognition.face_locations(arr)
print("HOG locations:", locations_hog)

locations_cnn = face_recognition.face_locations(arr, model="cnn")
print("CNN locations:", locations_cnn)

locations_hog_upsampled = face_recognition.face_locations(arr, number_of_times_to_upsample=2)
print("HOG upsampled locations:", locations_hog_upsampled)
