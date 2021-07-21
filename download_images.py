from dask.distributed import Client
import dask.bag as db
import json
import numpy as np
import pandas as pd
import s3fs
from PIL import Image
#	import all the necessary modules 

def extract_ids(record):
    """Take a single NMNH Botany metadata record, and pulls out ids

    Parameters
    ----------
    record : dict
        A single NMNH Botany metadata record in highly-nested dictionary format.

    Returns
    -------
    flattened_record: dict
        An un-nested dictionary that only contains the record id, unit code,
        object title, media_count, media_id, topic list, object type, and
        object medium.
    """
    flattened_record = dict()
    flattened_record['edan_id'] = record['id']
    flattened_record['title'] = record['title']
    
    flattened_record['Barcode'] = np.nan
    
    flattened_record['specimen_guid'] = record['content'].get('descriptiveNonRepeating', {}).get('guid',np.nan)
    
    media_count = record['content'].get('descriptiveNonRepeating', {}).get('online_media',{}).get('mediaCount',np.nan)
    flattened_record['media_count'] = float(media_count)
    media = record['content'].get('descriptiveNonRepeating', {}).get('online_media',{}).get('media',[])   
    if len(media):
        flattened_record['media_guid'] = media[0]['guid']
        if 'resources' in media[0]:
            for media_record in media[0]['resources']:
                if 'JPEG' in media_record['label']:
                    flattened_record['ids_id'] = media_record['url'].split('=')[1].split('.')[0]
    if 'freetext' in record['content']:
        if 'identifier' in record['content']['freetext']:
            for identifier in record['content']['freetext']['identifier']:
                id_type = identifier['label']
                id_number = identifier['content']
                flattened_record[id_type] = id_number
          
    return flattened_record

def download_thumbnail(edan_id, metadata_ids):
	"""
    Opens a full-size image from S3, compresses it to thumbnail, and writes 
    it to disk. Harcoded for NMNH Botany images, and to save to thumbnails directory.

    Parameters
    ----------
    edan_id : string
        The Smithsonian Enterprise Digital Asset Network (EDAN) ID of the object
        to download.

    metadata_ids : list of strings
    	List of ids from metadata to check against. NMNH includes more that just
    	botany images so this check makes sure to only get botany images.

    """
	if edan_id in metadata_ids[0:1]:
		thumb_size = (500, 500)
		s3_url = f'smithsonian-open-access/media/nmnh/{edan_id}.jpg'
		file_dest = f'/home/ashlynpowell/SI_project/thumbnails/{edan_id}.jpg' 
		with fs.open(s3_url,'rb') as s3_image:
			pil_image = Image.open(s3_image)
			pil_image.thumbnail(thumb_size)
			pil_image.save(file_dest)
	return

def get_media_list(media_info_file):
	"""
	Extracts a list of media_ids from media_list.txt

	Parameters
    ----------
    media_info_file : string
        A text file that contains list of NMNH media information. 
        File is located in the GitHub repository, as well as 
        information about how it was obtained.

    Returns
    -------
    media_ids : list of strings
    	List of ids for media, pulled from the text file, that will be 
    	used for downloading later.

	"""

	media_ids = []
	with open(media_info_file, 'r') as media_info:
		for line in media_info:
			line = line.strip('\n')
			if line.endswith('.jpg'):
				media_id = line.split(' ')[-1][0:-4]
				media_ids.append(media_id)
	return media_ids


if __name__ == '__main__':
	
	#	Set up s3fs object and list the top-level “directories” in the “smithsonian-
	#	open-access” S3 bucket. The bucket is split between metadata files and media files.
	fs = s3fs.S3FileSystem(anon=True)
	s3_bucket = fs.ls('smithsonian-open-access')

	#	Using the NMNH Botany unitcode, list metadata files.
	#	Metadata is stored in .txt files in JSONL format.
	metadata = fs.ls('smithsonian-open-access/metadata/edan/nmnhbotany')

	#	Set up a Dask “client” that will distribute processing across multiple workers
	client = Client(threads_per_worker=4, n_workers=1)

	#	Create a Dask “bag” to process all .txt files in the NMNH Botany metadata directory.
	metadata_s3 = [f's3://{path}' for path in metadata if 'index.txt' not in path]
	b = db.read_text(metadata_s3,storage_options={'anon': True}).map(json.loads)

	#	Get simplified metadata using extract_ids function, convert to pandas
	#	dataframe and write to metadata.tsv 
	metadata_json = b.map(extract_ids).compute()
	metadata_df = pd.DataFrame(metadata_json)
	metadata_df.to_csv('metadata.tsv', index=False, sep='\t')

	#	Pull out just the "ids_id" column into a list for download_thumbnail function
	metadata_ids = metadata_df['ids_id'].to_list()

	#	Call get_media_list function to get media ids for downloading
	media_ids = get_media_list('media_list.txt')

	#	Loop through the media_ids, print the id followed by it's index 
	#	Then call download_thumbnail function 
	#	Split into smaller batches to download faster
	for media_id in media_ids:
		print(media_id + " id # " + str(media_ids.index(media_id)))
		download_thumbnail(media_id, metadata_ids)

	#	Could use dask client instead of loop, probably goes faster, commands below
	#start = time.time()
	#futures = client.map(download_thumbnail, media_ids)
	#results = client.gather(futures)
	#end = time.time()
	#print(end - start)

	#	There are 2805190 media_ids (all nmnh)
	#	There are 4199032 metadata_ids (all nmnhbotany, not all have media)
	#	media_ids are queried against metadata_ids to ensure we are getting botany
	#	A total of 2292004 images downloaded with this script
	#	If a single specimen has multiple images, this script only gets one image
	#	Need to check the notebooks from Mike to download the "multimedia" images