import cv2
from google.oauth2 import service_account
from google.cloud import vision
import cv2
import io
import dateutil.parser
from itertools import chain
import datefinder
from PIL import Image
from glob import glob
import requests
import re

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
        cv2.imwrite("Detection.jpg", image)

    else:
        print("No image detected. Please! try again")


UNINTERESTING = set(chain(dateutil.parser.parserinfo.JUMP,
                          dateutil.parser.parserinfo.PERTAIN,
                          ['a']))

def read_barcode(path):
    image = cv2.imread(path)
    im = Image.open(path)
    width, height = im.size
    with open(path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)

    objects = client.object_localization(
        image=image).localized_object_annotations

    print(f'Number of objects found: {len(objects)}')
    for object_ in objects:
        print(f'\n{object_.name} (confidence: {object_.score})')
        if "barcode" in object_.name:
            print("barcode found")
            l1 = object_.bounding_poly.normalized_vertices[0].x
            l2 = object_.bounding_poly.normalized_vertices[0].y
            l3 = object_.bounding_poly.normalized_vertices[2].x
            l4 = object_.bounding_poly.normalized_vertices[3].y
            left = l1 * width
            top = l2 * height
            right = l3 * width
            bottom = l4 * height

            # height = abs(top - bottom)
            # width = abs(right - left)
            # extrawidth = max(0, height - width)
            extraheight = max(0, width - height)
            #
            # top -= extraheight // 6
            bottom += extraheight // 9
            # left -= extrawidth // 7
            # right += extrawidth // 7

            im = im.crop((left, top, right, bottom))
            im.save('barcode.png', 'png')

    with io.open('barcode.png', "rb") as f:
        byteImage = f.read()

    print("[INFO] making request to Google Cloud Vision API...")
    image = vision.Image(content=byteImage)
    response = client.text_detection(image=image)
    identified = ""
    for text in response.text_annotations[1::]:
        ocr = text.description
        identified += ocr

    barcodeOnly = re.findall('[0-9]+', identified)
    print(barcodeOnly[0][1:13])
    if len(barcodeOnly[0]) > 12:
        barcodeOnly = barcodeOnly[0][1:13]
    else:
        barcodeOnly = barcodeOnly[0][:12]
    print("Barcode ")
    print(barcodeOnly)
    results['serial_no'] = barcodeOnly

def processOcr(type):
    with io.open('Detection.jpg', "rb") as f:
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
    read_barcode('Detection.jpg')
    print("[INFO] Place the camera to expiration date")
    input("press enter to continue....")
    # capture()
    processOcr(type='date')
    url = "https://invoexpi.aviarthardph.net/api/scanLogs"
    print(results)
    res = requests.post(url, results)
    print(res.json())
    print(res.status_code)
