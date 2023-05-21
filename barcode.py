import cv2
from google.oauth2 import service_account
from google.cloud import vision
import cv2
import io
import dateutil.parser
from itertools import chain
import datefinder
from pyzbar import pyzbar
from glob import glob
import requests

cam_port = 0
credentials = service_account.Credentials.from_service_account_file(
    filename='vision-api-key.json',
    scopes=["https://www.googleapis.com/auth/cloud-platform"])
client = vision.ImageAnnotatorClient(credentials=credentials)
results = {}


def capture():
    print(("[INFO] Capturing ...."))
    cam = cv2.VideoCapture(cam_port)

    result, image = cam.read()
    if result:
        cv2.imshow("Detection", image)
        cv2.imwrite("Detection.png", image)

    else:
        print("No image detected. Please! try again")


UNINTERESTING = set(chain(dateutil.parser.parserinfo.JUMP,
                          dateutil.parser.parserinfo.PERTAIN,
                          ['a']))


def decode(image):
    # decodes all barcodes from an image
    decoded_objects = pyzbar.decode(image)
    for obj in decoded_objects:
        image = draw_barcode(obj, image)
        results['serial_number'] = obj.data

    return image


def draw_barcode(decoded, image):
    image = cv2.rectangle(image, (decoded.rect.left, decoded.rect.top),
                          (decoded.rect.left + decoded.rect.width, decoded.rect.top + decoded.rect.height),
                          color=(0, 255, 0),
                          thickness=5)
    return image


def readBarcode():
    barcodes = glob("Detection.png")
    for barcode_file in barcodes:
        img = cv2.imread(barcode_file)
        decode(img)


def processOcr(type):
    with io.open('test6.jpg', "rb") as f:
        byteImage = f.read()

    print("[INFO] making request to Google Cloud Vision API...")
    image = vision.Image(content=byteImage)
    response = client.text_detection(image=image)
    if response.error.message:
        raise Exception(
            "{}\nFor more info on errors, check:\n"
            "https://cloud.google.com/apis/design/errors".format(
                response.error.message))
    identified = ""
    for text in response.text_annotations[1::]:
        ocr = text.description
        identified += ocr

    if type == 'date':
        matches = list(datefinder.find_dates(identified))
        if len(matches) > 0:
            date = matches[0]
            results['exp_date'] = date
        else:
            print('No dates found')


if __name__ == '__main__':
    print("[INFO] Place the camera to product barcode")
    input('Press enter once to continue....')
    # capture()
    readBarcode()
    print("[INFO] Place the camera to expiration date")
    input("press enter to continue....")
    # capture()
    processOcr(type='date')
    url = "https://invoexpi.aviarthardph.net/api/scanLogs"
    res = requests.post(url, results)
    print(res.json())
    print(res.status_code)
    print(results)

