# Mercury sheets

`Pulling barcodes from FigShare.ipynb` is a notebook that shows how to download the image sets from FigShare, and extract the barcodes, which are then saved in `barcodes_from_figshare.tsv`. 

`Checking Botany scan dates` is a notebook that has a processing function for Dask that pulls out multiple image ids for records that have multiple images.
 
`media_list.txt` contains a list of aws media ids which are used in the `download_images.py` script. The file was created using the command `aws s3 ls s3://smithsonian-open-access/media/nmnh/ > media_list.txt`. To reduce the size of the file, the version in this repository was filtered to only include the ids that end with `.jpg` .

` download_images.py` is a script that downloads botany images and metadata using SI Open Access on AWS. The metadata from AWS is simplified using the `extract_ids` function in the script and saved to `metadata.tsv`. The media ids from `media_list.txt` are used to download 2292004 images to a `thumbnails` directory. Further explaination of steps are commented in the script. 