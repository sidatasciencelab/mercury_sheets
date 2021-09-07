import pandas as pd
import numpy as np
import requests
from PIL import Image
from io import BytesIO
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import argparse

def ids_ark_thumbnail(ids_url):
    start_epoch = time.time()
    thumb_size = 500
    ark_id = ids_url.split('/')[-1]
    ids_url = f'https://ids.si.edu/ids/deliveryService/id/ark:/65665/{ark_id}/500'
    file_dest = f'thumbnails/{ark_id}.jpg'
    try:
        response = requests.get(ids_url)
        pil_image = Image.open(BytesIO(response.content))
        width, height = pil_image.size
        pil_image.save(file_dest)
    except:
        width, height = np.nan, np.nan
        pass
    end_epoch = time.time()
    return_dict = {'start_time':start_epoch,
                'end_time':end_epoch,
                'dl_time':end_epoch - start_epoch,
                'width':width,
                'height':height,
                'ark_id':ark_id}  
    return return_dict

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--processes",
                    help="number of processes")
    args = ap.parse_args()

    df = pd.read_csv('mercury_specimen_data.tsv', sep='\t')

    ids_sample = df['accessURI'].to_list()

    start_time = time.perf_counter()

    with ProcessPoolExecutor(max_workers=int(args.processes)) as executor:
        results = list(executor.map(ids_ark_thumbnail, ids_sample))

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Downloaded {len(results)} images in {elapsed_time} s")

    ids_df = pd.DataFrame(results)
    filename = f'ids_benchmark_{args.processes}.tsv'
    ids_df.to_csv(filename, index=False, sep='\t')
