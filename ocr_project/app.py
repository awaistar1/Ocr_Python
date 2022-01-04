from flask import Flask
import flask
import requests
import re
import os
import magic
import json
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

car_brands = ['TOYOTA', 'HINO', 'MITSUBISHI', 'FORD',
              'SUZUKI', 'NISSAN', 'ISUZU', 'HONDA', 'HYUNDAI']
body_types = ['HATCHBACK', 'SEDAN', 'SUV',
              'MUV', 'COUPE', 'WAGON', 'VAN', 'JEEP']


def extract_data_from_image(file_path):
    image_file = open(file_path, "rb")
    mimetype = magic.from_file(file_path, mime=True)
    result = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file": (image_file.name, image_file, mimetype)},
        headers={"apiKey": "a9d6585d2688957"},
        data={"isTable": "true"},
    )

    if result.status_code != 200:
        raise Exception("Error while calling OCR.space")

    response = result.json()["ParsedResults"][0]["TextOverlay"]["Lines"]
    # json.dump(response, open("output.json", "w"))

    parsed_data = {}

    for k, resp in enumerate(response):
        if re.search(r"\d+/\d+/\d+$", resp["LineText"]):
            parsed_data["date"] = resp["LineText"]
        if re.search(r"-00", resp["LineText"]):
            parsed_data["mv_file_no"] = resp["LineText"]
        if re.match(r"[A-Z]{3}[0-9]{4}", resp["LineText"]):
            parsed_data["plate_no"] = resp["LineText"]
        if re.match(r"GAS|DIESEL|LPG|CNG|KEROSENE", resp["LineText"]):
            parsed_data["fuel_type"] = resp["LineText"]
        if re.search(r"BODY[a-zA-z]*", resp["LineText"]):
            parsed_data["body_type"] = resp["LineText"]
        if re.search(r"\d+,\d+.\d+", resp["LineText"]):
            parsed_data["amount"] = resp["LineText"]
        if re.search(r"[0-9]{15}", resp["LineText"]):
            parsed_data["or_no"] = resp["LineText"]
        if 'ENGINE' in resp['LineText']:
            try:
                parsed_data["engine_no"] = response[k +
                                                    1]['Words'][0]['WordText']
            except:
                pass
        if 'CAPACITY' in resp['LineText']:
            try:
                next_match = response[k + 1]['LineText']
                if re.search(r"[0-9]{3,4}", next_match):
                    parsed_data["net_weight"] = next_match
                    parsed_data["net_capacity"] = next_match
            except:
                pass
        if resp['LineText'].upper() in car_brands:
            parsed_data['brand'] = resp['LineText']
        if resp['LineText'].upper() in body_types:
            parsed_data['body_type'] = resp['LineText']
    os.remove(file_path)

    return parsed_data


def create_file(image_file):
    path = os.path.join(os.getcwd(), "tmp")
    if not os.path.exists(path):
        os.makedirs(path)
    save_name = os.urandom(16).hex()
    mimetype = image_file.content_type.split("/")[1]
    image_file.save(os.path.join(
        os.getcwd(), "tmp", f"{save_name}.{mimetype}"))
    return os.path.join(os.getcwd(), "tmp", f"{save_name}.{mimetype}")


@app.route("/", methods=['POST', 'GET'])
def process_image():
    if "image_file" not in flask.request.files:
        return app.response_class(
            status=400,
            response=json.dumps({"message": "No image file provided"}),
            mimetype="application/json",
        )
    image_file = flask.request.files.get("image_file")
    if not image_file.content_type.startswith("image"):
        return app.response_class(
            status=400,
            response=json.dumps({"message": "Invalid file type"}),
            mimetype="application/json",
        )
    try:
        file_path = create_file(image_file)
        data = extract_data_from_image(file_path)

        return app.response_class(
            status=200, response=json.dumps({"data": data}), mimetype="application/json"
        )
    except Exception as e:
        return app.response_class(
            status=400,
            response=json.dumps({"message": e.__str__()}),
            mimetype="application/json",
        )


if __name__ == "__main__":
    app.run(threaded=True, port=8080)
