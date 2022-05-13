import os
from PIL import Image
from flask import url_for,current_app

def add_product_pic(pic_upload,product_name):

    filename = pic_upload.filename

    ext_type = filename.split('.')[-1]

    storage_filename = str(product_name)+'.'+ext_type

    filepath = os.path.join(current_app.root_path,'static\profile_pics',storage_filename)

    output_size = (200,200)

    pic = Image.open(pic_upload)
    pic.thumbnail(output_size)
    pic.save(filepath)

    return storage_filename
