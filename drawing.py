#!/bin/python3

import argparse
import os.path
import logging
import os
import tempfile

from PIL import Image
import PIL.ImageDraw
from boto3.dynamodb.conditions import Key
from boto3 import resource

def get_drawing(img_path):
    """
    From the source image, get the drawing in the format we want and a list of regions for coloring.
    
    img_path: Full or relative path to alpha-transparent image
    """
    
    pil_im = Image.open(img_path)
    (r,g,b,a) = pil_im.split()
    
    # Take 100% opaque regions and color them white, everything else grey
    d = a.point(lambda x: 100 if x < 255 else 0)
    drawing_img = Image.merge('RGB', (d,d,d))
    
    regions = []

    # THis is quite side-effecty. Fill in drawing_img as we go, adding regions.
    for x in range(drawing_img.width):
        for y in range(drawing_img.height):
            c = drawing_img.getpixel((x,y))
            if c == (100,100,100):
                PIL.ImageDraw.floodfill(drawing_img, (x,y), (255,255,255))
                regions.append((x,y))
                
    return (drawing_img, regions)

def fetch_regions(image_name, table_name):
    """
    Fetch the color/region mappings for this image. Return entire DynamoDb response.

    image_name: Image name i.e. "test1.png"
    """

    dynamodb_resource = resource('dynamodb')
    table = dynamodb_resource.Table(table_name)
    response = table.query(KeyConditionExpression=Key('ImageName').eq(image_name))
    
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception("Non-200 response from DynamoDB")
        
    return response

def fill_regions(drawing, regions, items):
    """
    For pre-formatted drawing (drawing, regions), and for dbd response items,
    flood-fill all regions with given colors.

    drawing: RGB drawing with contiguous (probably (255,255,255)) blanks connected to each region
    regions: Iterable of region coordinates
    items: DBD response, items["Items"][x] should map to item with item["Color"] and item["Region"]
    """
    
    for item in items:
        try:
            region = int(item['Region'])
            if region < len(regions) and region >= 0:
                (rs, gs, bs) = item['Color'].split(',')
                color = (int(rs), int(gs), int(bs))
                PIL.ImageDraw.floodfill(drawing, regions[region], color)
        except Exception as e:
            logging.debug("Exception filling region %d: %s" % (region, str(e)))
            
def build_colored_drawing(image_folder, image_name, table_name):
    """
    For storage folder and image name, color image according to colorings
    in database.
    """
    
    image_path = os.path.join(image_folder, image_name)
    
    (drawing, regions) = get_drawing(image_path)
    
    coloring = fetch_regions(image_name, table_name)
    
    fill_regions(drawing, regions, coloring['Items'])
    
    fg = Image.open(image_path)
    
    (bg_r, bg_g, bg_b) = drawing.split()
    # Should just start with alpha layer... too lazy.
    bg = Image.merge('RGBA', (bg_r, bg_g, bg_b, Image.new('L', drawing.size, color=255)))
    
    bg.paste(fg, (0,0), fg)
    
    return bg

def get_image(imagename, in_bucket_name, out_bucket_name, table_name):
    """
    For an image name, grab it from the source bucket, color it with
    stored region colorings and move it to the destination bucket.
    """
    
    tmp = tempfile.mkdtemp()
    save_path = os.path.join(tmp, 'out-' + imagename)
    
    s3 = resource('s3')
    
    # Now we have i.e. test1.png in tmp/test1.png
    s3.Bucket(in_bucket_name).download_file(imagename, os.path.join(tmp, imagename))
    
    # Colored is a PIL image that is the colored version of 
    colored = build_colored_drawing(tmp, imagename, table_name)

    colored.save(save_path)
    s3.Bucket(out_bucket_name).upload_file(save_path, imagename)

def get_image_name(table_name):
    """
    Read latest image name from channel 'metadata'
    """
    
    dynamodb_resource = resource('dynamodb')
    table = dynamodb_resource.Table(table_name)

    response = table.get_item(Key={'ImageName': '__CONTROL', 'Region': -1})
    item = response['Item']

    return item['CurrentImageName']
    

def handler(event, context):
    try:
        FORMAT = '%(asctime)-15s %(levelname)s %(funcName)s %(message)s'
        logging.basicConfig(format=FORMAT, level=logging.ERROR)
        
        table_name = os.environ['TABLE_NAME']
        in_bucket_name = os.environ['IN_BUCKET_NAME']
        out_bucket_name = os.environ['OUT_BUCKET_NAME']

        image_name = get_image_name(table_name)
        get_image(image_name, args.in_bucket_name, args.out_bucket_name, args.table_name)
    except Exception as e:
        logging.error(str(e))
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Do a one-time run applying stored colors to current channel image")
    parser.add_argument("in_bucket_name", type=str, help="Name of in bucket")
    parser.add_argument("out_bucket_name", type=str, help="Name of out bucket")
    parser.add_argument("table_name", type=str, help="Name of DynamoDB bucket")

    FORMAT = '%(asctime)-15s %(levelname)s %(funcName)s %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)

    args = parser.parse_args()

    # Let any exceptions bubble.
    image_name = get_image_name(args.table_name)
    get_image(image_name, args.in_bucket_name, args.out_bucket_name, args.table_name)
