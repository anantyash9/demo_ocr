import os
import glob
from doctr.io import DocumentFile
from doctr.utils.visualization import visualize_page
from doctr.models import ocr_predictor
import json
import re
from spell_checker import correction
from states import CG,UP,bih,Maha,ap,WB,cbse
from ner import test_model
from pathlib import Path
import re
import jsonify
import msgpack
from redis import Redis

model = ocr_predictor(pretrained=True)
default_dict={"Status":"Processing","Details":{}}
redis = Redis(host="redis")
def set_dict_redis(key,dictionary):
    redis.set(key, msgpack.packb(dictionary))
def get_dict_redis(key):
    value = redis.get(key)
    return (msgpack.unpackb(value))

def temp(something):
    return something

def step1(img_path):
    doc = DocumentFile.from_images(img_path)
    result = model(doc)
    fig = visualize_page(result.pages[0].export(), doc[0], interactive=False)
    l = img_path.split("/")[-1]
    print(l)
    file_location = "processed/"+l
    fig.savefig(file_location)
    return result

def step2(result):
    json_output = result.export()
    num_words = len(json_output['pages'][0]['blocks'][0]['lines'][0]['words'])
    # checkConfidence = False
    words_list = []
    words_dic = json_output['pages'][0]['blocks'][0]['lines'][0]['words']


    for word in range(num_words):
        res = words_dic[word]['value']
        if not res.isdigit() and (words_dic[word]['confidence'] < 0.2):
            correct_word = correction(res.lower())
            # res = correct_word
            if(correct_word == 'lest'):
                res = 'West'
            if correct_word == res.lower() and len(correct_word)>1:
                res = ''
        words_list.append(res)

    total_text = ' '.join(words_list)

    punc = [')', '-', ':', '(', '$', '&']
    for p in punc:
        total_text = total_text.replace(p,"")

    return total_text


def classification(entitiess):
    classify = {'MUMBAI': 'maharastra',
       'State': 'maharastra',
       'State of Secondary and Board Higher Pune': 'maharastra',
       'Hyderabad': 'Andhra Pradesh',
       'Uttar': 'UP',
       'Uttar Pradesh':'UP',
       'Pradesh Uttar': 'UP',
       'COUNCIL FOR THE INDIAN SCHOOL': 'ICSE',
       'CENTRAL': 'CBSE',
       'CENTRAL SECONDARY BOARD': 'CBSE',
       'KERALA' : 'KERALA',
       'KARNATAKA' : 'KARNATAKA',
       'Bengal': 'West Bengal',
       'West': 'West Bengal',
       'BIHAR': 'BIHAR',
       'PATNA': 'BIHAR',
       'CHHATTISGARH': 'CHHATTISGARH',
       }
    
    board_name = ''
    for en in entitiess:
        if (en[1] == 'BOARD'):
            board_name = classify[en[0]]
            return board_name


def json_output(board_name,entitiess,img_path):
    funCall = {
    'maharastra': Maha,
    'Andhra Pradesh': ap,
    'UP': UP,
    'BIHAR': bih,
    'CHHATTISGARH': CG,
    'West Bengal': WB,
    'CBSE': cbse
    }

    json_data = funCall[board_name](entitiess)
    return json_data

def pipeline(filename):
    key=filename.split(".")[0]
    set_dict_redis(key,default_dict)  
    file = r'uploaded'
    res = step1("uploaded/"+filename)

    total_text = step2(res)
    ent = test_model(total_text)
    board_name = classification(ent)
    json_data = json_output(board_name,ent,filename)
    new_dict={}
    new_dict["Details"]=json_data
    new_dict["Status"]="Processed"
    set_dict_redis(key,new_dict)
    return filename

# def sync_pipeline(filename):
#     asyncio.run(pipeline(filename))
#     return filename
# pipeline("c2.png")
# print("ran")
# async def readback(key):
#     value = await redis.get(key)
#     print((msgpack.unpackb(value)))
# asyncio.run(readback("c2"))

# if __name__ == "__main__":
#     sync_pipeline("copy.png")
#     asyncio.run(readback("copy"))
