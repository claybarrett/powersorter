"""
based of ps.py
Unzips any zips
Then allows the -subset for processing.
Basically just calls powersorter and url_gen.
"""
import sys
from zipfile import ZipFile
import powersorter
#import url_genRF1 as url_gen
from url_gen import generate_url_records_suffixes
import shutil
from pathlib import Path
import os
import glob
import csv

def scan_for_archives(dir):
    '''
    Scans a dir for registered archive file extensions
    Registered means Zip or anything shutil can unzip.
    '''
    result = []

    other_exts = [i[1] for i in shutil.get_unpack_formats()]
    ext_patterns = ['*' + i for g in other_exts for i in g]
    # print(ext_patterns)
    try:
        folders = [f for f in Path(dir).iterdir()]
        archives = [f for f in Path(dir).iterdir() if any(f.match(p) for p in ext_patterns)]
        print(f'found', len(archives), 'archives to unpack out of', len(folders), 'total folders')
        result = archives
    except:
        print(dir, 'not a valid path')

    return result


def unpack_archives(archive_paths, delete_archive=True):
    '''
    Accepts a list of folder(s) (paths?). Replaces them with unzipped folder of the same name.
    Zips it tests for corruptions then only extracts the JPG and DNG file extensions found.
    Other archive types are handled by shutil.
    '''
    result = []

    for arc in archive_paths:
        # default location is cwd, instead parse name and path out to create new folder
        loc = arc.parent
        name = arc.stem
        # ext = arc.suffixes
        new_folder = os.path.join(loc, name)

        try:
            # if zip, just unpack JPG/DNG using ZipFile
            if arc.suffix.lower() == '.zip':
                with ZipFile(arc, 'r') as zip_object:
                    # test the archive first to see if it's corrupt
                    ret = zip_object.testzip()
                    if ret is not None:
                        print(f'First bad file in zip:', ret)
                    else:
                        print(f'Zip archive', arc, 'is good.')

                    list_names = zip_object.namelist()
                    for file_name in list_names:
                        if file_name.lower().endswith(tuple(['.jpg', '.jpeg', '.dng'])):
                            # Extract any file with these exts from zip
                            zip_object.extract(file_name, arc.parent)
                            # if verbose:
                            #   print(f'Extracting', file_name)
            # otherwise, fallback to shutil
            else:
                # 3.6 this can't handle path objects
                shutil.unpack_archive(str(arc), arc.parent)
            result.append(new_folder)
            # print('unpacked', new_folder)

            # remove the archive if everything worked
            if delete_archive:
                os.remove(arc)
        except ValueError:
            print(arc.stuffix, 'was not valid unpack archive type:', shutil.get_unpack_formats())
        except:
            print(f"Unexpected error:", sys.exc_info()[0])
            # print("Unexpected error:")
            raise

    return result

