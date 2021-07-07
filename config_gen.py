import json
"""
Generates an example JSON format for the configuration file
used by various scripts for sorting, URL generation, etc
in TORCH and BRIT image workflows.
Prints JSON text to screen. Pipe text to file to create cofig file.
"""

# boilerplate
config = {}
versions = config['versions'] = {}
versions['config_format'] = '3.0'
#versions['sort'] = '2.0'
collection = config['collection'] = {}
collection['name'] = 'TEST'
collection['prefix'] = 'TEST'
collection['catalog_number_regex'] = r'(?P<catNum>(?P<instID>BRIT)(-(?P<collID>L)-)*(?P<numerical>\d+))'
collection['web_base'] = '/corral-repl/projects/TORCH/web/TEST/'
collection['url_base'] = 'https://web.corral.tacc.utexas.edu/torch/'
files = config['files'] = {}
files['folder_increment'] = 1000
files['number_pad'] = 7
files['log_directory_path'] = '/corral-repl/projects/TORCH/archive/TEST/logs/'
files['output_base_path'] = '/corral-repl/projects/TORCH/ready_to_sort/'
files['input_path'] = '/corral-repl/projects/TORCH/staging/TEST'

# file_types
file_types = config['file_types'] = {}
# TODO create a pattern class to generate each pattern
# TODO use regex to test compile the pattern, maybe to test?
# NB - file_types key names are used by urlgen.py to determine which files have a URL generated.
web_jpg = file_types['web_jpg'] = {}
web_jpg['file_regex'] = r'(_(?P<suffix>.+))*(\.)(?i)(?P<ext>jpg|jpeg)'
web_jpg['output_sub_path'] = 'web/TEST/'

# TORCH config version 1.0
"""
web_derivs = file_types['web_derivs'] = {}
web_derivs['regex'] = r'(?P<prefix>BRIT)(?P<numerical>\d+)(?P<delimiter>_)(?P<size>med|thumb)(\.)(?P<ext>.+)'
web_derivs['output_sub_path'] = 'test/web/BRIT/'
"""
# TORCH config version 2.0 and 3.0
# replaces web_jpg with web_jpg_med and web_jpg_thumb
# TORCH config version 3.0 changes regex to file_regex. Full regex pattern is catalog_number_regex + file_regex
web_jpg_med = file_types['web_jpg_med'] = {}
web_jpg_med['file_regex'] = r'(_(?P<suffix>.+))*(_)(?P<size>med)(\.)(?i)(?P<ext>jpg|jpeg)'
web_jpg_med['output_sub_path'] = 'web/TEST/'

web_jpg_thumb = file_types['web_jpg_thumb'] = {}
web_jpg_thumb['file_regex'] = r'(_(?P<suffix>.+))*(_)(?P<size>thumb)(\.)(?i)(?P<ext>jpg|jpeg)'
web_jpg_thumb['output_sub_path'] = 'web/TEST/'

archive_dng = file_types['archive_dng'] = {}
archive_dng['file_regex'] = r'(_(?P<suffix>.+))*(\.)(?i)(?P<ext>dng)'
archive_dng['output_sub_path'] = 'archive/TEST/'

ocr = file_types['ocr'] = {}
ocr['file_regex'] = r'(_(?P<suffix>.+))*(_ocr)(\.)(?i)(?P<ext>txt|json)'
ocr['output_sub_path'] = 'web/TEST/'

print(json.dumps(config, indent=4))