def main():
    # set up argparse and get arguments
    args = powersorter.arg_setup()

    config_file = args['config']
    dry_run = args['dry_run']
    verbose = args['verbose']
    force_overwrite = args['force']
    input_path_override = args['input_path']
    subset = args['subset']

    #Confirm force overwrite
    force_overwrite_confirmed = False
    if force_overwrite:
        print('Files with identical names will be overwritten if you proceed.')
        response = input('Type \'overwrite\' and [RETURN/ENTER] to confirm desire to overwrite files: ')
        if response == 'overwrite':
            print('Will overwrite duplicate file names...')
            force_overwrite_confirmed = True
        else:
            print('Overwrite not confirmed. Exiting...')
            force_overwrite_confirmed = False
            sys.exit()

    #Initialize settings with arg parameters
    settings = powersorter.Settings(dry_run=dry_run, verbose=verbose, force_overwrite=force_overwrite_confirmed)
    #Load settings from config file
    settings.load_config(config_file=config_file)

    # input_path setting in config file can be overridden using value passed in args input_path_override
    # getting path from settings isn't necessary, just here for illustration
    # if input_path isn't passed to sort, it will use settings.input_path by default
    input_path = settings.input_path
    #print(f's.inp', settings.input_path, type(settings.input_path))
    # verify path exists before starting
    #print(f'inp', input_path, type(input_path))
    try:
        os.path.isdir(input_path)
    except:
        print(f'Input_path was not valid.')

    # scan for archives
    archives = scan_for_archives(input_path)
    #print(f'archives found:', archives)
    # if any archives, unpack them
    if archives:
        unpacked = unpack_archives(archives)  # , delete_archive=False
        print(f'unpacked archives :', unpacked)

    # subset based on parent folders, if flag says to
    if subset:
        print(f'Starting SUBSET process')
        # using chdir shortens the path glob returns to be SORTFOLDER/img.jpg
        orig_dir = os.getcwd()
        os.chdir(input_path)

        # this strongly supposes the files structure is /INPUT/sortable/jpg
        # would be better to iterate on path/to/sortable?
        parents = set([f.rpartition('/')[0] for f_ in [glob.glob(e) for e in ('*/*.jpg', '*/*.jpeg')] for f in f_])
        print(f'subsetting on:', parents)
        # return chdir
        os.chdir(orig_dir)

        # iterate on input+parent paths and call sort, url_gen
        for p in parents:
            subset_path = os.path.join(input_path, p)

            print(f'sorting subfolder', subset_path)
            sort_results = powersorter.sort(
                settings_obj=settings, \
                input_path=subset_path, #only diff is here \
                number_pad=settings.number_pad, \
                folder_increment=settings.folder_increment, \
                catalog_number_regex=settings.catalog_number_regex, \
                collection_prefix=settings.collection_prefix, \
                file_types=settings.file_types, \
                destination_base_path=settings.output_base_path)
            print(f'sorted_file_count', sort_results['sorted_file_count'])
            print(f'unmoved_file_count', sort_results['unmoved_file_count'])
            print(f'Log file written to:', sort_results['log_file_path'])
            print(f'Starting URL_GEN for the log file.')

            occurrence_set = generate_url_records_suffixes(settings=settings, input_file=sort_results['log_file_path'])
            # print(occurrence_set)
            # Get input file name
            #input_file_name_stem = Path(input_file).stem
            input_file_name_stem = Path(sort_results['log_file_path']).stem
            output_file_name = input_file_name_stem + '_urls.csv'
            print(f'Writing urls to:', output_file_name)

            with open(output_file_name, 'w', newline='') as csvfile:
                fieldnames = ['catalog_number', 'large', 'web', 'thumbnail']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for key, image_set in occurrence_set.items():
                    writer.writerow(image_set)
    else:
    # sort once
        print('STARTING sort')
        sort_results = powersorter.sort(
            settings_obj=settings, \
            input_path=input_path, \
            number_pad=settings.number_pad, \
            folder_increment=settings.folder_increment, \
            catalog_number_regex=settings.catalog_number_regex,\
            collection_prefix=settings.collection_prefix, \
            file_types=settings.file_types, \
            destination_base_path=settings.output_base_path)
        print(f'sort res', sort_results)

        occurrence_set = generate_url_records_suffixes(settings=settings, input_file=sort_results['log_file_path'])
        # print(occurrence_set)
        # Get input file name
        # input_file_name_stem = Path(input_file).stem
        input_file_name_stem = Path(sort_results['log_file_path']).stem
        output_file_name = input_file_name_stem + '_urls.csv'
        print(f'Writing urls to:', output_file_name)

        with open(output_file_name, 'w', newline='') as csvfile:
            fieldnames = ['catalog_number', 'large', 'web', 'thumbnail']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for key, image_set in occurrence_set.items():
                writer.writerow(image_set)

    # Summary report
    if verbose:
        print(f'sorted_file_count', sort_results['sorted_file_count'])
        print(f'unmoved_file_count', sort_results['unmoved_file_count'])
    print(f'Log file written to:', sort_results['log_file_path'])
    print(f'Process COMPLETE')

if __name__ == '__main__':
    main()